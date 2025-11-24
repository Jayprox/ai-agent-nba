# tests/test_api_basketball_ping.py
import os, sys, asyncio
from pathlib import Path
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from services.api_basketball_service import get_today_games

async def main():
    print("📡 Checking API-Basketball connection...\n")
    games = await get_today_games()
    print(f"✅ Retrieved {len(games)} games.")
    if games:
        print("Sample Game:\n", games[0])

if __name__ == "__main__":
    asyncio.run(main())
