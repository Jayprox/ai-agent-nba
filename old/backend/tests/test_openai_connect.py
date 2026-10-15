# backend/tests/test_openai_connect.py

from __future__ import annotations

import os

import pytest


pytestmark = [pytest.mark.live, pytest.mark.integration]


def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def test_openai_models_list_smoke():
    """
    Live integration smoke test:
      - requires OPENAI_API_KEY
      - verifies we can reach OpenAI and list models
    """
    if not _has_openai_key():
        pytest.skip("OPENAI_API_KEY missing; set it or run non-live test suite only.")

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        pytest.skip(f"openai package not available/importable: {type(e).__name__}: {e}")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())

    # Minimal: just ensure the call works and returns at least 1 model.
    resp = client.models.list()
    assert hasattr(resp, "data")
    assert isinstance(resp.data, list)
    assert len(resp.data) > 0
