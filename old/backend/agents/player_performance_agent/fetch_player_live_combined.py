# backend/agents/player_performance_agent/fetch_player_live_combined.py
from __future__ import annotations
import os, sys

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats
from agents.player_performance_agent.fetch_live_insights_api import get_live_insights_real

def get_combined_player_live(team_id: int):
    """Combine live player stats with insight verdicts."""
    # Fetch both payloads
    stats_data = fetch_player_stats(team_id)
    insights_data = get_live_insights_real()

    # Index insights by name for quick lookup
    insight_map = {p["player_name"].lower(): p for p in insights_data.get("insights", [])}

    combined = []
    for p in stats_data.get("data", {}).get("players", []):
        name = p.get("name", "").lower()
        insight = insight_map.get(name, {})
        combined.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "team": p.get("team"),
            "pts": p.get("points"),
            "reb": p.get("rebounds"),
            "ast": p.get("assists"),
            "fg_pct": p.get("fg_pct"),
            "three_pct": p.get("three_pct"),
            "trend": insight.get("trend"),
            "verdict": insight.get("verdict"),
        })

    return {
        "ok": True,
        "team_id": team_id,
        "count": len(combined),
        "players": combined
    }

if __name__ == "__main__":
    data = get_combined_player_live(134)
    print("=== Combined Live Player Insights ===")
    print(f"Players: {data['count']}")
    for p in data["players"][:5]:
        print(f"{p['name']} — {p['verdict']}")
