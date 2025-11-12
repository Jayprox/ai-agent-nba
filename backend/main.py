# backend/main.py
from __future__ import annotations

import os
import logging
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
    Read ALLOWED_ORIGINS from env (comma-separated).
    Defaults to ['*'] for local/dev.
    Example:
      ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:5173
    """
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    # Support JSON-like array or comma-separated string
    if raw.startswith("[") and raw.endswith("]"):
        # crude parse without json import: strip [ ] and split by comma
        inner = raw[1:-1]
        parts = [p.strip().strip("'").strip('"') for p in inner.split(",") if p.strip()]
        return parts or ["*"]
    return [p.strip() for p in raw.split(",") if p.strip()] or ["*"]


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
# 🌐 CORS Middleware
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 🧩 Route Imports
# -------------------------------------------------
from routes import nba_games_today, narrative  # noqa: E402

# -------------------------------------------------
# 🔗 Register Routers
# -------------------------------------------------
app.include_router(nba_games_today.router)
app.include_router(narrative.router)

# -------------------------------------------------
# 🏁 Root Endpoint
# -------------------------------------------------
@app.get("/")
def root():
    return {
        "ok": True,
        "message": "🏀 AI Agent NBA Backend is running!",
        "routes": [
            "/nba/narrative/today?mode=ai",
            "/nba/narrative/today?mode=template",
            "/nba/games/today",
            "/health",
        ],
    }

# -------------------------------------------------
# 🩺 Health Endpoint
# -------------------------------------------------
_STARTED_AT = datetime.now(timezone.utc)

@app.get("/health")
def health():
    now = datetime.now(timezone.utc)
    uptime = (now - _STARTED_AT).total_seconds()
    return {
        "status": "ok",
        "started_at": _STARTED_AT.isoformat(),
        "uptime_seconds": int(uptime),
        "env": {
            "openai_key": "present" if OPENAI_OK else "missing",
            "odds_key": "present" if ODDS_OK else "missing",
            "tz": TZ,
        },
        "cors": {
            "allow_origins": ALLOWED_ORIGINS,
        },
        "version": "1.0.0",
        "service": "AI Agent - NBA Narrative Backend",
    }

# -------------------------------------------------
# 🧪 Run Server (optional manual entry)
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
