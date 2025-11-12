# backend/services/openai_service.py
from __future__ import annotations
import os, json, re, logging
from datetime import datetime, timezone
from openai import OpenAI
from services.narrative_refiner import refine_narrative_output

logger = logging.getLogger(__name__)

# Initialize OpenAI client only if API key is present
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI client initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize OpenAI client: {e}")
        client = None
else:
    logger.info("⚠️ OPENAI_API_KEY not set - AI mode will use template fallback")


def generate_narrative_summary(narrative_data: dict, mode: str = "template") -> dict:
    """
    Generates + refines the daily NBA narrative.
    Now includes optional Player Prop section.
    """

    if mode == "template":
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
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

        # Old template mode - replaced with new JSON schema
        # return refine_narrative_output(summary.strip(), narrative_data, tone="neutral")
        logger.info("Generating template-based narrative with new JSON schema")
        return _generate_template_fallback(narrative_data, error_msg="")

    # --- AI Mode ---
    elif mode == "ai":
        # Check if OpenAI client is available
        if not client:
            logger.warning("AI mode requested but OpenAI client not available - using template fallback")
            return _generate_template_fallback(narrative_data, error_msg="OpenAI API key not configured")
        
        # Build the AI prompt
        system_prompt = "You are an NBA data analyst who writes concise JSON-based reports."
        
        user_prompt = f"""You are a professional NBA data journalist with access to live stats and betting odds.
Using the JSON data below, write a polished multi-layer report for today's NBA slate.

JSON Input:
{json.dumps(narrative_data, indent=2)}

Instructions:
- Macro Summary — 2–3 paragraphs summarizing key player & team trends.
- Micro Summary — highlight 3–5 key betting/performance insights (prefer from player_props or computed micro_summary).
- Analyst Takeaway — concise 1-paragraph recap (prediction or notable trend continuation).
- Tone — professional, analytical, fan-friendly.

Output strictly as JSON with this exact structure:
{{
  "macro_summary": "string",
  "micro_summary": {{
    "key_edges": [
      {{"text": "string", "edge_score": 7.5, "value_label": "High Value|Moderate|Low"}}
    ],
    "risk_score": 6.8
  }},
  "analyst_takeaway": "string",
  "confidence_summary": ["High", "Medium", "Low"],
  "metadata": {{
    "generated_at": "ISO-8601-UTC",
    "model": "gpt-4o"
  }}
}}"""

        try:
            logger.info("Calling OpenAI API for narrative generation...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1500,
                temperature=0.7,
                timeout=30.0,
            )
            raw_content = response.choices[0].message.content.strip()
            logger.info(f"Received response from OpenAI (length: {len(raw_content)})")
            
            # Extract JSON from response (handle cases where model wraps JSON in prose)
            json_output = _extract_json(raw_content)
            
            # Validate and fill in missing fields
            validated = _validate_narrative_json(json_output)
            
            logger.info("✅ AI narrative generated successfully")
            return validated

        except Exception as e:
            logger.error(f"❌ AI narrative generation failed: {e}")
            return _generate_template_fallback(narrative_data, error_msg=str(e))

    return _generate_template_fallback(narrative_data, error_msg="Invalid mode specified")


def _extract_json(text: str) -> dict:
    """
    Extract JSON object from text, handling cases where the model wraps JSON in prose.
    Looks for the first {...} block in the text.
    """
    # Try to parse the entire text as JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Look for JSON block in the text
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    logger.warning("Failed to extract valid JSON from AI response")
    return {}


