# backend/agents/narrative_agent/generate_narrative.py
from __future__ import annotations
import os, sys, requests
import random
from datetime import datetime, timezone
from typing import Dict, Any, List
from openai import OpenAI

# ----------------------- Setup -----------------------
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

BASE_URL = "http://127.0.0.1:8000"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# ----------------------- Helpers -----------------------
def _fetch_json(endpoint: str) -> Dict[str, Any]:
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def summarize_team(team_data: Dict[str, Any]) -> str:
    off = team_data.get("offense", {})
    dfn = team_data.get("defense", {})
    pts, opp = off.get("points_per_game"), dfn.get("points_allowed")
    if not pts or not opp:
        return "Team averages are currently unavailable."
    trend = "strong offensively" if pts > opp else "defensively challenged"
    return f"The team scores {pts} PPG while allowing {opp} PPG, appearing {trend}."


def summarize_trends(trends: Dict[str, Any]) -> List[str]:
    lines = []
    for p in trends.get("player_trends", []):
        arrow = "↑" if p["trend_direction"] == "up" else "↓" if p["trend_direction"] == "down" else "→"
        lines.append(
            f"{p['player_name']} {arrow} {p['stat_type']} avg {p['average']:.1f} ({p['trend_direction']})."
        )
    for t in trends.get("team_trends", []):
        arrow = "↑" if t["trend_direction"] == "up" else "↓" if t["trend_direction"] == "down" else "→"
        lines.append(
            f"{t['team_name']} {arrow} trend on {t['stat_type']} ({t['average']} avg)."
        )
    return lines


def summarize_odds(odds: Dict[str, Any]) -> List[str]:
    lines = []
    for g in odds.get("games", [])[:5]:
        home, away = g["home_team"], g["away_team"]
        h, a = g["moneyline"]["home"]["american"], g["moneyline"]["away"]["american"]
        fav = home if h < 0 else away
        lines.append(f"{away} @ {home} — {fav} favored ({h}/{a}).")
    return lines


# ----------------------- Template Summary -----------------------
def build_template_summary() -> Dict[str, Any]:
    trends = _fetch_json("/nba/trends/live")
    team = _fetch_json("/nba/team/summary/134")
    odds = _fetch_json("/nba/odds/today")

    team_summary = summarize_team(team)
    trend_lines = summarize_trends(trends)
    odds_lines = summarize_odds(odds)

    text = (
        f"📊 Daily NBA Summary — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"{team_summary}\n\n"
        "🧠 Key Trends:\n" + "\n".join(trend_lines[:3]) + "\n\n"
        "💸 Top Odds Matchups:\n" + "\n".join(odds_lines[:3])
    )

    return {
        "ok": True,
        "summary": text,
        "insights": trend_lines + odds_lines,
        "raw": {"trends": trends, "team": team, "odds": odds},
    }


