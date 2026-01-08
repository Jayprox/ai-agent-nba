# backend/tests/test_narrative_markdown_contract.py

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


# -----------------------------
# Make backend/ importable
# -----------------------------
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parents[1]  # .../backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402
from routes import narrative as narrative_route  # noqa: E402


def _install_common_stubs(monkeypatch, *, ai_allowed: bool = True):
    """
    Install stubs so tests are offline/CI safe and deterministic.

    ai_allowed:
      - True  => pretend OPENAI_API_KEY is present (baseline contract tests)
      - False => simulate missing key (AI soft-error coverage test)
    """

    # Make behavior deterministic even if developer env sets ENABLE_TRENDS_IN_NARRATIVE=0/1.
    # (Overrides still win for trends=0 / trends=1.)
    monkeypatch.setattr(narrative_route, "_ENV_ENABLE_TRENDS", True, raising=False)

    # Make AI enablement deterministic (Step 2.4: AI allowed gating)
    monkeypatch.setattr(narrative_route, "_ai_allowed", lambda: ai_allowed, raising=False)

    # -----------------------------
    # Stub: narrative generator (AI/template)
    # -----------------------------
    def fake_generate_narrative_summary(data: dict, mode: str = "ai") -> dict:
        # This stub always returns a valid shape; route-level validation should pass.
        return {
            "macro_summary": ["Stub macro summary."],
            "micro_summary": {"key_edges": [], "risk_score": 0.1, "risk_rationale": "Stub rationale."},
            "analyst_takeaway": "Stub analyst takeaway.",
            "confidence_summary": ["Medium"],
            "metadata": {"model": "TEST_MODEL"},
        }

    monkeypatch.setattr(
        narrative_route,
        "generate_narrative_summary",
        fake_generate_narrative_summary,
        raising=False,
    )

    # -----------------------------
    # Stub: odds (must be dict-like because route does (odds or {}).get("games"))
    # -----------------------------
    def fake_fetch_moneyline_odds(*args, **kwargs):
        return {"games": []}

    monkeypatch.setattr(
        narrative_route,
        "fetch_moneyline_odds",
        fake_fetch_moneyline_odds,
        raising=False,
    )

    # -----------------------------
    # Stub: API-Basketball games (awaitable in the route)
    # -----------------------------
    async def fake_get_today_games(*args, **kwargs):
        return [
            {
                "id": 1,
                "date": "2025-12-17T17:00:00-08:00",
                "timestamp": 1766029200,
                "timezone": "America/Los_Angeles",
                "home_team": {"name": "Home Team"},
                "away_team": {"name": "Away Team"},
                "status": {"long": "Not Started", "short": "NS", "timer": None},
                "league": {
                    "id": 12,
                    "name": "NBA",
                    "season": "2025-2026",
                    "type": "League",
                },
                "venue": "Test Arena",
            }
        ]

    monkeypatch.setattr(
        narrative_route,
        "get_today_games",
        fake_get_today_games,
        raising=False,
    )

    # -----------------------------
    # Stub: trends summary
    # Route expects objects with .model_dump()
    # -----------------------------
    class _FakeTrend:
        def __init__(self, payload: dict):
            self._payload = payload

        def model_dump(self):
            return dict(self._payload)

    def fake_get_trends_summary(*args, **kwargs):
        player_trends_list = [
            _FakeTrend(
                {
                    "player_name": "LeBron James",
                    "stat_type": "points",
                    "average": 25.0,
                    "trend_direction": "up",
                    "last_n_games": 5,
                }
            ),
            _FakeTrend(
                {
                    "player_name": "Stephen Curry",
                    "stat_type": "points",
                    "average": 29.0,
                    "trend_direction": "neutral",
                    "last_n_games": 5,
                }
            ),
            _FakeTrend(
                {
                    "player_name": "Luka Doncic",
                    "stat_type": "assists",
                    "average": 10.0,
                    "trend_direction": "down",
                    "last_n_games": 5,
                }
            ),
        ]

        return SimpleNamespace(team_trends=[], player_trends=player_trends_list)

    monkeypatch.setattr(
        narrative_route,
        "get_trends_summary",
        fake_get_trends_summary,
        raising=False,
    )


