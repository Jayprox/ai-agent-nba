# backend/agents/player_performance_agent/fetch_live_insights_api.py

from datetime import datetime, timezone
import requests
from common.config_loader import API_BASKETBALL_KEY, API_BASKETBALL_BASE

# NBA league ID = 12 in API-Basketball
LEAGUE_ID = 12
SEASON = 2024  # Current season year

# Map of NBA players and their known API-Basketball IDs (update as needed)
PLAYER_IDS = {
    "LeBron James": 265,
    "Stephen Curry": 115,
    "Luka Doncic": 132,
}

HEADERS = {
    "x-apisports-key": API_BASKETBALL_KEY,
    "x-rapidapi-host": "v1.basketball.api-sports.io",
}

def fetch_player_season_stats(player_id: int):
    """Fetch a player's average stats from API-Basketball."""
    try:
        url = f"{API_BASKETBALL_BASE}/players/statistics"
        params = {"season": SEASON, "id": player_id, "league": LEAGUE_ID}
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()

        # Validate and extract data
        if not data.get("response"):
            print(f"⚠️ No data found for player_id={player_id}")
            return None

        stats = data["response"][0]["statistics"][0]
        return {
            "ppg": round(stats.get("points", 0), 1),
            "rpg": round(stats.get("rebounds", 0), 1),
            "apg": round(stats.get("assists", 0), 1),
            "tpm": round(stats.get("three_points", 0), 1),
        }

    except Exception as e:
        print(f"⚠️ Error fetching stats for {player_id}: {e}")
        return None


def get_live_insights_real():
    """Combine live player stats into a structured API response."""
    insights = []

    for name, pid in PLAYER_IDS.items():
        stats = fetch_player_season_stats(pid)
        if not stats:
            continue

        # Basic trend logic — refine later
        trend = "up" if stats["ppg"] > 25 else "neutral"
        verdict = (
            "🔥 Performing above season average"
            if trend == "up"
            else "⚖️ Consistent with season form"
        )

        insights.append({
            "player_name": name,
            "ppg": stats["ppg"],
            "rpg": stats["rpg"],
            "apg": stats["apg"],
            "tpm": stats["tpm"],
            "trend": trend,
            "verdict": verdict,
        })

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "mode": "live",
        "insights": insights,
    }


if __name__ == "__main__":
    from pprint import pprint
    pprint(get_live_insights_real())