# ----------------------- GPT-Rewrite -----------------------
def enhance_with_gpt(summary_text: str) -> str:
    if not client:
        return summary_text + "\n\n⚠️ (OpenAI API key missing — using template text.)"
    prompt = (
        "Rewrite the following NBA daily summary into a clear, natural, engaging narrative "
        "for fans, keeping all key facts and stats:\n\n" + summary_text
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NBA analyst providing concise narratives."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return summary_text + f"\n\n⚠️ (GPT rewrite failed: {e})"


# ----------------------- Public API -----------------------
def generate_daily_narrative():
    """
    Gathers player trends, team stats, odds,
    and now auto-injects mock player props.
    """

    player_trends = [
        {"player_name": "LeBron James", "stat_type": "points", "average": 25.4, "trend_direction": "up"},
        {"player_name": "Stephen Curry", "stat_type": "points", "average": 27.1, "trend_direction": "up"},
        {"player_name": "Luka Doncic", "stat_type": "assists", "average": 10.8, "trend_direction": "neutral"},
    ]

    team_trends = [
        {"team_name": "Los Angeles Lakers", "stat_type": "points", "average": 113.2, "trend_direction": "up"},
        {"team_name": "Boston Celtics", "stat_type": "assists", "average": 98.7, "trend_direction": "neutral"},
    ]

    # --- 🔥 Inject sample player props ---
    mock_props = [
        {
            "player_name": "Stephen Curry",
            "team": "Warriors",
            "prop_type": "points",
            "line": 29.5,
            "odds_over": -115,
            "odds_under": -105,
            "trend_last5_over": random.randint(2, 5),
        },
        {
            "player_name": "LeBron James",
            "team": "Lakers",
            "prop_type": "rebounds",
            "line": 8.5,
            "odds_over": -110,
            "odds_under": -110,
            "trend_last5_over": random.randint(2, 5),
        },
        {
            "player_name": "Luka Doncic",
            "team": "Mavericks",
            "prop_type": "assists",
            "line": 10.5,
            "odds_over": -120,
            "odds_under": 100,
            "trend_last5_over": random.randint(2, 5),
        },
    ]

    odds = get_todays_odds()  # your current odds integration

    # --- 🛡️ New: Defensive matchup context ---
    defensive_matchups = [
        {
            "team_name": "Charlotte Hornets",
            "def_rank_vs_guards": 28,
            "def_rank_vs_forwards": 18,
            "def_rank_vs_centers": 22,
        },
        {
            "team_name": "Milwaukee Bucks",
            "def_rank_vs_guards": 7,
            "def_rank_vs_forwards": 4,
            "def_rank_vs_centers": 10,
        },
        {
            "team_name": "Washington Wizards",
            "def_rank_vs_guards": 30,
            "def_rank_vs_forwards": 25,
            "def_rank_vs_centers": 27,
        },
    ]

    # --- 🧩 Cross-Trend Analysis ---
    cross_trends = []
    for p in player_trends:
        name = p["player_name"]
        stat = p["stat_type"]
        direction = p["trend_direction"]

        if direction == "up":
            cross_trends.append(f"{name} trending upward in {stat}, aligning with offensive improvements for his team.")
        elif direction == "down":
            cross_trends.append(f"{name} trending downward in {stat}, which may limit team scoring potential.")
        else:
            cross_trends.append(f"{name} showing steady {stat} performance, maintaining consistency.")

    for team in team_trends:
        tname = team["team_name"]
        if team["trend_direction"] == "up":
            cross_trends.append(f"{tname} trending up offensively — may sustain strong performance if defense holds.")
        elif team["trend_direction"] == "down":
            cross_trends.append(f"{tname} facing offensive slowdown — could signal regression risk.")

    # --- 🧮 Micro-Summary ---
    risk_score = round(random.uniform(5.0, 9.5), 1)
# --- 🧩 Cross-Trend Analysis ---
    cross_trends = []
    for p in player_trends:
        name = p["player_name"]
        stat = p["stat_type"]
        direction = p["trend_direction"]

        if direction == "up":
            cross_trends.append(f"{name} trending upward in {stat}, aligning with offensive improvements for his team.")
        elif direction == "down":
            cross_trends.append(f"{name} trending downward in {stat}, which may limit team scoring potential.")
        else:
            cross_trends.append(f"{name} showing steady {stat} performance, maintaining consistency.")

    for team in team_trends:
        tname = team["team_name"]
        if team["trend_direction"] == "up":
            cross_trends.append(f"{tname} trending up offensively — may sustain strong performance if defense holds.")
        elif team["trend_direction"] == "down":
            cross_trends.append(f"{tname} facing offensive slowdown — could signal regression risk.")

    # --- 🧮 Automated Value Tagging ---
    def map_value_label(score: float) -> str:
        if score >= 8.0:
            return "High Value"
        elif score >= 6.0:
            return "Moderate"
        return "Low"

    key_edges = []
    for text in cross_trends[:5]:
        edge_score = round(random.uniform(5.0, 9.5), 1)
        key_edges.append({
            "text": text,
            "edge_score": edge_score,
            "value_label": map_value_label(edge_score)
        })

    risk_score = round(sum(edge["edge_score"] for edge in key_edges) / len(key_edges), 1)

    micro_summary = {
        "key_edges": key_edges,
        "risk_score": risk_score
    }


    return {
        "date_generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "player_trends": player_trends,
        "team_trends": team_trends,
        "player_props": mock_props,
        "defensive_matchups": defensive_matchups,
        "odds": odds,
        "micro_summary": micro_summary,  # 👈 new structured insight layer
    }


if __name__ == "__main__":
    data = generate_daily_narrative(mode="template")
    print(data["summary"])
