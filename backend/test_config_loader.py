from common.config_loader import (
    ODDS_API_KEY,
    ODDS_REGIONS,
    ODDS_MARKETS,
    ODDS_BOOKMAKERS,
    TZ
)

print("ODDS_API_KEY:", ODDS_API_KEY[:6] + "..." if ODDS_API_KEY else "MISSING")
print("REGION:", ODDS_REGIONS)
print("MARKETS:", ODDS_MARKETS)
print("BOOKMAKERS:", ODDS_BOOKMAKERS)
print("TIMEZONE:", TZ)
