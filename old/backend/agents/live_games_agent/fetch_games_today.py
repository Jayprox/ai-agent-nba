# backend/agents/live_games_agent/fetch_games_today.py
from __future__ import annotations

# --- Path bootstrap (ensures backend/ is recognized as the project root) ---
import os, sys
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Any, Dict, List
import pytz

from common.apisports_client import apisports_get

# Config
TZ = os.getenv("TZ", "America/Los_Angeles")
NBA_LEAGUE_ID = int(os.getenv("API_BASKETBALL_NBA_LEAGUE_ID", "12"))


def _today_str_local() -> str:
    """Return today's date in local timezone (YYYY-MM-DD)."""
    tz = pytz.timezone(TZ)
    return datetime.now(tz).strftime("%Y-%m-%d")


def _normalize_game(g: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize API-Basketball game object into a consistent structure.
    """
    game_info = g.get("game", g)
    stage = game_info.get("stage") or g.get("stage")
    status = g.get("status", {}) or game_info.get("status", {})
    status_long = (status.get("long") if isinstance(status, dict) else None) or str(status)
    status_short = status.get("short") if isinstance(status, dict) else None

    teams = g.get("teams", {})
    home = teams.get("home", {})
    away = teams.get("away", {})

    date_iso = g.get("date") or game_info.get("date")
    local_str = None
    if date_iso:
        try:
            dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
            local_str = dt.astimezone(pytz.timezone(TZ)).strftime("%Y-%m-%d %I:%M %p %Z")
        except Exception:
            local_str = date_iso

    return {
        "id": game_info.get("id") or g.get("id"),
        "league_id": g.get("league", {}).get("id"),
        "season": g.get("season"),
        "stage": stage,
        "date_utc": date_iso,
        "date_local": local_str,
        "status_long": status_long,
        "status_short": status_short,
        "home": {
            "id": home.get("id"),
            "name": home.get("name"),
            "code": home.get("code"),
            "logo": home.get("logo"),
        },
        "away": {
            "id": away.get("id"),
            "name": away.get("name"),
            "code": away.get("code"),
            "logo": away.get("logo"),
        },
    }


def fetch_nba_games_today() -> Dict[str, Any]:
    """
    Returns a normalized payload of today's NBA games.
    """
    date_str = _today_str_local()
    raw = apisports_get(
        "/games",
        params={
            "league": NBA_LEAGUE_ID,
            "date": date_str,
        },
    )

    response = raw.get("response", [])
    norm = [_normalize_game(item) for item in response]

    return {
        "date": date_str,
        "count": len(norm),
        "games": norm,
    }


if __name__ == "__main__":
    data = fetch_nba_games_today()
    print("=== NBA Games Today (API-Basketball) ===")
    print(f"Date: {data['date']} | Games: {data['count']}")
    for g in data["games"][:5]:
        print(f"- {g['away']['name']} @ {g['home']['name']} — {g['date_local']} ({g['status_short']})")
