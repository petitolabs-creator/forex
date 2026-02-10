# Docker Compose E2E Tests

## Overview

E2E tests for the Refresher service running in Docker Compose environment.

## Architecture

```
┌─────────────┐       ┌──────────────┐       ┌─────────┐
│  Refresher  │──────>│  One-Frame   │       │ Valkey  │
│  (CronJob)  │       │     API      │       │ (Redis) │
└──────┬──────┘       └──────────────┘       └────┬────┘
       │                                           │
       └───────────> Write rates ─────────────────┘
                                                   │
                                        ┌──────────▼──────┐
                                        │   E2E Tests     │
                                        │  (Verification) │
                                        └─────────────────┘
```

## Services

1. **valkey** - Redis-compatible cache (port 6379)
2. **one-frame** - Mock external API (port 8081)
3. **refresher** - Fetches from One-Frame → writes to Valkey
4. **e2e-tests** - Verifies data in Valkey

## Running Tests

### Full E2E Suite

```bash
cd e2e
docker-compose up --build --abort-on-container-exit
docker-compose down
```

### Run Specific Test

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d valkey one-frame refresher

# Run specific test
docker-compose run --rm e2e-tests python3 test_refresher_docker.py

# Cleanup
docker-compose down
```

### Local Development (without Docker)

```bash
# Start Valkey
docker run -d -p 6379:6379 --name valkey-dev valkey/valkey:7

# Start One-Frame
docker run -d -p 8081:8080 --name one-frame-dev paidyinc/one-frame

# Run integration tests
python3 test_refresher_integration.py

# Cleanup
docker stop valkey-dev one-frame-dev
docker rm valkey-dev one-frame-dev
```

## Test Coverage

### test_refresher_docker.py
- ✅ Valkey connection
- ✅ Refresher wrote data to Valkey
- ✅ Rate data structure validation
- ✅ Minimum rate count (≥8 USD pairs)
- ✅ USD currency pairs present

### test_refresher_integration.py
- ✅ Valkey write/read operations
- ✅ One-Frame API availability
- ✅ Full fetch & store workflow

### test_oneframe_connection.py
- ✅ One-Frame API connectivity
- ✅ Rate retrieval
- ✅ Token authentication

### test_forex_server.py
- ✅ Forex API endpoints
- ✅ Valid currency pairs
- ✅ Error handling
- ✅ Response validation

## Expected Results

```
============================================================
Refresher Docker E2E Tests
============================================================
Valkey: forex-valkey:6379

=== Test: Valkey Connection ===
✅ Valkey connection successful

=== Test: Refresher Wrote Data ===
✅ Found 8 rates in Valkey

=== Test: Rate Data Structure ===
✅ Rate structure valid
   Example: USD/EUR = 0.85

=== Test: Minimum Rate Count ===
✅ Rate count sufficient: 8 rates

=== Test: USD Pairs Present ===
✅ USD pairs present: ['EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'NZD', 'SGD']

============================================================
Test Summary
============================================================
✅ PASS - Valkey Connection
✅ PASS - Refresher Wrote Data
✅ PASS - Rate Data Structure
✅ PASS - Minimum Rate Count
✅ PASS - USD Pairs Present

Total: 5/5 passed

🎉 All E2E tests passed!
```

## Troubleshooting

### Refresher fails to start
```bash
# Check logs
docker-compose logs refresher

# Common issues:
# - JAVA_HOME not set → Fixed in Dockerfile
# - SBT build failed → Clean and rebuild
```

### Valkey connection refused
```bash
# Check Valkey is running
docker-compose ps valkey

# Check health
docker-compose exec valkey valkey-cli ping
# Should return: PONG
```

### No data in Valkey after 30s
```bash
# Check if refresher completed
docker-compose logs refresher

# Manually check Valkey
docker-compose exec valkey valkey-cli
> GET rates
```

### One-Frame API timeout
```bash
# Check One-Frame health
curl http://localhost:8081/rates?pair=USDEUR

# Restart if needed
docker-compose restart one-frame
```

## Continuous Integration

Add to `.github/workflows/test.yml`:

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run E2E tests
        run: |
          cd e2e
          docker-compose up --build --abort-on-container-exit

      - name: Cleanup
        if: always()
        run: |
          cd e2e
          docker-compose down
```

## Next Steps

1. Add performance tests (latency, throughput)
2. Add stress tests (concurrent refreshes)
3. Add failure recovery tests (Valkey down, One-Frame down)
4. Add data consistency tests (multiple refreshes)
