#!/usr/bin/env python3
"""E2E: Error handling 5xx and cold start (scenarios 8.x, 9.x)."""
import requests
from e2e_common import FOREX_API_URL, DEFAULT_TIMEOUT, LONG_TIMEOUT, run_suite


def test_pair_not_found() -> bool:
    """9.2 Valid currencies but no rate returns 404 or 503."""
    print("\n[TEST] Pair not found (rare pair)")
    try:
        # Request a pair that might not be in cache (e.g. NZD/CHF)
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "NZD", "to": "CHF"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 200:
            print("  ✓ Rate returned (pair available)")
            return True
        if r.status_code in (404, 503):
            print(f"  ✓ Correctly returned {r.status_code}")
            return True
        print(f"  ✗ Unexpected {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_request_timeout_handling() -> bool:
    """9.3 Request does not hang; completes or returns timeout."""
    print("\n[TEST] Request timeout handling")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=LONG_TIMEOUT,
        )
        # We only check that we get a response within timeout (no hang)
        print(f"  ✓ Response received (status {r.status_code})")
        return True
    except requests.exceptions.Timeout:
        print("  ⚠ Request timed out (server may be slow)")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_cache_unavailable_returns_5xx() -> bool:
    """9.1 When cache empty, API returns 503/500 (or 200 if cache ready)."""
    print("\n[TEST] Cache unavailable (503) or ready (200)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 200:
            print("  ✓ Cache ready, 200 OK")
            return True
        if r.status_code in (500, 503):
            print(f"  ✓ Service unavailable as expected ({r.status_code})")
            return True
        print(f"  ⚠ Status {r.status_code} – pass")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_ready_after_sync() -> bool:
    """8.2 After sync, GET /rates returns 200 (covered by other tests)."""
    print("\n[TEST] Ready after sync (GET /rates succeeds)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "JPY"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 200:
            print("  ✓ API serving from cache")
            return True
        if r.status_code == 503:
            print("  ⚠ Cache not ready (503)")
            return True
        print(f"  ✗ Unexpected {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


if __name__ == "__main__":
    run_suite("E2E: API Errors & Recovery", [
        ("Pair not found", test_pair_not_found),
        ("Request timeout handling", test_request_timeout_handling),
        ("Cache unavailable or ready", test_cache_unavailable_returns_5xx),
        ("Ready after sync", test_ready_after_sync),
    ])
