# backend/test_narrative_contract.py
"""
Contract test for /nba/narrative/today endpoint.
Runs both template and AI modes, validates schema keys,
and logs basic performance metrics.
"""

import json
import time
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/nba/narrative/today"


def _check_keys(data, required_keys):
    """Return list of missing keys (if any)."""
    return [k for k in required_keys if k not in data]


def run_contract_test(mode="template"):
    """Run a single test mode and validate."""
    print(f"\n🧪 Testing mode: {mode.upper()}")

    t0 = time.perf_counter()
    resp = requests.get(BASE_URL, params={"mode": mode, "cache_ttl": 0})
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code} — {resp.text[:200]}")
        return False

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        print("❌ Response was not valid JSON.")
        return False

    # ---------------- Schema validation ----------------
    required_top = ["ok", "summary", "raw", "mode"]
    missing_top = _check_keys(payload, required_top)
    if missing_top:
        print("❌ Missing top-level keys:", missing_top)
        return False

    summary = payload.get("summary", {})
    required_summary = ["metadata"]
    missing_summary = _check_keys(summary, required_summary)
    if missing_summary:
        print("❌ Missing summary keys:", missing_summary)
        return False

    metadata = summary.get("metadata", {})
    required_meta = ["generated_at", "model"]
    missing_meta = _check_keys(metadata, required_meta)
    if missing_meta:
        print("❌ Missing metadata keys:", missing_meta)
        return False

    raw = payload.get("raw", {})
    meta_raw = raw.get("meta", {})
    if meta_raw:
        latency = meta_raw.get("latency_ms", latency_ms)
        cache = meta_raw.get("cache_used", False)
        print(
            f"✅ {mode.upper()} PASS — "
            f"latency: {latency:.2f} ms | cache_used: {cache} | "
            f"model: {metadata.get('model')}"
        )
    else:
        print(
            f"✅ {mode.upper()} PASS — "
            f"latency: {latency_ms:.2f} ms | model: {metadata.get('model')}"
        )

    # Optional debug dump for detailed logs
    print(json.dumps(metadata, indent=2))
    return True


if __name__ == "__main__":
    print("🧭 NBA Narrative Contract Test")
    print(f"⏱️  Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    ok_template = run_contract_test("template")
    ok_ai = run_contract_test("ai")

    print("\n📊 Summary Report")
    print(f"Template mode: {'✅ PASS' if ok_template else '❌ FAIL'}")
    print(f"AI mode: {'✅ PASS' if ok_ai else '❌ FAIL'}")

    if ok_template and ok_ai:
        print("\n🎉 All narrative contract tests passed successfully.")
    else:
        print("\n⚠️  One or more tests failed.")
