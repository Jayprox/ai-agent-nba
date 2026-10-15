"""
sanity_check_live_api.py
Verifies API-Basketball connectivity, authentication, and response structure.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = os.getenv("API_BASKETBALL_BASE", "https://v1.basketball.api-sports.io")

def sanity_check():
    print("\n🏀 Running API-Basketball Live Sanity Check...\n")

    if not API_KEY:
        print("❌ Missing API_BASKETBALL_KEY in .env file.")
        return

    headers = {"x-apisports-key": API_KEY}

    # Quick endpoint test (season + team info)
    url = f"{BASE_URL}/seasons"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"❌ Request failed. Status code: {res.status_code}")
            print(res.text)
            return
        data = res.json()
        print("✅ API connection successful.")
        print(f"Available seasons (showing first 5): {data.get('response', [])[:5]}")
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")

if __name__ == "__main__":
    sanity_check()
