from agents.odds_agent.fetch_odds import fetch_today_moneyline

print("Fetching NBA Moneyline odds...\n")
response = fetch_today_moneyline()

print(f"Date: {response.date}")
print(f"Total games returned: {len(response.games)}\n")

if response.games:
    first = response.games[0]
    print("Sample Game:")
    print(f"{first.away_team} @ {first.home_team}")
    print(f"Home ({first.home_team}) odds: {first.moneyline['home'].price} "
          f"({first.moneyline['home'].american}) from {first.moneyline['home'].bookmaker}")
    print(f"Away ({first.away_team}) odds: {first.moneyline['away'].price} "
          f"({first.moneyline['away'].american}) from {first.moneyline['away'].bookmaker}")
    print(f"Bookmakers checked: {first.all_bookmakers[:3]} ...")
else:
    print("⚠️ No NBA games found. (May be off-season or no games scheduled today.)")
