from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from routes import narrative as narrative_route


def test_pick_lab_shape_and_decision(monkeypatch):
    async def fake_get_daily_narrative(*args, **kwargs):
        return {
            "ok": True,
            "raw": {
                "meta": {
                    "source_counts": {
                        "games_today": 5,
                        "player_trends": 3,
                        "team_trends": 2,
                        "player_props": 20,
                        "odds_games": 8,
                    },
                    "source_status": {
                        "games_today": {"status": "ok", "count": 5, "error": ""},
                        "odds": {"status": "ok", "count": 8, "error": ""},
                        "trends": {"status": "ok", "count": 5, "error": ""},
                        "player_props": {"status": "ok", "count": 20, "error": ""},
                    },
                    "soft_errors": {},
                }
            },
        }

    monkeypatch.setattr(narrative_route, "get_daily_narrative", fake_get_daily_narrative, raising=False)

    client = TestClient(app)
    res = client.get(
        "/nba/picks/lab?pick_type=smart_parlay&legs=3&odds_band=plus_100_to_plus_500&risk_profile=standard&mode=ai&trends=1&cache_ttl=0"
    )
    assert res.status_code == 200
    data = res.json()

    assert data.get("ok") is True
    assert data.get("disclaimer")
    assert isinstance(data.get("constraints"), dict)
    assert data["constraints"]["pick_type"] == "smart_parlay"
    assert data["constraints"]["legs"] == 3

    dq = data.get("data_quality") or {}
    assert isinstance(dq.get("source_counts"), dict)
    assert isinstance(dq.get("source_status"), dict)
    assert isinstance(dq.get("soft_errors"), dict)

    decision = data.get("decision") or {}
    assert decision.get("recommendation") in {"pass", "lean", "bet"}
    assert isinstance(decision.get("rationale"), list)
    assert isinstance(decision.get("risk_flags"), list)


def test_pick_lab_soft_fallback(monkeypatch):
    async def fake_get_daily_narrative_boom(*args, **kwargs):
        raise RuntimeError("narrative unavailable")

    monkeypatch.setattr(
        narrative_route,
        "get_daily_narrative",
        fake_get_daily_narrative_boom,
        raising=False,
    )

    client = TestClient(app)
    res = client.get("/nba/picks/lab?pick_type=lotto_parlay&legs=6")
    assert res.status_code == 200
    data = res.json()

    assert data.get("ok") is True
    assert (data.get("decision") or {}).get("recommendation") == "pass"
    assert "system" in ((data.get("data_quality") or {}).get("soft_errors") or {})
