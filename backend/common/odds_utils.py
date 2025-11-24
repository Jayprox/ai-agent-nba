# backend/common/odds_utils.py
from __future__ import annotations

"""
Odds + Basketball API integration
- Keeps TheOddsAPI moneyline logic
- Adds API-Basketball for team/game cross-validation
"""

import math
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pytz

from agents.odds_agent.models import GameOdds, OddsResponse, Moneyline
from common.config_loader import (
    ODDS_API_KEY,
    ODDS_REGIONS,
    ODDS_MARKETS,
    ODDS_BOOKMAKERS,
    TZ,
)
from common.api_headers import get_json
from services.api_basketball_service import get_today_games

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
_ODDS_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
_CACHE: Dict[str, Tuple[float, OddsResponse]] = {}
_DEFAULT_TTL = 60


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def to_american(decimal_price: float) -> int:
    try:
        d = float(decimal_price)
    except Exception:
        return 0

    if math.isclose(d, 1.0, rel_tol=1e-9, abs_tol=1e-9) or d <= 1.0:
        return -100000
    if d >= 2.0:
        val = (d - 1.0) * 100.0
    else:
        denom = (d - 1.0)
        if math.isclose(denom, 0.0, rel_tol=1e-9, abs_tol=1e-9):
            return -100000
        val = -100.0 / denom
    return int(round(max(min(val, 100000.0), -100000.0)))


def _tz_now_str(tz_name: str) -> str:
    tz = pytz.timezone(tz_name) if tz_name else pytz.utc
    return datetime.now(tz).strftime("%Y-%m-%d")


def _cache_key_for(date_str: Optional[str]) -> str:
    return f"date:{date_str or 'ALL'}"


def _cache_get(date_str: Optional[str]) -> Optional[OddsResponse]:
    item = _CACHE.get(_cache_key_for(date_str))
    if not item:
        return None
    exp, payload = item
    if time.time() < exp:
        return payload
    _CACHE.pop(_cache_key_for(date_str), None)
    return None


def _cache_set(date_str: Optional[str], payload: OddsResponse, ttl: int = _DEFAULT_TTL) -> None:
    if ttl <= 0:
        return
    _CACHE[_cache_key_for(date_str)] = (time.time() + ttl, payload)


# ------------------------------------------------------------------------------
# Core
# ------------------------------------------------------------------------------
def fetch_moneyline_odds(filter_date: Optional[str] = None, cache_ttl: int = _DEFAULT_TTL) -> OddsResponse:
    cached = _cache_get(filter_date)
    if cached:
        return cached

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,
        "oddsFormat": "decimal",
        "bookmakers": ",".join(ODDS_BOOKMAKERS),
    }

    games: List[GameOdds] = []
    date_out = filter_date or _tz_now_str(TZ or "UTC")

    try:
        raw = get_json(_ODDS_URL, params)
    except Exception:
        return OddsResponse(date=date_out, games=games)

    # Optional: fetch API-Basketball today games for richer metadata
    try:
        import asyncio
        api_games = asyncio.run(get_today_games())
        api_game_names = {
            f"{g['teams']['home']['name']} vs {g['teams']['away']['name']}"
            for g in api_games
        }
    except Exception:
        api_game_names = set()

    for event in raw or []:
        sport_key = event.get("sport_key", "")
        commence_time = event.get("commence_time", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        bookmakers = event.get("bookmakers", [])
        if not (home_team and away_team and bookmakers):
            continue

        all_bookmakers: List[str] = []
        best_home = best_away = None
        for bm in bookmakers:
            bm_key = bm.get("key", "")
            if bm_key:
                all_bookmakers.append(bm_key)
            for market in bm.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    price = outcome.get("price")
                    if not isinstance(price, (int, float)):
                        continue
                    if name == home_team:
                        if not best_home or price > float(best_home["price"]):
                            best_home = {"price": float(price), "bookmaker": bm_key}
                    elif name == away_team:
                        if not best_away or price > float(best_away["price"]):
                            best_away = {"price": float(price), "bookmaker": bm_key}

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
                moneyline=ml,  # type: ignore
                all_bookmakers=sorted(set(all_bookmakers)),
            )
        )

    resp = OddsResponse(date=date_out, games=games)
    _cache_set(filter_date, resp, cache_ttl)
    return resp


def get_todays_odds() -> Dict[str, any]:
    r = fetch_moneyline_odds(None, cache_ttl=_DEFAULT_TTL)
    return r.model_dump()


if __name__ == "__main__":
    print("🎯 Fetching today's NBA odds...")
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    r = fetch_moneyline_odds(today_utc, cache_ttl=_DEFAULT_TTL)
    print(f"✅ Retrieved {len(r.games)} games for {r.date}.")
