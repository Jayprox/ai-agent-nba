# backend/services/narrative_refiner.py
from __future__ import annotations
from typing import Dict, List


def calculate_confidence(avg: float, variance: float) -> str:
    """Classify trend confidence based on variance and deviation."""
    if variance < 2:
        return "High"
    elif variance < 4:
        return "Medium"
    return "Low"


def inject_confidence_and_quotes(narrative_data: dict) -> dict:
    """
    Enriches player_trends with confidence levels and AI-style player quotes.
    """
    player_trends = narrative_data.get("player_trends", [])
    for p in player_trends:
        confidence = calculate_confidence(p.get("average", 0), p.get("variance", 0))
        p["confidence"] = confidence

        # Add a lightweight AI "quote" style remark
        trend_word = (
            "improvement" if p.get("trend_direction") == "up"
            else "adjustment" if p.get("trend_direction") == "down"
            else "consistency"
        )
        p["ai_quote"] = (
            f'"{p.get("player_name", "This player")} continues to show {trend_word} '
            f'with a {confidence.lower()} confidence trend in recent games."'
        )

    narrative_data["player_trends"] = player_trends
    return narrative_data


def refine_narrative_output(summary: str, narrative_data: dict, tone: str = "neutral") -> dict:
    """
    Final formatting pass: enrich metadata, tone, and confidence tiers.
    """
    refined = inject_confidence_and_quotes(narrative_data)

    # Add tone metadata
    refined["tone"] = tone
    refined["summary"] = summary.strip()

    # Optionally inject a tone label or styling hints for frontend
    refined["meta"] = {
        "confidence_levels": [p.get("confidence", "Unknown") for p in refined.get("player_trends", [])],
        "player_count": len(refined.get("player_trends", [])),
        "team_count": len(refined.get("team_trends", [])),
    }

    return refined
