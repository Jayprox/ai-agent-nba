# backend/main.py
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------
# ENV + LOGGING SETUP
# ------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_key = os.getenv("OPENAI_API_KEY")
odds_key = os.getenv("ODDS_API_KEY")
tz = os.getenv("TZ", "America/Los_Angeles")

logger.info("🔐 Environment variables loaded:")
logger.info(f"  OPENAI_API_KEY: {'✅ Loaded' if openai_key else '❌ Missing'}")
logger.info(f"  ODDS_API_KEY: {'✅ Loaded' if odds_key else '❌ Missing'}")
logger.info(f"  TZ: {tz}")

# 🧠 Safety checks
if not openai_key:
    logger.warning("⚠️  OpenAI key not found. AI narrative features will be DISABLED.")
if not odds_key:
    logger.warning("⚠️  Odds API key not found. Betting odds fetching will be DISABLED.")




# backend/main.py

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone


# --- Models & Config ---
from agents.odds_agent.models import OddsResponse
from common.config_loader import TZ
from common.odds_utils import fetch_moneyline_odds  # ✅ Moved here
from common.api_headers import get_json

# --- Agents ---
from agents.trends_agent.fetch_trends import get_trends_summary
from agents.trends_agent.models import TrendsResponse
from agents.team_offense_agent.fetch_offense import fetch_team_offense_data
from agents.team_offense_agent.models import TeamOffenseResponse
from agents.team_defense_agent.fetch_defense import fetch_team_defense_data
from agents.team_defense_agent.models import TeamDefenseResponse
from agents.player_performance_agent.fetch_player_performance import summarize_players
from agents.player_performance_agent.models import PlayerPerformanceResponse
from agents.player_performance_agent.analyze_trends import analyze_player_trends
from agents.player_performance_agent.fetch_insights import get_player_insights
from agents.player_performance_agent.fetch_live_insights_api import get_live_insights_real
from agents.live_games_agent.fetch_games_today import fetch_nba_games_today

# --- Live team offense/defense (API-Basketball) ---
from agents.team_offense_agent.fetch_offense_live import fetch_team_offense as fetch_team_offense_live
from agents.team_defense_agent.fetch_defense_live import fetch_team_defense as fetch_team_defense_live
from agents.player_performance_agent.fetch_player_stats_live import fetch_player_stats
from agents.player_performance_agent.fetch_player_live_combined import get_combined_player_live

# --- Narrative Agent ---
from agents.narrative_agent.generate_narrative import generate_daily_narrative

# --- Routes ---
from routes import nba_games_today, narrative


# ------------------------------------------------------
# APP SETUP
# ------------------------------------------------------
app = FastAPI(
    title="NBA Odds Agent API",
    version="1.5.1",
    description="Fetches NBA odds, trends, and team offense data for AI-driven analysis."
)

# 🧱 Allow React frontend (localhost:5173) to call FastAPI backend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(nba_games_today.router, prefix="/nba")
app.include_router(narrative.router)


# ------------------------------------------------------
# ROUTES
# ------------------------------------------------------
@app.get("/health")
def health_check():
    """Simple check to verify the API is running."""
    return {"status": "ok"}


