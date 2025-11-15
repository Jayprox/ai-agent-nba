# backend/services/openai_service.py
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("openai_service")
logger.setLevel(logging.WARNING)

LOG_AI_RAW = os.getenv("LOG_AI_RAW", "0") == "1"

# Import conditionally so environments without the package still work.
try:
    from openai import OpenAI  # type: ignore
except Exception as _imp_err:  # pragma: no cover
    OpenAI = None  # type: ignore
    _IMPORT_ERROR = _imp_err
else:
    _IMPORT_ERROR = None


AI_NARRATIVE_PROMPT = """
You are a professional NBA data journalist with access to live stats and betting odds.

Using the JSON data below, write a polished multi-layer report for today’s NBA slate.

JSON Input:
{json_input}

Instructions:
1) Macro Summary — 2–3 paragraphs summarizing key player & team trends.
2) Micro Summary — 3–5 key betting/performance insights (use player_props or micro_summary if present).
3) Analyst Takeaway — 1 short paragraph with a prediction or notable continuation.
4) Tone — professional, analytical, fan-friendly (sports media style).
5) Output strictly as a SINGLE JSON object with EXACT keys:

{
  "macro_summary": "<string>",
  "micro_summary": {
    "key_edges": [{"text": "<string>", "edge_score": <float>, "value_label": "<string>"}],
    "risk_score": <float>
  },
  "analyst_takeaway": "<string>",
  "confidence_summary": ["High","Medium","Low"],
  "metadata": {
    "generated_at": "<ISO-8601-UTC>",
    "model": "gpt-4o"
  }
}
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_schema(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure required keys exist with sane defaults."""
    out: Dict[str, Any] = dict(parsed) if isinstance(parsed, dict) else {}
    out.setdefault("macro_summary", "Missing field: macro_summary")

    micro = out.get("micro_summary")
    if not isinstance(micro, dict):
        micro = {}
    micro.setdefault("key_edges", [])
    micro.setdefault("risk_score", 0.0)
    out["micro_summary"] = micro

    out.setdefault("analyst_takeaway", "Missing field: analyst_takeaway")

    cs = out.get("confidence_summary")
    if not isinstance(cs, list):
        cs = []
    out["confidence_summary"] = cs

    meta = out.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("generated_at", _now_iso())
    meta.setdefault("model", "gpt-4o")
    out["metadata"] = meta

    return out


def _extract_json_anywhere(text: str) -> Optional[Dict[str, Any]]:
    """
    Try multiple strategies to extract JSON:
      1) Strip code fences
      2) Take the widest {...} block
      3) As a last resort, attempt to parse the whole thing
    """
    if not text:
        return None

    # Remove code fences ```json ... ``` or ``` ... ```
    fenced = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text, flags=re.IGNORECASE)

    # Prefer the widest JSON object region
    start = fenced.find("{")
    end = fenced.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = fenced[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Try direct parse
    try:
        return json.loads(fenced)
    except Exception:
        return None


def _fallback_template(data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "macro_summary": "AI narrative unavailable — using template summary only.",
        "micro_summary": data.get("micro_summary", {}),
        "analyst_takeaway": "Ensure your OpenAI API key is active and GPT access is configured correctly.",
        "confidence_summary": [],
        "metadata": {
            "generated_at": _now_iso(),
            "model": "template-fallback",
        },
    }
    if error:
        out["error"] = error
    return out


_client: Optional["OpenAI"] = None  # late-bound client


def _get_client() -> Optional["OpenAI"]:
    """Lazy-initialize OpenAI client (works even if .env loads after import)."""
    global _client
    if _client:
        return _client

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("AI mode requested but OPENAI_API_KEY not set.")
        return None
    if OpenAI is None:
        logger.warning("AI mode requested but 'openai' package is not available: %r", _IMPORT_ERROR)
        return None

    try:
        _client = OpenAI(api_key=api_key)
        return _client
    except Exception as e:  # pragma: no cover
        logger.error("Failed to initialize OpenAI client: %s", e)
        return None


def _first_choice_content(resp_obj: Any) -> str:
    """
    Safely extract the assistant message content from the chat completion response.
    Never raises KeyError.
    """
    try:
        choices = getattr(resp_obj, "choices", None) or resp_obj.get("choices")
    except Exception:
        choices = None

    if not choices:
        return ""

    choice0 = choices[0]
    # Some SDKs return dicts; others return typed objects.
    msg = None
    try:
        msg = getattr(choice0, "message", None) or choice0.get("message")
    except Exception:
        msg = None

    if not msg:
        return ""

    content = None
    try:
        content = getattr(msg, "content", None) or msg.get("content")
    except Exception:
        content = None

    # Some SDKs (rare) might return content as dict or list; convert to string.
    if content is None:
        return ""
    if isinstance(content, (dict, list)):
        try:
            return json.dumps(content)
        except Exception:
            return str(content)

    return str(content)


def generate_narrative_summary(narrative_data: Dict[str, Any], mode: str = "template") -> Dict[str, Any]:
    """
    Generate an AI-enhanced narrative summary or fallback to structured text.
    """
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
        logger.warning("AI mode requested but OPENAI client unavailable. Falling back to template.")
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

    # --- Build prompt and call GPT with JSON response enforced ---
    try:
        json_input = json.dumps(narrative_data, indent=2)
        prompt = AI_NARRATIVE_PROMPT.format(json_input=json_input)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an NBA data analyst who writes concise JSON-based reports."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        raw_text = _first_choice_content(response)

        if LOG_AI_RAW:
            preview = (raw_text or "")[:500].replace("\n", "\\n")
            logger.warning("RAW_AI_PREVIEW: %s...", preview)

        # Try parsing as-is (should already be JSON with response_format)
        parsed = None
        try:
            parsed = json.loads(raw_text) if raw_text else None
        except Exception:
            parsed = _extract_json_anywhere(raw_text)

        coerced = _coerce_schema(parsed or {})
        return coerced

    except Exception as e:
        logger.error("OpenAI call failed despite API key present: %r", e)
        return _fallback_template(narrative_data, error=str(e))
