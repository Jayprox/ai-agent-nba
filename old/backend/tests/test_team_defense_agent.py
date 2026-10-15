from agents.team_defense_agent.fetch_defense import fetch_team_defense_data

# 🧪 Basic functional test
if __name__ == "__main__":
    data = fetch_team_defense_data()
    print("\n=== Testing Team Defense Agent ===")
    print(f"Generated: {data.date_generated}")

    for t in data.teams:
        print(
            f"{t.team_name}: "
            f"{t.opp_points_per_game} OPP PPG | "
            f"DRtg: {t.defensive_rating} | "
            f"Rank #{t.rank_overall} | "
            f"PG Def: {t.rank_pg_def} | SG Def: {t.rank_sg_def}"
        )

    # ✅ Sanity checks
    print("\nSanity checks:")
    print(f"Total teams: {len(data.teams)}")
    assert all(t.rank_overall >= 1 for t in data.teams), "Missing rank data"
    assert len(data.teams) >= 3, "Expected multiple teams"
    print("✔️ Team Defense Agent test passed successfully!")
