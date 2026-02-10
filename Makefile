.PHONY: help deps build clean test test-unit test-unit-local test-all e2e-test e2e-test-local load-test compile run docker-build docker-push

# Java 17 (required for SBT/Scala 2.13). Prefer java_home, fallback to Homebrew path.
JAVA_HOME ?= $(shell /usr/libexec/java_home -v 17 2>/dev/null || echo "/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home")
export JAVA_HOME

SBT = cd forex-mtl && sbt

# Default target
help:
	@echo "Forex Proxy Service - Makefile Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup & Dependencies:"
	@echo "  make deps          - Install all dependencies (Java, SBT, Docker)"
	@echo "  make deps-check    - Check if dependencies are installed"
	@echo ""
	@echo "Build & Compile:"
	@echo "  make build         - Compile the Scala project"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make compile       - Alias for build"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run unit tests (alias for test-unit)"
	@echo "  make test-unit     - Run Scala unit tests in Docker (Java 17)"
	@echo "  make test-unit-local - Run unit tests locally with SBT (requires Java 17)"
	@echo "  make test-all      - Run all tests (unit + E2E)"
	@echo "  make e2e-test      - Run E2E tests in Docker"
	@echo "  make e2e-test-local - Run E2E tests locally (requires Python)"
	@echo "  make load-test     - Load test 1k RPS / 20s, 100% success (starts stack, then down)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-push   - Push Docker image to registry"
	@echo ""
	@echo "Development:"
	@echo "  make run           - Run the application locally"
	@echo "  make fmt           - Format Scala code with scalafmt"
	@echo ""

# Check dependencies
deps-check:
	@echo "Checking dependencies..."
	@command -v java >/dev/null 2>&1 || { echo "Java not found. Please install Java 17."; exit 1; }
	@echo "  ✓ Java: $$(java -version 2>&1 | head -n 1)"
	@command -v sbt >/dev/null 2>&1 || { echo "SBT not found. Please install SBT."; exit 1; }
	@echo "  ✓ SBT: $$(sbt --version 2>&1 | grep 'sbt version')"
	@command -v docker >/dev/null 2>&1 || { echo "Docker not found. Please install Docker."; exit 1; }
	@echo "  ✓ Docker: $$(docker --version)"
	@command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose not found."; exit 1; }
	@echo "  ✓ Docker Compose: $$(docker-compose --version 2>&1 | head -n 1)"
	@echo ""
	@echo "All dependencies are installed ✓"

# Install dependencies (macOS with Homebrew)
deps:
	@echo "Installing dependencies..."
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "Homebrew not found. Please install Homebrew first:"; \
		echo "  /bin/bash -c \"\$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""; \
		exit 1; \
	fi
	@command -v java >/dev/null 2>&1 || brew install openjdk@17
	@command -v sbt >/dev/null 2>&1 || brew install sbt
	@command -v docker >/dev/null 2>&1 || echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
	@command -v python3 >/dev/null 2>&1 || brew install python@3.11
	@pip3 install --quiet requests 2>/dev/null || echo "Note: requests library install failed, needed for local E2E tests"
	@echo "Dependencies installed ✓"

# Build the project (use Java 17 if available)
build: deps-check
	@echo "Building Scala project..."
	cd forex-mtl && export JAVA_HOME=$${JAVA_HOME:-/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home} && sbt compile

compile: build

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	cd forex-mtl && export JAVA_HOME=$${JAVA_HOME:-/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home} && sbt clean
	@echo "Build artifacts cleaned ✓"

# Run unit tests (in Docker, Java 17)
test: test-unit

test-unit:
	@echo "Running Scala unit tests in Docker..."
	docker build -q -f forex-mtl/Dockerfile.test -t forex-test forex-mtl && docker run --rm forex-test

# Run unit tests locally (requires Java 17)
test-unit-local: deps-check
	@echo "Running Scala unit tests locally..."
	cd forex-mtl && export JAVA_HOME=$${JAVA_HOME:-/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home} && sbt test

# Run all tests (unit + E2E)
test-all: test-unit e2e-test
	@echo ""
	@echo "=========================================="
	@echo "All tests completed!"
	@echo "=========================================="

# Run E2E tests in Docker (start deps, run e2e once, then down)
e2e-test:
	@echo "Running E2E tests in Docker..."
	@docker rm -f one-frame-local 2>/dev/null || true
	cd e2e && docker-compose down --remove-orphans 2>/dev/null || true
	@sleep 2
	cd e2e && docker-compose build --no-cache e2e-tests && docker-compose up -d --build
	@sleep 35
	cd e2e && docker-compose run --rm e2e-tests python3 run_all_tests.py; EXIT=$$?; docker-compose down; exit $$EXIT
	@echo ""
	@echo "E2E tests completed ✓"

# Load test: 10k RPS target (15s duration, 300 workers). Stack must not be running.
load-test:
	@echo "Starting stack for load test..."
	@docker rm -f one-frame-local 2>/dev/null || true
	cd e2e && docker-compose down --remove-orphans 2>/dev/null || true
	@sleep 2
	cd e2e && docker-compose build e2e-tests && docker-compose up -d --build
	@sleep 35
	@echo "Running load test (1k RPS, 20s, 100% success)..."
	cd e2e && docker-compose run --rm -e LOAD_DURATION=20 -e LOAD_WORKERS=100 e2e-tests python3 test_load_10k_rps.py; EXIT=$$?; docker-compose down; exit $$EXIT

# Run E2E tests locally
e2e-test-local:
	@echo "Running E2E tests locally..."
	@command -v python3 >/dev/null 2>&1 || { echo "Python 3 not found."; exit 1; }
	@echo "Note: Ensure One-Frame container is running on port 8081"
	@docker ps | grep one-frame >/dev/null 2>&1 || { \
		echo "Starting One-Frame container..."; \
		docker run -d --name one-frame-local -p 8081:8080 paidyinc/one-frame; \
		sleep 3; \
	}
	cd e2e && python3 run_all_tests.py
	@echo ""
	@echo "E2E tests completed ✓"

# Format Scala code
fmt:
	@echo "Formatting Scala code..."
	cd forex-mtl && export JAVA_HOME=$${JAVA_HOME:-/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home} && sbt scalafmt

# Run the application
run: deps-check
	@echo "Running application..."
	cd forex-mtl && export JAVA_HOME=$${JAVA_HOME:-/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home} && sbt run

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t forex-proxy:latest -f forex-mtl/Dockerfile forex-mtl
	@echo "Docker image built ✓"

# Push Docker image
docker-push: docker-build
	@echo "Pushing Docker image..."
	@echo "Note: Update registry URL in Makefile"
	# docker tag forex-proxy:latest your-registry/forex-proxy:latest
	# docker push your-registry/forex-proxy:latest
	@echo "Docker image push command ready (uncomment and configure)"

# Development shortcuts
dev: build run

# Full CI pipeline
ci: deps-check clean build test e2e-test
	@echo ""
	@echo "CI pipeline completed ✓"
