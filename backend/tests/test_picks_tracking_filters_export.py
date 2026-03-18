from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from routes import nba_stats


def _track(client: TestClient, pick_type: str, recommendation: str = "lean"):
    return client.post(
        "/nba/picks/track",
        json={
            "constraints": {
                "pick_type": pick_type,
                "legs": 1,
                "odds_band": "minus_100_to_plus_500",
                "risk_profile": "standard",
            },
            "decision": {"recommendation": recommendation, "rationale": ["x"], "risk_flags": []},
            "sportsbook_odds_decimal": 1.9,
        },
    )


def test_tracked_filters_and_csv_export(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(nba_stats, "_PICKS_STORE_PATH", tmp_path / "picks_tracking.json", raising=False)
    client = TestClient(app)

    r1 = _track(client, "straight")
    assert r1.status_code == 200
    p1 = (r1.json().get("pick") or {}).get("pick_id")
    r2 = _track(client, "smart_parlay")
    assert r2.status_code == 200
    p2 = (r2.json().get("pick") or {}).get("pick_id")

    # settle one as win
    s1 = client.patch(f"/nba/picks/{p1}/settle", json={"result": "win", "stake_units": 1.0})
    assert s1.status_code == 200

    # settle other as loss
    s2 = client.patch(f"/nba/picks/{p2}/settle", json={"result": "loss", "stake_units": 1.0})
    assert s2.status_code == 200

    wins = client.get("/nba/picks/tracked?result=win")
    assert wins.status_code == 200
    wins_body = wins.json()
    assert wins_body.get("count") == 1
    assert (wins_body.get("picks") or [])[0].get("result") == "win"

    by_type = client.get("/nba/picks/tracked?pick_type=smart_parlay")
    assert by_type.status_code == 200
    by_type_body = by_type.json()
    assert by_type_body.get("count") == 1
    assert (by_type_body.get("picks") or [])[0].get("pick_type") == "smart_parlay"

    csv_res = client.get("/nba/picks/tracked/export.csv?result=loss")
    assert csv_res.status_code == 200
    assert csv_res.headers.get("content-type", "").startswith("text/csv")
    assert "attachment; filename=picks_tracked_export.csv" in csv_res.headers.get("content-disposition", "")
    text = csv_res.text
    assert "pick_id" in text
    assert "smart_parlay" in text
    assert "loss" in text
