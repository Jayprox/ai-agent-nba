import random
from datetime import datetime
from agents.team_offense_agent.models import TeamOffenseStats, TeamOffenseResponse


def fetch_team_offense_data() -> TeamOffenseResponse:
    """
    Returns team offensive metrics (mock for now).
    Will later pull real data from NBA Stats API.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Mock teams — replace later with API data
    mock_teams = [
        "Los Angeles Lakers",
        "Boston Celtics",
        "Milwaukee Bucks",
        "Golden State Warriors",
        "Dallas Mavericks",
    ]

    teams = []
    for rank, team in enumerate(mock_teams, start=1):
        teams.append(
            TeamOffenseStats(
                team_name=team,
                rank_overall=rank,
                rank_pg=random.randint(1, 30),
                rank_sg=random.randint(1, 30),
                rank_sf=random.randint(1, 30),
                rank_pf=random.randint(1, 30),
                rank_c=random.randint(1, 30),
                points_per_game=round(random.uniform(100, 125), 1),
                assists_per_game=round(random.uniform(20, 30), 1),
                rebounds_per_game=round(random.uniform(40, 55), 1),
            )
        )

    return TeamOffenseResponse(date_generated=now, teams=teams)


# 🧪 Local test
if __name__ == "__main__":
    data = fetch_team_offense_data()
    print(f"\n=== Team Offense Agent Test ===")
    print(f"Generated: {data.date_generated}\n")
    for t in data.teams:
        print(
            f"{t.team_name}: {t.points_per_game} PPG, "
            f"Rank #{t.rank_overall} overall, PG rank {t.rank_pg}"
        )
