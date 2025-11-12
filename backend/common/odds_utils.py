# backend/common/odds_utils.py
from __future__ import annotations

"""
Odds utility helpers with:
- safe decimal→American conversion
- robust error handling on upstream API
- optional 60s in-memory cache for today's slate
- explicit date filter support (YYYY-MM-DD, UTC)
- small self-test when run as a module: `python -m common.odds_utils`
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import math
import os
import time

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

# ------------------------------------------------------------------------------
# Config & constants
# ------------------------------------------------------------------------------
_ODDS_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"

# Tiny in-memory cache: key -> (expires_epoch, OddsResponse)
# key is "date:<YYYY-MM-DD|ALL>"
_CACHE: Dict[str, Tuple[float, OddsResponse]] = {}

# default cache TTL for today's slate in seconds
_DEFAULT_TTL = 60


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def to_american(decimal_price: float) -> int:
    """
    Convert decimal odds (e.g., 1.91) to American odds (e.g., -110).
    Handles edge-cases safely and rounds toward nearest integer.

    Formula:
      - If decimal >= 2.0: (decimal - 1) * 100
      - If decimal <  2.0: -100 / (decimal - 1)

    Notes:
      - protects against division by (decimal - 1) ≈ 0
      - clamps absurd values to a wide but finite range
    """
    try:
        d = float(decimal_price)
    except Exception:
        return 0

    # Guard tiny differences around 1.0 to avoid exploding values
    if math.isclose(d, 1.0, rel_tol=1e-9, abs_tol=1e-9) or d <= 1.0:
        # A decimal price of 1.0 means guaranteed, which isn't valid for betting;
        # return a very negative number to indicate extreme favorite.
        return -100000

    if d >= 2.0:
        val = (d - 1.0) * 100.0
    else:
        denom = (d - 1.0)
        if math.isclose(denom, 0.0, rel_tol=1e-9, abs_tol=1e-9):
            return -100000
        val = -100.0 / denom

    # Clamp to a wide reasonable American odds range
    val = max(min(val, 100000.0), -100000.0)

    # Exact bankers rounding to nearest int
    return int(round(val))


def _tz_now_str(tz_name: str) -> str:
    """Return YYYY-MM-DD for 'now' in the specified timezone."""
    tz = pytz.timezone(tz_name) if tz_name else pytz.utc
    return datetime.now(tz).strftime("%Y-%m-%d")


def _cache_key_for(date_str: Optional[str]) -> str:
    return f"date:{date_str or 'ALL'}"


def _cache_get(date_str: Optional[str]) -> Optional[OddsResponse]:
    key = _cache_key_for(date_str)
    item = _CACHE.get(key)
    if not item:
        return None
    exp, payload = item
    if time.time() < exp:
        return payload
    _CACHE.pop(key, None)
    return None


def _cache_set(date_str: Optional[str], payload: OddsResponse, ttl: int = _DEFAULT_TTL) -> None:
    if ttl <= 0:
        return
    key = _cache_key_for(date_str)
    _CACHE[key] = (time.time() + ttl, payload)


# ------------------------------------------------------------------------------
# Core: fetch & normalize
# ------------------------------------------------------------------------------
def fetch_moneyline_odds(filter_date: Optional[str] = None, cache_ttl: int = _DEFAULT_TTL) -> OddsResponse:
    """
    Fetch NBA Moneyline odds. If `filter_date` is provided (YYYY-MM-DD, UTC),
    only games for that date are returned. Otherwise, returns all upcoming odds.

    Returns:
        OddsResponse(date=<str>, games=<List[GameOdds]>)

    Raises:
        Any exceptions from network layer are caught and converted into empty payloads.
    """
    # Serve from cache if available
    cached = _cache_get(filter_date)
    if cached:
        return cached

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,  # e.g., "us"
        "markets": ODDS_MARKETS,  # e.g., "h2h"
        "oddsFormat": "decimal",
        "bookmakers": ",".join(ODDS_BOOKMAKERS),
    }

    games: List[GameOdds] = []
    date_out = filter_date or _tz_now_str(TZ or "UTC")

    try:
        raw = get_json(_ODDS_URL, params)
    except Exception as e:
        # Network/API error → return empty structured response
        resp = OddsResponse(date=date_out, games=games)
        _cache_set(filter_date, resp, cache_ttl)
        return resp

    # Normalize each event
    for event in raw or []:
        sport_key = event.get("sport_key", "")
        commence_time = event.get("commence_time", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        bookmakers = event.get("bookmakers", [])

        if not (home_team and away_team and bookmakers):
            continue

        # Optional: filter by UTC date if requested
        if filter_date:
            # commence_time expected ISO8601 "YYYY-MM-DDTHH:MM:SSZ"
            try:
                dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                if dt.astimezone(timezone.utc).strftime("%Y-%m-%d") != filter_date:
                    continue
            except Exception:
                # If parsing fails, keep the event (fail-open)
                pass

        all_bookmakers: List[str] = []
        best_home: Optional[Dict[str, float | str]] = None
        best_away: Optional[Dict[str, float | str]] = None

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
                        if not best_home or price > float(best_home["price"]):  # type: ignore[index]
                            best_home = {"price": float(price), "bookmaker": bm_key}
                    elif name == away_team:
                        if not best_away or price > float(best_away["price"]):  # type: ignore[index]
                            best_away = {"price": float(price), "bookmaker": bm_key}

        if not (best_home and best_away):
            continue

        ml = {
            "home": Moneyline(
                team=home_team,
                price=float(best_home["price"]),
                american=to_american(float(best_home["price"])),
                bookmaker=str(best_home["bookmaker"]),
            ),
            "away": Moneyline(
                team=away_team,
                price=float(best_away["price"]),
                american=to_american(float(best_away["price"])),
                bookmaker=str(best_away["bookmaker"]),
            ),
        }

        games.append(
            GameOdds(
                sport_key=sport_key,
                commence_time=commence_time,
                home_team=home_team,
                away_team=away_team,
                moneyline=ml,  # type: ignore[arg-type]
                all_bookmakers=sorted(set(all_bookmakers)),
            )
        )

    resp = OddsResponse(date=date_out, games=games)
    _cache_set(filter_date, resp, cache_ttl)
    return resp


# Back-compat alias used elsewhere
def get_todays_odds() -> Dict[str, any]:
    """
    Backward-compatible helper returning dict instead of pydantic model.
    """
    r = fetch_moneyline_odds(None, cache_ttl=_DEFAULT_TTL)
    return r.model_dump()


# ------------------------------------------------------------------------------
# Self-test: `python -m common.odds_utils`
# ------------------------------------------------------------------------------
if __name__ == "__main__" or __package__ == "common":
    # When invoked as a module: python -m common.odds_utils
    print("🎯 Fetching today's NBA odds...")
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    r = fetch_moneyline_odds(today_utc, cache_ttl=_DEFAULT_TTL)
    print(f"✅ Retrieved {len(r.games)} games for {r.date}.")
