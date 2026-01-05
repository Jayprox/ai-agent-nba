# backend/tests/conftest.py
from __future__ import annotations

import sys
from pathlib import Path


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

    # Put backend/ first so "common" resolves to backend/common, etc.
    b = str(backend_dir)
    r = str(repo_root)

    if b not in sys.path:
        sys.path.insert(0, b)

    # Optional: also include repo root for any top-level imports you might add later.
    if r not in sys.path:
        sys.path.append(r)


_ensure_backend_on_syspath()
