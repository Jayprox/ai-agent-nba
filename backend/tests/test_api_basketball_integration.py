# tests/test_api_basketball_integration.py
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# --- Add backend root to Python path ---
BACKEND_ROOT = Path(__file__).resolve().parent.parent  # /backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

print(f"📁 Added to sys.path: {BACKEND_ROOT}")

# --- Load environment variables ---
env_path = BACKEND_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"🔐 .env loaded from: {env_path}")
else:
    print(f"⚠️  No .env file found at: {env_path}")

from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats  # type: ignore[import]


def main() -> None:
    print("🏀 Testing API-Basketball integration (player stats)...\n")

    # From your /games sample: Miami Heat @ 76ers → Heat = 147, Sixers = 154
    team_id = 147

    try:
        data = fetch_player_stats(team_id=team_id)

        print(f"✅ Season: {data.get('season')}")
        print(f"✅ Raw count: {data.get('raw_count')}")
        print(f"✅ Normalized player count: {data.get('count')} for team {team_id}")

        players = data.get("players") or []
        if players:
            first = players[0]
            print("\nSample Player:")
            for k, v in first.items():
                print(f"  {k}: {v}")
        else:
            print("\n⚠️ No players returned. This could mean:")
            print("   - The season has just started and stats aren't populated yet, or")
            print("   - The parameters (league/season/team) still need tweaking.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   Error type: {type(e).__name__}")


if __name__ == "__main__":
    main()
