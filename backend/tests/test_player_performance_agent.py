# backend/test_player_performance_agent.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from agents.player_performance_agent.fetch_player_performance import summarize_players

if __name__ == "__main__":
    print("\n=== Testing Player Performance Agent ===")
    results = summarize_players(
        ["LeBron James", "Stephen Curry", "Luka Doncic"],
        last_n=5
    )
    for r in results:
        print(f"{r.player_name}: {r.ppg} PPG | {r.rpg} RPG | {r.apg} APG | {r.tpm} 3PM | trend: {r.trend}")

    # Simple sanity check (shape, not exact numbers)
    assert len(results) == 3
    assert all(hasattr(r, "ppg") for r in results)
    print("\n✔️ Player Performance Agent test completed.")
