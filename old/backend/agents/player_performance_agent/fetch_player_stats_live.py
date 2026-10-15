# backend/agents/player_performance_agent/fetch_player_stats_live.py
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

# --- Path bootstrap so this works in tests & scripts ---
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from common.apisports_client import apisports_get  # type: ignore[import]


# 🏀 Config from environment
NBA_LEAGUE_ID = int(os.getenv("API_BASKETBALL_NBA_LEAGUE_ID", "12"))
SEASON = os.getenv("API_BASKETBALL_SEASON", "2025-2026")


def _normalize_player(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten a player's API-Basketball statistics entry.

    Expected shape (basketball docs, similar to football):
      {
        "player": { "id": ..., "name": ..., ... },
        "statistics": [
          {
            "team": { "id": ..., "name": ... },
            "games": { ... },
            "averages": {
              "minutes": "...",
              "points": ...,
              "rebounds": ...,
              "assists": ...,
              ...
            }
          }
        ]
      }
    """
    player = p.get("player", {})
    stats_list: List[Dict[str, Any]] = p.get("statistics", []) or []

    if not stats_list:
        return {
            "id": player.get("id"),
            "name": player.get("name"),
            "team": None,
        }

    stats = stats_list[0]
    team = (stats.get("team") or {}).get("name")
    games = stats.get("games", {}) or {}
    averages = stats.get("averages", {}) or {}

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

        # You can add more fields from `games` or `averages` later if needed
        "games_played": games.get("played"),
        "position": games.get("position"),
        "starter": games.get("starter"),
    }


def fetch_player_stats(
    team_id: int | None = None,
    player_id: int | None = None,
) -> Dict[str, Any]:
    """
    Fetch player statistics from API-Basketball.

    ✅ IMPORTANT:
    - For the Basketball API, the `/players/statistics` endpoint does NOT like `league`
      in the same way the football API does, and was returning:
        {'league': 'The League field do not exist.'}
    - So here we ONLY send the parameters that are known to be valid:
      - season
      - team (optional)
      - player (optional)

    This keeps it simple and avoids the league-param error we were seeing.
    """
    # Minimal, safe params for this endpoint
    params: Dict[str, Any] = {
        "season": SEASON,
    }

    if team_id is not None:
        params["team"] = team_id

    if player_id is not None:
        params["player"] = player_id

    # 🔍 Call API-Basketball via shared client
    raw = apisports_get("/players/statistics", params=params)
    response = raw.get("response", []) or []

    # Normalize each entry
    players = [_normalize_player(p) for p in response]

    return {
        "season": SEASON,
        "count": len(players),
        "players": players,
        # Optional: include raw if you ever want to debug deeply
        # "raw": raw,
    }


if __name__ == "__main__":
    # Simple manual smoke test when you run:
    #   python -m agents.player_performance_agent.fetch_player_stats_live
    example_team_id = 147  # Miami Heat (from your ping test)
    print(f"=== NBA Player Stats (Live) — Team {example_team_id} ===")
    data = fetch_player_stats(team_id=example_team_id)
    print(f"Season: {data['season']}")
    print(f"Players returned: {data['count']}")
    for p in data["players"][:5]:
        print(f"- {p['name']} ({p['team']}): {p.get('points')} PTS, {p.get('assists')} AST, {p.get('rebounds')} REB")
