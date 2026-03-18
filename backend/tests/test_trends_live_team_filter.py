from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from routes import nba_stats


def test_trends_live_team_filter(monkeypatch):
    def fake_live_payload():
        return {
            "date_generated": "2026-01-01T00:00:00+00:00",
            "player_trends": [
                {
                    "player_name": "Donovan Mitchell",
                    "stat_type": "points",
                    "average": 27.5,
                    "trend_direction": "up",
                    "last_n_games": 1,
                    "matchup": "Orlando Magic @ Cleveland Cavaliers",
                },
                {
                    "player_name": "Jayson Tatum",
                    "stat_type": "points",
                    "average": 29.1,
                    "trend_direction": "up",
                    "last_n_games": 1,
                    "matchup": "Boston Celtics @ New York Knicks",
                },
            ],
            "team_trends": [
                {
                    "team_name": "Cleveland Cavaliers",
                    "stat_type": "market_strength",
                    "average": 63.2,
                    "trend_direction": "up",
                    "last_n_games": 1,
                },
                {
                    "team_name": "Boston Celtics",
                    "stat_type": "market_strength",
                    "average": 58.9,
                    "trend_direction": "up",
                    "last_n_games": 1,
                },
            ],
            "meta": {
                "provider": "live_odds_player_props",
                "count_player_trends": 2,
                "count_team_trends": 2,
            },
        }

    monkeypatch.setattr(nba_stats, "_build_live_trends_payload", fake_live_payload, raising=False)

    client = TestClient(app)
    res = client.get("/nba/trends/live?team=Cleveland%20Cavaliers")
    assert res.status_code == 200
    data = res.json()

    assert data.get("meta", {}).get("filtered_for_team") == "Cleveland Cavaliers"
    assert len(data.get("player_trends", [])) == 1
    assert len(data.get("team_trends", [])) == 1
    assert data["player_trends"][0]["player_name"] == "Donovan Mitchell"
    assert data["team_trends"][0]["team_name"] == "Cleveland Cavaliers"


def test_trends_live_team_filter_no_match_returns_empty(monkeypatch):
    def fake_live_payload():
        return {
            "date_generated": "2026-01-01T00:00:00+00:00",
            "player_trends": [],
            "team_trends": [],
            "meta": {"provider": "live_odds_player_props"},
        }

    monkeypatch.setattr(nba_stats, "_build_live_trends_payload", fake_live_payload, raising=False)

    client = TestClient(app)
    res = client.get("/nba/trends/live?team=Unknown%20Team")
    assert res.status_code == 200
    data = res.json()
    assert data.get("meta", {}).get("filtered_for_team") == "Unknown Team"
    assert data.get("player_trends") == []
    assert data.get("team_trends") == []


def test_trends_live_team_filter_on_live_error_returns_empty_not_mock(monkeypatch):
    def fake_live_payload_error():
        raise RuntimeError("upstream live unavailable")

    monkeypatch.setattr(nba_stats, "_build_live_trends_payload", fake_live_payload_error, raising=False)

    client = TestClient(app)
    res = client.get("/nba/trends/live?team=Milwaukee%20Bucks")
    assert res.status_code == 200
    data = res.json()
    assert data.get("meta", {}).get("provider") == "live_unavailable"
    assert data.get("meta", {}).get("filtered_for_team") == "Milwaukee Bucks"
    assert data.get("player_trends") == []
    assert data.get("team_trends") == []
