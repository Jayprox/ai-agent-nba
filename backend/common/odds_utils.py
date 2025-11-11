# backend/common/odds_utils.py
from datetime import datetime
import pytz
from agents.odds_agent.models import GameOdds, OddsResponse, Moneyline
from common.config_loader import ODDS_API_KEY, ODDS_REGIONS, ODDS_MARKETS, ODDS_BOOKMAKERS, TZ
from common.api_headers import get_json

def to_american(decimal_price: float) -> int:
    """Convert decimal odds to American odds."""
    if decimal_price >= 2.0:
        return int((decimal_price - 1) * 100)
    else:
        return int(-100 / (decimal_price - 1))

def fetch_moneyline_odds(filter_date: str | None = None) -> OddsResponse:
    """
    Fetch NBA Moneyline odds.
    If `filter_date` is provided (YYYY-MM-DD), returns only games for that date.
    """
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,
        "oddsFormat": "decimal",
        "bookmakers": ",".join(ODDS_BOOKMAKERS),
    }

    raw = get_json(url, params)
    tz = pytz.timezone(TZ)
    today_str = datetime.now(tz).strftime("%Y-%m-%d")

    games = []
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

                for outcome in market.get("outcomes", []):
                    if outcome.get("name") == home_team:
                        if not best_home or outcome["price"] > best_home["price"]:
                            best_home = {"price": outcome["price"], "bookmaker": bm_key}
                    elif outcome.get("name") == away_team:
                        if not best_away or outcome["price"] > best_away["price"]:
                            best_away = {"price": outcome["price"], "bookmaker": bm_key}

        if not (best_home and best_away):
            continue

        ml = {
            "home": Moneyline(
                team=home_team,
                price=best_home["price"],
                american=to_american(best_home["price"]),
                bookmaker=best_home["bookmaker"],
            ),
            "away": Moneyline(
                team=away_team,
                price=best_away["price"],
                american=to_american(best_away["price"]),
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

    return OddsResponse(date=filter_date or today_str, games=games)
