#!/usr/bin/env python3
"""
Test Runner: Discovers and runs all test_*.py files in the current directory
"""

import sys
import os
import subprocess
from pathlib import Path


def discover_tests():
    """Find all test_*.py files in current directory"""
    test_files = sorted(Path('.').glob('test_*.py'))
    return [f for f in test_files if f.name != 'run_all_tests.py']


def run_test(test_file):
    """Run a single test file and return success status"""
    print(f"\n{'='*70}")
    print(f"Running: {test_file}")
    print('='*70)

    try:
        result = subprocess.run(
            ['python3', str(test_file)],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {test_file}: {e}")
        return False


def main():
    """Main test runner"""
    test_files = discover_tests()

    if not test_files:
        print("No test files found (test_*.py)")
        sys.exit(1)

    print(f"Discovered {len(test_files)} test file(s):")
    for test_file in test_files:
        print(f"  - {test_file}")

    results = {}
    for test_file in test_files:
        success = run_test(test_file)
        results[test_file] = success

    # Summary
    print("\n" + "="*70)
    print("Test Suite Summary")
    print("="*70)

    passed = sum(1 for success in results.values() if success)
    failed = len(results) - passed

    for test_file, success in results.items():
        status = "PASS" if success else "FAIL"
        symbol = "✓" if success else "✗"
        print(f"  {symbol} {test_file}: {status}")

    print("\n" + "="*70)
    print(f"Total: {len(results)} test files | Passed: {passed} | Failed: {failed}")
    print("="*70)

    if failed > 0:
        print("\n✗ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✓ All test files passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
