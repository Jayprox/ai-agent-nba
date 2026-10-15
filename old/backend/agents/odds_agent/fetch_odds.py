from typing import List, Dict, Any
from datetime import datetime
import pytz

# ✅ Absolute imports — stable for direct testing & FastAPI
from common.config_loader import (
    ODDS_API_KEY, ODDS_REGIONS, ODDS_MARKETS, ODDS_BOOKMAKERS, TZ,
)
from common.api_headers import get_json
from agents.odds_agent.models import GameOdds, Moneyline, OddsResponse


# Base endpoint for NBA odds
ODDS_BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"


def _to_american(decimal_price: float) -> int:
    """
    Convert decimal odds to American odds.
    e.g., 2.10 -> +110, 1.90 -> -111
    """
    if decimal_price >= 2.0:
        return int((decimal_price - 1) * 100)
    else:
        return int(-100 / (decimal_price - 1))


def _pick_best_price(outcomes: List[Dict[str, Any]], team_name: str) -> Dict[str, Any] | None:
    """
    Given a list of bookmaker outcomes, find the one with the best (highest) decimal price for a team.
    """
    best = None
    for outcome in outcomes:
        if outcome.get("name") == team_name:
            if best is None or (outcome.get("price", 0) > best.get("price", 0)):
                best = outcome
    return best


def fetch_today_moneyline() -> OddsResponse:
    """
    Fetch NBA moneyline odds for upcoming games.
    Filters out games not scheduled for today's date (based on TZ in .env).
    Returns a cleaned OddsResponse ready for the frontend.
    """
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,  # h2h (Moneyline)
        "oddsFormat": "decimal",
        "bookmakers": ",".join(ODDS_BOOKMAKERS) if ODDS_BOOKMAKERS else None,
    }

    raw = get_json(ODDS_BASE, params)
    tz = pytz.timezone(TZ)
    today_str = datetime.now(tz).strftime("%Y-%m-%d")

    games: List[GameOdds] = []

    for event in raw:
        sport_key = event.get("sport_key", "")
        commence_time = event.get("commence_time", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        bookmakers = event.get("bookmakers", [])

        if not (home_team and away_team and bookmakers):
            continue

        all_bookmakers = []
        best_home = None
        best_away = None

        for bm in bookmakers:
            bm_key = bm.get("key", "")
            all_bookmakers.append(bm_key)

            for market in bm.get("markets", []):
                if market.get("key") != "h2h":
                    continue

                outcomes = market.get("outcomes", [])
                home_out = _pick_best_price(outcomes, home_team)
                away_out = _pick_best_price(outcomes, away_team)

                if home_out:
                    if not best_home or home_out["price"] > best_home["price"]:
                        best_home = {"price": home_out["price"], "bookmaker": bm_key}

                if away_out:
                    if not best_away or away_out["price"] > best_away["price"]:
                        best_away = {"price": away_out["price"], "bookmaker": bm_key}

        if not (best_home and best_away):
            continue

        ml = {
            "home": Moneyline(
                team=home_team,
                price=best_home["price"],
                american=_to_american(best_home["price"]),
                bookmaker=best_home["bookmaker"],
            ),
            "away": Moneyline(
                team=away_team,
                price=best_away["price"],
                american=_to_american(best_away["price"]),
                bookmaker=best_away["bookmaker"],
            ),
        }

        games.append(
            GameOdds(
                sport_key=sport_key,
                commence_time=commence_time,
                home_team=home_team,
                away_team=away_team,
                moneyline=ml,
                all_bookmakers=sorted(set(all_bookmakers)),
            )
        )

    # ✅ Filter to include only today's games (based on timezone)
    today_games: List[GameOdds] = []
    for g in games:
        try:
            commence = datetime.fromisoformat(g.commence_time.replace("Z", "+00:00"))
            local_time = commence.astimezone(tz)
            if local_time.strftime("%Y-%m-%d") == today_str:
                today_games.append(g)
        except Exception:
            continue

    return OddsResponse(date=today_str, games=today_games)


# 🧪 Direct run (for quick testing)
if __name__ == "__main__":
    print("Fetching NBA Moneyline odds for today...\n")
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
        print("⚠️ No NBA games found for today.")
