# tests/test_api_basketball_raw.py
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pprint import pprint

# --- Path bootstrap so "common" & "services" imports work ---
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

print(f"📁 Added to sys.path: {BACKEND_ROOT}")

# --- Load .env ---
env_path = BACKEND_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"🔐 .env loaded from: {env_path}")
else:
    print(f"⚠️  No .env file found at: {env_path}")

API_BASKETBALL_KEY = os.getenv("API_BASKETBALL_KEY")
API_BASKETBALL_BASE = os.getenv("API_BASKETBALL_BASE", "https://v1.basketball.api-sports.io")
NBA_LEAGUE_ID = int(os.getenv("API_BASKETBALL_NBA_LEAGUE_ID", "12"))
SEASON = os.getenv("API_BASKETBALL_SEASON", "2025-2026")

from common.apisports_client import apisports_get  # noqa: E402


def main() -> None:
    print("\n==============================")
    print("📡 API-Basketball RAW DEBUG v3")
    print("==============================\n")

    print(f"🔑 API_BASKETBALL_KEY present: {'✅' if bool(API_BASKETBALL_KEY) else '❌'}")
    print(f"🌐 API_BASKETBALL_BASE: {API_BASKETBALL_BASE}")
    print(f"🏀 league={NBA_LEAGUE_ID}, season={SEASON}\n")

    # 1) /status
    status = apisports_get("/status")
    print("1️⃣ /status")
    print("   get:", status.get("get"))
    print("   errors:", status.get("errors"))
    print("   requests:", status.get("response", {}).get("requests"))
    print("   subscription:", status.get("response", {}).get("subscription"))
    print("\n------------------------------\n")

    # 2) /leagues (id + season)  — but DON'T assume shape; just inspect it
    leagues = apisports_get("/leagues", params={"id": NBA_LEAGUE_ID, "season": SEASON})
    print("2️⃣ /leagues (id + season)")
    print("   results:", leagues.get("results"))
    print("   errors:", leagues.get("errors"))

    resp_leagues = leagues.get("response") or []
    if resp_leagues:
        first = resp_leagues[0]
        print("   🔍 First league object keys:", list(first.keys()))
        print("   🔍 First league object full payload:")
        pprint(first, indent=4, width=100)
    else:
        print("   ⚠️ No league data in response[].")
    print("\n------------------------------\n")

    # 3) /games (league + season + date + timezone)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    games = apisports_get(
        "/games",
        params={
            "league": NBA_LEAGUE_ID,
            "season": SEASON,
            "date": today,
            "timezone": "America/Los_Angeles",
        },
    )
    print("3️⃣ /games (league + season + date + timezone)")
    print("   date:", today)
    print("   results:", games.get("results"))
    print("   errors:", games.get("errors"))

    resp_games = games.get("response") or []
    if resp_games:
        print("   sample game (first item):")
        pprint(resp_games[0], indent=4, width=100)
    else:
        print("   (none)\n")

    print("✅ RAW DEBUG v3 FINISHED")


if __name__ == "__main__":
    main()
