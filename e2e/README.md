# E2E Tests

End-to-end tests for the Forex Proxy service.

## One-Frame Connection Test

Tests the ability to connect to the One-Frame API and fetch exchange rates.

### Running with Make (Recommended)

The easiest way to run E2E tests is using the Makefile from the project root:

```bash
# Run all E2E tests in Docker (from project root)
make e2e-test

# Run E2E tests locally (requires Python)
make e2e-test-local
```

### Running with Docker Compose

You can also run the tests directly with Docker Compose:

```bash
cd e2e
docker-compose up --build --abort-on-container-exit
docker-compose down
```

This will:
1. Start the One-Frame service
2. Build and run the E2E test container
3. Automatically discover and run all `test_*.py` files
4. Show the test results
5. Exit and clean up

### Running Locally

If you prefer to run the tests directly on your host machine:

1. **One-Frame Docker Container** must be running:
   ```bash
   docker run -p 8081:8080 paidyinc/one-frame
   ```

   Note: The container's internal port 8080 is mapped to host port 8081.

2. **Python 3** with `requests` library:
   ```bash
   pip3 install requests
   ```

3. **Run the test**:
   ```bash
   ./test_oneframe_connection.py
   ```

### Test Discovery

The test runner automatically discovers and runs all `test_*.py` files in the e2e directory:

- `run_all_tests.py` - Test runner (discovers and executes all tests)
- `test_oneframe_connection.py` - One-Frame API connection tests

To add a new test, simply create a new file matching the pattern `test_*.py` and it will be automatically discovered and executed.

### Current Tests

**test_pubsub_sync.py** - Pub/Sub event-driven sync (`rates_updated`):
1. **API accessible** – Prerequisite: API is up.
2. **Valkey accessible** – Prerequisite: Valkey has rates (Refresher has run).
3. **API syncs after PUBLISH** – SET new rates in Valkey, PUBLISH to `rates_updated`; within a few seconds the API serves the new data (proves event-driven sync).
4. **PUBLISH required for sync** – Without PUBLISH the API cache can stay stale; after PUBLISH the API returns the new value.

**test_oneframe_connection.py** - One-Frame API Connection:
1. **Single Pair Fetch**: Fetches a single currency pair (USDEUR)
2. **Single Pair Fetch**: Fetches another currency pair (USDJPY)
3. **Multiple Pairs Fetch**: Fetches all 8 USD pairs in one request

**test_forex_server.py** - Forex Server API (8 tests):
1. **Valid Currency Pairs**: Tests USD/EUR, JPY/GBP, EUR/USD
2. **Invalid Currency Code**: Tests error handling for invalid currency (XXX)
3. **Missing Parameters**: Tests error handling when from/to params are missing
4. **Same Currency Pair**: Tests USD/USD edge case
5. **Multiple Currency Pairs**: Tests 6 different currency combinations
6. **Response Time**: Validates response time is reasonable (<10s)

### Expected Output

```
======================================================================
One-Frame API Connection E2E Tests
======================================================================
[INFO] Checking One-Frame service availability...
  ✓ One-Frame service is reachable

[TEST] Fetching single pair: USDEUR
  ✓ Success
    USD/EUR: 0.85
    Timestamp: 2026-02-09T22:15:30Z

[TEST] Fetching single pair: USDJPY
  ✓ Success
    USD/JPY: 110.25
    Timestamp: 2026-02-09T22:15:30Z

[TEST] Fetching 8 pairs in one request
  ✓ Success - received 8 rates
    USD/AUD: 1.35
    USD/CAD: 1.25
    ...

[TEST] Testing invalid token rejection
  ✓ Success - invalid token rejected (status: 403)

======================================================================
Test Results Summary
======================================================================
  ✓ Single pair fetch (USDEUR): PASS
  ✓ Single pair fetch (USDJPY): PASS
  ✓ Multiple pairs fetch (8 pairs): PASS
  ✓ Invalid token rejection: PASS

======================================================================
Total: 4 tests | Passed: 4 | Failed: 0
======================================================================

✓ All tests passed!
```

### Configuration

The test uses the following defaults:

- **One-Frame URL**: `http://localhost:8081` (or `ONEFRAME_URL` env var)
- **Token**: `10dc303535874aeccc86a8251e6992f5` (or `ONEFRAME_TOKEN` env var)
- **Pairs**: All USD pairs (USDAUD, USDCAD, USDCHF, USDEUR, USDGBP, USDNZD, USDJPY, USDSGD)

You can override the URL and token using environment variables:
```bash
ONEFRAME_URL=http://custom-host:8080 ONEFRAME_TOKEN=mytoken ./test_oneframe_connection.py
```

When running with Docker Compose, these are configured automatically in `docker-compose.yml`.
