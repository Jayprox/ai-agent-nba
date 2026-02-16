from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from agents.team_offense_agent.fetch_offense import fetch_team_offense_data
from agents.team_defense_agent.fetch_defense import fetch_team_defense_data
from agents.trends_agent.fetch_trends import get_trends_summary
from agents.player_performance_agent.fetch_player_performance import summarize_players
from agents.player_performance_agent.fetch_insights import get_player_insights
from agents.player_performance_agent.analyze_trends import analyze_player_trends
from common.odds_utils import fetch_moneyline_odds
from common.player_props_utils import fetch_player_props_for_today

router = APIRouter(prefix="/nba", tags=["NBA Stats"])


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _props_based_trend(points_line: Optional[float]) -> str:
    if points_line is None:
        return "neutral"
    if points_line >= 25:
        return "up"
    if points_line <= 17:
        return "down"
    return "neutral"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decimal_to_win_prob(decimal_price: Optional[float]) -> Optional[float]:
    if decimal_price is None:
        return None
    try:
        d = float(decimal_price)
    except Exception:
        return None
    if d <= 1.0:
        return None
    return 1.0 / d


def _rank_30_from_score(score: float, values: List[float], reverse: bool = True) -> int:
    ordered = sorted(values, reverse=reverse)
    for i, v in enumerate(ordered, start=1):
        if v == score:
            return i
    return len(ordered)


def _collect_live_team_market_rows() -> List[Dict[str, Any]]:
    odds = fetch_moneyline_odds(None, cache_ttl=30)
    rows: List[Dict[str, Any]] = []

    for g in odds.games or []:
        home_team = g.home_team
        away_team = g.away_team
        moneyline = g.moneyline or {}
        home_ml = moneyline.get("home") if isinstance(moneyline, dict) else None
        away_ml = moneyline.get("away") if isinstance(moneyline, dict) else None
        home_price = (
            home_ml.get("price")
            if isinstance(home_ml, dict)
            else getattr(home_ml, "price", None)
        )
        away_price = (
            away_ml.get("price")
            if isinstance(away_ml, dict)
            else getattr(away_ml, "price", None)
        )
        home_prob = _decimal_to_win_prob(home_price)
        away_prob = _decimal_to_win_prob(away_price)
        if not home_team or not away_team:
            continue

        rows.append(
            {
                "team_name": home_team,
                "opponent": away_team,
                "is_home": True,
                "win_prob": home_prob,
                "commence_time": g.commence_time,
            }
        )
        rows.append(
            {
                "team_name": away_team,
                "opponent": home_team,
                "is_home": False,
                "win_prob": away_prob,
                "commence_time": g.commence_time,
            }
        )

    return rows


def _build_live_offense_teams(limit: int = 20) -> List[Dict[str, Any]]:
    rows = _collect_live_team_market_rows()
    if not rows:
        return []

    scores: Dict[str, float] = {}
    for r in rows:
        team = str(r.get("team_name") or "")
        p = _safe_float(r.get("win_prob")) or 0.5
        scores[team] = max(scores.get(team, 0.0), p)

    all_scores = list(scores.values())
    teams: List[Dict[str, Any]] = []
    for team_name, win_prob in scores.items():
        offense_score = round(95.0 + (win_prob * 30.0), 1)
        assists = round(17.0 + (win_prob * 10.0), 1)
        rebounds = round(40.0 + ((1.0 - win_prob) * 6.0), 1)
        rank = _rank_30_from_score(win_prob, all_scores, reverse=True)
        teams.append(
            {
                "team_name": team_name,
                "rank_overall": rank,
                "rank_pg": min(30, rank + 1),
                "rank_sg": min(30, rank + 2),
                "rank_sf": min(30, rank + 3),
                "rank_pf": min(30, rank + 4),
                "rank_c": min(30, rank + 5),
                "points_per_game": offense_score,
                "assists_per_game": assists,
                "rebounds_per_game": rebounds,
                "source": "live_odds_proxy",
            }
        )

    teams.sort(key=lambda t: (t.get("rank_overall") or 999, t.get("team_name") or ""))
    return teams[:limit]


