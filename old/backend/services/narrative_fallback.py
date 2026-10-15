# backend/services/narrative_fallback.py


from __future__ import annotations

from typing import Any, Dict, List

def build_fallback_narrative(games: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Minimal narrative payload that is ALWAYS available.
    Keep it simple and stable; frontend expects markdown anyway.
    """
    if not games:
        return {
            "macro_summary": "No games were returned for today’s slate.",
            "key_edges": [],
            "risk_score": 1.0,
            "analyst_takeaway": "No slate data available; verify upstream schedule source.",
            "metadata": {"fallback": True},
        }

    # Very basic macro summary
    macro = f"Today's NBA slate features {len(games)} games. " \
            "This is a fallback narrative (AI unavailable or invalid output)."

    # Create a few simple “edges”
    edges = []
    for g in games[:3]:
        away = (
            (g.get("away_team") or {}).get("name")
            or g.get("away_name")
            or g.get("away")
            or "Away"
        )
        home = (
            (g.get("home_team") or {}).get("name")
            or g.get("home_name")
            or g.get("home")
            or "Home"
        )
        edges.append({
            "matchup": f"{away} @ {home}",
            "score": None,
            "note": "Baseline matchup listed; AI edge scoring unavailable.",
        })

    return {
        "macro_summary": macro,
        "key_edges": edges,
        "risk_score": 0.9,
        "analyst_takeaway": "Treat this as a status-safe summary until AI output is restored.",
        "metadata": {"fallback": True},
    }
