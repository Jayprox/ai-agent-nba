from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from routes import narrative as narrative_route
from routes import nba_stats


def test_pick_lab_diagnostics_snapshot_updates(monkeypatch):
    async def fake_get_daily_narrative(*args, **kwargs):
        return {
            "ok": True,
            "summary": {"metadata": {"generated_at": "2026-03-18T00:00:00+00:00"}},
            "raw": {
                "meta": {
                    "source_counts": {
                        "games_today": 2,
                        "player_trends": 3,
                        "team_trends": 0,
                        "player_props": 12,
                        "odds_games": 5,
                    },
                    "source_status": {
                        "games_today": {"status": "ok", "count": 2, "error": ""},
                        "odds": {"status": "ok", "count": 5, "error": ""},
                        "trends": {"status": "ok", "count": 3, "error": ""},
                        "player_props": {"status": "error", "count": 0, "error": "props unavailable"},
                    },
                    "soft_errors": {"player_props": "props unavailable"},
                    "cache_used": False,
                    "cache_expires_in_s": 0,
                }
            },
        }

    monkeypatch.setattr(narrative_route, "get_daily_narrative", fake_get_daily_narrative, raising=False)

    client = TestClient(app)
    res = client.get("/nba/picks/lab")
    assert res.status_code == 200

    diag = client.get("/nba/picks/diagnostics")
    assert diag.status_code == 200
    body = diag.json()
    assert body.get("ok") is True
    sources = body.get("sources") or {}
    assert sources.get("games_today", {}).get("last_status") == "ok"
    assert sources.get("player_props", {}).get("last_status") == "error"
    assert sources.get("player_props", {}).get("last_error")


def test_pick_lab_retry_endpoint(monkeypatch):
    async def fake_games():
        return [{"id": 1}, {"id": 2}]

    monkeypatch.setattr(nba_stats, "get_today_games", fake_games, raising=False)
    monkeypatch.setattr(nba_stats, "fetch_moneyline_odds", lambda *a, **k: {"games": [{"id": 1}]}, raising=False)
    monkeypatch.setattr(
        nba_stats,
        "get_trends_summary",
        lambda *a, **k: type("X", (), {"player_trends": [1], "team_trends": []})(),
        raising=False,
    )
    monkeypatch.setattr(nba_stats, "fetch_player_props_for_today", lambda *a, **k: [{"id": 1}], raising=False)

    client = TestClient(app)
    res = client.post("/nba/picks/diagnostics/retry?source=all")
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    assert data.get("retried") == "all"
    src = data.get("sources") or {}
    assert src.get("games_today", {}).get("last_status") == "ok"
    assert src.get("odds", {}).get("last_status") in {"ok", "no_data"}
