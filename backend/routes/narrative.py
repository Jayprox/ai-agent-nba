# backend/routes/narrative.py
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

# --- Internal imports ---
from agents.trends_agent.fetch_trends import get_trends_summary
from agents.odds_agent.models import OddsResponse
from common.odds_utils import fetch_moneyline_odds
from services.openai_service import generate_narrative_summary

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])

# -------------------------
# Config / Cache
# -------------------------
_CACHE: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
_MAX_CACHE_TTL = 120
_PROMPT_VERSION = "v3.5-async"


# -------------------------
# Utility Helpers
# -------------------------
def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _cap_ttl(ttl: int) -> int:
    return max(0, min(ttl, _MAX_CACHE_TTL))


def _sha1_digest(obj: Any) -> str:
    """Deterministic digest of key inputs for smart invalidation."""
    try:
        pruned = {
            "date_generated": obj.get("date_generated"),
            "player_trends": obj.get("player_trends", []),
            "team_trends": obj.get("team_trends", []),
            "player_props": obj.get("player_props", []),
            "odds_len": len((obj.get("odds") or {}).get("games", [])),
        }
    except Exception:
        pruned = {"raw_len": len(str(obj))}
    data = json.dumps(pruned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha1:" + hashlib.sha1(data).hexdigest()


# -------------------------
# Markdown Renderer
# -------------------------
def _render_markdown(summary: Dict[str, Any], compact: bool = False) -> str:
    # Safely extract metadata
    meta = summary.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}

    gen_at = meta.get("generated_at", "")
    model = meta.get("model", "")

    # Safely extract summary components
    macro = summary.get("macro_summary")
    micro = summary.get("micro_summary", {})
    if not isinstance(micro, dict):
        micro = {}

    edges = micro.get("key_edges", []) or []
    if not isinstance(edges, list):
        edges = []

    risk = micro.get("risk_score")
    analyst = summary.get("analyst_takeaway")
    plain = summary.get("summary")

    lines = [f"**NBA Narrative**  \n_Generated: {gen_at} • Model: {model}_"]

    if macro:
        macro_text = "\n\n".join(macro) if isinstance(macro, list) else str(macro)
        lines.append("\n### Macro Summary")
        lines.append(macro_text.strip())

    if edges and not compact:
        lines.append("\n### Key Edges")
        for e in edges:
            # Safely handle edges that might be strings or dicts
            if isinstance(e, dict):
                lbl = e.get("value_label", "")
                score = e.get("edge_score", "")
                t = e.get("text", "")
                lines.append(f"- **{lbl}** (score: {score}): {t}")
            elif isinstance(e, str):
                lines.append(f"- {e}")
            else:
                lines.append(f"- {str(e)}")

    if risk is not None and not compact:
        lines.append(f"\n**Risk Score:** {risk}")

    if analyst:
        lines.append("\n### Analyst Takeaway")
        lines.append(str(analyst).strip())

    if not macro and plain:
        lines.append("\n### Summary")
        lines.append(str(plain).strip())

    return "\n".join(lines).strip() if not compact else " ".join(lines)[:1000]


# -------------------------
# Async Fetch Helpers
# -------------------------
async def _safe_call(label: str, func, *args, **kwargs):
    """Run a function safely and catch errors for meta logging."""
    try:
        result = await asyncio.to_thread(func, *args, **kwargs)
        return result, None
    except Exception as e:
        return None, f"{label}: {type(e).__name__}: {e}"


