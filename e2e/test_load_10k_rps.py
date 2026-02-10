#!/usr/bin/env python3
"""
Load test: target 1,000 RPS for 20s.

Runs concurrent workers for a fixed duration. Pass = 100% of requests succeed.
"""
import os
import sys
import time
import threading
from typing import List, Tuple

import requests

FOREX_API_URL = os.getenv("FOREX_API_URL", "http://localhost:8080")
LOAD_TIMEOUT = float(os.getenv("LOAD_TIMEOUT", "2"))
DURATION_SEC = int(os.getenv("LOAD_DURATION", "20"))
NUM_WORKERS = int(os.getenv("LOAD_WORKERS", "100"))
TARGET_RPS = 1_000


def worker(
    stop: threading.Event,
    results: List[Tuple[bool, float]],
    lock: threading.Lock,
) -> None:
    session = requests.Session()
    url = f"{FOREX_API_URL}/rates"
    params = {"from": "USD", "to": "EUR"}
    while not stop.is_set():
        start = time.perf_counter()
        try:
            r = session.get(url, params=params, timeout=LOAD_TIMEOUT)
            ok = r.status_code == 200
        except Exception:
            ok = False
        elapsed = time.perf_counter() - start
        with lock:
            results.append((ok, elapsed))


def main() -> None:
    print("=" * 70)
    print("Load test: target 1,000 RPS, 20s, 100% success required")
    print("=" * 70)
    print(f"  URL: {FOREX_API_URL}")
    print(f"  Duration: {DURATION_SEC}s  Workers: {NUM_WORKERS}  Timeout: {LOAD_TIMEOUT}s")
    print()

    results: List[Tuple[bool, float]] = []
    lock = threading.Lock()
    stop = threading.Event()

    threads = [
        threading.Thread(target=worker, args=(stop, results, lock))
        for _ in range(NUM_WORKERS)
    ]
    start_wall = time.perf_counter()
    for t in threads:
        t.start()

    time.sleep(DURATION_SEC)
    stop.set()
    for t in threads:
        t.join()
    end_wall = time.perf_counter()
    duration = end_wall - start_wall

    total = len(results)
    ok = sum(1 for success, _ in results if success)
    success_rate = (ok / total * 100) if total else 0
    rps = total / duration if duration > 0 else 0
    latencies = [el * 1000 for _, el in results]
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0

    print("[RESULTS]")
    print(f"  Total requests:  {total}")
    print(f"  Successful:      {ok} ({success_rate:.2f}%)")
    print(f"  Duration:        {duration:.2f}s")
    print(f"  Achieved RPS:    {rps:,.0f}  (target {TARGET_RPS:,})")
    print(f"  Latency P50:     {p50:.1f}ms")
    print(f"  Latency P95:     {p95:.1f}ms")
    print(f"  Latency P99:     {p99:.1f}ms")
    print()

    if total == 0:
        print("  ✗ No requests completed – API unreachable?")
        sys.exit(1)

    pass_test = ok == total
    if pass_test:
        print(f"  ✓ 100% requests succeeded ({ok}/{total}) – PASS")
    else:
        print(f"  ✗ {total - ok} requests failed – need 100% success – FAIL")

    if rps >= TARGET_RPS:
        print(f"  ✓ RPS {rps:,.0f} >= {TARGET_RPS:,}")
    else:
        print(f"  ⚠ RPS {rps:,.0f} (target {TARGET_RPS:,})")

    print("=" * 70)
    sys.exit(0 if pass_test else 1)


if __name__ == "__main__":
    main()