def _validate_narrative_json(data: dict) -> dict:
    """
    Validate and fill in missing fields in the AI-generated narrative JSON.
    Ensures the response matches the required schema.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    
    # Ensure macro_summary
    macro_summary = data.get("macro_summary", "")
    if not macro_summary:
        macro_summary = "NBA analysis data is currently being processed."
    
    # Ensure micro_summary structure
    micro_summary = data.get("micro_summary", {})
    if not isinstance(micro_summary, dict):
        micro_summary = {}
    
    key_edges = micro_summary.get("key_edges", [])
    if not isinstance(key_edges, list):
        key_edges = []
    
    # Validate each key_edge
    validated_edges = []
    for edge in key_edges:
        if isinstance(edge, dict):
            validated_edges.append({
                "text": edge.get("text", "Analysis in progress"),
                "edge_score": float(edge.get("edge_score", 5.0)),
                "value_label": edge.get("value_label", "Moderate")
            })
    
    # If no valid edges, create a default one
    if not validated_edges:
        validated_edges = [{
            "text": "Limited data available for analysis",
            "edge_score": 5.0,
            "value_label": "Low"
        }]
    
    risk_score = micro_summary.get("risk_score", 5.0)
    if not isinstance(risk_score, (int, float)):
        risk_score = 5.0
    
    # Ensure analyst_takeaway
    analyst_takeaway = data.get("analyst_takeaway", "")
    if not analyst_takeaway:
        analyst_takeaway = "Monitor trends closely for betting opportunities."
    
    # Ensure confidence_summary
    confidence_summary = data.get("confidence_summary", [])
    if not isinstance(confidence_summary, list) or not confidence_summary:
        confidence_summary = ["Medium"]
    
    # Ensure metadata
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    
    return {
        "macro_summary": macro_summary,
        "micro_summary": {
            "key_edges": validated_edges,
            "risk_score": float(risk_score)
        },
        "analyst_takeaway": analyst_takeaway,
        "confidence_summary": confidence_summary,
        "metadata": {
            "generated_at": metadata.get("generated_at", now_utc),
            "model": metadata.get("model", "gpt-4o")
        }
    }


def _generate_template_fallback(narrative_data: dict, error_msg: str = "") -> dict:
    """
    Generate a template fallback response when AI is unavailable.
    Returns the same JSON schema as AI mode but with template-generated content.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    
    player_trends = narrative_data.get("player_trends", [])
    team_trends = narrative_data.get("team_trends", [])
    odds = narrative_data.get("odds", {})
    games = odds.get("games", []) if isinstance(odds, dict) else []
    props = narrative_data.get("player_props", [])
    
    # Build macro summary
    macro_parts = []
    
    if player_trends:
        trend_text = "Key player trends show "
        highlights = []
        for p in player_trends[:3]:
            arrow = "rising" if p.get("trend_direction") == "up" else "declining" if p.get("trend_direction") == "down" else "stable"
            highlights.append(f"{p.get('player_name', 'Unknown')} with {arrow} {p.get('stat_type', 'performance')} (avg {p.get('average', 0):.1f})")
        trend_text += ", ".join(highlights) + "."
        macro_parts.append(trend_text)
    
    if team_trends:
        team_text = "Team performance indicators reveal "
        team_highlights = []
        for t in team_trends[:2]:
            direction = t.get("trend_direction", "neutral")
            team_highlights.append(f"{t.get('team_name', 'Unknown')} trending {direction} on {t.get('stat_type', 'metrics')}")
        team_text += " and ".join(team_highlights) + "."
        macro_parts.append(team_text)
    
    if games:
        game_text = f"Today's slate features {len(games)} matchups with varying betting opportunities across multiple bookmakers."
        macro_parts.append(game_text)
    
    macro_summary = " ".join(macro_parts) if macro_parts else "NBA data analysis for today's games is in progress."
    
    # Build key edges
    key_edges = []
    
    for p in player_trends[:3]:
        direction = p.get("trend_direction", "neutral")
        edge_score = 7.5 if direction == "up" else 6.0 if direction == "neutral" else 5.5
        value_label = "High Value" if edge_score >= 7.0 else "Moderate" if edge_score >= 6.0 else "Low"
        
        key_edges.append({
            "text": f"{p.get('player_name', 'Player')} showing {direction} trend in {p.get('stat_type', 'performance')}",
            "edge_score": edge_score,
            "value_label": value_label
        })
    
    if props:
        for prop in props[:2]:
            over_rate = prop.get("trend_last5_over", 0)
            edge_score = 7.0 if over_rate >= 4 else 6.0 if over_rate >= 3 else 5.5
            value_label = "High Value" if edge_score >= 7.0 else "Moderate" if edge_score >= 6.0 else "Low"
            
            key_edges.append({
                "text": f"{prop.get('player_name', 'Player')} {prop.get('prop_type', 'prop')} line {prop.get('line', 0)} (Over {over_rate}/5 recent)",
                "edge_score": edge_score,
                "value_label": value_label
            })
    
    if not key_edges:
        key_edges.append({
            "text": "Limited trend data available - monitor for updates",
            "edge_score": 5.0,
            "value_label": "Low"
        })
    
    risk_score = sum(e["edge_score"] for e in key_edges) / len(key_edges) if key_edges else 5.0
    
    # Build analyst takeaway
    analyst_takeaway = "Today's betting landscape presents "
    if risk_score >= 7.0:
        analyst_takeaway += "strong value opportunities with multiple high-confidence trends aligning."
    elif risk_score >= 6.0:
        analyst_takeaway += "moderate opportunities with some favorable trends emerging."
    else:
        analyst_takeaway += "limited high-value edges - recommend cautious approach and monitoring for live betting spots."
    
    if error_msg:
        analyst_takeaway += f" Note: AI analysis unavailable ({error_msg}), using template analysis."
    
    # Build confidence summary
    confidence_summary = []
    for edge in key_edges:
        if edge["edge_score"] >= 7.0:
            confidence_summary.append("High")
        elif edge["edge_score"] >= 6.0:
            confidence_summary.append("Medium")
        else:
            confidence_summary.append("Low")
    
    return {
        "macro_summary": macro_summary,
        "micro_summary": {
            "key_edges": key_edges[:5],  # Limit to 5
            "risk_score": round(risk_score, 1)
        },
        "analyst_takeaway": analyst_takeaway,
        "confidence_summary": list(set(confidence_summary)) if confidence_summary else ["Medium"],
        "metadata": {
            "generated_at": now_utc,
            "model": "template-fallback"
        }
    }
