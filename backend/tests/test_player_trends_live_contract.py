from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from routes import nba_stats


def test_player_trends_live_handles_missing_season_ppg(monkeypatch):
    def fake_live_players(max_players: int = 20):
        return [
            {
                "player_name": "Donovan Mitchell",
                "ppg": 27.5,
                "season_ppg": None,
                "trend": "up",
            },
            {
                "player_name": "Evan Mobley",
                "ppg": 18.2,
                "season_ppg": None,
                "trend": "neutral",
            },
        ]

    monkeypatch.setattr(
        nba_stats,
        "_build_live_player_metrics_from_props",
        fake_live_players,
        raising=False,
    )

    client = TestClient(app)
    res = client.get("/nba/player/trends?mode=live")
    assert res.status_code == 200
    data = res.json()

    assert data.get("mode") == "live"
    assert isinstance(data.get("summary"), list)
    assert len(data["summary"]) == 2
    assert data["summary"][0]["player_name"] == "Donovan Mitchell"