@pytest.mark.parametrize("mode", ["ai", "template"])
def test_narrative_markdown_contract(monkeypatch, mode: str):
    """
    Contract test for /nba/narrative/markdown (Step 2.4):
      - ok=true
      - markdown always present, non-empty
      - raw.meta always present
      - raw.meta.soft_errors always present (dict)
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)

    client = TestClient(app)
    res = client.get(f"/nba/narrative/markdown?mode={mode}&cache_ttl=0")
    assert res.status_code == 200

    data = res.json()
    assert data.get("ok") is True, data

    # Top-level contract
    assert isinstance(data.get("summary"), dict)
    assert isinstance(data.get("raw"), dict)
    assert isinstance(data.get("markdown"), str)
    assert data["markdown"].strip() != ""

    # Summary metadata contract
    assert isinstance(data["summary"].get("metadata"), dict)

    # Raw contract (aligns with your jq keys output)
    raw = data["raw"]
    required_raw_keys = {
        "date_generated",
        "games_today",
        "meta",
        "odds",
        "player_props",
        "player_trends",
        "team_trends",
    }
    assert required_raw_keys.issubset(set(raw.keys())), raw.keys()
    assert isinstance(raw.get("meta"), dict)

    # raw.meta contract fields
    meta = raw["meta"]
    assert isinstance(meta.get("soft_errors"), dict)

    # Odds contract (dict + games list)
    assert isinstance(raw.get("odds"), dict)
    assert isinstance(raw["odds"].get("games", []), list)

    # Markdown sanity
    md = data["markdown"]
    assert "**NBA Narrative**" in md
    assert "Macro Summary" in md


@pytest.mark.parametrize(
    "query, expected_override, expected_enabled, expected_min_player_trends, expect_trends_soft_error",
    [
        ("&trends=0", False, False, 0, True),
        ("&trends=1", True, True, 1, False),
    ],
)
def test_trends_override_contract_and_effect(
    monkeypatch,
    query: str,
    expected_override,
    expected_enabled: bool,
    expected_min_player_trends: int,
    expect_trends_soft_error: bool,
):
    """
    Step 2.4 + override coverage:
      - raw.meta.trends_override set when trends query param provided
      - raw.meta.trends_enabled_in_narrative follows override
      - raw.player_trends reflects enabled/disabled (0 when off, >0 when on)
      - raw.meta.soft_errors.trends present only when trends disabled/unavailable
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)

    client = TestClient(app)
    res = client.get(f"/nba/narrative/markdown?mode=ai&cache_ttl=0{query}")
    assert res.status_code == 200

    data = res.json()
    assert data.get("ok") is True, data

    raw = data.get("raw") or {}
    assert isinstance(raw, dict)

    meta = raw.get("meta") or {}
    assert isinstance(meta, dict)

    soft_errors = meta.get("soft_errors") or {}
    assert isinstance(soft_errors, dict)

    # Override contract
    assert meta.get("trends_override") == expected_override

    # Enabled flag contract
    assert meta.get("trends_enabled_in_narrative") is expected_enabled

    # Effect contract
    player_trends = raw.get("player_trends", [])
    assert isinstance(player_trends, list)
    assert len(player_trends) >= expected_min_player_trends
    if expected_enabled is False:
        assert len(player_trends) == 0

    # Soft-error for trends only when disabled/unavailable
    if expect_trends_soft_error:
        assert isinstance(soft_errors.get("trends"), str)
        assert soft_errors["trends"].strip() != ""
    else:
        assert "trends" not in soft_errors or soft_errors.get("trends") in (None, "")


