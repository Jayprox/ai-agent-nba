from pydantic import BaseModel, Field
from typing import List, Optional

class PlayerPerformanceModel(BaseModel):
    player_name: str
    last_n_games: int = 5
    ppg: float
    rpg: float
    apg: float
    tpm: float = Field(..., description="3-pointers made per game (3PM)")
    season_ppg: Optional[float] = None
    season_rpg: Optional[float] = None
    season_apg: Optional[float] = None
    season_tpm: Optional[float] = None
    trend: str
    generated_at: str

class PlayerPerformanceResponse(BaseModel):
    date_generated: str
    players: List[PlayerPerformanceModel]