def _build_live_defense_teams(limit: int = 20) -> List[Dict[str, Any]]:
    rows = _collect_live_team_market_rows()
    if not rows:
        return []

    scores: Dict[str, float] = {}
    for r in rows:
        team = str(r.get("team_name") or "")
        p = _safe_float(r.get("win_prob")) or 0.5
        scores[team] = max(scores.get(team, 0.0), p)

    all_scores = list(scores.values())
    teams: List[Dict[str, Any]] = []
    for team_name, win_prob in scores.items():
        defense_score = round(116.0 - (win_prob * 8.0), 1)
        opp_points = round(114.0 - (win_prob * 10.0), 1)
        opp_rebounds = round(47.0 - (win_prob * 4.0), 1)
        opp_assists = round(27.0 - (win_prob * 4.0), 1)
        rank = _rank_30_from_score(win_prob, all_scores, reverse=True)
        teams.append(
            {
                "team_name": team_name,
                "rank_overall": rank,
                "defensive_rating": defense_score,
                "opp_points_per_game": opp_points,
                "opp_rebounds_per_game": opp_rebounds,
                "opp_assists_per_game": opp_assists,
                "rank_pg_def": min(30, rank + 1),
                "rank_sg_def": min(30, rank + 2),
                "rank_sf_def": min(30, rank + 3),
                "rank_pf_def": min(30, rank + 4),
                "rank_c_def": min(30, rank + 5),
                "source": "live_odds_proxy",
            }
        )

    teams.sort(key=lambda t: (t.get("rank_overall") or 999, t.get("team_name") or ""))
    return teams[:limit]


def _build_live_player_metrics_from_props(max_players: int = 20) -> List[Dict[str, Any]]:
    """
    Build live-ish player cards from current player props markets.
    This gives real current-slate player names/signals even when basketball stats APIs are constrained.
    """
    props = fetch_player_props_for_today(max_total=300)
    by_player: Dict[str, Dict[str, Any]] = {}

    market_to_stat = {
        "player_points": "ppg",
        "player_rebounds": "rpg",
        "player_assists": "apg",
        "player_threes": "tpm",
    }

    for p in props:
        name = str(p.get("player_name") or "").strip()
        if not name:
            continue
        player = by_player.setdefault(
            name,
            {
                "player_name": name,
                "matchup": p.get("matchup"),
                "markets_seen": set(),
                "lines": {"ppg": [], "rpg": [], "apg": [], "tpm": []},
            },
        )
        market = str(p.get("market") or "")
        stat_key = market_to_stat.get(market)
        if stat_key:
            line = _safe_float(p.get("line"))
            if line is not None:
                player["lines"][stat_key].append(line)
                player["markets_seen"].add(market)

    players_out: List[Dict[str, Any]] = []
    for _, p in by_player.items():
        line_agg = {}
        for stat_key, lines in p["lines"].items():
            line_agg[stat_key] = round(sum(lines) / len(lines), 1) if lines else None

        trend = _props_based_trend(line_agg.get("ppg"))
        verdict = (
            "Live props indicate strong scoring expectation."
            if trend == "up"
            else "Live props indicate modest scoring expectation."
            if trend == "down"
            else "Live props indicate neutral scoring expectation."
        )

        players_out.append(
            {
                "player_name": p["player_name"],
                "ppg": line_agg.get("ppg"),
                "rpg": line_agg.get("rpg"),
                "apg": line_agg.get("apg"),
                "tpm": line_agg.get("tpm"),
                "season_ppg": None,
                "season_rpg": None,
                "season_apg": None,
                "season_tpm": None,
                "trend": trend,
                "verdict": verdict,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "source": "live_player_props",
                "markets_seen": len(p["markets_seen"]),
                "matchup": p.get("matchup"),
            }
        )

    players_out.sort(
        key=lambda x: (
            x.get("ppg") is not None,
            x.get("ppg") or 0.0,
            x.get("markets_seen") or 0,
        ),
        reverse=True,
    )
    return players_out[:max_players]


