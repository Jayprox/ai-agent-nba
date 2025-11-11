import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from datetime import datetime
from agents.team_defense_agent.models import TeamDefense, TeamDefenseResponse
import random


def fetch_team_defense_data() -> TeamDefenseResponse:
    """
    Simulates fetching team defensive statistics (mock data for now).
    Later: integrate with NBA Stats API or another advanced data source.
    """

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🧠 Mock team defensive data — sorted by fewest opponent points per game
    teams = [
        {
            "team_name": "Boston Celtics",
            "defensive_rating": 105.4,
            "opp_points_per_game": 107.8,
            "opp_rebounds_per_game": 40.3,
            "opp_assists_per_game": 22.1,
        },
        {
            "team_name": "Miami Heat",
            "defensive_rating": 107.1,
            "opp_points_per_game": 108.5,
            "opp_rebounds_per_game": 41.0,
            "opp_assists_per_game": 23.0,
        },
        {
            "team_name": "Milwaukee Bucks",
            "defensive_rating": 108.9,
            "opp_points_per_game": 110.2,
            "opp_rebounds_per_game": 42.4,
            "opp_assists_per_game": 24.2,
        },
        {
            "team_name": "Los Angeles Lakers",
            "defensive_rating": 110.6,
            "opp_points_per_game": 111.5,
            "opp_rebounds_per_game": 43.8,
            "opp_assists_per_game": 25.1,
        },
        {
            "team_name": "Golden State Warriors",
            "defensive_rating": 112.3,
            "opp_points_per_game": 112.9,
            "opp_rebounds_per_game": 44.5,
            "opp_assists_per_game": 25.9,
        },
    ]

    # Sort by opponent points allowed (lower = better defense)
    teams_sorted = sorted(teams, key=lambda t: t["opp_points_per_game"])

    ranked_teams = []
    for i, t in enumerate(teams_sorted, start=1):
        ranked_teams.append(
            TeamDefense(
                team_name=t["team_name"],
                rank_overall=i,
                defensive_rating=t["defensive_rating"],
                opp_points_per_game=t["opp_points_per_game"],
                opp_rebounds_per_game=t["opp_rebounds_per_game"],
                opp_assists_per_game=t["opp_assists_per_game"],
                # randomized mock ranks per position
                rank_pg_def=random.randint(1, 10),
                rank_sg_def=random.randint(1, 10),
                rank_sf_def=random.randint(1, 10),
                rank_pf_def=random.randint(1, 10),
                rank_c_def=random.randint(1, 10),
            )
        )

    return TeamDefenseResponse(date_generated=now, teams=ranked_teams)


# 🧪 Local Test
if __name__ == "__main__":
    data = fetch_team_defense_data()
    print("\n=== Testing Team Defense Agent ===")
    print(f"Generated: {data.date_generated}")
    for t in data.teams:
        print(f"{t.team_name}: {t.opp_points_per_game} OPP PPG (Rank #{t.rank_overall})")
