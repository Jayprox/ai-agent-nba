# ==========================================================
# 🧠 Player Performance Trend Analyzer
# ----------------------------------------------------------
# Compares mock player stats (last N games vs season averages)
# and returns a summarized trend verdict for each player.
# ==========================================================

from typing import List, Dict
from datetime import datetime, timezone


def analyze_player_trends(players: List[Dict]) -> Dict:
    """
    Analyze player trends based on last_n stats vs season averages.
    Returns a dict containing a timestamp and summary verdicts.
    """

    summaries = []

    for p in players:
        last_ppg = p.get("ppg", 0)
        season_ppg = p.get("season_ppg", 0)
        diff = last_ppg - season_ppg

        # 🔍 Determine performance verdict based on scoring difference
        if diff > 0.5:
            verdict = "🔥 Performing above season average"
        elif diff < -0.5:
            verdict = "❄️ Below season average"
        else:
            verdict = "⚖️ Consistent with season form"

        summaries.append({
            "player_name": p.get("player_name"),
            "ppg": last_ppg,
            "season_ppg": season_ppg,
            "trend": p.get("trend"),
            "verdict": verdict
        })

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "summary": summaries
    }


# ----------------------------------------------------------
# 🧩 Standalone test mode
# ----------------------------------------------------------
if __name__ == "__main__":
    mock_players = [
        {"player_name": "LeBron James", "ppg": 26.4, "season_ppg": 25.8, "trend": "up"},
        {"player_name": "Stephen Curry", "ppg": 29.7, "season_ppg": 29.5, "trend": "neutral"},
        {"player_name": "Luka Doncic", "ppg": 32.5, "season_ppg": 33.0, "trend": "down"},
    ]

    result = analyze_player_trends(mock_players)
    print(result)
