# backend/routes/narrative.py

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import APIRouter, Query, Request

# --- Internal imports ---
from agents.odds_agent.models import OddsResponse
from common.odds_utils import fetch_moneyline_odds
from common.player_props_utils import fetch_player_props_for_today
from services.api_basketball_service import get_today_games
from services.openai_service import generate_narrative_summary

# Optional: trends agent (may be unavailable)
try:
    from agents.trends_agent.fetch_trends import get_trends_summary  # type: ignore
except Exception:
    get_trends_summary = None  # type: ignore

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])

# -------------------------
# Config / Cache / Contract
# -------------------------
_CACHE: Dict[str, Dict[str, Any]] = {}
_INFLIGHT_LOCKS: Dict[str, asyncio.Lock] = {}
_MAX_CACHE_TTL = 120
_PROMPT_VERSION = "v3.10-structured-logging"
_CONTRACT_VERSION = "2.7"
_ENV_ENABLE_TRENDS = os.getenv("ENABLE_TRENDS_IN_NARRATIVE", "0") == "1"

# Step 2.7: Allowed soft_errors keys (contract hardening)
_ALLOWED_SOFT_ERROR_KEYS: Set[str] = {
    "ai",
    "trends",
    "odds",
    "games_today",
    "player_props",
    "markdown",
    "template",
}

# Step 2.8: Structured logging
logger = logging.getLogger(__name__)


# -------------------------
# Step 2.8: Logging Helpers
# -------------------------
def _log_request_start(*, request_id: str, mode: str, trends: Optional[int], cache_ttl: int, endpoint: str):
    """Log incoming request with context."""
    logger.info(
        f"narrative.request_start | request_id={request_id} | endpoint={endpoint} | "
        f"mode={mode} | trends={trends} | cache_ttl={cache_ttl}"
    )


def _log_cache_event(*, request_id: str, event: str, cache_key: str, ttl: int = 0, expires_in: float = 0):
    """Log cache hit/miss/store events."""
    if event == "hit":
        logger.info(
            f"narrative.cache_hit | request_id={request_id} | cache_key={cache_key} | expires_in={expires_in:.2f}s"
        )
    elif event == "miss":
        logger.info(
            f"narrative.cache_miss | request_id={request_id} | cache_key={cache_key} | will_cache={ttl > 0}"
        )
    elif event == "store":
        logger.info(
            f"narrative.cache_store | request_id={request_id} | cache_key={cache_key} | ttl={ttl}s"
        )


def _log_ai_gating(*, request_id: str, mode: str, ai_allowed: bool, reason: str = ""):
    """Log AI gating decision."""
    if mode == "ai" and not ai_allowed:
        logger.warning(
            f"narrative.ai_blocked | request_id={request_id} | mode={mode} | ai_allowed={ai_allowed} | reason={reason}"
        )
    else:
        logger.info(
            f"narrative.ai_gating | request_id={request_id} | mode={mode} | ai_allowed={ai_allowed}"
        )


def _log_ai_fallback(*, request_id: str, reason: str):
    """Log AI fallback with reason."""
    logger.warning(
        f"narrative.ai_fallback | request_id={request_id} | reason={reason}"
    )


def _log_trends_status(*, request_id: str, enabled: bool, override: Optional[bool], error: Optional[str] = None):
    """Log trends integration status."""
    if error:
        logger.warning(
            f"narrative.trends_disabled | request_id={request_id} | enabled={enabled} | override={override} | reason={error}"
        )
    else:
        logger.info(
            f"narrative.trends_status | request_id={request_id} | enabled={enabled} | override={override}"
        )


def _log_data_fetch(*, request_id: str, source: str, success: bool, error: Optional[str] = None, count: int = 0):
    """Log data fetch results."""
    if not success:
        logger.warning(
            f"narrative.fetch_failed | request_id={request_id} | source={source} | error={error}"
        )
    else:
        logger.debug(
            f"narrative.fetch_ok | request_id={request_id} | source={source} | count={count}"
        )


def _log_response_ready(*, request_id: str, latency_ms: float, cache_used: bool, ai_used: bool, soft_error_count: int):
    """Log request completion with timing."""
    logger.info(
        f"narrative.response_ready | request_id={request_id} | latency_ms={latency_ms:.2f} | "
        f"cache_used={cache_used} | ai_used={ai_used} | soft_errors={soft_error_count}"
    )


# -------------------------
# Utility Helpers
# -------------------------
def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cap_ttl(ttl: int) -> int:
    return max(0, min(ttl, _MAX_CACHE_TTL))


