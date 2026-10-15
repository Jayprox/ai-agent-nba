from common.api_headers import get_json
from common.config_loader import ODDS_API_KEY

url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"

params = {
    "apiKey": ODDS_API_KEY,
    "regions": "us",       # US sportsbooks
    "markets": "h2h",      # h2h = Moneyline
    "oddsFormat": "decimal"
}

print("Fetching NBA odds...\n")
data = get_json(url, params)

# Let's inspect a small portion safely
print(f"Total events found: {len(data)}\n")

if len(data) > 0:
    first = data[0]
    print("Sample event keys:\n", list(first.keys()))
    print("\nSample event:\n")
    for k, v in first.items():
        if isinstance(v, (list, dict)):
            print(f"{k}: [complex data]")
        else:
            print(f"{k}: {v}")
else:
    print("⚠️ No NBA events returned (may be off-season or no games today).")
