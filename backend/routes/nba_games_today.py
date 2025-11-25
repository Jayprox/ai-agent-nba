# backend/routes/nba_games_today.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from services.api_basketball_service import get_today_games

router = APIRouter(prefix="/nba/games", tags=["NBA Games"])


def _normalize_game(game: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shape a raw API-Basketball game object into a UI-friendly structure.
    We also keep the original object under 'raw' for debugging if needed.
    """
    league = game.get("league", {}) or {}
    country = game.get("country", {}) or {}
    teams = game.get("teams", {}) or {}
    status = game.get("status", {}) or {}
    scores = game.get("scores", {}) or {}

    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    return {
        "id": game.get("id"),
        "date": game.get("date"),            # ISO with offset
        "time": game.get("time"),
        "timestamp": game.get("timestamp"),
        "timezone": game.get("timezone"),
        "venue": game.get("venue"),
        "league": {
            "id": league.get("id"),
            "name": league.get("name"),
            "season": league.get("season"),
            "type": league.get("type"),
        },
        "country": {
            "id": country.get("id"),
            "name": country.get("name"),
            "code": country.get("code"),
        },
        "home_team": {
            "id": home.get("id"),
            "name": home.get("name"),
            "logo": home.get("logo"),
        },
        "away_team": {
            "id": away.get("id"),
            "name": away.get("name"),
            "logo": away.get("logo"),
        },
        "status": {
            "long": status.get("long"),
            "short": status.get("short"),
            "timer": status.get("timer"),
        },
        "scores": scores,
    }


@router.get("/today")
async def games_today() -> Dict[str, Any]:
    """
    Return today's NBA games from API-Basketball.
    """
    try:
        raw_games: List[Dict[str, Any]] = await get_today_games()
    except Exception as e:
        # Bubble up as a 502 so the frontend can show a clear error.
        raise HTTPException(status_code=502, detail=f"Upstream API error: {e}") from e

    games = [_normalize_game(g) for g in raw_games]

    return {
        "ok": True,
        "count": len(games),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "games": games,
        # keeping a small sample of raw data can help debugging; for now we omit it
    }
