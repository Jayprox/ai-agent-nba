# backend/routes/narrative.py
from __future__ import annotations

"""
Narrative endpoint with:
- async fan-out for data sources (trends, props, odds)
- optional in-memory TTL cache via ?cache_ttl=SECONDS (0 disables)
- meta block: latency, source counts, cache flags, soft_errors
- robust fallbacks (never 500 on upstream flakiness)
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from agents.trends_agent.fetch_trends import get_trends_summary
from agents.team_offense_agent.fetch_offense_live import fetch_team_offense  # kept for future
from agents.team_defense_agent.fetch_defense_live import fetch_team_defense  # kept for future
from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats
from agents.odds_agent.models import OddsResponse
from common.odds_utils import fetch_moneyline_odds
from services.openai_service import generate_narrative_summary

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])

# -----------------------------------------------------------------------------
# Tiny in-memory cache
# -----------------------------------------------------------------------------
# key -> (expires_epoch, payload)
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    item = _CACHE.get(key)
    if not item:
        return None
    exp, payload = item
    if time.time() < exp:
        return payload
    _CACHE.pop(key, None)
    return None


def _cache_set(key: str, payload: Dict[str, Any], ttl: int) -> None:
    if ttl <= 0:
        return
    _CACHE[key] = (time.time() + ttl, payload)


# -----------------------------------------------------------------------------
# Async helpers (wrap sync functions so they can run concurrently)
# -----------------------------------------------------------------------------
async def _to_thread(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


async def _safe_trends() -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Returns:
        (data_dict, soft_error) where data_dict has 'team_trends' & 'player_trends' lists.
    """
    try:
        ts = await _to_thread(get_trends_summary)
        return (
            {
                "team_trends": [t.model_dump() for t in (ts.team_trends or [])],
                "player_trends": [p.model_dump() for p in (ts.player_trends or [])],
            },
            None,
        )
    except Exception as e:
        return ({"team_trends": [], "player_trends": []}, f"{type(e).__name__}: {e}")


async def _safe_props() -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Simple demo props call (Lakers team_id=134). Replace/extend as needed.
    """
    try:
        data = await _to_thread(fetch_player_stats, 134)
        if isinstance(data, dict):
            return ({"player_props": data.get("data", [])}, None)
        return ({"player_props": []}, None)
    except Exception as e:
        return ({"player_props": []}, f"{type(e).__name__}: {e}")


async def _safe_odds() -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        odds: OddsResponse = await _to_thread(fetch_moneyline_odds)
        # Normalize to dict regardless of model presence
        if isinstance(odds, OddsResponse):
            return ({"odds": odds.model_dump()}, None)
        if isinstance(odds, dict):
            return ({"odds": odds}, None)
        return ({"odds": {"date": "", "games": []}}, None)
    except Exception as e:
        return ({"odds": {"date": "", "games": []}}, f"{type(e).__name__}: {e}")


# -----------------------------------------------------------------------------
# Route
# -----------------------------------------------------------------------------
@router.get("/today")
async def get_daily_narrative(
    mode: str = Query("template", description="template or ai"),
    cache_ttl: int = Query(0, ge=0, le=3600, description="Seconds to cache the assembled narrative (0 disables)"),
) -> Dict[str, Any]:
    """
    Generate the daily NBA narrative summary (template or AI).
    Provides a .raw.meta block with latency, count, cache flags, and soft_errors.
    """
    started = time.perf_counter()
    cache_key = f"narrative:{mode}"
    if cache_ttl:
        cached = _cache_get(cache_key)
        if cached:
            # Stamp a meta override to indicate cache hit (do not mutate cached in place)
            payload = dict(cached)
            raw = dict(payload.get("raw", {}))
            meta = dict(raw.get("meta", {}))
            meta["cache_used"] = True
            meta["cache_ttl_s"] = cache_ttl
            meta["latency_ms"] = 0.0
            meta["mode"] = mode
            raw["meta"] = meta
            payload["raw"] = raw
            return payload

    # fan out
    (trends_data, trends_err), (props_data, props_err), (odds_data, odds_err) = await asyncio.gather(
        _safe_trends(), _safe_props(), _safe_odds()
    )

    soft_errors: Dict[str, str] = {}
    if trends_err:
        soft_errors["trends"] = trends_err
    if props_err:
        soft_errors["props"] = props_err
    if odds_err:
        soft_errors["odds"] = odds_err

    # assemble raw data
    narrative_data: Dict[str, Any] = {
        "date_generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "player_trends": trends_data.get("player_trends", []),
        "team_trends": trends_data.get("team_trends", []),
        "player_props": props_data.get("player_props", []),
        "odds": odds_data.get("odds", {"date": "", "games": []}),
    }

    # generate summary (template or ai)
    try:
        summary = generate_narrative_summary(narrative_data, mode=mode)
    except Exception as e:
        # Keep this endpoint stable; expose as HTTP 500 only if something truly unexpected
        raise HTTPException(status_code=500, detail=f"narrative generation failed: {e}")

    # meta
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    source_counts = {
        "player_trends": len(narrative_data["player_trends"]),
        "team_trends": len(narrative_data["team_trends"]),
        "player_props": len(narrative_data["player_props"]),
        "odds_games": len(narrative_data["odds"].get("games", [])) if isinstance(narrative_data["odds"], dict) else 0,
    }
    meta = {
        "latency_ms": elapsed_ms,
        "source_counts": source_counts,
        "cache_used": False,
        "cache_ttl_s": cache_ttl,
        "soft_errors": soft_errors,
        "mode": mode,
    }

    payload = {
        "ok": True,
        "summary": summary,
        "raw": {**narrative_data, "meta": meta},
        "mode": mode,
    }

    if cache_ttl:
        _cache_set(cache_key, payload, cache_ttl)

    return payload
