# backend/ai_narrative_test.py
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

# ✅ Load .env BEFORE importing openai_service so OPENAI_API_KEY exists at import time
from dotenv import load_dotenv
load_dotenv()

from services.openai_service import generate_narrative_summary


def _mask(value: str | None, keep: int = 8) -> str:
    if not value:
        return "None"
    if len(value) <= keep:
        return value
    return f"{value[:keep]}..."


def _now_utc_str(fmt: str = "%Y-%m-%d %H:%M UTC") -> str:
    return datetime.now(timezone.utc).strftime(fmt)


def build_sample_payload() -> Dict[str, Any]:
    """Minimal, deterministic sample payload for quick smoke tests."""
    return {
        "date_generated": _now_utc_str(),
        "player_trends": [
            {"player_name": "LeBron James", "stat_type": "points", "average": 25.3, "trend_direction": "up"},
            {"player_name": "Stephen Curry", "stat_type": "points", "average": 29.7, "trend_direction": "up"},
        ],
        "team_trends": [
            {"team_name": "Los Angeles Lakers", "stat_type": "points", "average": 118.2, "trend_direction": "up"},
            {"team_name": "Golden State Warriors", "stat_type": "points", "average": 112.4, "trend_direction": "down"},
        ],
        "player_props": [
            {
                "player_name": "LeBron James",
                "team": "Lakers",
                "prop_type": "points",
                "line": 26.5,
                "odds_over": -110,
                "odds_under": -110,
            },
            {
                "player_name": "Stephen Curry",
                "team": "Warriors",
                "prop_type": "threes",
                "line": 4.5,
                "odds_over": -120,
                "odds_under": 100,
            },
        ],
        "odds": {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "games": [
                {
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "moneyline": {
                        "home": {"american": -150},
                        "away": {"american": 130},
                    },
                }
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate NBA narrative summary via services.openai_service (template or AI mode)."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["template", "ai"],
        default="template",
        help="Output mode. Default: template",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON (no pretty indent).",
    )
    args = parser.parse_args()

    mode = args.mode
    pretty = not args.compact

    # Key presence banner (masked)
    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"🎯 Generating NBA Narrative Summary (mode: {mode.upper()})...\n")
    if openai_key:
        print(f"✅ OPENAI_API_KEY loaded: { _mask(openai_key) } (hidden)\n")
    else:
        if mode == "ai":
            print("⚠️  OPENAI_API_KEY missing! AI mode will fallback to template.\n")

    # Build deterministic sample payload
    sample_data = build_sample_payload()

    # Generate
    summary = generate_narrative_summary(sample_data, mode=mode)

    print("✅ AI Narrative Generated!\n")
    if pretty:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(summary, separators=(",", ":"), ensure_ascii=False))

    # Helpful post-run tips
    print(
        "\n🧠 Hints:\n"
        "• Run `python3 ai_narrative_test.py` → template mode\n"
        "• Run `python3 ai_narrative_test.py ai` → AI (GPT-4o) mode\n"
        "• Add `--compact` for single-line JSON output"
    )


if __name__ == "__main__":
    main()
