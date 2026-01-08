# backend/routes/narrative.py

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Query

# --- Internal imports ---
from agents.odds_agent.models import OddsResponse
from common.odds_utils import fetch_moneyline_odds
from services.api_basketball_service import get_today_games
from services.openai_service import generate_narrative_summary

# Optional: trends agent (may be unavailable)
try:
    from agents.trends_agent.fetch_trends import get_trends_summary  # type: ignore
except Exception:
    get_trends_summary = None  # type: ignore

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])

# -------------------------
# Config / Cache
# -------------------------
_CACHE: Dict[str, Dict[str, Any]] = {}
_INFLIGHT_LOCKS: Dict[str, asyncio.Lock] = {}
_MAX_CACHE_TTL = 120
_PROMPT_VERSION = "v3.8-cache-observability"
_ENV_ENABLE_TRENDS = os.getenv("ENABLE_TRENDS_IN_NARRATIVE", "0") == "1"


# -------------------------
# Utility Helpers
# -------------------------
def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cap_ttl(ttl: int) -> int:
    return max(0, min(ttl, _MAX_CACHE_TTL))


def _sha1_digest(obj: Any) -> str:
    """
    Deterministic digest of key inputs for debugging/traceability.
    """
    try:
        games = obj.get("games_today", []) or []
        games_pruned = []
        for g in games[:30]:
            games_pruned.append(
                {
                    "id": g.get("id"),
                    "ts": g.get("timestamp"),
                    "away": (g.get("away_team") or {}).get("name"),
                    "home": (g.get("home_team") or {}).get("name"),
                    "status": (g.get("status") or {}).get("short")
                    or (g.get("status") or {}).get("long"),
                }
            )

        pruned = {
            "games_today": games_pruned,
            "player_trends_len": len(obj.get("player_trends", []) or []),
            "team_trends_len": len(obj.get("team_trends", []) or []),
            "player_props_len": len(obj.get("player_props", []) or []),
            "odds_len": len((obj.get("odds") or {}).get("games", []) or []),
        }
    except Exception:
        pruned = {"raw_len": len(str(obj))}

    data = json.dumps(pruned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha1:" + hashlib.sha1(data).hexdigest()


def _parse_trends_override(trends: Optional[int]) -> Optional[bool]:
    """
    trends query param:
      - trends=1 => True
      - trends=0 => False
      - omitted => None (use env default)
    """
    if trends is None:
        return None
    return bool(int(trends))


def _fmt_key(format_value: Optional[str]) -> str:
    """
    Normalizes format param into a stable cache key segment.
    """
    if format_value is None:
        return "none"
    v = str(format_value).strip().lower()
    return v if v else "none"


def _build_cache_key(
    *,
    mode: str,
    ttl: int,
    scope: str,
    format_value: Optional[str],
    trends_override: Optional[bool],
    effective_trends: bool,
    ai_allowed: bool,
    compact: bool = False,
) -> str:
    """
    Step 2.6 — Cache key correctness.
    Cache must be partitioned by all inputs that affect output:
      - mode (ai/template)
      - trends (effective + override)
      - format
      - ai_allowed
      - compact (for /markdown)
      - ttl (cache lifetime)
      - scope (today/markdown)
    """
    fmt = _fmt_key(format_value)
    
    # Normalize trends segment
    if trends_override is None:
        tr = f"tr:env={int(bool(effective_trends))}"
    else:
        tr = f"tr:ovr={int(bool(trends_override))}|eff={int(bool(effective_trends))}"
    
    ak = f"ai={int(bool(ai_allowed))}"
    cmp = f"cmp={int(bool(compact))}"
    
    # Deterministic string key
    return f"m={mode}|ttl={ttl}|sc={scope}|fmt={fmt}|{tr}|{ak}|{cmp}"


def _ai_allowed() -> bool:
    """
    Route-level AI gating (Step 2.4).
    Tests monkeypatch this function to simulate missing key.
    """
    if os.getenv("DISABLE_AI", "0") == "1":
        return False
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _fallback_summary(reason: str) -> Dict[str, Any]:
    """
    Route-owned fallback that does NOT depend on services.openai_service
    (important: tests may monkeypatch generate_narrative_summary to throw).
    """
    return {
        "macro_summary": [
            "NBA narrative is available in fallback mode.",
            "Detailed AI narrative is currently unavailable for this request.",
        ],
        "micro_summary": {
            "key_edges": [],
            "risk_score": 0.0,
            "risk_rationale": reason,
        },
        "analyst_takeaway": "Review the slate and odds context; retry AI mode once configuration stabilizes.",
        "confidence_summary": ["Low"],
        "metadata": {
            "model": "ROUTE_FALLBACK",
        },
    }


def _validate_or_fallback(
    *,
    candidate: Any,
    soft_errors: Dict[str, str],
    ai_used: bool,
    reason_prefix: str,
) -> Tuple[Dict[str, Any], bool]:
    """
    Ensure we always have a dict summary with required keys for the markdown renderer.
    Returns: (summary_dict, ai_used_bool)
    """
    if not isinstance(candidate, dict):
        soft_errors["ai"] = f"{reason_prefix}: AI output invalid type: {type(candidate).__name__}"
        return _fallback_summary(soft_errors["ai"]), False

    # Harden minimum structure for renderer stability
    candidate.setdefault("macro_summary", "")
    candidate.setdefault("micro_summary", {})
    if not isinstance(candidate["micro_summary"], dict):
        candidate["micro_summary"] = {}

    candidate.setdefault("analyst_takeaway", "")
    candidate.setdefault("confidence_summary", ["Medium"])
    candidate.setdefault("metadata", {})
    if not isinstance(candidate["metadata"], dict):
        candidate["metadata"] = {}

    candidate["micro_summary"].setdefault("key_edges", [])
    candidate["micro_summary"].setdefault("risk_score", 0.5)
    candidate["micro_summary"].setdefault("risk_rationale", "Narrative generated with guardrails.")

    return candidate, ai_used


# -------------------------
# Markdown Renderer
# -------------------------
def _render_markdown(summary: Dict[str, Any], compact: bool = False) -> str:
    meta = summary.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}

    gen_at = meta.get("generated_at", "")
    model = meta.get("model", "")

    macro = summary.get("macro_summary")
    micro = summary.get("micro_summary", {})
    if not isinstance(micro, dict):
        micro = {}

    edges = micro.get("key_edges", []) or []
    if not isinstance(edges, list):
        edges = []

    risk = micro.get("risk_score")
    risk_rationale = micro.get("risk_rationale")
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
            if isinstance(e, dict):
                lbl = e.get("value_label", "")
                score = e.get("edge_score", "")
                t = e.get("text", "")
                if lbl or score or t:
                    lines.append(f"- **{lbl}** (score: {score}): {t}")
                else:
                    lines.append(f"- {json.dumps(e)}")
            elif isinstance(e, str):
                lines.append(f"- {e}")
            else:
                lines.append(f"- {str(e)}")

    if risk is not None and not compact:
        if risk_rationale:
            lines.append(f"\n**Risk Score:** {risk}  \n_{risk_rationale}_")
        else:
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
    """Run a sync function safely in a thread and catch errors for meta logging."""
    try:
        result = await asyncio.to_thread(func, *args, **kwargs)
        return result, None
    except Exception as e:
        return None, f"{label}: {type(e).__name__}: {e}"


