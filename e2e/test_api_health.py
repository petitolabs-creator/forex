#!/usr/bin/env python3
"""E2E: API availability & health (scenarios 1.1–1.3)."""
import sys
import requests
from e2e_common import FOREX_API_URL, DEFAULT_TIMEOUT, run_suite


def test_api_responds() -> bool:
    """1.1 GET /rates returns 200 when server is up."""
    print("\n[TEST] API responds")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 200:
            print("  ✓ API is accessible")
            return True
        print(f"  ✗ API returned {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ Cannot reach API: {e}")
        return False


def test_health_endpoint() -> bool:
    """1.2 GET /health returns 200 (if implemented)."""
    print("\n[TEST] Health endpoint")
    try:
        r = requests.get(f"{FOREX_API_URL}/health", timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            print("  ✓ GET /health returned 200")
            return True
        if r.status_code == 404:
            print("  ⚠ GET /health not implemented (404) – skip")
            return True
        print(f"  ✗ GET /health returned {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ GET /health failed: {e}")
        return False


def test_ready_endpoint() -> bool:
    """1.3 GET /ready returns 200 when cache loaded (if implemented)."""
    print("\n[TEST] Readiness endpoint")
    try:
        r = requests.get(f"{FOREX_API_URL}/ready", timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            print("  ✓ GET /ready returned 200")
            return True
        if r.status_code == 404:
            print("  ⚠ GET /ready not implemented (404) – skip")
            return True
        if r.status_code == 503:
            print("  ⚠ GET /ready returned 503 (cache not ready)")
            return True
        print(f"  ✗ GET /ready returned {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ GET /ready failed: {e}")
        return False


if __name__ == "__main__":
    run_suite("E2E: API Health", [
        ("API responds", test_api_responds),
        ("Health endpoint", test_health_endpoint),
        ("Ready endpoint", test_ready_endpoint),
    ])
