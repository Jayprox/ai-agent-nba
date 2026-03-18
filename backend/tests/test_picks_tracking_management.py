from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from routes import nba_stats


def _create_pick(client: TestClient) -> str:
    res = client.post(
        "/nba/picks/track",
        json={
            "constraints": {"pick_type": "straight", "legs": 1, "odds_band": "minus_100_to_plus_500", "risk_profile": "standard"},
            "decision": {"recommendation": "lean", "rationale": ["test"], "risk_flags": []},
            "sportsbook_odds_decimal": 1.95,
        },
    )
    assert res.status_code == 200
    return (res.json().get("pick") or {}).get("pick_id")


def test_edit_open_pick(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(nba_stats, "_PICKS_STORE_PATH", tmp_path / "picks_tracking.json", raising=False)
    client = TestClient(app)
    pick_id = _create_pick(client)

    edit = client.patch(
        f"/nba/picks/{pick_id}",
        json={"sportsbook_odds_decimal": 2.05, "stake_units": 1.5, "notes": "line moved pregame"},
    )
    assert edit.status_code == 200
    p = (edit.json().get("pick") or {})
    assert p.get("sportsbook_odds_decimal") == 2.05
    assert p.get("stake_units") == 1.5
    assert p.get("notes") == "line moved pregame"


def test_edit_settled_pick_blocked(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(nba_stats, "_PICKS_STORE_PATH", tmp_path / "picks_tracking.json", raising=False)
    client = TestClient(app)
    pick_id = _create_pick(client)

    settle = client.patch(f"/nba/picks/{pick_id}/settle", json={"result": "win", "stake_units": 1.0})
    assert settle.status_code == 200

    edit = client.patch(f"/nba/picks/{pick_id}", json={"notes": "should fail"})
    assert edit.status_code == 409


def test_delete_pick(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(nba_stats, "_PICKS_STORE_PATH", tmp_path / "picks_tracking.json", raising=False)
    client = TestClient(app)
    pick_id = _create_pick(client)

    delete = client.delete(f"/nba/picks/{pick_id}")
    assert delete.status_code == 200
    body = delete.json()
    assert body.get("ok") is True
    assert body.get("deleted_pick_id") == pick_id

    listed = client.get("/nba/picks/tracked?limit=10")
    assert listed.status_code == 200
    assert listed.json().get("count") == 0
