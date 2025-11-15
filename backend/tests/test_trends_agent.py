from agents.trends_agent.fetch_trends import get_trends_summary

if __name__ == "__main__":
    data = get_trends_summary()
    print("\n=== Trends Agent Test ===")
    print(f"Generated: {data.date_generated}")
    print("\nPlayers:")
    for p in data.player_trends:
        print(f"- {p.player_name}: {p.average} {p.stat_type}/gm ({p.trend_direction})")
    print("\nTeams:")
    for t in data.team_trends:
        print(f"- {t.team_name}: {t.average} {t.stat_type}/gm ({t.trend_direction})")