def test_ai_soft_error_when_ai_not_allowed(monkeypatch):
    """
    Step 2.4: If mode=ai but AI is not allowed (e.g., missing OPENAI_API_KEY),
    endpoint should NOT fail hard. It should:
      - return ok=true
      - include markdown
      - populate raw.meta.soft_errors.ai
      - set summary.metadata.ai_used = False
    """
    _install_common_stubs(monkeypatch, ai_allowed=False)

    client = TestClient(app)
    res = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=0&trends=1")
    assert res.status_code == 200

    data = res.json()
    assert data.get("ok") is True, data
    assert isinstance(data.get("markdown"), str)
    assert data["markdown"].strip() != ""

    raw = data.get("raw") or {}
    meta = raw.get("meta") or {}
    soft_errors = meta.get("soft_errors") or {}
    assert isinstance(soft_errors, dict)

    # AI soft-error should exist
    assert isinstance(soft_errors.get("ai"), str)
    assert soft_errors["ai"].strip() != ""

    # AI usage flag should be false
    summary_meta = (data.get("summary") or {}).get("metadata") or {}
    assert isinstance(summary_meta, dict)
    assert summary_meta.get("ai_used") is False


def test_ai_soft_fallback_when_generator_returns_invalid(monkeypatch):
    """
    Step 2.4: If AI returns an invalid shape, endpoint still returns:
      - ok=true
      - markdown present
      - raw.meta.soft_errors.ai present
      - summary.metadata.ai_used=false
    """
    _install_common_stubs(monkeypatch)

    # Force AI generator to return invalid type
    monkeypatch.setattr(
        narrative_route,
        "generate_narrative_summary",
        lambda *args, **kwargs: "NOT_A_DICT",
        raising=False,
    )

    client = TestClient(app)
    res = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=0&trends=1")
    assert res.status_code == 200
    data = res.json()

    assert data.get("ok") is True
    assert isinstance(data.get("markdown"), str)
    assert data["markdown"].strip() != ""

    raw = data.get("raw") or {}
    meta = raw.get("meta") or {}
    soft = meta.get("soft_errors") or {}

    assert isinstance(soft, dict)
    assert soft.get("ai") is not None

    md = data.get("summary", {}).get("metadata", {})
    assert md.get("ai_used") is False


def test_ai_soft_fallback_when_generator_throws(monkeypatch):
    """
    Step 2.4: If AI generation throws, endpoint still returns ok=true and a markdown fallback,
    and surfaces raw.meta.soft_errors.ai
    """
    _install_common_stubs(monkeypatch)

    def _boom(*args, **kwargs):
        raise RuntimeError("AI exploded")

    monkeypatch.setattr(
        narrative_route,
        "generate_narrative_summary",
        _boom,
        raising=False,
    )

    client = TestClient(app)
    res = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=0&trends=1")
    assert res.status_code == 200
    data = res.json()

    assert data.get("ok") is True
    assert isinstance(data.get("markdown"), str)
    assert data["markdown"].strip() != ""

    raw = data.get("raw") or {}
    meta = raw.get("meta") or {}
    soft = meta.get("soft_errors") or {}

    assert isinstance(soft, dict)
    assert "ai" in soft
    assert "AI generation threw" in str(soft["ai"])


def test_cache_partitioned_by_trends_override(monkeypatch):
    """
    Step 2.5: Regression coverage.
    Cache must NOT leak payloads across trends overrides.

    Prior bug:
      cache_key = (mode, ttl, "today")
      so trends=0 could poison cache for trends=1 (or vice versa)
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)

    client = TestClient(app)

    # First call: trends OFF, with cache enabled
    r0 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=0")
    assert r0.status_code == 200
    d0 = r0.json()
    assert d0.get("ok") is True, d0
    meta0 = (d0.get("raw") or {}).get("meta") or {}
    assert meta0.get("trends_enabled_in_narrative") is False
    assert (d0.get("raw") or {}).get("player_trends") == []
    # first call should not be cache-used
    assert meta0.get("cache_used") is False

    # Second call: trends ON, same ttl
    # If cache is not partitioned, this would incorrectly return trends OFF payload.
    r1 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1.get("ok") is True, d1
    meta1 = (d1.get("raw") or {}).get("meta") or {}
    assert meta1.get("trends_enabled_in_narrative") is True
    pt1 = (d1.get("raw") or {}).get("player_trends") or []
    assert isinstance(pt1, list)
    assert len(pt1) >= 1
    # second call should not be served from the trends=0 cache bucket
    assert meta1.get("cache_used") is False


def test_cache_observability_fields_present(monkeypatch):
    """
    Step 2.6: Cache observability contract.
    raw.meta must always contain:
      - cache_used (bool)
      - cache_ttl_s (int)
      - cache_key (str)
      - cache_expires_in_s (float/int)
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)
    
    # Clear cache to ensure clean state
    narrative_route._CACHE.clear()
    narrative_route._INFLIGHT_LOCKS.clear()

    client = TestClient(app)

    # First call: no cache
    res = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1")
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True

    meta = (data.get("raw") or {}).get("meta") or {}
    assert isinstance(meta, dict)

    # Step 2.6 observability fields
    assert isinstance(meta.get("cache_used"), bool)
    assert meta["cache_used"] is False  # First call

    assert isinstance(meta.get("cache_ttl_s"), int)
    assert meta["cache_ttl_s"] == 60

    assert isinstance(meta.get("cache_key"), str)
    assert meta["cache_key"].strip() != ""

    assert isinstance(meta.get("cache_expires_in_s"), (int, float))
    assert meta["cache_expires_in_s"] > 0


