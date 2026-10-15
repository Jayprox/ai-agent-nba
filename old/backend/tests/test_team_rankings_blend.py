from __future__ import annotations

from routes import nba_stats


def test_build_live_offense_teams_blended_model(monkeypatch):
    def fake_rows():
        return [
            {"team_name": "Team A", "win_prob": 0.65},
            {"team_name": "Team B", "win_prob": 0.55},
            {"team_name": "Team C", "win_prob": 0.45},
        ]

    def fake_props(max_total: int = 400):
        return {
            "Team A": {"prop_entries": 40.0, "points_line_avg": 27.0},
            "Team B": {"prop_entries": 10.0, "points_line_avg": 21.0},
            "Team C": {"prop_entries": 20.0, "points_line_avg": 24.0},
        }

    monkeypatch.setattr(nba_stats, "_collect_live_team_market_rows", fake_rows, raising=False)
    monkeypatch.setattr(nba_stats, "_collect_props_team_signals", fake_props, raising=False)

    teams = nba_stats._build_live_offense_teams(limit=3)
    assert len(teams) == 3
    assert teams[0]["source"] == "live_blended_odds_props"
    assert "ranking_model" in teams[0]
    assert "signal_inputs" in teams[0]
    assert teams[0]["rank_overall"] == 1


def test_build_live_defense_teams_blended_model(monkeypatch):
    def fake_rows():
        return [
            {"team_name": "Team A", "win_prob": 0.65},
            {"team_name": "Team B", "win_prob": 0.55},
            {"team_name": "Team C", "win_prob": 0.45},
        ]

    # Team C has lowest points-line context, should get some defense boost.
    def fake_props(max_total: int = 400):
        return {
            "Team A": {"prop_entries": 25.0, "points_line_avg": 28.0},
            "Team B": {"prop_entries": 20.0, "points_line_avg": 24.0},
            "Team C": {"prop_entries": 15.0, "points_line_avg": 18.0},
        }

    monkeypatch.setattr(nba_stats, "_collect_live_team_market_rows", fake_rows, raising=False)
    monkeypatch.setattr(nba_stats, "_collect_props_team_signals", fake_props, raising=False)

    teams = nba_stats._build_live_defense_teams(limit=3)
    assert len(teams) == 3
    assert teams[0]["source"] == "live_blended_odds_props"
    assert "ranking_model" in teams[0]
    assert "signal_inputs" in teams[0]
    assert all("composite_score" in t["signal_inputs"] for t in teams)
