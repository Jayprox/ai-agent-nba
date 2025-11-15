# backend/routes/narrative.py
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, HTTPException

# ✅ existing working agent modules
from agents.trends_agent.fetch_trends import get_trends_summary
from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats
from common.odds_utils import fetch_moneyline_odds

from services.openai_service import generate_narrative_summary

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])
logger = logging.getLogger("routes.narrative")

# -------------------------
# Simple async cache + throttle
# -------------------------
_CACHE: Dict[str, Dict[str, Any]] = {}
THROTTLE_SECONDS = 0.75


async def _gather_sources() -> Dict[str, Any]:
    """Fetch all narrative sources concurrently."""
    soft_errors: Dict[str, str] = {}

    async def safe_call(name: str, fn, *args, **kwargs):
        try:
            # run sync functions in thread pool if needed
            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as e:
            soft_errors[name] = f"{type(e).__name__}: {e}"
            return [] if name != "odds" else {}

    results = await asyncio.gather(
        safe_call("trends", get_trends_summary),
        safe_call("props", fetch_player_stats, 134),  # Lakers demo
        safe_call("odds", fetch_moneyline_odds),
    )

    trends, props, odds = results

    team_trends = getattr(trends, "team_trends", [])
    player_trends = getattr(trends, "player_trends", [])

    return {
        "player_trends": [p.model_dump() for p in player_trends],
        "team_trends": [t.model_dump() for t in team_trends],
        "player_props": props.get("data", []) if isinstance(props, dict) else [],
        "odds": odds.model_dump() if hasattr(odds, "model_dump") else odds,
        "soft_errors": soft_errors,
    }


@router.get("/today")
async def get_daily_narrative(
    mode: str = Query("template", description="template or ai"),
    cache_ttl: int = Query(60, ge=0, le=600, description="Cache TTL seconds"),
) -> Dict[str, Any]:
    """Async-enhanced daily narrative with caching and soft error tracking."""
    start = time.perf_counter()
    await asyncio.sleep(THROTTLE_SECONDS)

    # cache key
    cache_key = f"{mode}:{cache_ttl}"
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"]) < cache_ttl:
        cached["meta"]["cache_used"] = True
        return {"ok": True, **cached["payload"]}

    try:
        sources = await _gather_sources()

        narrative_data = {
            "date_generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "player_trends": sources["player_trends"],
            "team_trends": sources["team_trends"],
            "player_props": sources["player_props"],
            "odds": sources["odds"],
        }

        summary = await asyncio.to_thread(generate_narrative_summary, narrative_data, mode)

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        meta = {
            "latency_ms": latency_ms,
            "source_counts": {
                "player_trends": len(narrative_data["player_trends"]),
                "team_trends": len(narrative_data["team_trends"]),
                "player_props": len(narrative_data["player_props"]),
                "odds_games": len(narrative_data["odds"].get("games", [])),
            },
            "cache_used": False,
            "cache_ttl_s": cache_ttl,
            "soft_errors": sources["soft_errors"],
            "mode": mode,
        }

        payload = {"summary": summary, "raw": {**narrative_data, "meta": meta}, "mode": mode}
        _CACHE[cache_key] = {"payload": payload, "ts": time.time(), "meta": meta}

        logger.info("Narrative generated in %.2f ms (mode=%s)", latency_ms, mode)
        return {"ok": True, **payload}

    except Exception as e:
        logger.exception("Failed to build narrative: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
