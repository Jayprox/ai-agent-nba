from pydantic import BaseModel
from typing import List, Optional


class TeamDefense(BaseModel):
    """Represents a single team's defensive profile."""
    team_name: str
    rank_overall: int
    defensive_rating: float                    # NBA defensive efficiency metric
    opp_points_per_game: float                 # Points allowed per game
    opp_rebounds_per_game: float               # Rebounds allowed per game
    opp_assists_per_game: Optional[float] = None
    rank_pg_def: Optional[int] = None          # Rank vs Point Guards
    rank_sg_def: Optional[int] = None          # Rank vs Shooting Guards
    rank_sf_def: Optional[int] = None          # Rank vs Small Forwards
    rank_pf_def: Optional[int] = None          # Rank vs Power Forwards
    rank_c_def: Optional[int] = None           # Rank vs Centers


class TeamDefenseResponse(BaseModel):
    """Aggregated response for all team defensive stats."""
    date_generated: str
    teams: List[TeamDefense]