async def _safe_await(label: str, coro):
    """Run an awaitable safely and catch errors for meta logging."""
    try:
        result = await coro
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
    trends: Optional[int] = Query(
        None,
        description="Override trends in narrative: 1=on, 0=off, omit=use env default",
    ),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    ttl = _cap_ttl(cache_ttl)

    # --- Determine effective trends setting (needed for cache partition) ---
    override = _parse_trends_override(trends)
    effective_trends = _ENV_ENABLE_TRENDS if override is None else override

    # --- Determine AI gating (needed for cache partition) ---
    ai_allowed = _ai_allowed()

    # --- Step 2.6: Cache key MUST include trends + format + ai_allowed ---
    cache_key = _build_cache_key(
        mode=mode,
        ttl=ttl,
        scope="today",
        format_value=format,
        trends_override=override,
        effective_trends=bool(effective_trends),
        ai_allowed=bool(ai_allowed),
        compact=False,
    )

    # --- Step 2.6: Check cache before acquiring lock ---
    cached = _CACHE.get(cache_key)
    if cached and cached["expires_at"] > time.time():
        payload = dict(cached["payload"])
        try:
            payload.setdefault("raw", {}).setdefault("meta", {})
            meta = payload["raw"]["meta"]
            meta["latency_ms"] = 0.0
            meta["cache_used"] = True
            meta["cache_key"] = cache_key
            meta["cache_ttl_s"] = ttl
            meta["cache_expires_in_s"] = round(cached["expires_at"] - time.time(), 2)
        except Exception:
            pass
        return payload

    # --- Step 2.6: Stampede protection via inflight lock ---
    if cache_key not in _INFLIGHT_LOCKS:
        _INFLIGHT_LOCKS[cache_key] = asyncio.Lock()
    
    lock = _INFLIGHT_LOCKS[cache_key]
    
    async with lock:
        # Double-check cache after acquiring lock (another request may have populated it)
        cached = _CACHE.get(cache_key)
        if cached and cached["expires_at"] > time.time():
            payload = dict(cached["payload"])
            try:
                payload.setdefault("raw", {}).setdefault("meta", {})
                meta = payload["raw"]["meta"]
                meta["latency_ms"] = 0.0
                meta["cache_used"] = True
                meta["cache_key"] = cache_key
                meta["cache_ttl_s"] = ttl
                meta["cache_expires_in_s"] = round(cached["expires_at"] - time.time(), 2)
            except Exception:
                pass
            return payload

        # --- Parallel data fetches (games + odds, trends optional) ---
        games_task = _safe_await("games_today", get_today_games())
        odds_task = _safe_call("odds", fetch_moneyline_odds)

        trends_task = None
        trends_err: Optional[str] = None
        trends_data = None

        if effective_trends:
            if get_trends_summary is None:
                trends_err = "Trends agent unavailable (import failed)."
            else:
                trends_task = _safe_call("trends", get_trends_summary)
        else:
            trends_err = "Disabled (trends=0 override or ENABLE_TRENDS_IN_NARRATIVE=0)."

        if trends_task is not None:
            (games, odds, trends_res) = await asyncio.gather(games_task, odds_task, trends_task)
            trends_data, trends_err = trends_res
        else:
            (games, odds) = await asyncio.gather(games_task, odds_task)

        # --- Soft errors always present ---
        soft_errors: Dict[str, str] = {}

        games_today, games_err = games
        odds_data, odds_err = odds

        if games_err:
            soft_errors["games_today"] = games_err
        if odds_err:
            soft_errors["odds"] = odds_err
        if trends_err:
            soft_errors["trends"] = trends_err

        # Explicitly mark player props as backlogged / disabled for now
        soft_errors["player_props"] = "Live player props integration temporarily disabled (backlog)."

        # Trends unpacking
        team_trends, player_trends = [], []
        if trends_data:
            team_trends = getattr(trends_data, "team_trends", []) or []
            player_trends = getattr(trends_data, "player_trends", []) or []

        narrative_data = {
            "date_generated": _now_utc_str(),
            "games_today": games_today or [],
            "player_trends": [p.model_dump() for p in player_trends] if player_trends else [],
            "team_trends": [t.model_dump() for t in team_trends] if team_trends else [],
            "player_props": [],
            "odds": odds_data.model_dump() if isinstance(odds_data, OddsResponse) else odds_data,
        }

        # -------------------------
        # Step 2.4 — Validate + soft-fallback (AI gating + try/except)
        # -------------------------
        requested_mode = (mode or "template").strip().lower()
        ai_requested = requested_mode == "ai"
        ai_used = False

        summary_obj: Any = None

        if ai_requested and not ai_allowed:
            soft_errors["ai"] = "AI mode requested but not allowed (OPENAI_API_KEY missing/disabled)."
            summary_obj = _fallback_summary(soft_errors["ai"])
            ai_used = False
        else:
            try:
                # Call the generator with the requested mode.
                summary_obj = generate_narrative_summary(narrative_data, mode=requested_mode)
                ai_used = bool(ai_requested)  # only counts as used if mode=ai AND we got a usable result
            except Exception as e:
                # Soft-fallback on throw (tests require substring "AI generation threw")
                if ai_requested:
                    soft_errors["ai"] = f"AI generation threw: {type(e).__name__}: {e}"
                else:
                    soft_errors["template"] = f"Template generation threw: {type(e).__name__}: {e}"
                summary_obj = _fallback_summary(soft_errors.get("ai") or soft_errors.get("template") or "Generation failed.")
                ai_used = False

        # Validate / harden summary
        reason_prefix = "AI" if ai_requested else "Template"
        summary, ai_used = _validate_or_fallback(
            candidate=summary_obj,
            soft_errors=soft_errors,
            ai_used=ai_used,
            reason_prefix=reason_prefix,
        )

        # Metadata hardening
        metadata = summary.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update(
            {
                "generated_at": _now_iso(),
                "model": metadata.get("model", "template" if not ai_requested else "gpt-4o"),
                "prompt_version": _PROMPT_VERSION,
                "inputs_digest": _sha1_digest(narrative_data),
                "games_today_count": len(narrative_data.get("games_today", []) or []),
                "ai_used": bool(ai_used),
                "ai_allowed": bool(ai_allowed),
            }
        )
        summary["metadata"] = metadata

        resp: Dict[str, Any] = {
            "ok": True,
            "summary": summary,
            "raw": {
                **narrative_data,
                "meta": {
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "source_counts": {
                        "games_today": len(narrative_data.get("games_today", []) or []),
                        "player_trends": len(narrative_data.get("player_trends", [])),
                        "team_trends": len(narrative_data.get("team_trends", [])),
                        "player_props": len(narrative_data.get("player_props", [])),
                        "odds_games": len((narrative_data.get("odds") or {}).get("games", []) or []),
                    },
                    "cache_used": False,
                    "cache_ttl_s": ttl,
                    "cache_key": cache_key,
                    "cache_expires_in_s": ttl,  # Fresh generation
                    "soft_errors": soft_errors,  # ALWAYS present (dict)
                    "mode": requested_mode,
                    "trends_enabled_in_narrative": bool(effective_trends),
                    "trends_override": override,
                },
            },
            "mode": requested_mode,
        }

        # /today supports optional markdown embedding
        fmt_str = str(format).lower() if format is not None else ""
        if fmt_str == "markdown":
            # Renderer should not throw, but we still guard to keep ok=true
            try:
                resp["markdown"] = _render_markdown(summary)
            except Exception as e:
                soft_errors["markdown"] = f"Markdown render failed: {type(e).__name__}: {e}"
                resp["markdown"] = _render_markdown(_fallback_summary(soft_errors["markdown"]))

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
    trends: Optional[int] = Query(
        None,
        description="Override trends in narrative: 1=on, 0=off, omit=use env default",
    ),
) -> Dict[str, Any]:
    # Step 2.6: /markdown has its own cache key (includes compact flag)
    override = _parse_trends_override(trends)
    effective_trends = _ENV_ENABLE_TRENDS if override is None else override
    ai_allowed = _ai_allowed()
    ttl = _cap_ttl(cache_ttl)
    
    cache_key = _build_cache_key(
        mode=mode,
        ttl=ttl,
        scope="markdown",
        format_value=None,
        trends_override=override,
        effective_trends=bool(effective_trends),
        ai_allowed=bool(ai_allowed),
        compact=compact,
    )
    
    # Check cache before lock
    cached = _CACHE.get(cache_key)
    if cached and cached["expires_at"] > time.time():
        payload = dict(cached["payload"])
        try:
            payload.setdefault("raw", {}).setdefault("meta", {})
            meta = payload["raw"]["meta"]
            meta["latency_ms"] = 0.0
            meta["cache_used"] = True
            meta["cache_key"] = cache_key
            meta["cache_ttl_s"] = ttl
            meta["cache_expires_in_s"] = round(cached["expires_at"] - time.time(), 2)
        except Exception:
            pass
        return payload
    
    # Stampede protection
    if cache_key not in _INFLIGHT_LOCKS:
        _INFLIGHT_LOCKS[cache_key] = asyncio.Lock()
    
    lock = _INFLIGHT_LOCKS[cache_key]
    
    async with lock:
        # Double-check cache
        cached = _CACHE.get(cache_key)
        if cached and cached["expires_at"] > time.time():
            payload = dict(cached["payload"])
            try:
                payload.setdefault("raw", {}).setdefault("meta", {})
                meta = payload["raw"]["meta"]
                meta["latency_ms"] = 0.0
                meta["cache_used"] = True
                meta["cache_key"] = cache_key
                meta["cache_ttl_s"] = ttl
                meta["cache_expires_in_s"] = round(cached["expires_at"] - time.time(), 2)
            except Exception:
                pass
            return payload

        # Call /today with format=markdown
        data = await get_daily_narrative(mode=mode, cache_ttl=0, trends=trends, format="markdown")

        # --- Guardrails: enforce minimum shape ---
        if not isinstance(data, dict):
            data = {"ok": True, "summary": {}, "raw": {"meta": {"soft_errors": {}}}}

        data.setdefault("summary", {})
        if not isinstance(data["summary"], dict):
            data["summary"] = {}

        data["summary"].setdefault("metadata", {})
        if not isinstance(data["summary"]["metadata"], dict):
            data["summary"]["metadata"] = {}

        data.setdefault("raw", {})
        if not isinstance(data["raw"], dict):
            data["raw"] = {}

        data["raw"].setdefault("meta", {})
        if not isinstance(data["raw"]["meta"], dict):
            data["raw"]["meta"] = {}

        data["raw"]["meta"].setdefault("soft_errors", {})
        if not isinstance(data["raw"]["meta"]["soft_errors"], dict):
            data["raw"]["meta"]["soft_errors"] = {}

        # Ensure raw keys exist (even if empty)
        data["raw"].setdefault("games_today", [])
        data["raw"].setdefault("team_trends", [])
        data["raw"].setdefault("player_trends", [])
        data["raw"].setdefault("player_props", [])
        data["raw"].setdefault("odds", {"games": []})
        data["raw"].setdefault("date_generated", "")

        summary = data.get("summary", {}) or {}
        if not isinstance(summary, dict):
            summary = _fallback_summary(f"Summary invalid type: {type(summary).__name__}")
            data["summary"] = summary

        # Render markdown (never fail hard)
        try:
            markdown = _render_markdown(summary, compact=compact)
        except Exception as e:
            se = data["raw"]["meta"].setdefault("soft_errors", {})
            se["markdown"] = f"Markdown generation failed: {type(e).__name__}: {e}"
            markdown = _render_markdown(_fallback_summary(se["markdown"]), compact=compact)

        data["markdown"] = markdown
        data["summary"]["metadata"]["prompt_version"] = _PROMPT_VERSION
        data["ok"] = True  # /markdown should never flip ok=false for soft failures
        
        # Step 2.6: Update cache meta for /markdown endpoint
        meta = data["raw"]["meta"]
        meta["cache_key"] = cache_key
        meta["cache_ttl_s"] = ttl
        meta["cache_expires_in_s"] = ttl
        
        # Cache this markdown response
        if ttl > 0:
            _CACHE[cache_key] = {"expires_at": time.time() + ttl, "payload": data}

        return data