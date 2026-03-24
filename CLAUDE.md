# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**almapy** is an async Python wrapper library for the [Alma API](https://developers.exlibrisgroup.com/alma/apis/) (Ex Libris' library management system). It abstracts API complexity with rate limiting, retry logic, error mapping, and response wrapping.

## Commands

Uses `just` as the task runner (wraps `uv run`):

```bash
just           # Run lint then test (default)
just lint      # ruff format, ruff check --fix, mypy, deptry
just lint-ci   # Strict CI lint (no auto-fix, format check only)
just test      # Run pytest
just test -k "test_name"  # Run a single test
just upgrade   # Update lockfile and sync
just publish   # Build and publish to GitLab package registry
just hook      # Install pre-commit hooks
```

Direct equivalents:
```bash
uv run pytest tests/test_foo.py::test_bar  # Single test
uv run mypy .                               # Type check only
uv run ruff check --fix && uv run ruff format  # Lint only
```

Tests use `--exitfirst` and re-run failures first. Coverage minimum is 50%.

## Architecture

### Namespace Pattern

`AlmaClient` extends `Gracy[AlmaEndpoint]` and exposes functional namespaces as properties:

```
client.users.loans.get(...)
client.users.fees.get(...)
client.users.requests.create(...)
client.bibs.get_item(barcode=...)
client.config.sets.get(...)
client.acq.get_po_line(...)
client.analytics.get_full_report(...)
```

Each namespace class (e.g. `AlmaClientUserLoansNS`) inherits from `GracyNamespace` and wraps HTTP calls with domain logic.

### Error Handling

`AlmaErrorValidator` intercepts all HTTP responses. `_handle_error()` in `_utils.py` maps Alma's numeric error codes (extracted via regex from response bodies) to ~50 specific exception types in `exceptions.py`.

Exception hierarchy:
- `APIClientError` (4xx) → specific errors like `BarcodeNotFoundError`, `UserNotFoundError`, `LoanLimitError`
- `APIServerError` (5xx) → server-side failures
- `ThresholdError` (429) → rate limit hit

### Retry & Rate Limiting

Configured in `_client.py`:
- **Retry**: 3 attempts, exponential backoff (`delay_modifier=4`), retries on server errors, rate limits, timeouts
- **Throttle**: 25 req/sec (configurable via `rate_limit` param)
- **Concurrency**: 150 concurrent requests max

### Response Objects

All JSON responses are wrapped in `Box` (type alias `RESP_TYPE`), enabling dot-notation access: `resp.bib_data.title`.

### Endpoints

All API paths are defined in `_endpoints.py` as an enum (`AlmaEndpoint`). URL parameters use `{USER_ID}`, `{MMS_ID}`, etc. placeholder conventions.

### Testing

Tests use Gracy's replay mode with SQLite storage (`.gracy/alma.sqlite3`) — HTTP responses are recorded once and replayed in subsequent runs. The `client` fixture in `conftest.py` configures this automatically. A `.env` file with `API_KEY` is required to record new interactions.

## Key Files

| File | Purpose |
|------|---------|
| `src/almapy/_client.py` | `AlmaClient` — main entry point, Gracy config, namespace wiring |
| `src/almapy/_endpoints.py` | All API URL paths as enum |
| `src/almapy/_utils.py` | `AlmaErrorValidator`, `_handle_error()`, shared types |
| `src/almapy/exceptions.py` | ~50 specific exception classes |
| `src/almapy/_users.py` | User/patron namespaces |
| `src/almapy/_bibs.py` | Bib/holdings/item namespaces |
| `src/almapy/_acq.py` | Acquisitions namespace |
| `src/almapy/_config.py` | Config namespaces (sets, libraries, code tables, jobs) |
| `src/almapy/_analytics.py` | Analytics/reports namespace |

## Conventions

- **Strict mypy**: All code must pass strict type checking. Use `TypedDict` for request shapes.
- **Conventional commits**: Required by commitizen pre-commit hook. Format: `feat(module): description`.
- **Adding exceptions**: New Alma error codes map to new exception classes in `exceptions.py`, matched by numeric code in `_utils.py`'s `_handle_error()`.
- **New API areas**: Create a new `_<area>.py` module with namespace class(es), wire into `AlmaClient` in `_client.py`.
