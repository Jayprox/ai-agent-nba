# backend/services/api_basketball_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from common.apisports_client import apisports_get
from common.api_headers import get_json
import os

NBA_LEAGUE_ID = 12  # NBA
SEASON = os.getenv("API_BASKETBALL_SEASON", "2025-2026")
DEFAULT_TZ = "America/Los_Angeles"  # you can change this if you want
_ODDS_EVENTS_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"


def _today_local_str(tz_name: str) -> str:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz).strftime("%Y-%m-%d")


def _event_date_str_local(commence_time: str, tz_name: str) -> str:
    if not commence_time:
        return ""
    try:
        dt = datetime.fromisoformat(str(commence_time).replace("Z", "+00:00"))
        tz = ZoneInfo(tz_name)
        return dt.astimezone(tz).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _odds_fallback_games(date_local: str, tz_name: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("ODDS_API_KEY", "").strip()
    if not api_key:
        return []

    events = get_json(_ODDS_EVENTS_URL, params={"apiKey": api_key}) or []
    if not isinstance(events, list):
        return []

    mapped: List[Dict[str, Any]] = []
    for ev in events:
        commence_time = str(ev.get("commence_time") or "")
        ev_date = _event_date_str_local(commence_time, tz_name)
        if ev_date != date_local:
            continue

        home = str(ev.get("home_team") or "")
        away = str(ev.get("away_team") or "")
        if not home or not away:
            continue

        ts = None
        try:
            ts = int(datetime.fromisoformat(commence_time.replace("Z", "+00:00")).timestamp())
        except Exception:
            ts = None

        mapped.append(
            {
                "id": f"odds_{ev.get('id')}",
                "date": commence_time,
                "timestamp": ts,
                "timezone": tz_name,
                "home_team": {"name": home},
                "away_team": {"name": away},
                "status": {"long": "Scheduled", "short": "NS", "timer": None},
                "league": {"id": NBA_LEAGUE_ID, "name": "NBA", "season": SEASON, "type": "League"},
                "venue": None,
                "source": "odds_fallback",
            }
        )

    return mapped


async def get_today_games() -> List[Dict[str, Any]]:
    """
    Fetch today's NBA games from API-Basketball.

    Uses:
      - league=12 (NBA)
      - season=API_BASKETBALL_SEASON
      - date=<today in UTC YYYY-MM-DD>
      - timezone=<DEFAULT_TZ>  (affects times only)
    """
    tz_name = os.getenv("TZ", DEFAULT_TZ)
    date_today = _today_local_str(tz_name)

    params = {
        "league": NBA_LEAGUE_ID,
        "season": SEASON,
        "date": date_today,
        "timezone": tz_name,
    }

    raw = {}
    games: List[Dict[str, Any]] = []
    api_errors = None
    try:
        raw = apisports_get("/games", params=params)
        # Standard response shape: {"get": "games", "parameters": {...}, "errors": [], "results": N, "response": [ ... ]}
        games = raw.get("response", []) or []
        api_errors = raw.get("errors")
    except Exception:
        games = []

    # Soft fallback: if API-Basketball returns no games (or plan/date issue),
    # derive today's slate from Odds events so downstream narrative stays useful.
    if games:
        return games

    fallback = _odds_fallback_games(date_today, tz_name)
    if fallback:
        return fallback

    # Preserve original behavior when both sources are empty/unavailable.
    if api_errors:
        return []
    return games
