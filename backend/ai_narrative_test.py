#!/usr/bin/env python3
"""
Smoke test for AI narrative generation.
Usage:
    python3 ai_narrative_test.py          # Test template mode
    python3 ai_narrative_test.py ai       # Test AI mode
"""
import sys
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from services.openai_service import generate_narrative_summary


def create_mock_data():
    """Create mock narrative data for testing."""
    return {
        "date_generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "player_trends": [
            {
                "player_name": "LeBron James",
                "stat_type": "points",
                "average": 25.4,
                "variance": 1.8,
                "trend_direction": "up"
            },
            {
                "player_name": "Stephen Curry",
                "stat_type": "points",
                "average": 27.1,
                "variance": 2.3,
                "trend_direction": "up"
            },
            {
                "player_name": "Luka Doncic",
                "stat_type": "assists",
                "average": 10.8,
                "variance": 1.5,
                "trend_direction": "neutral"
            },
        ],
        "team_trends": [
            {
                "team_name": "Los Angeles Lakers",
                "stat_type": "points",
                "average": 113.2,
                "variance": 5.4,
                "trend_direction": "up"
            },
            {
                "team_name": "Boston Celtics",
                "stat_type": "assists",
                "average": 98.7,
                "variance": 3.2,
                "trend_direction": "neutral"
            },
        ],
        "player_props": [
            {
                "player_name": "Stephen Curry",
                "team": "Warriors",
                "prop_type": "points",
                "line": 29.5,
                "odds_over": -115,
                "odds_under": -105,
                "trend_last5_over": 4
            },
            {
                "player_name": "LeBron James",
                "team": "Lakers",
                "prop_type": "rebounds",
                "line": 8.5,
                "odds_over": -110,
                "odds_under": -110,
                "trend_last5_over": 3
            },
        ],
        "odds": {
            "date": "2025-11-12",
            "games": [
                {
                    "sport_key": "basketball_nba",
                    "commence_time": "2025-11-12T19:00:00Z",
                    "home_team": "Los Angeles Lakers",
                    "away_team": "Golden State Warriors",
                    "moneyline": {
                        "home": {
                            "team": "Los Angeles Lakers",
                            "price": 1.75,
                            "american": -133,
                            "bookmaker": "draftkings"
                        },
                        "away": {
                            "team": "Golden State Warriors",
                            "price": 2.15,
                            "american": 115,
                            "bookmaker": "fanduel"
                        }
                    },
                    "all_bookmakers": ["draftkings", "fanduel"]
                },
                {
                    "sport_key": "basketball_nba",
                    "commence_time": "2025-11-12T20:30:00Z",
                    "home_team": "Boston Celtics",
                    "away_team": "Miami Heat",
                    "moneyline": {
                        "home": {
                            "team": "Boston Celtics",
                            "price": 1.45,
                            "american": -222,
                            "bookmaker": "draftkings"
                        },
                        "away": {
                            "team": "Miami Heat",
                            "price": 2.75,
                            "american": 175,
                            "bookmaker": "fanduel"
                        }
                    },
                    "all_bookmakers": ["draftkings", "fanduel"]
                }
            ]
        }
    }


def validate_schema(result, mode):
    """Validate the output schema."""
    print(f"\n📋 Validating {mode.upper()} mode schema...")
    
    errors = []
    
    # Check for required top-level keys
    if mode == "ai" or (mode == "template" and "macro_summary" in result):
        required_keys = ["macro_summary", "micro_summary", "analyst_takeaway", "confidence_summary", "metadata"]
        for key in required_keys:
            if key not in result:
                errors.append(f"Missing required key: {key}")
        
        # Validate micro_summary structure
        if "micro_summary" in result:
            micro = result["micro_summary"]
            if not isinstance(micro, dict):
                errors.append("micro_summary must be a dict")
            else:
                if "key_edges" not in micro:
                    errors.append("micro_summary missing key_edges")
                elif not isinstance(micro["key_edges"], list):
                    errors.append("key_edges must be a list")
                else:
                    for i, edge in enumerate(micro["key_edges"]):
                        if not isinstance(edge, dict):
                            errors.append(f"key_edges[{i}] must be a dict")
                        else:
                            for field in ["text", "edge_score", "value_label"]:
                                if field not in edge:
                                    errors.append(f"key_edges[{i}] missing {field}")
                
                if "risk_score" not in micro:
                    errors.append("micro_summary missing risk_score")
        
        # Validate metadata structure
        if "metadata" in result:
            meta = result["metadata"]
            if not isinstance(meta, dict):
                errors.append("metadata must be a dict")
            else:
                for field in ["generated_at", "model"]:
                    if field not in meta:
                        errors.append(f"metadata missing {field}")
                        
                if "model" in meta and mode == "template":
                    if meta["model"] != "template-fallback":
                        print(f"⚠️ Warning: Expected model='template-fallback' in template mode, got '{meta['model']}'")
        
        # Validate confidence_summary
        if "confidence_summary" in result:
            conf = result["confidence_summary"]
            if not isinstance(conf, list):
                errors.append("confidence_summary must be a list")
    
    if errors:
        print(f"❌ Schema validation FAILED:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print(f"✅ Schema validation PASSED")
        return True


def main():
    mode = "ai" if len(sys.argv) > 1 and sys.argv[1].lower() == "ai" else "template"
    
    print(f"{'='*60}")
    print(f"AI Narrative Test - {mode.upper()} mode")
    print(f"{'='*60}")
    
    # Check environment
    api_key_set = bool(os.getenv("OPENAI_API_KEY"))
    print(f"\n🔐 Environment Check:")
    print(f"   OPENAI_API_KEY: {'✅ Set' if api_key_set else '❌ Not Set'}")
    
    if mode == "ai" and not api_key_set:
        print(f"\n⚠️ Warning: AI mode requested but OPENAI_API_KEY not set.")
        print(f"   Will fall back to template mode.\n")
    
    # Create mock data
    print(f"\n📊 Creating mock narrative data...")
    mock_data = create_mock_data()
    print(f"   - {len(mock_data.get('player_trends', []))} player trends")
    print(f"   - {len(mock_data.get('team_trends', []))} team trends")
    print(f"   - {len(mock_data.get('player_props', []))} player props")
    print(f"   - {len(mock_data.get('odds', {}).get('games', []))} games with odds")
    
    # Generate narrative
    print(f"\n🤖 Generating narrative summary (mode={mode})...")
    try:
        result = generate_narrative_summary(mock_data, mode=mode)
        
        # Print result
        print(f"\n{'='*60}")
        print(f"Result:")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2))
        print(f"{'='*60}")
        
        # Validate schema
        is_valid = validate_schema(result, mode)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"{'='*60}")
        
        if "metadata" in result:
            print(f"   Model: {result['metadata'].get('model', 'unknown')}")
            print(f"   Generated: {result['metadata'].get('generated_at', 'unknown')}")
        
        if "macro_summary" in result:
            print(f"   Macro summary length: {len(result.get('macro_summary', ''))} chars")
        
        if "micro_summary" in result:
            edges_count = len(result.get('micro_summary', {}).get('key_edges', []))
            risk = result.get('micro_summary', {}).get('risk_score', 0)
            print(f"   Key edges: {edges_count}")
            print(f"   Risk score: {risk}")
        
        if is_valid:
            print(f"\n✅ TEST PASSED - {mode.upper()} mode working correctly")
            return 0
        else:
            print(f"\n❌ TEST FAILED - Schema validation errors")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
