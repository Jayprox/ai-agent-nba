import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import requests
from datetime import datetime
from agents.trends_agent.models import PlayerTrend, TeamTrend, TrendsResponse
import random
from dotenv import load_dotenv

# Load .env if available
load_dotenv()

# 🔧 Config
BALLDONTLIE_BASE = "https://api.balldontlie.io/v1"
BALLDONTLIE_KEY = os.getenv("BALLDONTLIE_KEY", "d2ca1dd0-abb7-475b-a805-9f42ce88a160")

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; BallDontLie-Agent/2.0)",
    "Accept": "application/json",
}

if BALLDONTLIE_KEY:
    headers["Authorization"] = f"Bearer {BALLDONTLIE_KEY}"


def fetch_player_trends(player_name: str, stat_type: str, last_n_games: int = 5) -> PlayerTrend:
    """
    Fetch recent player trends (points, rebounds, assists) from BallDontLie API.
    Fallback to mock data if API is unavailable or player not found.
    """
    try:
        # Step 1: Get Player ID
        search_query = player_name.split()[0].lower()
        search_url = f"{BALLDONTLIE_BASE}/players?search={search_query}"
        search_resp = requests.get(search_url, headers=headers, timeout=10)

        if search_resp.status_code != 200:
            raise ValueError(f"Player search failed for {player_name} (HTTP {search_resp.status_code})")

        search_data = search_resp.json()
        if not search_data.get("data"):
            raise ValueError(f"Player not found: {player_name}")

        player_id = search_data["data"][0]["id"]

        # Step 2: Get recent stats
        stats_url = f"{BALLDONTLIE_BASE}/stats?player_ids[]={player_id}&per_page={last_n_games}&page=0"
        stats_resp = requests.get(stats_url, headers=headers, timeout=10)

        if stats_resp.status_code != 200:
            raise ValueError(f"Stats fetch failed for {player_name} (HTTP {stats_resp.status_code})")

        stats_data = stats_resp.json().get("data", [])
        if not stats_data:
            raise ValueError(f"No recent games found for {player_name}")

        # Step 3: Compute averages
        values = []
        for s in stats_data:
            if stat_type.lower() in ["points", "pts"]:
                values.append(s.get("pts", 0))
            elif stat_type.lower() in ["rebounds", "reb"]:
                values.append(s.get("reb", 0))
            elif stat_type.lower() in ["assists", "ast"]:
                values.append(s.get("ast", 0))
            else:
                raise ValueError(f"Unsupported stat type: {stat_type}")

        if not values:
            raise ValueError("No valid stat values found")

        avg = round(sum(values) / len(values), 2)
        last_game = values[-1]
        trend_direction = (
            "up" if last_game > avg + 1 else
            "down" if last_game < avg - 1 else
            "neutral"
        )

        print(f"✅ {player_name}: {len(values)} games fetched ({stat_type}, avg {avg})")

        return PlayerTrend(
            player_name=player_name,
            stat_type=stat_type,
            last_n_games=last_n_games,
            average=avg,
            trend_direction=trend_direction,
            variance=round((max(values) - min(values)) / 2, 2),
            weighted_avg=round((avg * 0.7) + (last_game * 0.3), 2)
        )

    except Exception as e:
        print(f"⚠️ [Fallback] Error fetching {player_name}: {e}")
        # fallback mock data
        avg = round(random.uniform(15, 30), 2)
        return PlayerTrend(
            player_name=player_name,
            stat_type=stat_type,
            last_n_games=last_n_games,
            average=avg,
            trend_direction=random.choice(["up", "down", "neutral"]),
            variance=round(random.uniform(1, 5), 2),
            weighted_avg=round(avg * random.uniform(0.9, 1.1), 2)
        )


def fetch_team_trends(team_name: str, stat_type: str, last_n_games: int = 5) -> TeamTrend:
    """
    (Placeholder) Team data not directly available in BallDontLie.
    Future: Replace with NBA Stats API.
    """
    avg = round(random.uniform(90, 130), 1)
    trend_direction = random.choice(["up", "down", "neutral"])

    return TeamTrend(
        team_name=team_name,
        stat_type=stat_type,
        last_n_games=last_n_games,
        average=avg,
        trend_direction=trend_direction
    )


def get_trends_summary() -> TrendsResponse:
    """
    Combine player + team trends into unified TrendsResponse.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    player_trends = [
        fetch_player_trends("LeBron James", "points"),
        fetch_player_trends("Stephen Curry", "points"),
        fetch_player_trends("Luka Doncic", "assists")
    ]

    team_trends = [
        fetch_team_trends("Los Angeles Lakers", "points"),
        fetch_team_trends("Boston Celtics", "assists")
    ]

    return TrendsResponse(
        date_generated=now,
        player_trends=player_trends,
        team_trends=team_trends
    )


# 🧪 Local test
if __name__ == "__main__":
    data = get_trends_summary()
    print(f"\n=== Live Trends Agent Test (BallDontLie) ===")
    print(f"Generated: {data.date_generated}")
    print("\nPlayers:")
    for p in data.player_trends:
        print(f"- {p.player_name}: {p.average} {p.stat_type}/gm ({p.trend_direction})")
    print("\nTeams:")
    for t in data.team_trends:
        print(f"- {t.team_name}: {t.average} {t.stat_type}/gm ({t.trend_direction})")
