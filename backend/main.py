# backend/main.py
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -------------------------------------------------
# 🌍 Load environment variables on every reload
# -------------------------------------------------
load_dotenv()

# -------------------------------------------------
# 🧠 Logging setup
# -------------------------------------------------
logger = logging.getLogger("main")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

# -------------------------------------------------
# ⚙️ Config helpers
# -------------------------------------------------
def _parse_allowed_origins() -> List[str]:
    """
    Returns a list of allowed frontend origins for CORS.
    Includes both localhost and 127.0.0.1 for ports 3000 and 5173 by default.
    """
    origins_env = os.getenv("ALLOWED_ORIGINS", "")
    if not origins_env.strip():
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000"
        ]
    return [origin.strip() for origin in origins_env.split(",") if origin.strip()]


OPENAI_OK = bool(os.getenv("OPENAI_API_KEY"))
ODDS_OK = bool(os.getenv("ODDS_API_KEY"))
TZ = os.getenv("TZ", "Not set")
ALLOWED_ORIGINS = _parse_allowed_origins()

logger.info("🔐 Environment variables loaded:")
logger.info(f"  OPENAI_API_KEY: {'✅ Loaded' if OPENAI_OK else '❌ Missing'}")
logger.info(f"  ODDS_API_KEY: {'✅ Loaded' if ODDS_OK else '❌ Missing'}")
logger.info(f"  TZ: {TZ}")
logger.info(f"  ALLOWED_ORIGINS: {ALLOWED_ORIGINS}")

# -------------------------------------------------
# ⚙️ FastAPI app setup
# -------------------------------------------------
app = FastAPI(
    title="AI Agent - NBA Narrative Backend",
    version="1.0.0",
    description="Backend service providing NBA data, odds, and AI-driven narratives.",
)

# -------------------------------------------------
# 🌐 CORS Middleware (Wildcard Dev Mode)
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 📂 Import route modules after app is initialized
# -------------------------------------------------
from routes import nba_games_today, narrative  # noqa: E402

# -------------------------------------------------
# 🛤️ Register route modules
# -------------------------------------------------
app.include_router(nba_games_today.router)
app.include_router(narrative.router)

# -------------------------------------------------
# 🏠 Root endpoint
# -------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "🏀 AI Agent NBA Backend is running!",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "narrative_today": "/nba/narrative/today",
            "narrative_markdown": "/nba/narrative/markdown",
            "games_today": "/nba/games/today",
            "docs": "/docs"
        }
    }

# -------------------------------------------------
# 🧪 Health check endpoint
# -------------------------------------------------
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "openai_configured": OPENAI_OK,
            "odds_configured": ODDS_OK,
            "timezone": TZ
        }
    }
