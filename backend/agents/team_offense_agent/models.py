from pydantic import BaseModel
from typing import List, Optional


class TeamOffenseStats(BaseModel):
    team_name: str
    rank_overall: Optional[int] = None
    rank_pg: Optional[int] = None
    rank_sg: Optional[int] = None
    rank_sf: Optional[int] = None
    rank_pf: Optional[int] = None
    rank_c: Optional[int] = None
    points_per_game: Optional[float] = None
    assists_per_game: Optional[float] = None
    rebounds_per_game: Optional[float] = None


class TeamOffenseResponse(BaseModel):
    date_generated: str
    teams: List[TeamOffenseStats]
