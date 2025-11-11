# backend/agents/player_performance_agent/fetch_player_performance.py
import os
import sys
import json
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

# Allow running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

MOCK_PATH = os.path.join(os.path.dirname(__file__), "../../common/mock_data/player_performance.json")

class PlayerPerformance(BaseModel):
    player_name: str
    last_n_games: int = 5
    ppg: float
    rpg: float
    apg: float
    tpm: float = Field(..., description="3-pointers made per game (3PM)")
    season_ppg: float
    season_rpg: float
    season_apg: float
    season_tpm: float
    trend: str
    generated_at: str


def summarize_players(names: List[str], last_n: int = 5, season: int | None = None) -> List[PlayerPerformance]:
    """
    Mock version of summarize_players that loads from local JSON.
    Accepts last_n and season for compatibility, but ignores them.
    """
    with open(MOCK_PATH, "r", encoding="utf-8") as f:
        mock_data = json.load(f)["data"]

    # Filter only requested names (case-insensitive)
    filtered = [p for p in mock_data if p["player_name"].lower() in [n.lower() for n in names]]

    if not filtered:
        raise ValueError("No matching mock players found.")

    # Update generation time dynamically
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    for p in filtered:
        p["generated_at"] = now

    return [PlayerPerformance(**p) for p in filtered]



if __name__ == "__main__":
    players = ["LeBron James", "Stephen Curry", "Luka Doncic"]
    results = summarize_players(players)
    print("\n=== Mock Player Performance (last 5 games) ===")
    for r in results:
        print(f"{r.player_name}: {r.ppg} PPG | {r.rpg} RPG | {r.apg} APG | {r.tpm} 3PM | trend: {r.trend}")
