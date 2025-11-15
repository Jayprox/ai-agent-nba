# backend/test_api_basketball_live_games.py
from agents.live_games_agent.fetch_games_today import fetch_nba_games_today

if __name__ == "__main__":
    data = fetch_nba_games_today()
    print("\n🏀 Live NBA Games Today (API-Basketball)")
    print(f"Date: {data['date']} | Count: {data['count']}")
    for g in data["games"]:
        print(f"- {g['away']['name']} @ {g['home']['name']} — {g['date_local']} [{g['status_short']}]")
