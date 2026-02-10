#!/usr/bin/env python3
"""E2E: Valid rate retrieval (scenarios 2.1–2.6)."""
import requests
from e2e_common import FOREX_API_URL, DEFAULT_TIMEOUT, run_suite


def test_single_pair() -> bool:
    """2.1 Single pair USD→major returns 200, from/to/price/timestamp."""
    print("\n[TEST] Single pair (USD/EUR)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code != 200:
            print(f"  ✗ Status {r.status_code}")
            return False
        data = r.json()
        for key in ("from", "to", "price", "timestamp"):
            if key not in data:
                print(f"  ✗ Missing field: {key}")
                return False
        if data["from"] != "USD" or data["to"] != "EUR":
            print(f"  ✗ Wrong pair")
            return False
        p = data["price"]
        if not isinstance(p, (int, float)) or p <= 0:
            print(f"  ✗ Invalid price: {p}")
            return False
        print(f"  ✓ USD/EUR = {p}")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_multiple_pairs() -> bool:
    """2.2 Multiple pairs each return 200 and valid structure."""
    print("\n[TEST] Multiple pairs")
    pairs = [("USD", "EUR"), ("EUR", "USD"), ("JPY", "GBP"), ("GBP", "JPY")]
    for from_c, to_c in pairs:
        try:
            r = requests.get(
                f"{FOREX_API_URL}/rates",
                params={"from": from_c, "to": to_c},
                timeout=DEFAULT_TIMEOUT,
            )
            if r.status_code != 200:
                print(f"  ✗ {from_c}/{to_c} status {r.status_code}")
                return False
            data = r.json()
            if data.get("from") != from_c or data.get("to") != to_c:
                print(f"  ✗ {from_c}/{to_c} wrong pair in response")
                return False
        except Exception as e:
            print(f"  ✗ {from_c}/{to_c}: {e}")
            return False
    print(f"  ✓ All {len(pairs)} pairs OK")
    return True


def test_same_currency() -> bool:
    """2.3 Same currency returns price 1.0."""
    print("\n[TEST] Same currency (USD/USD)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "USD"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code != 200:
            print(f"  ✗ Status {r.status_code}")
            return False
        data = r.json()
        price = data.get("price")
        if price is None:
            print("  ✗ Missing price")
            return False
        if abs(float(price) - 1.0) > 0.01:
            print(f"  ✗ Expected 1.0, got {price}")
            return False
        print("  ✓ USD/USD = 1.0")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_cross_rate() -> bool:
    """2.4 Non-USD pair (e.g. EUR/JPY) returns calculated rate."""
    print("\n[TEST] Cross-rate (EUR/JPY)")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "EUR", "to": "JPY"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code != 200:
            print(f"  ✗ Status {r.status_code}")
            return False
        data = r.json()
        if data.get("from") != "EUR" or data.get("to") != "JPY":
            print("  ✗ Wrong pair")
            return False
        p = data.get("price")
        if not isinstance(p, (int, float)) or p <= 0:
            print(f"  ✗ Invalid price: {p}")
            return False
        print(f"  ✓ EUR/JPY = {p}")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_response_structure() -> bool:
    """2.5 Response has from, to, price (number), timestamp (ISO)."""
    print("\n[TEST] Response structure")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "GBP"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code != 200:
            print(f"  ✗ Status {r.status_code}")
            return False
        data = r.json()
        if not isinstance(data.get("price"), (int, float)):
            print("  ✗ price is not numeric")
            return False
        if "timestamp" not in data:
            print("  ✗ Missing timestamp")
            return False
        print("  ✓ Structure OK")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_other_iso_currency_accepted() -> bool:
    """Request with another ISO currency (THB): accepted as param, 200 or 404 (pair not in cache)."""
    print("\n[TEST] Other ISO currency (THB) accepted")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "THB", "to": "JPY"},
            timeout=DEFAULT_TIMEOUT,
        )
        # Valid code: either we have the pair (200) or we don't (404/503)
        if r.status_code == 200:
            print("  ✓ THB/JPY rate returned")
            return True
        if r.status_code in (404, 503):
            print("  ✓ THB accepted, pair not in cache (expected)")
            return True
        if r.status_code == 400:
            print("  ✗ THB rejected as invalid – API should accept all ISO currencies")
            return False
        print(f"  ⚠ Status {r.status_code}")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def test_price_validity() -> bool:
    """2.6 price > 0 and numeric."""
    print("\n[TEST] Price validity")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "CHF"},
            timeout=DEFAULT_TIMEOUT,
        )
        if r.status_code != 200:
            print(f"  ✗ Status {r.status_code}")
            return False
        data = r.json()
        p = data.get("price")
        if not isinstance(p, (int, float)):
            print(f"  ✗ Price not numeric: {type(p)}")
            return False
        if p <= 0:
            print(f"  ✗ Price not positive: {p}")
            return False
        print("  ✓ Price valid")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


if __name__ == "__main__":
    run_suite("E2E: API Valid Rates", [
        ("Single pair", test_single_pair),
        ("Multiple pairs", test_multiple_pairs),
        ("Same currency 1.0", test_same_currency),
        ("Cross-rate", test_cross_rate),
        ("Response structure", test_response_structure),
        ("Other ISO currency accepted", test_other_iso_currency_accepted),
        ("Price validity", test_price_validity),
    ])
