# backend/common/apisports_client.py
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_API_BASE = os.getenv("API_BASKETBALL_BASE", "https://v1.basketball.api-sports.io")
_API_KEY = os.getenv("API_BASKETBALL_KEY", "")


def _build_url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return _API_BASE.rstrip("/") + path


def apisports_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Thin wrapper around requests.get for API-Basketball.

    - Uses API_BASKETBALL_BASE + `path`
    - Sends key in header (x-apisports-key is allowed per docs, as is x-rapidapi-key)
    - Logs HTTP status and any API 'errors' field
    """
    if not _API_KEY:
        raise RuntimeError("API_BASKETBALL_KEY is not set in the environment")

    url = _build_url(path)
    headers = {
        # Direct API-Sports key header (preferred)
        "x-apisports-key": _API_KEY,
        # RapidAPI-style header is ALSO allowed according to docs, so we include both
        "x-rapidapi-key": _API_KEY,
    }

    logger.info(f"[API-Basketball] GET {url} params={params}")

    resp = requests.get(url, headers=headers, params=params or {}, timeout=15)
    logger.info(f"[API-Basketball] HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception:
        logger.error("Failed to decode JSON from API-Basketball")
        resp.raise_for_status()
        raise

    # Log API-level errors if present
    if isinstance(data, dict):
        errors = data.get("errors") or []
        if errors:
            logger.warning(f"[API-Basketball] API errors: {errors}")

    # Raise for non-2xx so our tests see the problem
    resp.raise_for_status()
    return data  # {'get', 'parameters', 'errors', 'results', 'response'}
