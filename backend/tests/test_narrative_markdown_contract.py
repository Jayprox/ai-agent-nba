# backend/tests/test_narrative_markdown_contract.py
from __future__ import annotations

import sys
from pathlib import Path

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


@pytest.mark.parametrize("mode", ["ai", "template"])
def test_narrative_markdown_contract(monkeypatch, mode: str):
    """
    Contract test for /nba/narrative/markdown:
      - returns ok=true
      - includes required top-level keys
      - includes required raw keys (including games_today)
      - markdown is present and non-empty

    All external/expensive calls are stubbed so this can run offline/CI.
    """

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
    # Stub: odds must be a dict-like object (because your code does odds.get("games"))
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
    # Stub: trends summary (even if narrative currently disables trends via C1,
    # this prevents any accidental agent calls during refactors)
    # -----------------------------
    def fake_get_trends_summary(*args, **kwargs):
        class _T:
            team_trends = []
            player_trends = []

        return _T()

    monkeypatch.setattr(
        narrative_route,
        "get_trends_summary",
        fake_get_trends_summary,
        raising=False,
    )

    # -----------------------------
    # Execute
    # -----------------------------
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
