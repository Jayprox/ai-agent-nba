from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from routes import narrative as narrative_route


def test_pick_lab_parlay_quality_fields_present(monkeypatch):
    async def fake_get_daily_narrative(*args, **kwargs):
        return {
            "ok": True,
            "raw": {
                "meta": {
                    "source_counts": {
                        "games_today": 4,
                        "player_trends": 3,
                        "team_trends": 1,
                        "player_props": 25,
                        "odds_games": 8,
                    },
                    "source_status": {
                        "games_today": {"status": "ok", "count": 4, "error": ""},
                        "odds": {"status": "ok", "count": 8, "error": ""},
                        "trends": {"status": "ok", "count": 4, "error": ""},
                        "player_props": {"status": "ok", "count": 25, "error": ""},
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
    decision = data.get("decision") or {}
    assert isinstance(decision.get("parlay_quality_score"), int)
    assert decision.get("parlay_quality_label") in {"strong", "solid", "fragile", "weak"}
    assert isinstance(decision.get("parlay_quality_reasons"), list)


def test_pick_lab_parlay_weak_quality_for_extreme_constraints(monkeypatch):
    async def fake_get_daily_narrative(*args, **kwargs):
        return {
            "ok": True,
            "raw": {
                "meta": {
                    "source_counts": {
                        "games_today": 0,
                        "player_trends": 0,
                        "team_trends": 0,
                        "player_props": 0,
                        "odds_games": 1,
                    },
                    "source_status": {
                        "games_today": {"status": "no_data", "count": 0, "error": ""},
                        "odds": {"status": "ok", "count": 1, "error": ""},
                        "trends": {"status": "no_data", "count": 0, "error": ""},
                        "player_props": {"status": "no_data", "count": 0, "error": ""},
                    },
                    "soft_errors": {},
                }
            },
        }

    monkeypatch.setattr(narrative_route, "get_daily_narrative", fake_get_daily_narrative, raising=False)

    client = TestClient(app)
    res = client.get(
        "/nba/picks/lab?pick_type=lotto_parlay&legs=8&odds_band=plus_1000_plus&risk_profile=standard&mode=ai&trends=1&cache_ttl=0"
    )
    assert res.status_code == 200
    data = res.json()
    decision = data.get("decision") or {}
    assert decision.get("parlay_quality_label") == "weak"
    assert decision.get("recommendation") == "pass"
