# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="AI Agent NBA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("🔐 Environment variables loaded:")
    for key in ["OPENAI_API_KEY", "ODDS_API_KEY"]:
        val = os.getenv(key)
        logger.info(f"  {key}: {'✅ Loaded' if val else '❌ Missing'}")
    logger.info(f"  TZ: {os.getenv('TZ', 'America/Los_Angeles')}")

# --- Routes ---
from routes import narrative, nba_games_today
app.include_router(narrative.router)
app.include_router(nba_games_today.router)

@app.get("/")
def root():
    return {"message": "NBA AI Agent Backend is running"}
