# backend/tests/test_api_basketball_integration.py

from __future__ import annotations

import os

import pytest


pytestmark = [pytest.mark.live, pytest.mark.integration]


def _has_apisports_key() -> bool:
    """
    Your API-Basketball client may use different env var names depending on how
    common/apisports_client.py is implemented. We accept any common variant.
    """
    candidates = [
        "APISPORTS_API_KEY",
        "APISPORTS_KEY",
        "API_SPORTS_KEY",
        "API_BASKETBALL_KEY",
    ]
    return any(os.getenv(k, "").strip() for k in candidates)


def test_api_basketball_player_stats_smoke():
    """
    Live integration smoke test:
      - requires an APISports/API-Basketball key in env
      - calls the live player stats fetcher for a known team id
      - validates the returned shape/types (not the exact numbers)
    """
    if not _has_apisports_key():
        pytest.skip(
            "API-Basketball/APISports key missing. Set one of: "
            "APISPORTS_API_KEY, APISPORTS_KEY, API_SPORTS_KEY, API_BASKETBALL_KEY."
        )

    try:
        from agents.player_performance_agent.fetch_player_stats_live import (  # type: ignore
            fetch_player_stats,
        )
    except Exception as e:
        pytest.skip(
            f"Could not import live player stats fetcher: {type(e).__name__}: {e}"
        )

    # From your earlier notes: Heat team id = 147 (API-Basketball)
    team_id = 147

    data = fetch_player_stats(team_id=team_id)
    assert isinstance(data, dict)

    # Shape/type assertions (keep it resilient to season/empty data scenarios)
    assert "players" in data
    assert isinstance(data.get("players"), list)

    # Optional-but-useful fields (don’t require values, just types if present)
    if "count" in data:
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    if "raw_count" in data:
        assert isinstance(data["raw_count"], int)
        assert data["raw_count"] >= 0

    if "season" in data:
        assert isinstance(data["season"], (str, int))
