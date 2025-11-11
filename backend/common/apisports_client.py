# backend/common/apisports_client.py
from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional, Tuple
import requests

API_BASKETBALL_BASE = os.getenv("API_BASKETBALL_BASE", "https://v1.basketball.api-sports.io").rstrip("/")
API_BASKETBALL_KEY = os.getenv("API_BASKETBALL_KEY", "3cbe7bb1fa1ef31e806d64ea452d77cd").strip()

# Sensible defaults; adjust later if needed
DEFAULT_TIMEOUT = (6.0, 20.0)  # (connect, read)
MAX_RETRIES = 3
RETRY_BACKOFF_SECS = 1.5

# --- Simple in-memory cache -------------------------------------------------
_CACHE: dict[Tuple[str, Tuple[Tuple[str, str], ...]], Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL = 60.0  # seconds


def _cache_key(path: str, params: Optional[Dict[str, Any]]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
    """Generate a consistent cache key based on path and sorted params."""
    items = tuple(sorted((params or {}).items()))
    return (path, items)
# -----------------------------------------------------------------------------


def _headers() -> Dict[str, str]:
    if not API_BASKETBALL_KEY:
        raise RuntimeError("API_BASKETBALL_KEY is missing. Add it to your .env")
    return {
        "x-apisports-key": API_BASKETBALL_KEY,
        "Accept": "application/json",
        "User-Agent": "OddsAgent/1.0 (+AI Agent Backend)"
    }


def apisports_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    GET wrapper with simple retry/backoff on 429/5xx, plus 60s in-memory cache.
    Returns parsed JSON dict from API-Sports (with keys like 'results', 'response', etc.).
    """
    url = f"{API_BASKETBALL_BASE}/{path.lstrip('/')}"
    key = _cache_key(path, params)
    now = time.time()

    # --- Check cache first ---
    if key in _CACHE:
        ts, data = _CACHE[key]
        if now - ts < _CACHE_TTL:
            return data
        else:
            del _CACHE[key]  # expired
    # --------------------------

    last_exc: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=_headers(), params=params or {}, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    _CACHE[key] = (time.time(), data)  # store in cache
                    return data
                except Exception as e:
                    raise RuntimeError(f"Invalid JSON from API-Sports at {url}: {e}") from e

            # soft backoff for rate limit or transient server errors
            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else RETRY_BACKOFF_SECS * attempt
                time.sleep(min(wait, 8.0))
                last_exc = RuntimeError(f"HTTP {resp.status_code} at {url}: {resp.text[:200]}")
                continue

            # non-retryable
            raise RuntimeError(f"HTTP {resp.status_code} at {url}: {resp.text[:200]}")

        except requests.RequestException as e:
            last_exc = e
            time.sleep(RETRY_BACKOFF_SECS * attempt)

    # out of retries
    if last_exc:
        raise RuntimeError(f"API-Sports request failed after {MAX_RETRIES} attempts: {last_exc}")
    raise RuntimeError("API-Sports request failed unexpectedly.")
