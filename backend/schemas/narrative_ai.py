from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class KeyEdge(BaseModel):
    matchup: str = Field(default="Unknown matchup")
    score: Union[int, float, None] = None
    note: str = Field(default="")

class NarrativeAIResponse(BaseModel):
    macro_summary: str = Field(default="")
    key_edges: List[KeyEdge] = Field(default_factory=list)
    risk_score: Optional[Union[int, float]] = None
    analyst_takeaway: str = Field(default="")

    # Optional extras (safe if you extend later)
    metadata: Dict[str, Any] = Field(default_factory=dict)
