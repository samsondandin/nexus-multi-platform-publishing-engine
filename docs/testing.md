# Testing Strategy & Quality Assurance Guide

NEXUS employs a comprehensive, multi-tiered testing strategy ensuring 100% deterministic test execution, boundary validation, and external failure isolation.

---

## 1. Test Architecture

The test suite is partitioned into three distinct domains:

1. **Validation Tests (`tests/test_validation.py`)**:
   - Unit tests focusing strictly on text parsing, length limits (<= 200 chars), non-truncation guarantees, URL regex correctness, multiple URL rejection, and malformed URL detection.
2. **Mocked Platform Adapter Tests (`tests/test_platforms.py`)**:
   - Tests covering all five individual platform adapters across all possible API responses (HTTP 200 success, HTTP 401 auth failures, HTTP 429 rate limits, HTTP 500 server errors, malformed payloads, and unconfigured state).
   - Mocking is performed using `respx`, intercepting HTTPX requests at the transport level.
3. **End-to-End Orchestration Tests (`tests/test_posting.py`)**:
   - Integration tests executing real HTTP calls against the FastAPI application using `httpx.AsyncClient` and `ASGITransport`.
   - Tests scenarios:
     - All platforms succeed (`overall_status = all_success`).
     - Partial success (one platform fails while four succeed, validating that failures are completely isolated).
     - All platforms fail (`overall_status = all_failed`).
     - No platforms configured (`overall_status = no_platforms_configured`).
     - Centralized validation exceptions (`HTTP 422`).
     - System health and platform listing endpoints.
4. **Live Integration Tests (`tests/test_live_publishing.py`)**:
   - Opt-in tests executing genuine HTTP calls against real platform endpoints when environment credentials are present.
   - **Skipped by default** during CI/CD and standard runs to guarantee deterministic local execution without network flakiness.

---

## 2. Running Automated Tests

Run the complete deterministic test suite:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run tests with test coverage reporting:

```bash
pytest --cov=app --cov-report=term-missing
```

---

## 3. Running Opt-in Live Publishing Tests

To run real publishing requests against live platforms configured in your `.env`:

```bash
pytest tests/test_live_publishing.py --run-live -v
```

If an adapter is not configured in `.env`, the test cleanly skips with an informative message.

---

## 4. Linting & Formatting Checks

NEXUS uses `ruff` for ultra-fast, modern linting and code formatting:

```bash
# Check code style and common bugs
ruff check .

# Automatically apply safe fixes
ruff check --fix .
```