def _fallback_mock_players() -> List[Dict[str, Any]]:
    mock_path = Path(__file__).resolve().parents[1] / "common" / "mock_data" / "player_performance.json"
    names: List[str] = []
    try:
        with open(mock_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("data", []) if isinstance(data, dict) else []
        names = [str(r.get("player_name")) for r in rows if r.get("player_name")]
    except Exception:
        names = []

    if not names:
        return []

    players = summarize_players(names[:20])
    return [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in players]


def _build_live_trends_payload() -> Dict[str, Any]:
    players = _build_live_player_metrics_from_props(max_players=20)
    team_rows = _collect_live_team_market_rows()

    player_trends = [
        {
            "player_name": p.get("player_name"),
            "stat_type": "points",
            "average": float(p.get("ppg") or 0.0),
            "weighted_avg": float(p.get("ppg") or 0.0),
            "variance": 0.0,
            "trend_direction": p.get("trend") or "neutral",
            "last_n_games": 1,
        }
        for p in players
    ]

    team_by_name: Dict[str, float] = {}
    for row in team_rows:
        team = str(row.get("team_name") or "")
        prob = _safe_float(row.get("win_prob")) or 0.5
        if team:
            team_by_name[team] = max(team_by_name.get(team, 0.0), prob)

    team_trends = []
    for team, prob in sorted(team_by_name.items(), key=lambda kv: kv[1], reverse=True):
        direction = "up" if prob >= 0.55 else "down" if prob <= 0.45 else "neutral"
        team_trends.append(
            {
                "team_name": team,
                "stat_type": "market_strength",
                "average": round(prob * 100.0, 2),
                "weighted_avg": round(prob * 100.0, 2),
                "variance": 0.0,
                "trend_direction": direction,
                "last_n_games": 1,
            }
        )

    return {
        "date_generated": _now_iso(),
        "player_trends": player_trends,
        "team_trends": team_trends,
        "meta": {
            "provider": "live_odds_player_props",
            "count_player_trends": len(player_trends),
            "count_team_trends": len(team_trends),
        },
    }


@router.get("/offense/teams")
async def offense_teams() -> Dict[str, Any]:
    live_error = ""
    try:
        teams = _build_live_offense_teams(limit=20)
        if teams:
            return {
                "date_generated": _now_iso(),
                "teams": teams,
                "source": "live_odds_proxy",
            }
    except Exception as e:
        live_error = f"{type(e).__name__}: {e}"

    try:
        data = fetch_team_offense_data()
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        payload["source"] = "mock_fallback"
        if live_error:
            payload["live_error"] = live_error
        return payload
    except Exception as e:
        return {
            "date_generated": _now_iso(),
            "teams": [],
            "source": "empty_fallback",
            "error": f"{type(e).__name__}: {e}",
            "live_error": live_error,
        }


@router.get("/defense/teams")
async def defense_teams() -> Dict[str, Any]:
    live_error = ""
    try:
        teams = _build_live_defense_teams(limit=20)
        if teams:
            return {
                "date_generated": _now_iso(),
                "teams": teams,
                "source": "live_odds_proxy",
            }
    except Exception as e:
        live_error = f"{type(e).__name__}: {e}"

    try:
        data = fetch_team_defense_data()
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        payload["source"] = "mock_fallback"
        if live_error:
            payload["live_error"] = live_error
        return payload
    except Exception as e:
        return {
            "date_generated": _now_iso(),
            "teams": [],
            "source": "empty_fallback",
            "error": f"{type(e).__name__}: {e}",
            "live_error": live_error,
        }


@router.get("/trends")
async def trends() -> Dict[str, Any]:
    try:
        data = get_trends_summary()
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        payload.setdefault("meta", {})
        payload["meta"]["provider"] = "mock"
        return payload
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"trends failed: {type(e).__name__}: {e}") from e


@router.get("/trends/live")
async def trends_live() -> Dict[str, Any]:
    try:
        payload = _build_live_trends_payload()
        if payload.get("player_trends") or payload.get("team_trends"):
            return payload
        return await trends()
    except Exception:
        return await trends()


@router.get("/player/performance")
async def player_performance() -> Dict[str, Any]:
    try:
        try:
            payload = _build_live_player_metrics_from_props(max_players=20)
        except Exception:
            payload = []
        if not payload:
            payload = _fallback_mock_players()
        return {
            "ok": True,
            "date_generated": _now_iso(),
            "players": payload,
            "source": "live_player_props" if payload and payload[0].get("source") == "live_player_props" else "mock_fallback",
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"player_performance failed: {type(e).__name__}: {e}") from e


@router.get("/player/trends")
async def player_trends(mode: str = Query("mock", description="mock or live")) -> Dict[str, Any]:
    try:
        if mode == "live":
            player_dicts = _build_live_player_metrics_from_props(max_players=20)
            if not player_dicts:
                player_dicts = _fallback_mock_players()
        else:
            player_dicts = _fallback_mock_players()

        trend_summary = analyze_player_trends(player_dicts)
        trend_summary["mode"] = mode
        return trend_summary
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"player_trends failed: {type(e).__name__}: {e}") from e


@router.get("/player/insights")
async def player_insights() -> Dict[str, Any]:
    try:
        payload = get_player_insights()
        payload["mode"] = "mock"
        return payload
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"player_insights failed: {type(e).__name__}: {e}") from e


@router.get("/player/insights/live")
async def player_insights_live() -> Dict[str, Any]:
    try:
        live_players = _build_live_player_metrics_from_props(max_players=20)
        if not live_players:
            # Preserve endpoint shape with safe fallback.
            payload = get_player_insights()
            payload["mode"] = "mock_fallback"
            return payload

        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "mode": "live",
            "insights": [
                {
                    "player_name": p.get("player_name"),
                    "ppg": p.get("ppg"),
                    "rpg": p.get("rpg"),
                    "apg": p.get("apg"),
                    "tpm": p.get("tpm"),
                    "season_ppg": p.get("season_ppg"),
                    "season_rpg": p.get("season_rpg"),
                    "season_apg": p.get("season_apg"),
                    "trend": p.get("trend"),
                    "verdict": p.get("verdict"),
                    "matchup": p.get("matchup"),
                    "source": p.get("source"),
                }
                for p in live_players
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"player_insights_live failed: {type(e).__name__}: {e}") from e
