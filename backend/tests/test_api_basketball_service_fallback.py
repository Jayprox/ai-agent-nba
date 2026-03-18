from __future__ import annotations

import pytest

from services import api_basketball_service as svc


@pytest.mark.asyncio
async def test_get_today_games_uses_odds_fallback_when_api_empty(monkeypatch):
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    monkeypatch.setenv("ODDS_API_KEY", "test_key")

    monkeypatch.setattr(
        svc,
        "apisports_get",
        lambda *args, **kwargs: {"errors": {"plan": "restricted"}, "response": []},
        raising=False,
    )
    monkeypatch.setattr(svc, "_today_local_str", lambda tz_name: "2026-03-10", raising=False)
    monkeypatch.setattr(
        svc,
        "get_json",
        lambda url, params: [
            {
                "id": "evt_1",
                "commence_time": "2026-03-10T23:30:00Z",
                "home_team": "Boston Celtics",
                "away_team": "Miami Heat",
            },
            {
                "id": "evt_2",
                "commence_time": "2026-03-11T23:30:00Z",
                "home_team": "Lakers",
                "away_team": "Warriors",
            },
        ],
        raising=False,
    )

    games = await svc.get_today_games()
    assert isinstance(games, list)
    assert len(games) == 1
    assert games[0]["source"] == "odds_fallback"
    assert games[0]["home_team"]["name"] == "Boston Celtics"
    assert games[0]["away_team"]["name"] == "Miami Heat"
