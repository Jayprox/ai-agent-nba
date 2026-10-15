from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


def _ensure_backend_on_syspath() -> None:
    """
    Ensure the backend/ directory is importable as a top-level package root.

    This allows test modules to import:
      - common.*
      - routes.*
      - services.*
      - agents.*
    when running `pytest` from the repo root.
    """
    this_file = Path(__file__).resolve()
    backend_dir = this_file.parents[1]  # .../backend
    repo_root = backend_dir.parent      # .../ai-agent-nba

    b = str(backend_dir)
    r = str(repo_root)

    # Put backend/ first so "common" resolves to backend/common, etc.
    if b not in sys.path:
        sys.path.insert(0, b)

    # Optional: include repo root for any future top-level imports.
    if r not in sys.path:
        sys.path.append(r)


def _live_enabled(config: pytest.Config) -> bool:
    """
    Live tests are allowed when either:
      - RUN_LIVE_TESTS=1 is set, OR
      - pytest is run with --live
    """
    env_flag = os.getenv("RUN_LIVE_TESTS", "").strip()
    if env_flag == "1":
        return True
    return bool(getattr(config.option, "live", False))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Enable tests marked with @pytest.mark.live (network/keys required).",
    )


def pytest_configure(config: pytest.Config) -> None:
    # Ensure marker is known even if pytest.ini changes
    config.addinivalue_line("markers", "live: tests that hit real external services (OpenAI, API-Basketball, TheOddsAPI)")
    config.addinivalue_line("markers", "integration: integration tests that may require network/keys")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Auto-skip any test marked live unless live mode is enabled.
    """
    if item.get_closest_marker("live") is None:
        return

    if not _live_enabled(item.config):
        pytest.skip("Skipped live/integration test (set RUN_LIVE_TESTS=1 or run `pytest --live` to enable).")


_ensure_backend_on_syspath()
