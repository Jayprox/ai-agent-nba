# backend/routes/narrative.py
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from agents.trends_agent.fetch_trends import get_trends_summary
from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats
from common.odds_utils import fetch_moneyline_odds
from agents.odds_agent.models import OddsResponse
from services.openai_service import generate_narrative_summary

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])

# ---------------------------------------------------------------------------
# Cache & Throttle Controls
# ---------------------------------------------------------------------------
_CACHE: Dict[Tuple[str, int], Dict[str, Any]] = {}
_LAST_CALL: Dict[str, float] = {}
_THROTTLE_SECONDS = 3
_MAX_CACHE_TTL = 120
_PROMPT_VERSION = "v2-async"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _cap_ttl(ttl: int) -> int:
    if ttl < 0:
        return 0
    return min(ttl, _MAX_CACHE_TTL)


def _sha1_digest(obj: Any) -> str:
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
    data = json.dumps(pruned, sort_keys=True, separators=(",", ":")).encode()
    return "sha1:" + hashlib.sha1(data).hexdigest()


def _to_markdown(summary: Dict[str, Any]) -> str:
    meta = summary.get("metadata", {})
    gen_at = meta.get("generated_at", "")
    model = meta.get("model", "")
    macro = summary.get("macro_summary")
    micro = summary.get("micro_summary", {})
    edges = micro.get("key_edges", []) or []
    risk = micro.get("risk_score")
    analyst = summary.get("analyst_takeaway")
    text = summary.get("summary")

    lines = [f"**NBA Narrative**  \n_Generated: {gen_at} • Model: {model}_"]

    if macro:
        lines.append("\n### Macro Summary")
        if isinstance(macro, list):
            lines.extend(macro)
        else:
            lines.append(str(macro))

    if edges:
        lines.append("\n### Key Edges")
        for e in edges:
            lbl = e.get("value_label", "")
            score = e.get("edge_score", "")
            t = e.get("text", "")
            lines.append(f"- **{lbl}** (score: {score}): {t}")

    if risk is not None:
        lines.append(f"\n**Risk Score:** {risk}")

    if analyst:
        lines.append("\n### Analyst Takeaway")
        lines.append(str(analyst))

    if not macro and text:
        lines.append("\n### Summary")
        lines.append(text.strip())

    return "\n".join(lines).strip()


async def _fetch_trends_safe() -> Tuple[list, list, dict]:
    try:
        trends = await asyncio.to_thread(get_trends_summary)
        return trends.player_trends, trends.team_trends, {}
    except Exception as e:
        return [], [], {"trends": f"{type(e).__name__}: {e}"}


async def _fetch_props_safe() -> Tuple[list, dict]:
    try:
        props = await asyncio.to_thread(fetch_player_stats, 134)
        if isinstance(props, dict):
            return props.get("data", []), {}
        return [], {}
    except Exception as e:
        return [], {"props": f"{type(e).__name__}: {e}"}


async def _fetch_odds_safe() -> Tuple[dict, dict]:
    try:
        odds = await asyncio.to_thread(fetch_moneyline_odds)
        return (
            odds.model_dump() if isinstance(odds, OddsResponse) else odds,
            {},
        )
    except Exception as e:
        return {"games": []}, {"odds": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@router.get("/today")
async def get_daily_narrative(
    mode: str = Query("template", description="template or ai"),
    cache_ttl: int = Query(0, description="seconds to cache the response (server caps at 120s)"),
    format: Optional[str] = Query(None, description="Set to 'markdown' to include a rendered markdown field"),
) -> Dict[str, Any]:
    """Generate the daily NBA narrative summary asynchronously with throttling."""
    t0 = time.perf_counter()
    ttl = _cap_ttl(cache_ttl)
    cache_key = (mode, ttl)

    # --- Throttle (1 request / 3s per mode)
    now = time.time()
    last_call = _LAST_CALL.get(mode, 0)
    if now - last_call < _THROTTLE_SECONDS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests for mode '{mode}'. Try again in {round(_THROTTLE_SECONDS - (now - last_call), 1)}s.",
        )
    _LAST_CALL[mode] = now

    # --- Cache check
    cached = _CACHE.get(cache_key)
    if cached and cached["expires_at"] > now:
        payload = dict(cached["payload"])
        payload["raw"]["meta"]["latency_ms"] = 0.0
        payload["raw"]["meta"]["cache_used"] = True
        return payload

    # --- Async gather for data
    player_trends, team_trends, err_trends = await _fetch_trends_safe()
    props, err_props = await _fetch_props_safe()
    odds, err_odds = await _fetch_odds_safe()
    soft_errors = {**err_trends, **err_props, **err_odds}

    narrative_data = {
        "date_generated": _now_utc_str(),
        "player_trends": [p.model_dump() for p in player_trends],
        "team_trends": [t.model_dump() for t in team_trends],
        "player_props": props,
        "odds": odds,
    }

    # --- Generate narrative (AI or template)
    summary = await asyncio.to_thread(generate_narrative_summary, narrative_data, mode)

    metadata = summary.get("metadata", {}) if isinstance(summary, dict) else {}
    metadata.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    metadata.setdefault("model", "template" if mode != "ai" else "gpt-4o")
    metadata["prompt_version"] = _PROMPT_VERSION
    metadata["inputs_digest"] = _sha1_digest(narrative_data)
    summary["metadata"] = metadata

    resp = {
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

    if (format or "").lower() == "markdown":
        resp["markdown"] = _to_markdown(summary)

    if ttl > 0:
        _CACHE[cache_key] = {"expires_at": now + ttl, "payload": resp}

    return resp
