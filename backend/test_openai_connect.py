# backend/test_openai_connect.py
import os
from openai import OpenAI
from dotenv import load_dotenv

def main():
    # Explicitly load .env for standalone tests
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"🔐 .env loaded from: {env_path}")
    else:
        print("⚠️  No .env file found next to this script.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment.")
        print("   Try running: export OPENAI_API_KEY='sk-yourkeyhere'")
        return

    print(f"✅ OPENAI_API_KEY loaded: {api_key[:10]}... (hidden)")

    try:
        client = OpenAI(api_key=api_key)
        resp = client.models.list()
        print(f"✅ Models retrieved: {len(resp.data)}")
        for m in resp.data[:5]:
            print("  -", m.id)
    except Exception as e:
        print("❌ Error communicating with OpenAI:", e)

if __name__ == "__main__":
    main()
