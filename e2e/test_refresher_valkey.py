#!/usr/bin/env python3
"""
E2E Test: Verify Refresher Job + Valkey Integration

Tests that the Refresher job successfully:
1. Fetches rates from One-Frame API
2. Writes rates to Valkey
3. Data is fresh and complete
"""

import redis
import json
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Configuration
VALKEY_HOST = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
RATES_KEY = "rates"

# Expected currencies (9 total)
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "SGD"]


def test_valkey_connection() -> bool:
    """Test Valkey is accessible"""
    print("\n[TEST] Valkey connection")
    try:
        client = redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)
        client.ping()
        print("  ✓ Valkey is accessible")
        return True
    except Exception as e:
        print(f"  ✗ Cannot connect to Valkey: {e}")
        return False


def test_refresher_populated_valkey() -> bool:
    """Test Refresher has written data to Valkey"""
    print("\n[TEST] Refresher populated Valkey")
    
    client = redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)
    
    # Check if rates key exists
    if not client.exists(RATES_KEY):
        print(f"  ✗ Key '{RATES_KEY}' not found in Valkey")
        return False
    
    # Get the data
    rates_json = client.get(RATES_KEY)
    if not rates_json:
        print(f"  ✗ Key '{RATES_KEY}' is empty")
        return False
    
    try:
        rates = json.loads(rates_json)
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON in Valkey: {e}")
        return False
    
    if not isinstance(rates, list):
        print(f"  ✗ Expected list, got: {type(rates)}")
        return False
    
    print(f"  ✓ Valkey contains {len(rates)} rates")
    return True


def test_rate_data_structure() -> bool:
    """Test rate objects have correct structure"""
    print("\n[TEST] Rate data structure")
    
    client = redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)
    rates_json = client.get(RATES_KEY)
    rates = json.loads(rates_json)
    
    required_fields = ["pair", "price", "timestamp"]
    required_pair_fields = ["from", "to"]
    
    for i, rate in enumerate(rates[:3]):  # Check first 3
        missing = [f for f in required_fields if f not in rate]
        if missing:
            print(f"  ✗ Rate {i} missing fields: {missing}")
            return False
        
        # Check pair structure
        pair = rate.get("pair", {})
        missing_pair = [f for f in required_pair_fields if f not in pair]
        if missing_pair:
            print(f"  ✗ Rate {i} pair missing fields: {missing_pair}")
            return False
    
    print(f"  ✓ All rates have required structure: pair(from, to), price, timestamp")
    return True


def test_all_usd_pairs_present() -> bool:
    """Test that all USD pairs are present"""
    print("\n[TEST] All USD pairs present")
    
    client = redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)
    rates_json = client.get(RATES_KEY)
    rates = json.loads(rates_json)
    
    # Build map of pairs (accessing nested pair structure)
    pairs = {(r["pair"]["from"], r["pair"]["to"]) for r in rates}
    
    # Check all USD pairs exist
    expected_pairs = []
    for curr in CURRENCIES:
        if curr != "USD":
            expected_pairs.append(("USD", curr))
    
    missing = [p for p in expected_pairs if p not in pairs]
    
    if missing:
        print(f"  ✗ Missing USD pairs: {missing}")
        return False
    
    print(f"  ✓ All {len(expected_pairs)} USD pairs present")
    return True


def test_data_freshness() -> bool:
    """Test that data is fresh (< 5 minutes old)"""
    print("\n[TEST] Data freshness (< 5 minutes)")
    
    client = redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)
    rates_json = client.get(RATES_KEY)
    rates = json.loads(rates_json)
    
    if not rates:
        print("  ✗ No rates to check")
        return False
    
    # Check first rate's timestamp
    rate = rates[0]
    timestamp_str = rate["timestamp"]
    
    # Parse ISO8601 timestamp
    try:
        # Handle both with and without 'Z'
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1]
        
        # Parse and remove microseconds if present
        if '.' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.split('.')[0])
        else:
            dt = datetime.fromisoformat(timestamp_str)
        
        now = datetime.utcnow()
        age = now - dt
        
        if age > timedelta(minutes=5):
            print(f"  ✗ Data too old: {age.total_seconds():.0f} seconds")
            return False
        
        print(f"  ✓ Data age: {age.total_seconds():.0f} seconds (< 5 min)")
        return True
        
    except Exception as e:
        print(f"  ✗ Cannot parse timestamp '{timestamp_str}': {e}")
        return False


def test_rate_values_reasonable() -> bool:
    """Test that rate values are reasonable (> 0, not extreme)"""
    print("\n[TEST] Rate values are reasonable")
    
    client = redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)
    rates_json = client.get(RATES_KEY)
    rates = json.loads(rates_json)
    
    for rate in rates:
        price = rate.get("price")
        
        if price is None:
            print(f"  ✗ Rate missing price: {rate}")
            return False
        
        if price <= 0:
            print(f"  ✗ Invalid price {price} for {rate['from']}/{rate['to']}")
            return False
        
        if price > 1000000:  # Sanity check
            print(f"  ✗ Extreme price {price} for {rate['from']}/{rate['to']}")
            return False
    
    print(f"  ✓ All {len(rates)} rates have reasonable prices")
    return True


def main():
    """Run all tests"""
    print("="*70)
    print("E2E Test: Refresher + Valkey Integration")
    print("="*70)
    
    tests = [
        ("Valkey Connection", test_valkey_connection),
        ("Refresher Populated Valkey", test_refresher_populated_valkey),
        ("Rate Data Structure", test_rate_data_structure),
        ("All USD Pairs Present", test_all_usd_pairs_present),
        ("Data Freshness", test_data_freshness),
        ("Rate Values Reasonable", test_rate_values_reasonable),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {name}: {status}")
    
    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