def _sanitize_soft_errors(soft_errors: Dict[str, Any]) -> Dict[str, str]:
    """
    Step 2.7: Filter soft_errors to only include known/allowed keys.
    Logs warnings for unexpected keys (helps detect bugs/typos).
    Always returns a dict (even if empty).
    """
    if not isinstance(soft_errors, dict):
        logger.warning(f"soft_errors is not a dict: {type(soft_errors).__name__}")
        return {}

    sanitized = {}
    for key, value in soft_errors.items():
        if key in _ALLOWED_SOFT_ERROR_KEYS:
            # Ensure value is a string
            sanitized[key] = str(value) if value is not None else ""
        else:
            # Log unexpected keys for debugging
            logger.warning(f"Unexpected soft_error key filtered: {key}={value}")

    return sanitized


def _build_source_status(
    *,
    games_count: int,
    games_err: Optional[str],
    odds_count: int,
    odds_err: Optional[str],
    player_trends_count: int,
    team_trends_count: int,
    trends_err: Optional[str],
    trends_enabled: bool,
    player_props_count: int,
    player_props_err: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """
    Build compact per-source status metadata for observability.
    """
    trends_count = player_trends_count + team_trends_count
    trends_status = "ok"
    if trends_err:
        trends_status = "disabled" if not trends_enabled else "error"
    elif trends_count == 0:
        trends_status = "no_data"

    return {
        "games_today": {
            "status": "error" if games_err else ("ok" if games_count > 0 else "no_data"),
            "count": games_count,
            "error": games_err or "",
        },
        "odds": {
            "status": "error" if odds_err else ("ok" if odds_count > 0 else "no_data"),
            "count": odds_count,
            "error": odds_err or "",
        },
        "trends": {
            "status": trends_status,
            "count": trends_count,
            "error": trends_err or "",
        },
        "player_props": {
            "status": "error" if player_props_err else ("ok" if player_props_count > 0 else "no_data"),
            "count": player_props_count,
            "error": player_props_err or "",
        },
    }


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


def _extract_teams_from_game(game: Dict[str, Any]) -> Tuple[str, str]:
    away = (
        ((game.get("away_team") or {}).get("name"))
        or ((game.get("teams") or {}).get("away") or {}).get("name")
        or game.get("away_team")
        or "Away"
    )
    home = (
        ((game.get("home_team") or {}).get("name"))
        or ((game.get("teams") or {}).get("home") or {}).get("name")
        or game.get("home_team")
        or "Home"
    )
    return str(away), str(home)


def _build_grounded_template_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a grounded non-AI narrative for template mode.
    Uses only fetched inputs; never invents stats or injuries.
    """
    games = data.get("games_today", []) or []
    odds_games = (data.get("odds") or {}).get("games", []) or []
    player_trends = data.get("player_trends", []) or []
    team_trends = data.get("team_trends", []) or []
    player_props = data.get("player_props", []) or []

    macro_lines = []
    if games:
        macro_lines.append(f"Slate overview: {len(games)} NBA game(s) were returned for the current window.")
        sample_matchups = []
        for g in games[:3]:
            away, home = _extract_teams_from_game(g)
            status = (g.get("status") or {}).get("short") or (g.get("status") or {}).get("long") or "Scheduled"
            sample_matchups.append(f"{away} @ {home} ({status})")
        macro_lines.append("Sample matchups: " + "; ".join(sample_matchups) + ".")
    else:
        macro_lines.append("Slate overview: no games were returned for the current window.")

    macro_lines.append(
        "Data coverage: "
        f"odds_games={len(odds_games)}, "
        f"player_trends={len(player_trends)}, "
        f"team_trends={len(team_trends)}, "
        f"player_props={len(player_props)}."
    )

    key_edges = []
    for g in odds_games[:3]:
        away = g.get("away_team") or "Away"
        home = g.get("home_team") or "Home"
        ml = g.get("moneyline") or {}
        away_a = (ml.get("away") or {}).get("american")
        home_a = (ml.get("home") or {}).get("american")
        if away_a is not None and home_a is not None:
            text = f"{away} @ {home}: moneyline context shows away {away_a} and home {home_a}."
        else:
            text = f"{away} @ {home}: moneyline context available with partial pricing detail."
        key_edges.append({"value_label": "Market Context", "edge_score": 5.0, "text": text})

    for t in player_trends[:2]:
        player = t.get("player_name") or "Player"
        stat = t.get("stat_type") or "stat"
        avg = t.get("average")
        direction = t.get("trend_direction") or "neutral"
        avg_txt = f"{avg}" if avg is not None else "n/a"
        key_edges.append(
            {
                "value_label": "Trend Signal",
                "edge_score": 5.5,
                "text": f"{player} {stat} trend is {direction} with average={avg_txt}.",
            }
        )

    for p in player_props[:2]:
        player = p.get("player_name") or "Player"
        market = p.get("market") or "player market"
        line = p.get("line")
        line_txt = f"{line}" if line is not None else "n/a"
        key_edges.append(
            {
                "value_label": "Props Availability",
                "edge_score": 5.0,
                "text": f"{player} has {market} posted with line={line_txt}.",
            }
        )

    missing_sources = []
    if not games:
        missing_sources.append("games_today")
    if not odds_games:
        missing_sources.append("odds")
    if not player_trends:
        missing_sources.append("player_trends")
    if not player_props:
        missing_sources.append("player_props")

    risk_score = min(0.95, round(0.35 + (0.12 * len(missing_sources)), 2))
    if missing_sources:
        risk_rationale = "Higher uncertainty due to limited inputs: " + ", ".join(missing_sources) + "."
    else:
        risk_rationale = "Core inputs were available; uncertainty remains because this is a template-mode summary."

    if risk_score <= 0.45:
        confidence = "High"
    elif risk_score <= 0.65:
        confidence = "Medium"
    else:
        confidence = "Low"

    analyst_takeaway = (
        "Use this summary as a grounded slate snapshot. "
        "Prioritize matchups with both odds and trend signals, and treat games without those inputs as lower-conviction."
    )

    return {
        "macro_summary": macro_lines,
        "micro_summary": {
            "key_edges": key_edges[:6],
            "risk_score": risk_score,
            "risk_rationale": risk_rationale,
        },
        "analyst_takeaway": analyst_takeaway,
        "confidence_summary": [confidence],
        "metadata": {
            "model": "TEMPLATE_GROUNDED_V1",
            "ai_used": False,
            "ai_error": "mode=template (AI not requested).",
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

    confidence = summary.get("confidence_summary", [])
    if not isinstance(confidence, list):
        confidence = [confidence] if confidence else []
    confidence_text = ", ".join([str(c).strip() for c in confidence if str(c).strip()])

    lines = [f"**NBA Narrative**  \n_Generated: {gen_at} • Model: {model}_"]

    if macro:
        if isinstance(macro, list):
            macro_items = [str(m).strip() for m in macro if str(m).strip()]
            macro_text = "\n".join([f"- {m}" for m in macro_items]) if macro_items else ""
        else:
            macro_text = str(macro).strip()
        lines.append("\n### Macro Summary")
        lines.append(macro_text)

    if edges and not compact:
        lines.append("\n### Key Edges")
        for idx, e in enumerate(edges, start=1):
            if isinstance(e, dict):
                lbl = e.get("value_label", "")
                score = e.get("edge_score", "")
                t = e.get("text", "")
                if lbl or score or t:
                    lines.append(f"{idx}. **{lbl}** (score: {score})")
                    lines.append(f"   {t}")
                else:
                    lines.append(f"{idx}. {json.dumps(e)}")
            elif isinstance(e, str):
                lines.append(f"{idx}. {e}")
            else:
                lines.append(f"{idx}. {str(e)}")

    if risk is not None and not compact:
        lines.append("\n### Risk & Confidence")
        if risk_rationale:
            lines.append(f"- **Risk Score:** {risk}")
            lines.append(f"- **Risk Rationale:** {risk_rationale}")
        else:
            lines.append(f"- **Risk Score:** {risk}")
        if confidence_text:
            lines.append(f"- **Confidence:** {confidence_text}")

    if analyst:
        lines.append("\n### Analyst Takeaway")
        analyst_text = str(analyst).strip()
        if ". " in analyst_text:
            sentences = [s.strip() for s in analyst_text.split(". ") if s.strip()]
            for s in sentences:
                suffix = "" if s.endswith(".") else "."
                lines.append(f"- {s}{suffix}")
        else:
            lines.append(analyst_text)

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
    # Step 2.8: Generate request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    
    t0 = time.perf_counter()
    ttl = _cap_ttl(cache_ttl)

    # Step 2.8: Log request start
    _log_request_start(
        request_id=request_id,
        mode=mode,
        trends=trends,
        cache_ttl=ttl,
        endpoint="/today"
    )

    # --- Determine effective trends setting (needed for cache partition) ---
    override = _parse_trends_override(trends)
    effective_trends = _ENV_ENABLE_TRENDS if override is None else override

    # --- Determine AI gating (needed for cache partition) ---
    ai_allowed = _ai_allowed()
    
    # Step 2.8: Log AI gating decision
    _log_ai_gating(
        request_id=request_id,
        mode=mode,
        ai_allowed=ai_allowed,
        reason="OPENAI_API_KEY missing or DISABLE_AI=1" if not ai_allowed else ""
    )

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
        expires_in = cached["expires_at"] - time.time()
        
        # Step 2.8: Log cache hit
        _log_cache_event(
            request_id=request_id,
            event="hit",
            cache_key=cache_key,
            expires_in=expires_in
        )
        
        payload = dict(cached["payload"])
        try:
            payload.setdefault("raw", {}).setdefault("meta", {})
            meta = payload["raw"]["meta"]
            meta["latency_ms"] = 0.0
            meta["cache_used"] = True
            meta["cache_key"] = cache_key
            meta["cache_ttl_s"] = ttl
            meta["cache_expires_in_s"] = round(expires_in, 2)
            meta["request_id"] = request_id  # Step 2.8
        except Exception:
            pass
        return payload

    # Step 2.8: Log cache miss
    _log_cache_event(
        request_id=request_id,
        event="miss",
        cache_key=cache_key,
        ttl=ttl
    )

    # --- Step 2.6: Stampede protection via inflight lock ---
    if cache_key not in _INFLIGHT_LOCKS:
        _INFLIGHT_LOCKS[cache_key] = asyncio.Lock()
    
    lock = _INFLIGHT_LOCKS[cache_key]
    
    async with lock:
        # Double-check cache after acquiring lock (another request may have populated it)
        cached = _CACHE.get(cache_key)
        if cached and cached["expires_at"] > time.time():
            expires_in = cached["expires_at"] - time.time()
            _log_cache_event(
                request_id=request_id,
                event="hit",
                cache_key=cache_key,
                expires_in=expires_in
            )
            payload = dict(cached["payload"])
            try:
                payload.setdefault("raw", {}).setdefault("meta", {})
                meta = payload["raw"]["meta"]
                meta["latency_ms"] = 0.0
                meta["cache_used"] = True
                meta["cache_key"] = cache_key
                meta["cache_ttl_s"] = ttl
                meta["cache_expires_in_s"] = round(expires_in, 2)
                meta["request_id"] = request_id
            except Exception:
                pass
            return payload

        # --- Parallel data fetches (games + odds + player props, trends optional) ---
        t_fetch_start = time.perf_counter()
        games_task = _safe_await("games_today", get_today_games())
        odds_task = _safe_call("odds", fetch_moneyline_odds)
        player_props_task = _safe_call("player_props", fetch_player_props_for_today)

        trends_task = None
        trends_err: Optional[str] = None
        trends_data = None
        player_props_data = []
        player_props_err: Optional[str] = None

        if effective_trends:
            if get_trends_summary is None:
                trends_err = "Trends agent unavailable (import failed)."
            else:
                trends_task = _safe_call("trends", get_trends_summary)
        else:
            trends_err = "Disabled (trends=0 override or ENABLE_TRENDS_IN_NARRATIVE=0)."

        tasks = {
            "games": games_task,
            "odds": odds_task,
            "player_props": player_props_task,
        }
        if trends_task is not None:
            tasks["trends"] = trends_task

        task_keys = list(tasks.keys())
        task_results = await asyncio.gather(*tasks.values())
        results_by_key = dict(zip(task_keys, task_results))

        games = results_by_key["games"]
        odds = results_by_key["odds"]
        player_props_data, player_props_err = results_by_key["player_props"]
        if "trends" in results_by_key:
            trends_data, trends_err = results_by_key["trends"]

        t_fetch_ms = (time.perf_counter() - t_fetch_start) * 1000

        # --- Soft errors always present ---
        soft_errors: Dict[str, str] = {}

        games_today, games_err = games
        odds_data, odds_err = odds

        # Step 2.8: Log data fetch results
        _log_data_fetch(
            request_id=request_id,
            source="games_today",
            success=not bool(games_err),
            error=games_err,
            count=len(games_today or [])
        )
        _log_data_fetch(
            request_id=request_id,
            source="odds",
            success=not bool(odds_err),
            error=odds_err
        )
        _log_data_fetch(
            request_id=request_id,
            source="player_props",
            success=not bool(player_props_err),
            error=player_props_err,
            count=len(player_props_data or [])
        )

        if games_err:
            soft_errors["games_today"] = games_err
        if odds_err:
            soft_errors["odds"] = odds_err
        if trends_err:
            soft_errors["trends"] = trends_err
        if player_props_err:
            soft_errors["player_props"] = player_props_err

        # Step 2.8: Log trends status
        _log_trends_status(
            request_id=request_id,
            enabled=bool(effective_trends),
            override=override,
            error=trends_err
        )

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
            "player_props": player_props_data or [],
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
            ai_block_reason = "AI mode requested but not allowed (OPENAI_API_KEY missing/disabled)."
            soft_errors["ai"] = ai_block_reason
            summary_obj = _fallback_summary(soft_errors["ai"])
            ai_used = False
            
            # Step 2.8: Log AI blocked
            _log_ai_fallback(request_id=request_id, reason=ai_block_reason)
        else:
            t_ai_start = time.perf_counter()
            try:
                if ai_requested:
                    # AI mode: use OpenAI-backed generator with route-level soft-fallbacks.
                    summary_obj = generate_narrative_summary(narrative_data, mode=requested_mode)
                    ai_used = True
                else:
                    # Template mode: build a grounded deterministic summary from available inputs.
                    summary_obj = _build_grounded_template_summary(narrative_data)
                    ai_used = False
                t_ai_ms = (time.perf_counter() - t_ai_start) * 1000
                logger.debug(f"narrative.ai_generation | request_id={request_id} | ai_latency_ms={t_ai_ms:.2f}")
            except Exception as e:
                t_ai_ms = (time.perf_counter() - t_ai_start) * 1000
                # Soft-fallback on throw (tests require substring "AI generation threw")
                if ai_requested:
                    fallback_reason = f"AI generation threw: {type(e).__name__}: {e}"
                    soft_errors["ai"] = fallback_reason
                    _log_ai_fallback(request_id=request_id, reason=fallback_reason)
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

        # Step 2.7: Sanitize soft_errors before returning
        soft_errors_sanitized = _sanitize_soft_errors(soft_errors)

        total_latency_ms = (time.perf_counter() - t0) * 1000

        source_counts = {
            "games_today": len(narrative_data.get("games_today", []) or []),
            "player_trends": len(narrative_data.get("player_trends", [])),
            "team_trends": len(narrative_data.get("team_trends", [])),
            "player_props": len(narrative_data.get("player_props", [])),
            "odds_games": len((narrative_data.get("odds") or {}).get("games", []) or []),
        }
        source_status = _build_source_status(
            games_count=source_counts["games_today"],
            games_err=games_err,
            odds_count=source_counts["odds_games"],
            odds_err=odds_err,
            player_trends_count=source_counts["player_trends"],
            team_trends_count=source_counts["team_trends"],
            trends_err=trends_err,
            trends_enabled=bool(effective_trends),
            player_props_count=source_counts["player_props"],
            player_props_err=player_props_err,
        )

        resp: Dict[str, Any] = {
            "ok": True,
            "summary": summary,
            "raw": {
                **narrative_data,
                "meta": {
                    "contract_version": _CONTRACT_VERSION,  # Step 2.7
                    "request_id": request_id,  # Step 2.8
                    "latency_ms": round(total_latency_ms, 2),
                    "latency_breakdown": {  # Step 2.8
                        "fetch_ms": round(t_fetch_ms, 2),
                        "total_ms": round(total_latency_ms, 2),
                    },
                    "source_counts": source_counts,
                    "source_status": source_status,
                    "cache_used": False,
                    "cache_ttl_s": ttl,
                    "cache_key": cache_key,
                    "cache_expires_in_s": ttl,  # Fresh generation
                    "soft_errors": soft_errors_sanitized,  # Step 2.7: sanitized
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
                # Re-sanitize after adding markdown error
                resp["raw"]["meta"]["soft_errors"] = _sanitize_soft_errors(soft_errors)
                resp["markdown"] = _render_markdown(_fallback_summary(soft_errors["markdown"]))

        # Step 2.8: Log response ready
        _log_response_ready(
            request_id=request_id,
            latency_ms=total_latency_ms,
            cache_used=False,
            ai_used=bool(ai_used),
            soft_error_count=len(soft_errors_sanitized)
        )

        if ttl > 0:
            _CACHE[cache_key] = {"expires_at": time.time() + ttl, "payload": resp}
            _log_cache_event(request_id=request_id, event="store", cache_key=cache_key, ttl=ttl)

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
    # Step 2.8: Generate request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Step 2.8: Log request start
    _log_request_start(
        request_id=request_id,
        mode=mode,
        trends=trends,
        cache_ttl=cache_ttl,
        endpoint="/markdown"
    )

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
        expires_in = cached["expires_at"] - time.time()
        
        # Step 2.8: Log cache hit
        _log_cache_event(
            request_id=request_id,
            event="hit",
            cache_key=cache_key,
            expires_in=expires_in
        )
        
        payload = dict(cached["payload"])
        try:
            payload.setdefault("raw", {}).setdefault("meta", {})
            meta = payload["raw"]["meta"]
            meta["latency_ms"] = 0.0
            meta["cache_used"] = True
            meta["cache_key"] = cache_key
            meta["cache_ttl_s"] = ttl
            meta["cache_expires_in_s"] = round(expires_in, 2)
            meta["request_id"] = request_id
        except Exception:
            pass
        
        # Step 2.8: Log response from cache
        _log_response_ready(
            request_id=request_id,
            latency_ms=0.0,
            cache_used=True,
            ai_used=meta.get("ai_used", False),
            soft_error_count=len(meta.get("soft_errors", {}))
        )
        
        return payload
    
    # Step 2.8: Log cache miss
    _log_cache_event(
        request_id=request_id,
        event="miss",
        cache_key=cache_key,
        ttl=ttl
    )
    
    # Stampede protection
    if cache_key not in _INFLIGHT_LOCKS:
        _INFLIGHT_LOCKS[cache_key] = asyncio.Lock()
    
    lock = _INFLIGHT_LOCKS[cache_key]
    
    async with lock:
        # Double-check cache
        cached = _CACHE.get(cache_key)
        if cached and cached["expires_at"] > time.time():
            expires_in = cached["expires_at"] - time.time()
            _log_cache_event(
                request_id=request_id,
                event="hit",
                cache_key=cache_key,
                expires_in=expires_in
            )
            payload = dict(cached["payload"])
            try:
                payload.setdefault("raw", {}).setdefault("meta", {})
                meta = payload["raw"]["meta"]
                meta["latency_ms"] = 0.0
                meta["cache_used"] = True
                meta["cache_key"] = cache_key
                meta["cache_ttl_s"] = ttl
                meta["cache_expires_in_s"] = round(expires_in, 2)
                meta["request_id"] = request_id
            except Exception:
                pass
            return payload

        # Call /today with format=markdown
        data = await get_daily_narrative(mode=mode, cache_ttl=0, trends=trends, format="markdown")

        # --- Guardrails: enforce minimum shape ---
        if not isinstance(data, dict):
            data = {"ok": True, "summary": {}, "raw": {"meta": {"soft_errors": {}, "contract_version": _CONTRACT_VERSION}}}

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

        # Step 2.7: Ensure contract_version is present
        data["raw"]["meta"].setdefault("contract_version", _CONTRACT_VERSION)
        
        # Step 2.8: Update request_id for /markdown endpoint
        data["raw"]["meta"]["request_id"] = request_id

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
            # Step 2.7: Sanitize after adding error
            data["raw"]["meta"]["soft_errors"] = _sanitize_soft_errors(se)
            markdown = _render_markdown(_fallback_summary(se["markdown"]), compact=compact)

        data["markdown"] = markdown
        data["summary"]["metadata"]["prompt_version"] = _PROMPT_VERSION
        data["ok"] = True  # /markdown should never flip ok=false for soft failures
        
        # Step 2.6: Update cache meta for /markdown endpoint
        meta = data["raw"]["meta"]
        meta["cache_key"] = cache_key
        meta["cache_ttl_s"] = ttl
        meta["cache_expires_in_s"] = ttl
        
        # Step 2.7: Final sanitization before caching/returning
        meta["soft_errors"] = _sanitize_soft_errors(meta.get("soft_errors", {}))
        
        # Step 2.8: Log response ready
        _log_response_ready(
            request_id=request_id,
            latency_ms=meta.get("latency_ms", 0.0),
            cache_used=False,
            ai_used=data.get("summary", {}).get("metadata", {}).get("ai_used", False),
            soft_error_count=len(meta.get("soft_errors", {}))
        )
        
        # Cache this markdown response
        if ttl > 0:
            _CACHE[cache_key] = {"expires_at": time.time() + ttl, "payload": data}
            _log_cache_event(request_id=request_id, event="store", cache_key=cache_key, ttl=ttl)

        return data
