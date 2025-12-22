# backend/tests/test_narrative_markdown_contract.py
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


def _install_common_stubs(monkeypatch):
    """
    Install stubs so tests are offline/CI safe and deterministic.
    """

    # Make behavior deterministic even if developer env sets ENABLE_TRENDS_IN_NARRATIVE=0/1.
    # (Overrides still win for trends=0 / trends=1.)
    monkeypatch.setattr(narrative_route, "_ENV_ENABLE_TRENDS", True, raising=False)

    # -----------------------------
    # Stub: narrative generator (AI/template)
    # -----------------------------
    def fake_generate_narrative_summary(data: dict, mode: str = "ai") -> dict:
        return {
            "macro_summary": ["Stub macro summary."],
            "micro_summary": {"key_edges": [], "risk_score": 0.1},
            "analyst_takeaway": "Stub analyst takeaway.",
            "metadata": {"model": "TEST_MODEL"},
        }

    monkeypatch.setattr(
        narrative_route,
        "generate_narrative_summary",
        fake_generate_narrative_summary,
        raising=False,
    )

    # -----------------------------
    # Stub: odds (must be dict-like because route does (odds or {}).get("games"))
    # -----------------------------
    def fake_fetch_moneyline_odds(*args, **kwargs):
        return {"games": []}

    monkeypatch.setattr(
        narrative_route,
        "fetch_moneyline_odds",
        fake_fetch_moneyline_odds,
        raising=False,
    )

    # -----------------------------
    # Stub: API-Basketball games (awaitable in the route)
    # -----------------------------
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
                "league": {
                    "id": 12,
                    "name": "NBA",
                    "season": "2025-2026",
                    "type": "League",
                },
                "venue": "Test Arena",
            }
        ]

    monkeypatch.setattr(
        narrative_route,
        "get_today_games",
        fake_get_today_games,
        raising=False,
    )

    # -----------------------------
    # Stub: trends summary
    # Route expects objects with .model_dump()
    # -----------------------------
    class _FakeTrend:
        def __init__(self, payload: dict):
            self._payload = payload

        def model_dump(self):
            return dict(self._payload)

    def fake_get_trends_summary(*args, **kwargs):
        player_trends_list = [
            _FakeTrend(
                {
                    "player_name": "LeBron James",
                    "stat_type": "points",
                    "average": 25.0,
                    "trend_direction": "up",
                    "last_n_games": 5,
                }
            ),
            _FakeTrend(
                {
                    "player_name": "Stephen Curry",
                    "stat_type": "points",
                    "average": 29.0,
                    "trend_direction": "neutral",
                    "last_n_games": 5,
                }
            ),
            _FakeTrend(
                {
                    "player_name": "Luka Doncic",
                    "stat_type": "assists",
                    "average": 10.0,
                    "trend_direction": "down",
                    "last_n_games": 5,
                }
            ),
        ]

        # SimpleNamespace avoids any class-body scoping issues across Python versions.
        return SimpleNamespace(team_trends=[], player_trends=player_trends_list)

    monkeypatch.setattr(
        narrative_route,
        "get_trends_summary",
        fake_get_trends_summary,
        raising=False,
    )


@pytest.mark.parametrize("mode", ["ai", "template"])
def test_narrative_markdown_contract(monkeypatch, mode: str):
    """
    Contract test for /nba/narrative/markdown:
      - returns ok=true
      - includes required top-level keys
      - includes required raw keys (including games_today)
      - markdown is present and non-empty
    """
    _install_common_stubs(monkeypatch)

    client = TestClient(app)
    res = client.get(f"/nba/narrative/markdown?mode={mode}&cache_ttl=0")
    assert res.status_code == 200

    data = res.json()
    assert data.get("ok") is True, data  # include payload if it fails

    # Top-level contract
    assert isinstance(data.get("summary"), dict)
    assert isinstance(data.get("raw"), dict)
    assert isinstance(data.get("markdown"), str)
    assert data["markdown"].strip() != ""

    # Summary metadata contract
    assert isinstance(data["summary"].get("metadata"), dict)

    # Raw contract (aligns with your jq keys output)
    raw = data["raw"]
    required_raw_keys = {
        "date_generated",
        "games_today",
        "meta",
        "odds",
        "player_props",
        "player_trends",
        "team_trends",
    }
    assert required_raw_keys.issubset(set(raw.keys())), raw.keys()
    assert isinstance(raw.get("meta"), dict)

    # Odds contract (dict + games list)
    assert isinstance(raw.get("odds"), dict)
    assert isinstance(raw["odds"].get("games", []), list)

    # Markdown sanity
    md = data["markdown"]
    assert "**NBA Narrative**" in md
    assert "Macro Summary" in md


@pytest.mark.parametrize(
    "query, expected_override, expected_enabled, expected_min_player_trends",
    [
        ("&trends=0", False, False, 0),
        ("&trends=1", True, True, 1),
    ],
)
def test_trends_override_contract_and_effect(
    monkeypatch,
    query: str,
    expected_override,
    expected_enabled: bool,
    expected_min_player_trends: int,
):
    """
    Contract coverage for trends overrides:
      - raw.meta.trends_override is set when trends query param is provided
      - raw.meta.trends_enabled_in_narrative follows the override
      - raw.player_trends length reflects enabled/disabled (0 when off, >0 when on)
    """
    _install_common_stubs(monkeypatch)

    client = TestClient(app)
    res = client.get(f"/nba/narrative/markdown?mode=ai&cache_ttl=0{query}")
    assert res.status_code == 200

    data = res.json()
    assert data.get("ok") is True, data

    raw = data.get("raw") or {}
    assert isinstance(raw, dict)

    meta = raw.get("meta") or {}
    assert isinstance(meta, dict)

    # Override contract
    assert meta.get("trends_override") == expected_override

    # Enabled flag contract
    assert meta.get("trends_enabled_in_narrative") is expected_enabled

    # Effect contract
    player_trends = raw.get("player_trends", [])
    assert isinstance(player_trends, list)
    assert len(player_trends) >= expected_min_player_trends
    if expected_enabled is False:
        assert len(player_trends) == 0
