from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from routes import nba_stats


def test_track_and_list_picks(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(nba_stats, "_PICKS_STORE_PATH", tmp_path / "picks_tracking.json", raising=False)

    client = TestClient(app)
    track_payload = {
        "constraints": {
            "pick_type": "smart_parlay",
            "legs": 3,
            "odds_band": "plus_100_to_plus_500",
            "risk_profile": "standard",
        },
        "decision": {
            "recommendation": "lean",
            "rationale": ["Coverage is mixed."],
            "risk_flags": ["games_today: no_data"],
        },
        "sportsbook_odds_decimal": 1.95,
    }
    res = client.post("/nba/picks/track", json=track_payload)
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    pick = data.get("pick") or {}
    assert pick.get("pick_id")
    assert pick.get("status") == "open"
    assert pick.get("pick_type") == "smart_parlay"

    res2 = client.get("/nba/picks/tracked?limit=5")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("ok") is True
    assert data2.get("count") == 1
    assert len(data2.get("picks") or []) == 1


def test_settle_pick_and_performance(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(nba_stats, "_PICKS_STORE_PATH", tmp_path / "picks_tracking.json", raising=False)

    client = TestClient(app)
    create = client.post(
        "/nba/picks/track",
        json={
            "constraints": {"pick_type": "straight", "legs": 1, "odds_band": "minus_100_to_plus_500", "risk_profile": "standard"},
            "decision": {"recommendation": "bet", "rationale": ["good setup"], "risk_flags": []},
            "sportsbook_odds_decimal": 2.1,
        },
    )
    assert create.status_code == 200
    pick_id = (create.json().get("pick") or {}).get("pick_id")
    assert pick_id

    settle = client.patch(
        f"/nba/picks/{pick_id}/settle",
        json={"result": "win", "closing_odds_decimal": 1.9, "stake_units": 1.0},
    )
    assert settle.status_code == 200
    settled_pick = (settle.json().get("pick") or {})
    assert settled_pick.get("status") == "settled"
    assert settled_pick.get("result") == "win"
    assert settled_pick.get("pnl_units") == 1.1
    assert settled_pick.get("clv") == -0.2

    perf = client.get("/nba/picks/performance")
    assert perf.status_code == 200
    p = perf.json()
    assert p.get("ok") is True
    overall = p.get("overall") or {}
    assert overall.get("settled") == 1
    assert overall.get("wins") == 1
    assert overall.get("roi") == 1.1
    assert (p.get("by_pick_type") or {}).get("straight", {}).get("settled") == 1
