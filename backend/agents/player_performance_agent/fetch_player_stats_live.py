# backend/agents/player_performance_agent/fetch_player_stats_live.py
from __future__ import annotations
import os, sys
from typing import Any, Dict, List

# --- Path bootstrap ---
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from common.apisports_client import apisports_get

NBA_LEAGUE_ID = int(os.getenv("API_BASKETBALL_NBA_LEAGUE_ID", "12"))
SEASON = os.getenv("API_BASKETBALL_SEASON", "2024-2025")


def _normalize_player(p: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a player's API-Basketball stat entry."""
    player = p.get("player", {})
    stats_list = p.get("statistics", [])
    if not stats_list:
        return {"id": player.get("id"), "name": player.get("name"), "team": None}

    stats = stats_list[0]
    team = stats.get("team", {}).get("name")
    games = stats.get("games", {})
    averages = stats.get("averages", {})

    return {
        "id": player.get("id"),
        "name": player.get("name"),
        "team": team,
        "minutes": averages.get("minutes"),
        "points": averages.get("points"),
        "rebounds": averages.get("rebounds"),
        "assists": averages.get("assists"),
        "steals": averages.get("steals"),
        "blocks": averages.get("blocks"),
        "turnovers": averages.get("turnovers"),
        "fg_pct": averages.get("fgp"),
        "three_pct": averages.get("tpp"),
        "ft_pct": averages.get("ftp"),
    }


def fetch_player_stats(team_id: int | None = None, player_id: int | None = None) -> Dict[str, Any]:
    """
    Fetch live player stats for a specific team or player.
    """
    params = {"league": NBA_LEAGUE_ID, "season": SEASON}
    if team_id:
        params["team"] = team_id
    if player_id:
        params["player"] = player_id

    raw = apisports_get("/players/statistics", params=params)
    response = raw.get("response", [])
    norm = [_normalize_player(p) for p in response]

    return {
        "season": SEASON,
        "count": len(norm),
        "players": norm,
    }


if __name__ == "__main__":
    # Example: Lakers team ID 134
    team_id = 134
    data = fetch_player_stats(team_id=team_id)
    print(f"=== NBA Player Stats (Live) — Team {team_id} ===")
    print(f"Players: {data['count']}")
    for p in data["players"][:5]:
        print(f"- {p['name']} ({p['team']}): {p['points']} PTS, {p['assists']} AST, {p['rebounds']} REB")
