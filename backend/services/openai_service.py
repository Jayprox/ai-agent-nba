# backend/services/openai_service.py
import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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
        # remove possible "json" label line
        cleaned = cleaned.replace("json\n", "", 1)
        cleaned = cleaned.replace("JSON\n", "", 1)
        # remove trailing fences
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


def generate_narrative_summary(data: dict, mode: str = "ai") -> dict:
    """
    Grounded narrative generator.
    Uses response_format JSON mode + robust parsing to prevent invalid-JSON fallbacks.
    """

    fallback_template = {
        "macro_summary": (
            "The current NBA slate is available, but AI narrative generation is not enabled. "
            "Use the schedule page for matchup context and revisit once AI is configured."
        ),
        "micro_summary": {
            "key_edges": [],
            "risk_score": 0.0,
            "risk_rationale": "Template mode.",
        },
        "analyst_takeaway": "Enable AI mode (OPENAI_API_KEY) to generate a grounded narrative.",
        "confidence_summary": ["Medium"],
        "metadata": {
            "generated_at": _now_iso(),
            "model": "NBA_Template_Fallback",
        },
    }

    if mode != "ai":
        if LOG_AI_RAW:
            logger.info("🧩 [Fallback] mode=template → returning template narrative.")
        return fallback_template

    client = _get_openai_client()
    if client is None:
        fallback_template["metadata"]["model"] = "AI_Fallback_Mode"
        fallback_template["metadata"]["error"] = "OPENAI_API_KEY missing or OpenAI client not initialized."
        return fallback_template

    games_today = data.get("games_today") or []
    slate_block = _build_slate_grounding(games_today)
    input_json = _safe_json_dumps(data)

    system_rules = (
        "You are an expert NBA analyst producing a schedule-grounded narrative.\n"
        "Rules:\n"
        "1) Use ONLY the provided inputs.\n"
        "2) Do NOT invent injuries, betting lines, rumors, or player statistics.\n"
        "3) If something is not present in the input JSON, explicitly say it is not available.\n"
        "4) Ground analysis primarily in the slate: matchups, venues, times, timezone, and game status.\n"
        "5) Output MUST be valid JSON ONLY (no markdown, no code fences).\n"
    )

    # Keep the schema simple and aligned with your renderer
    schema = {
        "macro_summary": "string (2–6 sentences; reference at least 2 real matchups from the slate)",
        "micro_summary": {
            "key_edges": [
                {"value_label": "string", "edge_score": "number 0-10", "text": "string"}
            ],
            "risk_score": "number 0.0-1.0",
            "risk_rationale": "string (1 sentence explaining what limits confidence)",
        },
        "analyst_takeaway": "string (2–4 sentences; conservative and actionable)",
        "confidence_summary": ["string"],
        "metadata": {"model": "string"},
    }

    user_prompt = (
        f"{slate_block}\n\n"
        "Generate an NBA slate narrative.\n\n"
        "Return JSON matching this schema exactly:\n"
        f"{_safe_json_dumps(schema)}\n\n"
        "INPUT JSON:\n"
        f"{input_json}\n"
    )

    if LOG_AI_RAW:
        logger.info(f"🧠 [AI] Prompt length={len(user_prompt)} chars")

    ai_text = ""
    try:
        # Enforce JSON mode at the API layer
        # If the SDK/model combination doesn’t support response_format, we fall back gracefully.
        kwargs = dict(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_rules},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=900,
        )

        # JSON mode: strongly reduces invalid JSON responses
        kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        ai_text = (response.choices[0].message.content or "").strip()

        if LOG_AI_RAW:
            logger.info(f"🧠 [AI] Raw response length={len(ai_text)} chars")
            logger.info(f"🧠 [AI] Raw response preview: {ai_text[:300]}")

        parsed = _try_parse_json(ai_text)

        # Minimal contract hardening
        parsed.setdefault("micro_summary", {})
        if not isinstance(parsed["micro_summary"], dict):
            parsed["micro_summary"] = {}

        parsed.setdefault("metadata", {})
        if not isinstance(parsed["metadata"], dict):
            parsed["metadata"] = {}

        parsed["metadata"].update({
            "generated_at": _now_iso(),
            "model": parsed["metadata"].get("model", "NBA_Data_Analyst-v1.1"),
        })

        # Ensure required keys exist so the renderer stays stable
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
    except json.JSONDecodeError as e:
        logger.error(f"❌ AI output not valid JSON: {e}")
    except OpenAIError as e:
        logger.error(f"❌ OpenAI API error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected AI generation error: {type(e).__name__}: {e}")

    if LOG_AI_RAW and ai_text:
        logger.info(f"🧠 [AI RAW OUTPUT]\n{ai_text}")

    fallback_template["metadata"]["model"] = "AI_Fallback_Mode"
    fallback_template["metadata"]["error"] = "AI generation failed or returned invalid JSON — fallback used."
    return fallback_template


if __name__ == "__main__":
    sample_data = {"games_today": [], "player_trends": [], "team_trends": [], "odds": {"games": []}}
    print(generate_narrative_summary(sample_data, mode="ai"))
