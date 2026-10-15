from agents.team_offense_agent.fetch_offense import fetch_team_offense_data

print("\n=== Testing Team Offense Agent ===")
data = fetch_team_offense_data()
print(f"Generated: {data.date_generated}")
for t in data.teams:
    print(f"{t.team_name}: {t.points_per_game} PPG (Rank #{t.rank_overall})")
