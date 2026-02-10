#!/usr/bin/env python3
"""
E2E Test: Pub/Sub Event-Driven Sync (rates_updated)

Verifies that when Valkey is updated and a message is published to the
rates_updated channel, the API pod receives the event and syncs its in-memory
cache from Valkey (event-driven sync, not polling).

Flow under test:
  1. Refresher (or test) writes rates to Valkey (SET rates).
  2. Refresher (or test) publishes to channel "rates_updated" (PUBLISH).
  3. API pod is subscribed to rates_updated; on message it GETs rates from Valkey.
  4. API cache is updated; next GET /rates returns the new data.

Tests:
  - API cache reflects Valkey after we SET rates + PUBLISH rates_updated.
  - Channel rates_updated is used (publish triggers sync within a few seconds).
"""

import json
import os
import sys
import time

import redis
import requests

# Configuration
FOREX_API_URL = os.getenv("FOREX_API_URL", "http://localhost:8080")
VALKEY_HOST = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
RATES_KEY = "rates"
RATES_UPDATED_CHANNEL = "rates_updated"

# How long to wait for API to process pub/sub message and sync (seconds)
SYNC_WAIT_SECONDS = 5


def get_valkey_client():
    return redis.Redis(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)


def test_api_accessible() -> bool:
    """Ensure API is up and returns rates (prerequisite)."""
    print("\n[TEST] API is accessible")
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=5,
        )
        if r.status_code != 200:
            print(f"  ✗ API returned {r.status_code}")
            return False
        print("  ✓ API is up and returns rates")
        return True
    except Exception as e:
        print(f"  ✗ Cannot reach API: {e}")
        return False


def test_valkey_accessible() -> bool:
    """Ensure Valkey is up and has rates key (prerequisite)."""
    print("\n[TEST] Valkey is accessible and has rates")
    try:
        client = get_valkey_client()
        client.ping()
        raw = client.get(RATES_KEY)
        if not raw:
            print(f"  ✗ Key '{RATES_KEY}' not found (Refresher may not have run)")
            return False
        rates = json.loads(raw)
        if not isinstance(rates, list) or len(rates) == 0:
            print(f"  ✗ '{RATES_KEY}' is empty or not a list")
            return False
        print(f"  ✓ Valkey has {len(rates)} rates")
        return True
    except Exception as e:
        print(f"  ✗ Valkey: {e}")
        return False


def test_api_syncs_after_publish() -> bool:
    """
    Event-driven sync: after we SET new rates in Valkey and PUBLISH to
    rates_updated, the API should serve the new data (it subscribed and
    syncs on message).
    """
    print("\n[TEST] API syncs from Valkey after PUBLISH rates_updated (event-driven)")

    client = get_valkey_client()

    # 1) Backup current rates
    raw_original = client.get(RATES_KEY)
    if not raw_original:
        print("  ✗ No existing rates in Valkey")
        return False
    original_rates = json.loads(raw_original)

    # 2) Build modified rates: set USD/EUR to a unique sentinel so we can assert
    sentinel_price = 77.777777
    modified_rates = []
    for r in original_rates:
        pair = r.get("pair") or {}
        if pair.get("from") == "USD" and pair.get("to") == "EUR":
            modified_rates.append({
                **r,
                "price": sentinel_price,
            })
        else:
            modified_rates.append(r)

    # 3) Write to Valkey (simulate Refresher SET)
    client.set(RATES_KEY, json.dumps(modified_rates))

    # 4) Publish to rates_updated (simulate Refresher publishRatesUpdated)
    num_subscribers = client.publish(RATES_UPDATED_CHANNEL, "1")
    print(f"  → Published to '{RATES_UPDATED_CHANNEL}' (subscribers: {num_subscribers})")

    # 5) Wait for API to receive message and sync
    time.sleep(SYNC_WAIT_SECONDS)

    # 6) Ask API for USD/EUR — must return the new value
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=5,
        )
    except Exception as e:
        print(f"  ✗ API request failed: {e}")
        _restore_valkey(client, raw_original)
        return False

    if r.status_code != 200:
        print(f"  ✗ API returned {r.status_code}")
        _restore_valkey(client, raw_original)
        return False

    data = r.json()
    api_price = data.get("price")
    if api_price is None:
        print("  ✗ Response missing price")
        _restore_valkey(client, raw_original)
        return False

    # Allow small float tolerance
    if abs(float(api_price) - sentinel_price) > 0.0001:
        print(f"  ✗ Expected price ~{sentinel_price} (event-driven sync), got {api_price}")
        _restore_valkey(client, raw_original)
        return False

    print(f"  ✓ API returned new price {api_price} after PUBLISH (event-driven sync works)")

    # 7) Restore Valkey so other tests see original data; notify API again
    _restore_valkey(client, raw_original)
    return True