# ------------------------------------------------------
# ODDS ROUTES
# ------------------------------------------------------
@app.get("/nba/odds/today", response_model=OddsResponse)
def get_nba_odds_today():
    """NBA Moneyline odds for today only."""
    try:
        tz = pytz.timezone(TZ)
        today_str = datetime.now(tz).strftime("%Y-%m-%d")
        return fetch_moneyline_odds(filter_date=today_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/odds/upcoming", response_model=OddsResponse)
def get_nba_odds_upcoming():
    """NBA Moneyline odds for all upcoming games."""
    try:
        return fetch_moneyline_odds(filter_date=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/odds/by-date", response_model=OddsResponse)
def get_nba_odds_by_date(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """NBA Moneyline odds for a specific date."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return fetch_moneyline_odds(filter_date=date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------
# TRENDS ROUTES
# ------------------------------------------------------
@app.get("/nba/trends", response_model=TrendsResponse)
def get_nba_trends():
    """Return player and team trend summaries."""
    try:
        return get_trends_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/trends/live", response_model=TrendsResponse)
def get_nba_trends_live(team: str | None = Query(None, description="Optional team name filter")):
    """Return live player and team trend summaries, optionally filtered by team."""
    try:
        data = get_trends_summary()

        if team:
            team_lower = team.lower()
            filtered_players = [
                p for p in data.player_trends
                if team_lower in p.player_name.lower() or team_lower.split()[0] in p.player_name.lower()
            ]
            filtered_teams = [
                t for t in data.team_trends if team_lower in t.team_name.lower()
            ]
            data.player_trends = filtered_players
            data.team_trends = filtered_teams

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------
# TEAM DATA ROUTES
# ------------------------------------------------------
@app.get("/nba/offense/teams", response_model=TeamOffenseResponse)
def get_team_offense():
    """Return offensive rankings and averages for all NBA teams."""
    try:
        return fetch_team_offense_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/defense/teams", response_model=TeamDefenseResponse)
def get_team_defense():
    """Return defensive team rankings."""
    try:
        return fetch_team_defense_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------
# PLAYER PERFORMANCE ROUTES
# ------------------------------------------------------
@app.get("/nba/player/performance", response_model=PlayerPerformanceResponse)
def get_player_performance():
    """Return mock player performance data."""
    try:
        player_names = ["LeBron James", "Stephen Curry", "Luka Doncic"]
        players = summarize_players(player_names)
        player_dicts = [p.model_dump() for p in players]

        return PlayerPerformanceResponse(
            date_generated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            players=player_dicts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/player/trends")
def get_player_performance_trends():
    """Return analyzed trend summaries for mock player data."""
    try:
        player_names = ["LeBron James", "Stephen Curry", "Luka Doncic"]
        players = summarize_players(player_names)
        trend_summary = analyze_player_trends([p.dict() for p in players])
        return trend_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/player/insights")
def get_player_insights_route():
    """Return combined player performance and trend analysis."""
    try:
        return get_player_insights()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/player/insights/live")
def get_player_insights_live():
    """Return live player insights from API-Basketball."""
    try:
        return get_live_insights_real()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------
# LIVE DATA ROUTES
# ------------------------------------------------------
@app.get("/nba/live/games/today")
def get_nba_live_games_today():
    """Live NBA games for *today* (API-Basketball)."""
    try:
        return fetch_nba_games_today()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/team/offense/{team_id}")
def get_team_offense_live(team_id: int):
    """Live offensive stats for a team (API-Basketball)."""
    try:
        data = fetch_team_offense_live(team_id)
        return {"ok": True, "team_id": team_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/team/defense/{team_id}")
def get_team_defense_live(team_id: int):
    """Live defensive stats for a team (API-Basketball)."""
    try:
        data = fetch_team_defense_live(team_id)
        return {"ok": True, "team_id": team_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/team/summary/{team_id}")
def get_team_summary_live(team_id: int):
    """Combined offense + defense snapshot for a team."""
    try:
        offense = fetch_team_offense_live(team_id)
        defense = fetch_team_defense_live(team_id)
        return {
            "ok": True,
            "team_id": team_id,
            "season": offense.get("season") or defense.get("season"),
            "offense": offense,
            "defense": defense,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/player/live/{team_id}")
def get_nba_player_live_stats(team_id: int):
    """Return live player stats for the given team."""
    try:
        data = fetch_player_stats(team_id=team_id)
        return {"ok": True, "team_id": team_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nba/player/live/combined/{team_id}")
def get_player_live_combined(team_id: int):
    """Combine live player stats + insights for unified output."""
    try:
        return get_combined_player_live(team_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------
# NARRATIVE ROUTE (LEGACY)
# ------------------------------------------------------
@app.get("/nba/narrative/today")
def get_narrative_today(
    mode: str = Query("template", description="Use 'template' or 'ai' for enhanced GPT narrative")
):
    """Generate daily NBA narrative summary (template or GPT-enhanced)."""
    try:
        mode = mode.lower()
        result = generate_daily_narrative(mode=mode)
        result = dict(result)
        result["mode"] = mode
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
