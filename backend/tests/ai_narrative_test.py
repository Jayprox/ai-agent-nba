# backend/tests/ai_narrative_test.py

"""
Pytest smoke test for /nba/narrative/markdown

Goal:
- Confirm the narrative endpoint returns ok=true and markdown is present
- Stay OFFLINE/CI-safe by stubbing upstream dependencies
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# -----------------------------
# Make backend/ importable
# -----------------------------
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parents[1]  # .../backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402
from routes import narrative as narrative_route  # noqa: E402


def _install_offline_stubs(monkeypatch):
    """
    Stubs all external dependencies so this test is stable and does not hit the network.
    """

    # Force trends feature flag behavior to be deterministic
    monkeypatch.setattr(narrative_route, "_ENV_ENABLE_TRENDS", True, raising=False)

    # Ensure AI is treated as allowed here (we’re not testing gating in this file)
    monkeypatch.setattr(narrative_route, "_ai_allowed", lambda: True, raising=False)

    # Stub narrative generator
    def fake_generate_narrative_summary(data: dict, mode: str = "ai") -> dict:
        return {
            "macro_summary": ["Offline stub macro summary."],
            "micro_summary": {"key_edges": [], "risk_score": 0.2, "risk_rationale": "Offline stub."},
            "analyst_takeaway": "Offline stub analyst takeaway.",
            "confidence_summary": ["Medium"],
            "metadata": {"model": "OFFLINE_TEST_MODEL"},
        }

    monkeypatch.setattr(
        narrative_route,
        "generate_narrative_summary",
        fake_generate_narrative_summary,
        raising=False,
    )

    # Stub odds fetch
    monkeypatch.setattr(
        narrative_route,
        "fetch_moneyline_odds",
        lambda *args, **kwargs: {"games": []},
        raising=False,
    )

    # Stub API-Basketball games
    async def fake_get_today_games(*args, **kwargs):
        return [
            {
                "id": 1,
                "date": "2025-12-17T17:00:00-08:00",
                "timestamp": 1766029200,
                "timezone": "America/Los_Angeles",
                "home_team": {"name": "Home Team"},
                "away_team": {"name": "Away Team"},
                "status": {"long": "Not Started", "short": "NS", "timer": None},
                "league": {"id": 12, "name": "NBA", "season": "2025-2026", "type": "League"},
                "venue": "Test Arena",
            }
        ]

    monkeypatch.setattr(narrative_route, "get_today_games", fake_get_today_games, raising=False)

    # Stub trends summary (optional)
    class _FakeTrend:
        def __init__(self, payload: dict):
            self._payload = payload

        def model_dump(self):
            return dict(self._payload)

    def fake_get_trends_summary(*args, **kwargs):
        return SimpleNamespace(
            team_trends=[],
            player_trends=[
                _FakeTrend(
                    {
                        "player_name": "LeBron James",
                        "stat_type": "points",
                        "average": 25.0,
                        "trend_direction": "up",
                        "last_n_games": 5,
                    }
                )
            ],
        )

    monkeypatch.setattr(narrative_route, "get_trends_summary", fake_get_trends_summary, raising=False)


def test_ai_narrative_markdown_smoke_offline(monkeypatch):
    _install_offline_stubs(monkeypatch)

    client = TestClient(app)
    res = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=0&trends=1")
    assert res.status_code == 200

    data = res.json()
    assert data.get("ok") is True, data
    assert isinstance(data.get("markdown"), str)
    assert data["markdown"].strip() != ""
    assert "**NBA Narrative**" in data["markdown"]