# -------------------------
# Core /today Endpoint
# -------------------------
@router.get("/today")
async def get_daily_narrative(
    mode: str = Query("template", description="template or ai"),
    cache_ttl: int = Query(0, description="seconds to cache (max 120s)"),
    format: Optional[str] = Query(None, description="Set to 'markdown' to include Markdown field"),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    ttl = _cap_ttl(cache_ttl)
    cache_key = (mode, ttl, "today")

    cached = _CACHE.get(cache_key)
    if cached and cached["expires_at"] > time.time():
        payload = dict(cached["payload"])
        payload["raw"]["meta"]["latency_ms"] = 0.0
        payload["raw"]["meta"]["cache_used"] = True
        return payload

    # --- Parallel data fetches (trends + odds only for now) ---
    trends_task = _safe_call("trends", get_trends_summary)
    odds_task = _safe_call("odds", fetch_moneyline_odds)

    trends, odds = await asyncio.gather(trends_task, odds_task)
    soft_errors: Dict[str, str] = {}

    # --- Unpack safely ---
    trends_data, trends_err = trends
    odds_data, odds_err = odds

    if trends_err:
        soft_errors["trends"] = trends_err
    if odds_err:
        soft_errors["odds"] = odds_err

    # Explicitly mark player props as backlogged / disabled for now
    soft_errors["player_props"] = "Live player props integration temporarily disabled (backlog)."

    team_trends, player_trends = [], []
    if trends_data:
        team_trends, player_trends = trends_data.team_trends, trends_data.player_trends

    narrative_data = {
        "date_generated": _now_utc_str(),
        "player_trends": [p.model_dump() for p in player_trends],
        "team_trends": [t.model_dump() for t in team_trends],
        # 👇 Backlogged: no live player props yet
        "player_props": [],
        "odds": odds_data.model_dump() if isinstance(odds_data, OddsResponse) else odds_data,
    }

    # --- Generate Narrative ---
    summary = generate_narrative_summary(narrative_data, mode=mode)
    if not isinstance(summary, dict):
        summary = {"summary": str(summary), "metadata": {}}

    # Safely handle metadata
    metadata = summary.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    metadata.update({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": metadata.get("model", "template" if mode != "ai" else "gpt-4o"),
        "prompt_version": _PROMPT_VERSION,
        "inputs_digest": _sha1_digest(narrative_data),
    })
    summary["metadata"] = metadata

    # --- Construct Final Response ---
    resp: Dict[str, Any] = {
        "ok": True,
        "summary": summary,
        "raw": {
            **narrative_data,
            "meta": {
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "source_counts": {
                    "player_trends": len(narrative_data.get("player_trends", [])),
                    "team_trends": len(narrative_data.get("team_trends", [])),
                    "player_props": len(narrative_data.get("player_props", [])),
                    "odds_games": len((narrative_data.get("odds") or {}).get("games", [])),
                },
                "cache_used": False,
                "cache_ttl_s": ttl,
                "soft_errors": soft_errors,
                "mode": mode,
            },
        },
        "mode": mode,
    }

    fmt_str = str(format).lower() if format is not None else ""
    if fmt_str == "markdown":
        resp["markdown"] = _render_markdown(summary)

    if ttl > 0:
        _CACHE[cache_key] = {"expires_at": time.time() + ttl, "payload": resp}

    return resp


# -------------------------
# Markdown Endpoint
# -------------------------
@router.get("/markdown")
async def get_markdown_narrative(
    mode: str = Query("template", description="template or ai"),
    cache_ttl: int = Query(0, description="seconds to cache (max 120s)"),
    compact: bool = Query(False, description="Return a compact Markdown form"),
) -> Dict[str, Any]:
    try:
        data = await get_daily_narrative(mode=mode, cache_ttl=cache_ttl)
        summary = data.get("summary", {}) or {}

        # ✅ Ensure summary is a dict (not string fallback)
        if not isinstance(summary, dict):
            summary = {"summary": str(summary), "metadata": {}}

        markdown = _render_markdown(summary, compact=compact)

        data["markdown"] = markdown
        data["summary"]["metadata"]["prompt_version"] = _PROMPT_VERSION
        return data
    except Exception as e:
        err_text = f"Markdown generation failed: {type(e).__name__}: {e}"
        return {
            "ok": False,
            "error": err_text,
            "markdown": f"**NBA Narrative (Error Fallback)**\n\n{err_text}",
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "prompt_version": _PROMPT_VERSION,
            },
        }
