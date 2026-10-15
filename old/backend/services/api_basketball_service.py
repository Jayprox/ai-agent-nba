# backend/services/api_basketball_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from common.apisports_client import apisports_get
import os

NBA_LEAGUE_ID = 12  # NBA
SEASON = os.getenv("API_BASKETBALL_SEASON", "2025-2026")
DEFAULT_TZ = "America/Los_Angeles"  # you can change this if you want


def _today_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def get_today_games() -> List[Dict[str, Any]]:
    """
    Fetch today's NBA games from API-Basketball.

    Uses:
      - league=12 (NBA)
      - season=API_BASKETBALL_SEASON
      - date=<today in UTC YYYY-MM-DD>
      - timezone=<DEFAULT_TZ>  (affects times only)
    """
    date_today = _today_utc_str()

    params = {
        "league": NBA_LEAGUE_ID,
        "season": SEASON,
        "date": date_today,
        "timezone": DEFAULT_TZ,
    }

    raw = apisports_get("/games", params=params)
    # Standard response shape: {"get": "games", "parameters": {...}, "errors": [], "results": N, "response": [ ... ]}
    games = raw.get("response", []) or []
    return games
