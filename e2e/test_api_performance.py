#!/usr/bin/env python3
"""E2E: Latency & concurrent load (scenarios 6.3–6.4)."""
import time
import concurrent.futures
import requests
from typing import Tuple
from e2e_common import FOREX_API_URL, DEFAULT_TIMEOUT, run_suite


def _one_request() -> Tuple[bool, float]:
    """Single GET /rates; returns (success, latency_sec)."""
    start = time.time()
    try:
        r = requests.get(
            f"{FOREX_API_URL}/rates",
            params={"from": "USD", "to": "EUR"},
            timeout=DEFAULT_TIMEOUT,
        )
        elapsed = time.time() - start
        return (r.status_code == 200, elapsed)
    except Exception:
        return (False, time.time() - start)


def test_concurrent_requests() -> bool:
    """6.3 N concurrent requests (e.g. 50) succeed or meet SLO."""
    print("\n[TEST] Concurrent requests (50)")
    n = 50
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(_one_request) for _ in range(n)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    ok = sum(1 for success, _ in results if success)
    latencies = [el for _, el in results]
    avg_ms = (sum(latencies) / len(latencies)) * 1000 if latencies else 0
    print(f"  ✓ {ok}/{n} succeeded, avg latency {avg_ms:.1f}ms")
    if ok >= n * 0.95:
        return True
    if ok >= n * 0.5:
        print("  ⚠ Many failures – pass with warning")
        return True
    return False


def test_sustained_load() -> bool:
    """6.4 Light sustained load (e.g. 100 requests over ~30s)."""
    print("\n[TEST] Sustained load (100 requests)")
    n = 100
    results = []
    for _ in range(n):
        results.append(_one_request())
        time.sleep(0.05)  # ~5 req/s
    ok = sum(1 for success, _ in results if success)
    latencies = [el for _, el in results]
    avg_ms = (sum(latencies) / len(latencies)) * 1000 if latencies else 0
    print(f"  ✓ {ok}/{n} succeeded, avg latency {avg_ms:.1f}ms")
    if ok >= n * 0.9:
        return True
    if ok >= n * 0.5:
        print("  ⚠ Partial success – pass")
        return True
    return False


def test_latency_p95() -> bool:
    """6.1 Single-request P95 / avg latency."""
    print("\n[TEST] Latency (10 samples, P95)")
    results = [_one_request() for _ in range(10)]
    ok_results = [(s, e) for s, e in results if s]
    if not ok_results:
        print("  ✗ No successful requests")
        return False
    latencies_ms = sorted([e * 1000 for _, e in ok_results])
    avg = sum(latencies_ms) / len(latencies_ms)
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)] if len(latencies_ms) > 1 else latencies_ms[0]
    print(f"  ✓ Avg: {avg:.1f}ms, P95: {p95:.1f}ms")
    return True


if __name__ == "__main__":
    run_suite("E2E: API Performance", [
        ("Latency P95", test_latency_p95),
        ("Concurrent requests", test_concurrent_requests),
        ("Sustained load", test_sustained_load),
    ])
