# backend/services/openai_service.py
from __future__ import annotations
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("openai_service")
logger.setLevel(logging.INFO)

LOG_AI_RAW = os.getenv("LOG_AI_RAW", "0") == "1"

try:
    from openai import OpenAI  # type: ignore
except Exception as _imp_err:
    OpenAI = None  # type: ignore
    _IMPORT_ERROR = _imp_err
else:
    _IMPORT_ERROR = None


AI_NARRATIVE_PROMPT = """
You are a professional NBA data journalist with access to live stats and betting odds.

Using the JSON data below, produce a multi-layer narrative summary in clean JSON.

JSON Input:
{json_input}

Instructions:
1. "macro_summary": 2–3 paragraphs summarizing major player and team trends.
2. "micro_summary": A JSON object with "key_edges" (list of insights) and "risk_score" (0–1 float).
3. "analyst_takeaway": One paragraph highlighting predictions or trends.
4. "confidence_summary": Array of confidence labels (High, Medium, Low).
5. "metadata": Object with ISO timestamp and model used.

Return ONLY valid JSON. Do NOT include commentary or markdown.
"""

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_schema(parsed: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(parsed) if isinstance(parsed, dict) else {}
    out.setdefault("macro_summary", "Missing macro_summary.")
    micro = out.get("micro_summary") or {}
    if not isinstance(micro, dict):
        micro = {}
    micro.setdefault("key_edges", [])
    micro.setdefault("risk_score", 0.0)
    out["micro_summary"] = micro
    out.setdefault("analyst_takeaway", "Missing analyst_takeaway.")
    out.setdefault("confidence_summary", ["Low"])
    meta = out.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("generated_at", _now_iso())
    meta.setdefault("model", "gpt-4o")
    out["metadata"] = meta
    return out


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    fenced = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text, flags=re.IGNORECASE)
    start, end = fenced.find("{"), fenced.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(fenced[start:end + 1])
        except Exception:
            pass
    try:
        return json.loads(fenced)
    except Exception:
        return None


def _fallback_template(data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
    out = {
        "macro_summary": "AI narrative unavailable — using template summary only.",
        "micro_summary": {},
        "analyst_takeaway": "Ensure your OpenAI API key is active and GPT access is configured correctly.",
        "confidence_summary": [],
        "metadata": {
            "generated_at": _now_iso(),
            "model": "template-fallback",
        },
    }
    if error:
        out["error"] = str(error)
    return out


_client: Optional["OpenAI"] = None


def _get_client() -> Optional["OpenAI"]:
    global _client
    if _client:
        return _client
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("⚠️ OPENAI_API_KEY not found in environment.")
        return None
    if OpenAI is None:
        logger.error("❌ 'openai' package missing:", _IMPORT_ERROR)
        return None
    try:
        _client = OpenAI(api_key=api_key)
        return _client
    except Exception as e:
        logger.error("❌ Failed to initialize OpenAI client:", e)
        return None


def generate_narrative_summary(narrative_data: Dict[str, Any], mode: str = "template") -> Dict[str, Any]:
    if mode == "template":
        return {
            "date_generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "tone": "neutral",
            "summary": (
                f"**NBA Update — {datetime.now(timezone.utc).strftime('%B %d, %Y')}**\n\n"
                f"Welcome to today’s NBA roundup!\n\n"
                f"**Player Trends:** {len(narrative_data.get('player_trends', []))} tracked.\n"
                f"**Team Trends:** {len(narrative_data.get('team_trends', []))} observed.\n"
                f"**Odds:** {len(narrative_data.get('odds', {}).get('games', []))} games active.\n\n"
                "Enable AI mode for full narrative insights."
            ),
            "metadata": {
                "generated_at": _now_iso(),
                "model": "template",
            },
        }

    client = _get_client()
    if not client:
        return _fallback_template(narrative_data, "No OpenAI client available")

    try:
        json_input = json.dumps(narrative_data, indent=2)
        prompt = AI_NARRATIVE_PROMPT.format(json_input=json_input)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a concise NBA data analyst who writes JSON reports only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content or ""
        if LOG_AI_RAW:
            logger.info("RAW_AI_PREVIEW: %s", raw_text[:400].replace("\n", "\\n"))

        parsed = _extract_json(raw_text) or {}
        return _coerce_schema(parsed)

    except Exception as e:
        logger.error("OpenAI call failed: %s", e)
        return _fallback_template(narrative_data, str(e))
