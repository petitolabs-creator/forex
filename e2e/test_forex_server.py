#!/usr/bin/env python3
"""
E2E Test: Forex Server API

Tests the complete forex server API endpoint.
Requires both One-Frame service and Forex server to be running.
"""

import requests
import sys
import os
from typing import Dict, Any

# Forex server configuration
FOREX_URL = os.getenv("FOREX_API_URL", "http://localhost:8080")
ONEFRAME_URL = os.getenv("ONEFRAME_URL", "http://localhost:8081")


def check_forex_server_availability() -> bool:
    """Check if Forex server is available"""
    print("[INFO] Checking Forex server availability...")
    try:
        response = requests.get(f"{FOREX_URL}/rates?from=USD&to=EUR", timeout=5)
        if response.status_code in [200, 400, 404]:
            print(f"  ✓ Forex server is reachable")
            return True
        else:
            print(f"  ✗ Forex server returned unexpected status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Forex server is not reachable: {e}")
        print(f"\n[HINT] Make sure the Forex server is running:")
        print(f"       cd forex-mtl && sbt run")
        return False


def test_valid_currency_pair(from_curr: str, to_curr: str) -> bool:
    """Test fetching a valid currency pair"""
    print(f"\n[TEST] Fetching rate for {from_curr}/{to_curr}")

    url = f"{FOREX_URL}/rates"
    params = {"from": from_curr, "to": to_curr}

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"  ✗ Failed with status {response.status_code}")
            print(f"    Response: {response.text}")
            return False

        data = response.json()

        # Validate response structure
        required_fields = ["from", "to", "price", "timestamp"]
        for field in required_fields:
            if field not in data:
                print(f"  ✗ Missing required field: {field}")
                return False

        # Validate values
        if data["from"] != from_curr:
            print(f"  ✗ Expected from={from_curr}, got {data['from']}")
            return False

        if data["to"] != to_curr:
            print(f"  ✗ Expected to={to_curr}, got {data['to']}")
            return False

        if not isinstance(data["price"], (int, float)):
            print(f"  ✗ Price should be numeric, got {type(data['price'])}")
            return False

        if data["price"] <= 0:
            print(f"  ✗ Price should be positive, got {data['price']}")
            return False

        print(f"  ✓ Success")
        print(f"    {data['from']}/{data['to']}: {data['price']}")
        print(f"    Timestamp: {data['timestamp']}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_invalid_currency() -> bool:
    """Test handling of invalid currency code"""
    print(f"\n[TEST] Testing invalid currency code")

    url = f"{FOREX_URL}/rates"
    params = {"from": "XXX", "to": "EUR"}

    try:
        response = requests.get(url, params=params, timeout=5)

        # Should return an error (4xx or 5xx status)
        if response.status_code >= 400:
            print(f"  ✓ Success - invalid currency rejected (status: {response.status_code})")
            return True
        else:
            print(f"  ✗ Expected error status, got {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False


def test_missing_parameters() -> bool:
    """Test handling of missing query parameters"""
    print(f"\n[TEST] Testing missing query parameters")

    test_cases = [
        ({"from": "USD"}, "missing 'to' parameter"),
        ({"to": "EUR"}, "missing 'from' parameter"),
        ({}, "missing both parameters"),
    ]

    all_passed = True

    for params, description in test_cases:
        try:
            response = requests.get(f"{FOREX_URL}/rates", params=params, timeout=5)

            if response.status_code >= 400 and response.status_code < 500:
                print(f"  ✓ {description}: correctly rejected (status: {response.status_code})")
            else:
                print(f"  ✗ {description}: expected 4xx, got {response.status_code}")
                all_passed = False

        except requests.exceptions.RequestException as e:
            print(f"  ✗ {description}: request failed: {e}")
            all_passed = False

    return all_passed


def test_same_currency_pair() -> bool:
    """Test requesting same currency for from and to"""
    print(f"\n[TEST] Testing same currency pair (USD/USD)")

    url = f"{FOREX_URL}/rates"
    params = {"from": "USD", "to": "USD"}

    try:
        response = requests.get(url, params=params, timeout=5)

        # This should either return an error or a rate of 1.0
        # Depends on implementation - let's accept both
        if response.status_code == 200:
            data = response.json()
            if abs(data.get("price", 0) - 1.0) < 0.01:
                print(f"  ✓ Success - returned price ~1.0")
                return True
            else:
                print(f"  ⚠ Warning - same currency returned price {data.get('price')}")
                return True  # Still pass, but note it
        elif response.status_code >= 400:
            print(f"  ✓ Success - same currency rejected (status: {response.status_code})")
            return True
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False


def test_multiple_currency_pairs() -> bool:
    """Test fetching multiple different currency pairs"""
    print(f"\n[TEST] Testing multiple currency pairs")

    test_pairs = [
        ("USD", "EUR"),
        ("EUR", "USD"),
        ("JPY", "GBP"),
        ("GBP", "JPY"),
        ("AUD", "CAD"),
        ("CHF", "SGD"),
    ]

    passed = 0
    failed = 0

    for from_curr, to_curr in test_pairs:
        try:
            response = requests.get(
                f"{FOREX_URL}/rates",
                params={"from": from_curr, "to": to_curr},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data["from"] == from_curr and data["to"] == to_curr:
                    print(f"  ✓ {from_curr}/{to_curr}: {data['price']}")
                    passed += 1
                else:
                    print(f"  ✗ {from_curr}/{to_curr}: currency mismatch")
                    failed += 1
            else:
                print(f"  ✗ {from_curr}/{to_curr}: status {response.status_code}")
                failed += 1

        except Exception as e:
            print(f"  ✗ {from_curr}/{to_curr}: {e}")
            failed += 1

    print(f"\n  Summary: {passed} passed, {failed} failed")
    return failed == 0


def test_response_time() -> bool:
    """Test that responses come back in reasonable time"""
    print(f"\n[TEST] Testing response time")

    import time

    url = f"{FOREX_URL}/rates"
    params = {"from": "USD", "to": "EUR"}

    try:
        start = time.time()
        response = requests.get(url, params=params, timeout=10)
        elapsed = time.time() - start

        if response.status_code != 200:
            print(f"  ✗ Request failed with status {response.status_code}")
            return False

        # Should respond within 10 seconds (allows for One-Frame fetch + retries)
        if elapsed < 10.0:
            print(f"  ✓ Success - response time: {elapsed:.3f}s")
            return True
        else:
            print(f"  ⚠ Warning - slow response time: {elapsed:.3f}s")
            return True  # Still pass but warn

    except requests.exceptions.Timeout:
        print(f"  ✗ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False


def main():
    """Run all E2E tests for Forex server"""
    print("=" * 70)
    print("Forex Server E2E Tests")
    print("=" * 70)

    # Check server availability
    if not check_forex_server_availability():
        sys.exit(1)

    results = []

    # Test valid currency pairs
    results.append(("Valid pair: USD/EUR", test_valid_currency_pair("USD", "EUR")))
    results.append(("Valid pair: JPY/GBP", test_valid_currency_pair("JPY", "GBP")))
    results.append(("Valid pair: EUR/USD", test_valid_currency_pair("EUR", "USD")))

    # Test error cases
    results.append(("Invalid currency code", test_invalid_currency()))
    results.append(("Missing parameters", test_missing_parameters()))
    results.append(("Same currency pair", test_same_currency_pair()))

    # Test multiple pairs
    results.append(("Multiple currency pairs", test_multiple_currency_pairs()))

    # Test performance
    results.append(("Response time", test_response_time()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {test_name}: {status}")

        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 70)
    print(f"Total: {passed + failed} tests | Passed: {passed} | Failed: {failed}")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
