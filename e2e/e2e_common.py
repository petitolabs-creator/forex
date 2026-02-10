"""Shared config and helpers for E2E tests. Not a test file (no test_ prefix)."""
import os

FOREX_API_URL = os.getenv("FOREX_API_URL", "http://localhost:8080")
VALKEY_HOST = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
ONEFRAME_URL = os.getenv("ONEFRAME_URL", "http://localhost:8081")
ONEFRAME_TOKEN = os.getenv("ONEFRAME_TOKEN", "10dc303535874aeccc86a8251e6992f5")

DEFAULT_TIMEOUT = 5
LONG_TIMEOUT = 10


def run_suite(name: str, tests: list) -> bool:
    """Run a list of (test_name, test_callable) and exit 0/1."""
    import sys
    print("=" * 70)
    print(name)
    print("=" * 70)
    results = []
    for label, fn in tests:
        try:
            ok = fn()
            results.append((label, ok))
        except Exception as e:
            print(f"  ✗ {label}: {e}")
            results.append((label, False))
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    for label, ok in results:
        print(f"  {'✓' if ok else '✗'} {label}: {'PASS' if ok else 'FAIL'}")
    print(f"\n{passed}/{total} passed")
    print("=" * 70)
    sys.exit(0 if passed == total else 1)
