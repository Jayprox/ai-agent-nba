# backend/test_env_load.py
"""
Simple environment validation script to confirm .env variables are loading correctly.
Run with:
    python3 test_env_load.py
"""

import os
import pathlib
from dotenv import load_dotenv

# Determine backend directory and .env path
backend_dir = pathlib.Path(__file__).parent
dotenv_path = backend_dir / ".env"

print(f"🔍 Checking for .env at: {dotenv_path}")

# Load .env explicitly
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    key = os.getenv("OPENAI_API_KEY")
    if key:
        print(f"✅ OPENAI_API_KEY loaded successfully: {key[:10]}... (hidden)")
    else:
        print("⚠️ .env file found but OPENAI_API_KEY is missing or blank.")
else:
    print("❌ No .env file found in backend directory.")

# Optional: check for ODDS_API_KEY too
odds_key = os.getenv("ODDS_API_KEY")
if odds_key:
    print(f"✅ ODDS_API_KEY loaded successfully: {odds_key[:8]}... (hidden)")
else:
    print("⚠️ ODDS_API_KEY not found.")
