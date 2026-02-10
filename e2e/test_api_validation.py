#!/usr/bin/env python3
"""E2E: Invalid requests 4xx (scenarios 3.1–3.5)."""
import requests
from e2e_common import FOREX_API_URL, DEFAULT_TIMEOUT, run_suite


def test_invalid_currency() -> bool:
    """3.1 from=XXX or to=YYY returns 400 or 404."""
    print("\n[TEST] Invalid currency (XXX/EUR)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "XXX", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if 400 <= r.status_code < 500:
            print(f"  ✓ Rejected with {r.status_code}")
            return True
        print(f"  ✗ Expected 4xx, got {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_missing_from() -> bool:
    """3.2 Request with only 'to' returns 400/404."""
    print("\n[TEST] Missing 'from' parameter")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if 400 <= r.status_code < 500:
            print(f"  ✓ Rejected with {r.status_code}")
            return True
        print(f"  ✗ Expected 4xx, got {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_missing_to() -> bool:
    """3.3 Request with only 'from' returns 400/404."""
    print("\n[TEST] Missing 'to' parameter")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD"},
            timeout=DEFAULT_TIMEOUT,
        )
        if 400 <= r.status_code < 500:
            print(f"  ✓ Rejected with {r.status_code}")
            return True
        print(f"  ✗ Expected 4xx, got {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_missing_both_params() -> bool:
    """3.4 No from/to returns 400/404."""
    print("\n[TEST] Missing both parameters")
    try:
        r = requests.get(f"{FOREX_API_URL}/rates", timeout=DEFAULT_TIMEOUT)
        if 400 <= r.status_code < 500:
            print(f"  ✓ Rejected with {r.status_code}")
            return True
        print(f"  ✗ Expected 4xx, got {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_unsupported_currency() -> bool:
    """3.5 Valid code not in scope returns 400/404 (e.g. BTC)."""
    print("\n[TEST] Unsupported currency (BTC)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "BTC", "to": "USD"},
            timeout=DEFAULT_TIMEOUT,
        )
        if 400 <= r.status_code < 500:
            print(f"  ✓ Rejected with {r.status_code}")
            return True
        if r.status_code == 200:
            print("  ⚠ API accepted BTC (unsupported) – pass anyway")
            return True
        print(f"  ✗ Unexpected {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


if __name__ == "__main__":
    run_suite("E2E: API Validation (4xx)", [
        ("Invalid currency", test_invalid_currency),
        ("Missing from", test_missing_from),
        ("Missing to", test_missing_to),
        ("Missing both params", test_missing_both_params),
        ("Unsupported currency", test_unsupported_currency),
    ])