def _restore_valkey(client: redis.Redis, original_json: str) -> None:
    """Restore Valkey to original rates and publish so API re-syncs."""
    try:
        client.set(RATES_KEY, original_json)
        client.publish(RATES_UPDATED_CHANNEL, "1")
    except Exception:
        pass


def test_publish_triggers_sync_not_polling() -> bool:
    """
    Sanity: if we only SET Valkey but do NOT publish, the API might still
    have old cache for a while (we use event-driven sync, not 150s polling).
    So after SET + no PUBLISH, waiting a few seconds and checking could show
    old value. Then we PUBLISH and see new value. This reinforces that
    PUBLISH is what triggers the sync.
    """
    print("\n[TEST] PUBLISH is required for sync (no publish = cache can stay stale)")

    client = get_valkey_client()
    raw_original = client.get(RATES_KEY)
    if not raw_original:
        print("  ✗ No rates in Valkey")
        return False
    original_rates = json.loads(raw_original)

    sentinel_price = 66.666666
    modified_rates = []
    for r in original_rates:
        pair = r.get("pair") or {}
        if pair.get("from") == "USD" and pair.get("to") == "EUR":
            modified_rates.append({**r, "price": sentinel_price})
        else:
            modified_rates.append(r)

    # SET only — do NOT publish yet
    client.set(RATES_KEY, json.dumps(modified_rates))
    time.sleep(2)

    # API might still have old value (event-driven: no event yet)
    r = requests.get(
        f"{FOREX_API_URL}/rates",
        params={"from": "USD", "to": "EUR"},
        timeout=5,
    )
    if r.status_code != 200:
        _restore_valkey(client, raw_original)
        return False

    api_price_before = r.json().get("price")
    # Now publish
    client.publish(RATES_UPDATED_CHANNEL, "1")
    time.sleep(SYNC_WAIT_SECONDS)

    r2 = requests.get(
        f"{FOREX_API_URL}/rates",
        params={"from": "USD", "to": "EUR"},
        timeout=5,
    )
    if r2.status_code != 200:
        _restore_valkey(client, raw_original)
        return False
    api_price_after = r2.json().get("price")

    _restore_valkey(client, raw_original)

    # After PUBLISH we must see the new value
    if abs(float(api_price_after) - sentinel_price) > 0.0001:
        print(f"  ✗ After PUBLISH expected ~{sentinel_price}, got {api_price_after}")
        return False
    print(f"  ✓ Before PUBLISH: {api_price_before}; after PUBLISH: {api_price_after} (sync on event)")
    return True


def main():
    print("=" * 70)
    print("E2E Test: Pub/Sub Event-Driven Sync (rates_updated)")
    print("=" * 70)

    tests = [
        ("API accessible", test_api_accessible),
        ("Valkey accessible", test_valkey_accessible),
        ("API syncs after PUBLISH", test_api_syncs_after_publish),
        ("PUBLISH required for sync", test_publish_triggers_sync_not_polling),
    ]

    results = []
    for name, test_func in tests:
        try:
            ok = test_func()
            results.append((name, ok))
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {name}: {'PASS' if ok else 'FAIL'}")
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n✓ All pub/sub sync tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
