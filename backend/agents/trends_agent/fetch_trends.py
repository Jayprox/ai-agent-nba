from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("trends_agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# -------------------------
# Config
# -------------------------
TRENDS_PROVIDER = os.getenv("TRENDS_PROVIDER", "mock").strip().lower()
TRENDS_CACHE_TTL = int(os.getenv("TRENDS_CACHE_TTL", "300"))  # seconds
TRENDS_MAX_PLAYERS = int(os.getenv("TRENDS_MAX_PLAYERS", "3"))
TRENDS_LAST_N_GAMES = int(os.getenv("TRENDS_LAST_N_GAMES", "5"))

# -------------------------
# Import project models if available
# -------------------------
try:
    from agents.trends_agent.models import PlayerTrend, TeamTrend, TrendsResponse  # type: ignore
except Exception:
    # Fallback minimal models so this module still works in isolation
    from pydantic import BaseModel

    class PlayerTrend(BaseModel):
        player_name: str
        stat_type: str = "points"
        average: float = 0.0
        variance: float = 0.0
        trend_direction: str = "neutral"
        last_n_games: int = 5

    class TeamTrend(BaseModel):
        team_name: str
        metric: str = "rating"
        average: float = 0.0
        variance: float = 0.0
        trend_direction: str = "neutral"

    class TrendsResponse(BaseModel):
        date_generated: str
        player_trends: List[PlayerTrend] = []
        team_trends: List[TeamTrend] = []
        meta: Dict[str, Any] = {}


# -------------------------
# Simple in-memory cache
# -------------------------
_CACHE: Dict[str, Tuple[float, Any]] = {}


def _cache_get(key: str) -> Optional[Any]:
    now = time.time()
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires_at, payload = hit
    if expires_at <= now:
        _CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key: str, payload: Any, ttl_s: int) -> None:
    _CACHE[key] = (time.time() + max(0, ttl_s), payload)


# -------------------------
# Helpers
# -------------------------
def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    # backend/agents/trends_agent/fetch_trends.py -> backend/
    return Path(__file__).resolve().parents[2]


def _load_mock_player_performance() -> List[Dict[str, Any]]:
    """
    Reads: backend/common/mock_data/player_performance.json

    Expected-ish shape (we handle several):
      { "players": [ ... ] }
      { "data": [ ... ] }
      [ ... ]
    """
    p = _repo_root() / "common" / "mock_data" / "player_performance.json"
    if not p.exists():
        logger.warning("Mock data not found at %s", str(p))
        return []

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))

        if isinstance(raw, list):
            return raw

        if isinstance(raw, dict):
            players = raw.get("players") or raw.get("data") or raw.get("results") or []
            return players if isinstance(players, list) else []

        return []
    except Exception as e:
        logger.warning("Failed reading mock player_performance.json: %s", e)
        return []


def _normalize_trend_direction(value: Any) -> str:
    v = str(value or "").strip().lower()
    if v in ("up", "uparrow", "rising", "increase", "increasing"):
        return "up"
    if v in ("down", "downarrow", "falling", "decrease", "decreasing"):
        return "down"
    if v in ("neutral", "flat", "even", "same"):
        return "neutral"
    return v or "neutral"


def _pydantic_build(model_cls, payload: Dict[str, Any]):
    """
    Build a pydantic model safely:
    - filter payload keys to known model fields (avoids extra-field issues)
    - supply common required fields if missing
    """
    fields = getattr(model_cls, "model_fields", None)

    if isinstance(fields, dict):
        allowed = set(fields.keys())
        filtered = {k: v for k, v in payload.items() if k in allowed}

        # Common required fields
        if "last_n_games" in allowed and "last_n_games" not in filtered:
            filtered["last_n_games"] = TRENDS_LAST_N_GAMES

        if "date_generated" in allowed and "date_generated" not in filtered:
            filtered["date_generated"] = _now_iso_utc()

        return model_cls(**filtered)

    # Non-pydantic or unknown shape
    return model_cls(**payload)


# -------------------------
# Mock trends builder
# -------------------------
def _build_mock_trends() -> TrendsResponse:
    cache_key = f"mock_trends_v3|max={TRENDS_MAX_PLAYERS}|n={TRENDS_LAST_N_GAMES}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    rows = _load_mock_player_performance()

    player_trends: List[PlayerTrend] = []
    for r in rows[: max(0, TRENDS_MAX_PLAYERS)]:
        name = r.get("player_name") or r.get("name") or "Unknown"

        # Support a few possible keys from the mock file
        ppg = float(r.get("ppg") or r.get("points") or r.get("avg") or 0.0)
        season_ppg = float(r.get("season_ppg") or r.get("season_points") or ppg or 0.0)

        variance = abs(ppg - season_ppg)
        trend = _normalize_trend_direction(r.get("trend") or r.get("trend_direction") or "neutral")

        payload = {
            "player_name": str(name),
            "stat_type": "points",
            "average": ppg,
            "variance": variance,
            "trend_direction": trend,
            "last_n_games": TRENDS_LAST_N_GAMES,  # required in your project model
        }

        player_trends.append(_pydantic_build(PlayerTrend, payload))

    meta_blob = {
        "provider": "mock",
        "count_player_trends": len(player_trends),
        "count_team_trends": 0,
        "note": "Mock trends (no external API calls).",
        "last_n_games": TRENDS_LAST_N_GAMES,
    }

    # Include both meta and metadata; field-filtering will keep the correct one.
    resp_payload = {
        "date_generated": _now_iso_utc(),  # ✅ required by your TrendsResponse
        "player_trends": player_trends,
        "team_trends": [],
        "meta": meta_blob,
        "metadata": meta_blob,
    }

    resp = _pydantic_build(TrendsResponse, resp_payload)

    _cache_set(cache_key, resp, TRENDS_CACHE_TTL)
    return resp


# -------------------------
# Public API used by narrative.py
# -------------------------
def get_trends_summary() -> TrendsResponse:
    """
    Safe, bounded trends summary.
    - Default provider is 'mock' to avoid noisy external calls.
    - Unknown providers fall back to mock.
    """
    provider = TRENDS_PROVIDER

    if provider == "mock":
        return _build_mock_trends()

    logger.warning("Unknown TRENDS_PROVIDER=%s; falling back to mock.", provider)
    return _build_mock_trends()
