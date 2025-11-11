import os
from dotenv import load_dotenv

# Load the .env file into environment variables
load_dotenv()

def get_env(name: str, default: str | None = None) -> str:
    """Safely get an environment variable or raise an error if missing."""
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# Core configuration for The Odds API
ODDS_API_KEY = get_env("ODDS_API_KEY")
ODDS_REGIONS = os.getenv("ODDS_REGIONS", "us")
ODDS_MARKETS = os.getenv("ODDS_MARKETS", "h2h")  # h2h = Moneyline
ODDS_BOOKMAKERS = [
    b.strip() for b in os.getenv("ODDS_BOOKMAKERS", "draftkings,fanduel").split(",") if b.strip()
]
TZ = os.getenv("TZ", "America/Los_Angeles")

# 🏀 API-Basketball integration
API_BASKETBALL_KEY = os.getenv("API_BASKETBALL_KEY")
API_BASKETBALL_BASE = os.getenv("API_BASKETBALL_BASE", "https://v1.basketball.api-sports.io")
