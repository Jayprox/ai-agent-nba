# backend/services/openai_service.py

import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI, OpenAIError

logger = logging.getLogger("openai_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

LOG_AI_RAW = os.getenv("LOG_AI_RAW", "0") == "1"

# -------------------------
# Lazy OpenAI client cache
# -------------------------
_client: Optional[OpenAI] = None
_client_key_fingerprint: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _fingerprint_key(key: str) -> str:
    k = key.strip()
    if not k:
        return "empty"
    return f"len:{len(k)}:tail:{k[-6:]}"


def _get_openai_client() -> Optional[OpenAI]:
    global _client, _client_key_fingerprint

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        _client = None
        _client_key_fingerprint = None
        return None

    fp = _fingerprint_key(api_key)
    if _client is None or _client_key_fingerprint != fp:
        try:
            _client = OpenAI(api_key=api_key)
            _client_key_fingerprint = fp
            logger.info(f"✅ OpenAI client ready (key {fp})")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {type(e).__name__}: {e}")
            _client = None
            _client_key_fingerprint = None

    return _client


def _build_slate_grounding(games_today: list[dict]) -> str:
    if not games_today:
        return "Today’s NBA slate: 0 games returned from API-Basketball."

    lines = [f"Today’s NBA slate (API-Basketball): {len(games_today)} games"]
    for g in games_today[:15]:
        away = (g.get("away_team") or {}).get("name", "Away")
        home = (g.get("home_team") or {}).get("name", "Home")
        venue = g.get("venue") or "Venue TBD"
        time_val = g.get("time") or "—"
        tz = g.get("timezone") or ""
        status = (g.get("status") or {}).get("long") or (g.get("status") or {}).get("short") or "Scheduled"
        lines.append(f"- {away} @ {home} — {time_val} {tz} — {venue} — Status: {status}")
    return "\n".join(lines)


def _build_data_coverage_block(data: Dict[str, Any]) -> str:
    """
    Compact input coverage summary so the model can explicitly handle sparse data.
    """
    games_today = data.get("games_today") or []
    odds_games = (data.get("odds") or {}).get("games", []) or []
    player_trends = data.get("player_trends") or []
    team_trends = data.get("team_trends") or []
    player_props = data.get("player_props") or []
    return (
        "Input coverage snapshot:\n"
        f"- games_today_count: {len(games_today)}\n"
        f"- odds_games_count: {len(odds_games)}\n"
        f"- player_trends_count: {len(player_trends)}\n"
        f"- team_trends_count: {len(team_trends)}\n"
        f"- player_props_count: {len(player_props)}"
    )


def _try_parse_json(text: str) -> Dict[str, Any]:
    """
    Robust JSON parsing:
    1) direct json.loads
    2) strip ```json fences
    3) extract first {...} block
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Empty AI output")

    # 1) Direct
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
        raise ValueError("JSON parsed but not an object")
    except json.JSONDecodeError:
        pass

    # 2) Strip code fences
    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = cleaned.strip().lstrip("`")
        cleaned = cleaned.replace("json\n", "", 1)
        cleaned = cleaned.replace("JSON\n", "", 1)
        cleaned = cleaned.replace("```", "").strip()

    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
        raise ValueError("JSON parsed (after fence strip) but not an object")
    except json.JSONDecodeError:
        pass

    # 3) Extract substring between first { and last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start:end + 1]
        obj = json.loads(snippet)
        if isinstance(obj, dict):
            return obj
        raise ValueError("Extracted JSON parsed but not an object")

    raise ValueError("Could not parse valid JSON from AI output")


def _fallback_template(ai_error: str, model: str = "NBA_Template_Fallback") -> Dict[str, Any]:
    """
    Standard fallback narrative structure. Consumers can render markdown from this safely.
    """
    return {
        "macro_summary": (
            "The current NBA slate is available, but AI narrative generation could not be completed. "
            "This response is a safe fallback."
        ),
        "micro_summary": {
            "key_edges": [],
            "risk_score": 0.0,
            "risk_rationale": "Fallback mode.",
        },
        "analyst_takeaway": (
            "Review the slate matchups and odds sections for context. "
            "If this was unexpected, check the backend logs for the AI soft error."
        ),
        "confidence_summary": ["Low"],
        "metadata": {
            "generated_at": _now_iso(),
            "model": model,
            "ai_used": False,
            "ai_error": ai_error,
        },
    }


def generate_narrative_summary(data: dict, mode: str = "ai") -> dict:
    """
    Grounded narrative generator.

    Step 2.4 support:
    - Always returns a dict in the expected narrative shape.
    - On any AI failure, returns a structured fallback and includes:
        metadata.ai_used = False
        metadata.ai_error = "<reason>"
    """
    if mode != "ai":
        # Template mode is an intentional "non-AI" path.
        return _fallback_template(ai_error="mode=template (AI not requested).", model="NBA_Template_Fallback")

    client = _get_openai_client()
    if client is None:
        return _fallback_template(ai_error="OPENAI_API_KEY missing or OpenAI client not initialized.", model="AI_Fallback_Mode")

    games_today = data.get("games_today") or []
    slate_block = _build_slate_grounding(games_today)
    coverage_block = _build_data_coverage_block(data)
    input_json = _safe_json_dumps(data)

    system_rules = (
        "You are an expert NBA analyst producing a schedule-grounded narrative.\n"
        "Rules:\n"
        "1) Use ONLY the provided inputs.\n"
        "2) Do NOT invent injuries, betting lines, rumors, player statistics, or outcomes.\n"
        "3) If a source is absent/sparse, explicitly state that limitation in the narrative.\n"
        "4) Ground analysis in concrete available data: matchups, schedule status, trends, odds, and props coverage.\n"
        "5) Keep tone concise and decision-useful; avoid generic filler.\n"
        "6) Output MUST be valid JSON ONLY (no markdown, no code fences).\n"
    )

    schema = {
        "macro_summary": (
            "string (3-6 sentences). Structure: "
            "(a) slate overview, (b) strongest available signals, (c) explicit missing-data limitations."
        ),
        "micro_summary": {
            "key_edges": [
                {
                    "value_label": "string (e.g., Market Context / Trend Signal / Props Availability)",
                    "edge_score": "number 0-10",
                    "text": "string (1 sentence, grounded in specific provided input)",
                }
            ],
            "risk_score": "number 0.0-1.0",
            "risk_rationale": "string (1 sentence naming concrete limitations from the input)",
        },
        "analyst_takeaway": (
            "string (2-4 sentences): "
            "prioritize where data is strongest, and caution where data is missing."
        ),
        "confidence_summary": ["string"],
        "metadata": {"model": "string"},
    }

    user_prompt = (
        f"{slate_block}\n\n"
        f"{coverage_block}\n\n"
        "Generate an NBA slate narrative.\n\n"
        "Quality requirements:\n"
        "- Be explicit about what is known vs unavailable.\n"
        "- Prefer short, concrete statements tied to provided inputs.\n"
        "- Keep key_edges focused on the most actionable 2-5 signals.\n\n"
        "Return JSON matching this schema exactly:\n"
        f"{_safe_json_dumps(schema)}\n\n"
        "INPUT JSON:\n"
        f"{input_json}\n"
    )

    if LOG_AI_RAW:
        logger.info(f"🧠 [AI] Prompt length={len(user_prompt)} chars")

    ai_text = ""
    try:
        kwargs = dict(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_rules},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=900,
            response_format={"type": "json_object"},
        )

        response = client.chat.completions.create(**kwargs)
        ai_text = (response.choices[0].message.content or "").strip()

        if LOG_AI_RAW:
            logger.info(f"🧠 [AI] Raw response length={len(ai_text)} chars")
            logger.info(f"🧠 [AI] Raw response preview: {ai_text[:300]}")

        parsed = _try_parse_json(ai_text)

        # Minimal contract hardening (route layer will perform full validation/fallback)
        parsed.setdefault("micro_summary", {})
        if not isinstance(parsed["micro_summary"], dict):
            parsed["micro_summary"] = {}

        parsed.setdefault("metadata", {})
        if not isinstance(parsed["metadata"], dict):
            parsed["metadata"] = {}

        parsed["metadata"].update({
            "generated_at": _now_iso(),
            "model": parsed["metadata"].get("model", "NBA_Data_Analyst-v1.1"),
            "ai_used": True,
            "ai_error": None,
        })

        parsed.setdefault("macro_summary", "")
        parsed.setdefault("analyst_takeaway", "")
        parsed.setdefault("confidence_summary", ["Medium"])
        parsed["micro_summary"].setdefault("key_edges", [])
        parsed["micro_summary"].setdefault("risk_score", 0.5)
        parsed["micro_summary"].setdefault("risk_rationale", "Generated with schedule-grounding constraints.")

        return parsed

    except TypeError as e:
        # response_format not supported by this SDK version/model
        logger.error(f"❌ OpenAI call failed (TypeError). response_format may be unsupported: {e}")
        return _fallback_template(ai_error=f"OpenAI TypeError (response_format unsupported): {e}", model="AI_Fallback_Mode")
    except json.JSONDecodeError as e:
        logger.error(f"❌ AI output not valid JSON: {e}")
        return _fallback_template(ai_error=f"AI output invalid JSON: {e}", model="AI_Fallback_Mode")
    except OpenAIError as e:
        logger.error(f"❌ OpenAI API error: {e}")
        return _fallback_template(ai_error=f"OpenAI API error: {e}", model="AI_Fallback_Mode")
    except Exception as e:
        logger.error(f"❌ Unexpected AI generation error: {type(e).__name__}: {e}")
        if LOG_AI_RAW and ai_text:
            logger.info(f"🧠 [AI RAW OUTPUT]\n{ai_text}")
        return _fallback_template(ai_error=f"Unexpected AI error: {type(e).__name__}: {e}", model="AI_Fallback_Mode")


if __name__ == "__main__":
    sample_data = {"games_today": [], "player_trends": [], "team_trends": [], "odds": {"games": []}}
    print(generate_narrative_summary(sample_data, mode="ai"))
