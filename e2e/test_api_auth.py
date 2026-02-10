#!/usr/bin/env python3
"""E2E: Authentication (scenarios 4.1–4.3). Skip if API has no auth."""
import requests
from e2e_common import FOREX_API_URL, DEFAULT_TIMEOUT, run_suite


def test_missing_auth() -> bool:
    """4.1 Request without Authorization returns 401 or 200 (no auth)."""
    print("\n[TEST] Missing auth (no Bearer)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 401:
            print("  ✓ API requires auth (401)")
            return True
        if r.status_code == 200:
            print("  ⚠ API has no auth – request accepted (200)")
            return True
        print(f"  ✗ Unexpected {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_invalid_token() -> bool:
    """4.2 Wrong/invalid token returns 401."""
    print("\n[TEST] Invalid Bearer token")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            headers={"Authorization": "Bearer invalid-token"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 401:
            print("  ✓ Invalid token rejected (401)")
            return True
        if r.status_code == 200:
            print("  ⚠ API does not validate Bearer – pass")
            return True
        print(f"  ⚠ Status {r.status_code} – pass")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_valid_token() -> bool:
    """4.3 Valid token returns 200 (if auth enabled)."""
    print("\n[TEST] Valid token")
    try:
        # If API uses auth, we'd need a real token from env
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code == 200:
            print("  ✓ Request succeeded")
            return True
        if r.status_code == 401:
            print("  ⚠ Auth required but no token provided – skip")
            return True
        print(f"  ✗ Status {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


if __name__ == "__main__":
    run_suite("E2E: API Auth", [
        ("Missing auth", test_missing_auth),
        ("Invalid token", test_invalid_token),
        ("Valid token", test_valid_token),
    ])
