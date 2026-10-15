# tests/test_openai_output.py
import os, sys
from pathlib import Path
from dotenv import load_dotenv

# --- Ensure backend root is on sys.path ---
BACKEND_ROOT = Path(__file__).resolve().parent.parent  # go up from /tests to /backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

print("📁 Added to sys.path:", BACKEND_ROOT)

# --- Load environment variables from .env file ---
env_path = BACKEND_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"🔐 .env loaded from: {env_path}")
else:
    print(f"⚠️  No .env file found at: {env_path}")

# --- Check if OPENAI_API_KEY is now loaded ---
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    print(f"✅ OPENAI_API_KEY loaded: {openai_key[:10]}... (hidden)")
else:
    print("❌ OPENAI_API_KEY still not found after loading .env")

# --- Import target function ---
from services.openai_service import generate_narrative_summary

print("🔍 Testing generate_narrative_summary(mode='ai')\n")

# --- Minimal test data ---
data = {"player_trends": [], "team_trends": [], "odds": {"games": []}}

result = generate_narrative_summary(data, mode="ai")

print("✅ Type:", type(result))
print("✅ Value:\n", result)