from pydantic import BaseModel
from typing import List, Optional


class PlayerTrend(BaseModel):
    player_name: str
    stat_type: str
    last_n_games: int
    average: float
    trend_direction: str  # "up", "down", "neutral"
    variance: Optional[float] = None
    weighted_avg: Optional[float] = None


class TeamTrend(BaseModel):
    team_name: str
    stat_type: str
    home_away_split: Optional[str] = None  # "home", "away", or "overall"
    last_n_games: int
    average: float
    trend_direction: str


class TrendsResponse(BaseModel):
    date_generated: str
    player_trends: Optional[List[PlayerTrend]] = []
    team_trends: Optional[List[TeamTrend]] = []
