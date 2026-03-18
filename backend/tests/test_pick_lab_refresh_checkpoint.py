from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from routes import narrative as narrative_route


def test_pick_lab_refresh_checkpoint_present(monkeypatch):
    async def fake_get_daily_narrative(*args, **kwargs):
        return {
            "ok": True,
            "summary": {"metadata": {"generated_at": "2026-03-18T00:00:00+00:00"}},
            "raw": {
                "meta": {
                    "cache_used": False,
                    "cache_expires_in_s": 0,
                    "source_counts": {
                        "games_today": 0,
                        "player_trends": 3,
                        "team_trends": 0,
                        "player_props": 20,
                        "odds_games": 8,
                    },
                    "source_status": {
                        "games_today": {"status": "no_data", "count": 0, "error": ""},
                        "odds": {"status": "ok", "count": 8, "error": ""},
                        "trends": {"status": "ok", "count": 3, "error": ""},
                        "player_props": {"status": "ok", "count": 20, "error": ""},
                    },
                    "soft_errors": {},
                }
            },
        }

    monkeypatch.setattr(narrative_route, "get_daily_narrative", fake_get_daily_narrative, raising=False)

    client = TestClient(app)
    res = client.get("/nba/picks/lab?pick_type=straight&legs=1")
    assert res.status_code == 200
    data = res.json()
    rc = ((data.get("data_quality") or {}).get("refresh_checkpoint") or {})
    assert isinstance(rc, dict)
    assert "is_stale" in rc
    assert isinstance(rc.get("stale_reasons"), list)
    assert isinstance(rc.get("pre_bet_checklist"), list)
