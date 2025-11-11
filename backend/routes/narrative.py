# backend/routes/narrative.py
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timezone
import json

from agents.trends_agent.fetch_trends import get_trends_summary
from agents.team_offense_agent.fetch_offense_live import fetch_team_offense
from agents.team_defense_agent.fetch_defense_live import fetch_team_defense
from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats
from agents.odds_agent.models import OddsResponse
from common.odds_utils import fetch_moneyline_odds
from services.openai_service import generate_narrative_summary

router = APIRouter(prefix="/nba/narrative", tags=["Narrative"])

@router.get("/today")
def get_daily_narrative(mode: str = Query("template", description="template or ai")):
    """Generate the daily NBA narrative summary."""
    try:
        try:
            trends = get_trends_summary()
            team_trends, player_trends = trends.team_trends, trends.player_trends
        except Exception:
            team_trends, player_trends = [], []

        try:
            props = fetch_player_stats(team_id=134)  # Lakers for demo
        except Exception:
            props = {"data": []}

        try:
            odds = fetch_moneyline_odds()
        except Exception:
            odds = {"games": []}

        narrative_data = {
            "date_generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "player_trends": [p.model_dump() for p in player_trends],
            "team_trends": [t.model_dump() for t in team_trends],
            "player_props": props.get("data", []) if isinstance(props, dict) else [],
            "odds": odds.model_dump() if isinstance(odds, OddsResponse) else odds,
        }

        summary = generate_narrative_summary(narrative_data, mode=mode)
        return {"ok": True, "summary": summary, "raw": narrative_data, "mode": mode}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