def test_cache_hit_returns_cache_meta(monkeypatch):
    """
    Step 2.6: On cache hit, raw.meta should reflect:
      - cache_used=true
      - cache_expires_in_s should decrease on subsequent hits
      - cache_key should match
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)
    
    # Clear cache to ensure clean state
    narrative_route._CACHE.clear()
    narrative_route._INFLIGHT_LOCKS.clear()

    client = TestClient(app)

    # First call: populate cache
    r1 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1")
    assert r1.status_code == 200
    d1 = r1.json()
    meta1 = (d1.get("raw") or {}).get("meta") or {}
    assert meta1.get("cache_used") is False
    key1 = meta1.get("cache_key")
    assert isinstance(key1, str)

    # Second call: should hit cache
    r2 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1")
    assert r2.status_code == 200
    d2 = r2.json()
    meta2 = (d2.get("raw") or {}).get("meta") or {}
    assert meta2.get("cache_used") is True
    assert meta2.get("cache_key") == key1
    assert isinstance(meta2.get("cache_expires_in_s"), (int, float))
    assert 0 < meta2["cache_expires_in_s"] <= 60


def test_cache_partitioned_by_mode(monkeypatch):
    """
    
    # Clear cache to ensure clean state
    narrative_route._CACHE.clear()
    narrative_route._INFLIGHT_LOCKS.clear()
    Step 2.6: Cache should partition by mode.
    mode=ai and mode=template should have different cache keys.
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)

    client = TestClient(app)

    # mode=ai
    r1 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1")
    assert r1.status_code == 200
    d1 = r1.json()
    meta1 = (d1.get("raw") or {}).get("meta") or {}
    key1 = meta1.get("cache_key")

    # mode=template
    r2 = client.get("/nba/narrative/markdown?mode=template&cache_ttl=60&trends=1")
    assert r2.status_code == 200
    d2 = r2.json()
    meta2 = (d2.get("raw") or {}).get("meta") or {}
    key2 = meta2.get("cache_key")

    # Keys should differ
    assert key1 != key2
    
    # Clear cache to ensure clean state
    narrative_route._CACHE.clear()
    narrative_route._INFLIGHT_LOCKS.clear()


def test_cache_partitioned_by_compact_flag(monkeypatch):
    """
    Step 2.6: Cache should partition by compact flag.
    /markdown?compact=true and /markdown?compact=false should have different keys.
    """
    _install_common_stubs(monkeypatch, ai_allowed=True)

    client = TestClient(app)

    # compact=false (default)
    r1 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1&compact=false")
    assert r1.status_code == 200
    d1 = r1.json()
    meta1 = (d1.get("raw") or {}).get("meta") or {}
    key1 = meta1.get("cache_key")

    # compact=true
    r2 = client.get("/nba/narrative/markdown?mode=ai&cache_ttl=60&trends=1&compact=true")
    assert r2.status_code == 200
    d2 = r2.json()
    meta2 = (d2.get("raw") or {}).get("meta") or {}
    key2 = meta2.get("cache_key")

    # Keys should differ
    assert key1 != key2