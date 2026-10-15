from common.api_headers import get_json
from common.config_loader import (
    ODDS_API_KEY,
    ODDS_REGIONS,
    ODDS_MARKETS,
    ODDS_BOOKMAKERS,
    TZ
)

url = "https://api.the-odds-api.com/v4/sports"
params = {"apiKey": ODDS_API_KEY}
data = get_json(url, params)
print(data[:2])  # Print first two sports
