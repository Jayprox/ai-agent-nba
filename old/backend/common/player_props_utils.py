from __future__ import annotations

from datetime import datetime
import os
from typing import Any, Dict, List, Optional

import pytz

from common.api_headers import get_json

_SPORT = "basketball_nba"
_EVENTS_URL = f"https://api.the-odds-api.com/v4/sports/{_SPORT}/events"
_EVENT_ODDS_URL = f"https://api.the-odds-api.com/v4/sports/{_SPORT}/events/{{event_id}}/odds"
_DEFAULT_MARKETS = "player_points,player_rebounds,player_assists"
_DEFAULT_REGIONS = "us"
_DEFAULT_BOOKMAKERS = "draftkings,fanduel"
_DEFAULT_MAX_TOTAL = 30
_DEFAULT_MAX_EVENTS = 6


def _today_str_tz(tz_name: str) -> str:
    tz = pytz.timezone(tz_name) if tz_name else pytz.utc
    return datetime.now(tz).strftime("%Y-%m-%d")


def _event_date_str(commence_time: str, tz_name: str) -> Optional[str]:
    if not commence_time:
        return None
    try:
        tz = pytz.timezone(tz_name) if tz_name else pytz.utc
        dt = datetime.fromisoformat(str(commence_time).replace("Z", "+00:00"))
        return dt.astimezone(tz).strftime("%Y-%m-%d")
    except Exception:
        return None


def _split_markets(markets_raw: str) -> str:
    return ",".join([m.strip() for m in str(markets_raw or "").split(",") if m.strip()])


def fetch_player_props_for_today(max_total: int = _DEFAULT_MAX_TOTAL) -> List[Dict[str, Any]]:
    """
    Fetch live NBA player props from The Odds API.
    Returns a flat list of lightweight prop records for narrative grounding.
    """
    api_key = os.getenv("ODDS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ODDS_API_KEY missing for player props fetch.")

    tz_name = os.getenv("TZ", "America/Los_Angeles")
    today_str = _today_str_tz(tz_name)
    try:
        max_events = max(1, int(os.getenv("ODDS_PLAYER_PROPS_MAX_EVENTS", str(_DEFAULT_MAX_EVENTS))))
    except ValueError:
        max_events = _DEFAULT_MAX_EVENTS

    events_params = {
        "apiKey": api_key,
    }
    odds_params = {
        "apiKey": api_key,
        "regions": os.getenv("ODDS_REGIONS", _DEFAULT_REGIONS),
        "markets": _split_markets(os.getenv("ODDS_PLAYER_PROPS_MARKETS", _DEFAULT_MARKETS)),
        "oddsFormat": "decimal",
        "bookmakers": os.getenv("ODDS_BOOKMAKERS", _DEFAULT_BOOKMAKERS),
    }

    events = get_json(_EVENTS_URL, params=events_params)
    props: List[Dict[str, Any]] = []
    events_today: List[Dict[str, Any]] = []

    for event in events or []:
        commence_time = str(event.get("commence_time") or "")
        event_date = _event_date_str(commence_time, tz_name)
        if event_date != today_str:
            continue
        events_today.append(event)

    # Fallback: if strict local-date filter yields no events, use available events.
    # This avoids timezone/date-boundary misses while still keeping limits small.
    candidate_events = events_today if events_today else list(events or [])

    for event in candidate_events[:max_events]:
        event_id = event.get("id")
        if not event_id:
            continue

        event_odds = get_json(_EVENT_ODDS_URL.format(event_id=event_id), params=odds_params)

        home_team = event_odds.get("home_team") or event.get("home_team")
        away_team = event_odds.get("away_team") or event.get("away_team")
        commence_time = str(event_odds.get("commence_time") or event.get("commence_time") or "")
        matchup = f"{away_team} @ {home_team}" if home_team and away_team else None

        for bm in event_odds.get("bookmakers", []) or []:
            bookmaker = bm.get("key")
            for market in bm.get("markets", []) or []:
                market_key = str(market.get("key") or "")
                if not market_key.startswith("player_"):
                    continue

                for outcome in market.get("outcomes", []) or []:
                    player_name = outcome.get("description") or outcome.get("name")
                    if not player_name:
                        continue
                    props.append(
                        {
                            "event_id": event_id,
                            "matchup": matchup,
                            "home_team": home_team,
                            "away_team": away_team,
                            "player_name": player_name,
                            "market": market_key,
                            "selection": outcome.get("name"),
                            "line": outcome.get("point"),
                            "price": outcome.get("price"),
                            "bookmaker": bookmaker,
                            "commence_time": commence_time,
                        }
                    )
                    if len(props) >= max_total:
                        return props

    return props
