# backend/agents/team_offense_agent/fetch_offense_live.py
from __future__ import annotations
import os, sys
from typing import Any, Dict

# Ensure backend root is importable
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from common.apisports_client import apisports_get

NBA_LEAGUE_ID = int(os.getenv("API_BASKETBALL_NBA_LEAGUE_ID", "12"))
SEASON = os.getenv("API_BASKETBALL_SEASON", "2024-2025")

def fetch_team_offense(team_id: int) -> Dict[str, Any]:
    """
    Fetches offensive stats for a given NBA team (live season stats).
    """
    raw = apisports_get(
        "/teams/statistics",
        params={"league": NBA_LEAGUE_ID, "season": SEASON, "team": team_id},
    )

    # ✅ Handle case where "response" is a list
    response = raw.get("response") or []
    stats = response[0] if isinstance(response, list) and response else {}

    return {
        "team_id": team_id,
        "season": SEASON,
        "points_per_game": stats.get("points", {}).get("for", {}).get("average", {}).get("total"),
        "fg_pct": stats.get("fieldGoals", {}).get("for", {}).get("percentage"),
        "three_pct": stats.get("threePoints", {}).get("for", {}).get("percentage"),
        "assists": stats.get("assists", {}).get("average", {}).get("total"),
        "turnovers": stats.get("turnovers", {}).get("average", {}).get("total"),
        "pace": stats.get("possession", {}).get("average", {}).get("total"),
    }

if __name__ == "__main__":
    test_team_id = 145  # Lakers (example)
    data = fetch_team_offense(test_team_id)
    print("=== NBA Team Offense (Live) ===")
    print(data)
