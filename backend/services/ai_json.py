## backend/services/ai_json.py

from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

def _extract_json_object(text: str) -> str | None:
    if not text:
        return None

    # 1) Try code-fenced JSON
    m = _JSON_FENCE_RE.search(text)
    if m:
        return m.group(1)

    # 2) Try first '{' ... last '}' heuristic
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return None


def parse_ai_json(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Returns (payload_dict, error_string).
    Never throws.
    """
    try:
        # Fast path: strict json
        return json.loads(text), None
    except Exception:
        pass

    snippet = _extract_json_object(text)
    if not snippet:
        return None, "Could not find JSON object in model output."

    try:
        return json.loads(snippet), None
    except Exception as e:
        return None, f"JSON parse failed after extraction: {e}"
