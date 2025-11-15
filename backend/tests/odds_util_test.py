# backend/tests/odds_utils_test.py
"""
Quick verification script for get_todays_odds()
Ensures odds API integration and structure integrity.
"""

import json
from common.odds_utils import get_todays_odds

def main():
    print("🎯 Fetching today's NBA odds...\n")
    odds = get_todays_odds()

    if "error" in odds:
        print("⚠️  Error fetching odds:", odds["error"])
        return

    games = odds.get("games", [])
    print(f"✅ Retrieved {len(games)} games for today's slate.\n")

    if games:
        sample = games[0]
        print("📝 Sample Game Structure:")
        print(json.dumps(sample, indent=2)[:500])  # partial preview
    else:
        print("No games returned. Possibly off-day or API limit reached.")

if __name__ == "__main__":
    main()
