# backend/services/openai_service.py
from __future__ import annotations
import os, json
from datetime import datetime
from openai import OpenAI
from services.narrative_refiner import refine_narrative_output

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_narrative_summary(narrative_data: dict, mode: str = "template") -> dict:
    """
    Generates + refines the daily NBA narrative.
    Now includes optional Player Prop section.
    """

    if mode == "template":
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        player_trends = narrative_data.get("player_trends", [])
        team_trends = narrative_data.get("team_trends", [])
        odds = narrative_data.get("odds", {}).get("games", [])
        props = narrative_data.get("player_props", [])

        summary = f"**NBA Update — {date_str}**\n\nWelcome to today’s NBA roundup!\n\n"

        if player_trends:
            summary += "**Key Player Trends:**\n\n"
            for p in player_trends[:3]:
                arrow = "↑" if p["trend_direction"] == "up" else "↓" if p["trend_direction"] == "down" else "→"
                summary += f"- **{p['player_name']}** {arrow} {p['stat_type']} avg {p['average']:.1f}\n"
            summary += "\n"

        if team_trends:
            summary += "**Team Performance:**\n\n"
            for t in team_trends[:2]:
                summary += f"- {t['team_name']} {t['trend_direction']} on {t['stat_type']} ({t['average']:.1f} avg)\n"
            summary += "\n"

        if props:
            summary += "**Player Props Watch:**\n\n"
            for pr in props[:3]:
                summary += (
                    f"- {pr['player_name']} ({pr['prop_type']}) line {pr['line']} "
                    f"(O:{pr['odds_over']}, U:{pr['odds_under']}) – "
                    f"Over in {pr['trend_last5_over']}/5 recent games\n"
                )
            summary += "\n"

        if odds:
            summary += "**Top Odds Matchups:**\n\n"
            for g in odds[:3]:
                summary += (
                    f"- {g['away_team']} @ {g['home_team']} — "
                    f"{g['home_team']} favored "
                    f"({g['moneyline']['home']['american']}/{g['moneyline']['away']['american']})\n"
                )

        return refine_narrative_output(summary.strip(), narrative_data, tone="neutral")

    # --- AI Mode ---
    elif mode == "ai":
        prompt = f"""
You are an expert NBA betting analyst.
Analyze the following JSON dataset and craft a 2–3 paragraph daily report.

JSON Data:
{json.dumps(narrative_data, indent=2)}

Cover these sections:
1️⃣ **Player Performance Trends** – increases/decreases in points, assists, rebounds.  
2️⃣ **Team Trends** – key offensive/defensive shifts.  
3️⃣ **Matchup Context** – favored teams, close spreads, or underdog angles.  
4️⃣ **Player Props Watch** – mention notable prop lines (if provided) and whether recent form supports Over or Under.  
5️⃣ **Matchup Context** – integrate defensive matchup data (e.g., team defensive ranks vs guards/forwards/centers) to explain how it might influence player or team outcomes.
6️⃣ **Cross-Trend Insights** – connect player and team trajectories. Highlight synergy (e.g., upward player + weak opponent defense) or conflict (e.g., hot player vs elite defense).
7️⃣ **Micro Summary JSON** – summarize top 3–5 actionable insights as compact takeaways. Reference `micro_summary` for `key_edges` and `risk_score`.



Tone = professional analyst, concise (< 250 words).
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a seasoned NBA betting and data analyst."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.7,
            )
            summary = response.choices[0].message.content.strip()
            return refine_narrative_output(summary, narrative_data, tone="analyst")

        except Exception as e:
            fallback = f"⚠️ (GPT rewrite failed: {e})"
            return refine_narrative_output(fallback, narrative_data, tone="error")

    return refine_narrative_output("⚠️ Invalid mode specified.", narrative_data, tone="error")
