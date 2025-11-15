# backend/test_refiner.py
import argparse
import json
from services.narrative_refiner import refine_narrative_output
from services.openai_service import generate_narrative_summary



def run_local_refiner():
    """Runs the local mock test using only the narrative_refiner."""
    mock_data = {
        "player_trends": [
            {"player_name": "Luka Doncic", "trend_direction": "up", "average": 28.5, "variance": 1.3},
            {"player_name": "LeBron James", "trend_direction": "down", "average": 22.4, "variance": 4.8},
            {"player_name": "Stephen Curry", "trend_direction": "neutral", "average": 25.1, "variance": 2.9},
        ],
        "team_trends": [
            {"team_name": "Los Angeles Lakers", "trend_direction": "up", "stat_type": "points"},
            {"team_name": "Boston Celtics", "trend_direction": "down", "stat_type": "assists"},
        ],
    }

    summary_text = "Daily NBA narrative summary generated from test_refiner.py"
    refined = refine_narrative_output(summary_text, mock_data, tone="analyst")

    print("\n🧩 LOCAL TEST OUTPUT (no AI call):\n")
    print(json.dumps(refined, indent=2))


def run_ai_refiner():
    """Runs the AI-powered pipeline test (OpenAI -> refinement layer)."""
    mock_data = {
        "player_trends": [
            {"player_name": "Luka Doncic", "trend_direction": "up", "average": 28.5, "variance": 1.3},
            {"player_name": "LeBron James", "trend_direction": "down", "average": 22.4, "variance": 4.8},
            {"player_name": "Stephen Curry", "trend_direction": "neutral", "average": 25.1, "variance": 2.9},
        ],
        "team_trends": [
            {"team_name": "Los Angeles Lakers", "trend_direction": "up", "stat_type": "points"},
            {"team_name": "Boston Celtics", "trend_direction": "down", "stat_type": "assists"},
        ],
        "odds": {
            "date": "2025-11-10",
            "games": [
                {
                    "home_team": "Phoenix Suns",
                    "away_team": "New Orleans Pelicans",
                    "moneyline": {
                        "home": {"team": "Phoenix Suns", "american": -312},
                        "away": {"team": "New Orleans Pelicans", "american": 260},
                    },
                }
            ],
        },
    }

    print("\n⚙️ CALLING OpenAI GPT → Refinement Layer...\n")

    result = generate_narrative_summary(mock_data, mode="ai")

    print("\n✅ AI TEST OUTPUT (GPT + refinement):\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the narrative refiner pipeline.")
    parser.add_argument("--ai", action="store_true", help="Run AI-powered test instead of local mode.")
    args = parser.parse_args()

    if args.ai:
        run_ai_refiner()
    else:
        run_local_refiner()
