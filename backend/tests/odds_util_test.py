# backend/tests/odds_util_test.py

"""
Pytest verification for common.odds_utils.get_todays_odds()

Goal:
- Ensure odds helper returns a dict with stable structure
- Stay OFFLINE/CI-safe by stubbing network calls
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# -----------------------------
# Make backend/ importable
# -----------------------------
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parents[1]  # .../backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from common import odds_utils  # noqa: E402


def test_get_todays_odds_contract_offline(monkeypatch):
    """
    Offline-safe contract test:
      - get_todays_odds() returns a dict
      - contains keys: date, games
      - games is a list
    """

    # Clear module cache to avoid cross-test contamination
    monkeypatch.setattr(odds_utils, "_CACHE", {}, raising=False)

    # Stub outbound HTTP call used by fetch_moneyline_odds()
    # odds_utils imports `get_json` into its own module namespace, so patch odds_utils.get_json.
    monkeypatch.setattr(odds_utils, "get_json", lambda *args, **kwargs: [], raising=True)

    # ODDS_API_KEY is used only to build params; stub for clarity
    monkeypatch.setattr(odds_utils, "ODDS_API_KEY", "TEST_KEY", raising=False)

    out = odds_utils.get_todays_odds()

    assert isinstance(out, dict)
    assert "date" in out
    assert "games" in out
    assert isinstance(out["games"], list)


def test_fetch_moneyline_odds_returns_empty_games_when_no_events(monkeypatch):
    """
    If the odds provider returns an empty list, fetch_moneyline_odds() should return a valid OddsResponse with games=[].
    """

    monkeypatch.setattr(odds_utils, "_CACHE", {}, raising=False)
    monkeypatch.setattr(odds_utils, "get_json", lambda *args, **kwargs: [], raising=True)
    monkeypatch.setattr(odds_utils, "ODDS_API_KEY", "TEST_KEY", raising=False)

    resp = odds_utils.fetch_moneyline_odds(filter_date=None, cache_ttl=0)

    # OddsResponse is a pydantic model in your project; validate the expected interface.
    assert hasattr(resp, "games")
    assert isinstance(resp.games, list)
    assert len(resp.games) == 0
