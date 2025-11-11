# backend/routes/nba_games_today.py
from fastapi import APIRouter
from common.apisports_client import apisports_get

router = APIRouter()

@router.get("/nba/games/today")
def get_nba_games_today():
    """Fetch today's NBA games"""
    data = apisports_get("games", {"league": 12, "season": "2024-2025", "date": "2025-11-07"})
    games = []

    for g in data.get("response", []):
        home = g.get("teams", {}).get("home", {})
        away = g.get("teams", {}).get("away", {})
        games.append({
            "id": g.get("id"),
            "home_team": {"id": home.get("id"), "name": home.get("name")},
            "away_team": {"id": away.get("id"), "name": away.get("name")},
            "status": g.get("status", {}).get("long"),
            "date": g.get("date"),
        })

    return {"ok": True, "count": len(games), "games": games}
