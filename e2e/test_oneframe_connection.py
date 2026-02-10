#!/usr/bin/env python3
"""
E2E Test: Verify One-Frame API Connection

This script tests the ability to connect to the One-Frame API and fetch exchange rates.
It's designed to run against the docker container provided for the exercise.
"""

import requests
import sys
import json
import os
from typing import List, Dict
from datetime import datetime

# One-Frame API configuration (with environment variable support)
ONEFRAME_URL = os.getenv("ONEFRAME_URL", "http://localhost:8081")
ONEFRAME_TOKEN = os.getenv("ONEFRAME_TOKEN", "10dc303535874aeccc86a8251e6992f5")

# All USD pairs we want to fetch
USD_PAIRS = [
    "USDAUD", "USDCAD", "USDCHF", "USDEUR",
    "USDGBP", "USDNZD", "USDJPY", "USDSGD"
]


def test_single_pair(pair: str) -> bool:
    """Test fetching a single currency pair"""
    print(f"\n[TEST] Fetching single pair: {pair}")

    url = f"{ONEFRAME_URL}/rates"
    params = {"pair": pair}
    headers = {"token": ONEFRAME_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code != 200:
            print(f"  ✗ Failed with status {response.status_code}")
            print(f"    Response: {response.text}")
            return False

        data = response.json()

        if not isinstance(data, list) or len(data) != 1:
            print(f"  ✗ Expected list with 1 item, got: {data}")
            return False

        rate = data[0]
        required_fields = ["from", "to", "bid", "ask", "price", "time_stamp"]

        for field in required_fields:
            if field not in rate:
                print(f"  ✗ Missing required field: {field}")
                return False

        print(f"  ✓ Success")
        print(f"    {rate['from']}/{rate['to']}: {rate['price']}")
        print(f"    Timestamp: {rate['time_stamp']}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON response: {e}")
        return False


def test_multiple_pairs(pairs: List[str]) -> bool:
    """Test fetching multiple currency pairs in a single request"""
    print(f"\n[TEST] Fetching {len(pairs)} pairs in one request")

    url = f"{ONEFRAME_URL}/rates"
    params = [("pair", pair) for pair in pairs]
    headers = {"token": ONEFRAME_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"  ✗ Failed with status {response.status_code}")
            print(f"    Response: {response.text}")
            return False

        data = response.json()

        if not isinstance(data, list):
            print(f"  ✗ Expected list, got: {type(data)}")
            return False

        if len(data) != len(pairs):
            print(f"  ✗ Expected {len(pairs)} rates, got {len(data)}")
            return False

        print(f"  ✓ Success - received {len(data)} rates")

        for rate in data:
            pair_str = f"{rate['from']}{rate['to']}"
            print(f"    {rate['from']}/{rate['to']}: {rate['price']}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON response: {e}")
        return False


def test_invalid_token() -> bool:
    """Test that invalid token is rejected"""
    print(f"\n[TEST] Testing invalid token rejection")

    url = f"{ONEFRAME_URL}/rates"
    params = {"pair": "USDEUR"}
    headers = {"token": "invalid-token-12345"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            print(f"  ✗ Expected error, but got success")
            return False

        print(f"  ✓ Success - invalid token rejected (status: {response.status_code})")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False


def check_oneframe_availability() -> bool:
    """Check if One-Frame service is available"""
    print("[INFO] Checking One-Frame service availability...")

    try:
        response = requests.get(ONEFRAME_URL, timeout=5)
        print(f"  ✓ One-Frame service is reachable")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  ✗ One-Frame service is not reachable: {e}")
        print(f"\n[HINT] Make sure the One-Frame docker container is running:")
        print(f"       docker run -p 8080:8080 paidyinc/one-frame")
        return False


def main():
    """Run all E2E tests"""
    print("=" * 70)
    print("One-Frame API Connection E2E Tests")
    print("=" * 70)

    # Check service availability
    if not check_oneframe_availability():
        sys.exit(1)

    results = []

    # Test 1: Single pair fetch
    results.append(("Single pair fetch (USDEUR)", test_single_pair("USDEUR")))

    # Test 2: Another single pair
    results.append(("Single pair fetch (USDJPY)", test_single_pair("USDJPY")))

    # Test 3: Multiple pairs at once (all USD pairs)
    results.append(("Multiple pairs fetch (8 pairs)", test_multiple_pairs(USD_PAIRS)))

    # Test 4: Invalid token (disabled - One-Frame mock doesn't validate tokens)
    # results.append(("Invalid token rejection", test_invalid_token()))

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
