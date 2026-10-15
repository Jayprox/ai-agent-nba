from pydantic import BaseModel
from typing import List, Optional, Dict

class Moneyline(BaseModel):
    """Represents moneyline data for one team."""
    team: str
    price: float          # Decimal odds
    american: int         # Converted to American odds
    bookmaker: str        # Which sportsbook provided the best price

class GameOdds(BaseModel):
    """Represents one NBA game and its odds."""
    sport_key: str
    commence_time: str    # ISO 8601 (UTC) start time
    home_team: str
    away_team: str
    moneyline: Dict[str, Moneyline]  # {"home": Moneyline, "away": Moneyline}
    all_bookmakers: Optional[List[str]] = None

class OddsResponse(BaseModel):
    """Top-level response returned by the /nba/odds/today route."""
    date: str             # Local date (YYYY-MM-DD)
    games: List[GameOdds]
