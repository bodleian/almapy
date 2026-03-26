# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**almapy** is an async Python wrapper library for the [Alma API](https://developers.exlibrisgroup.com/alma/apis/) (Ex Libris' library management system). It abstracts API complexity with rate limiting, retry logic, error mapping, and response wrapping.

## Commands

Uses `just` as the task runner (wraps `uv run`):

```bash
just           # Run lint then test (default)
just lint      # ruff format, ruff check --fix, mypy, deptry
just lint-ci   # Strict CI lint (ruff check/format, djlint, mypy — no auto-fix)
just test      # Run pytest
just test -k "test_name"  # Run a single test
just upgrade   # Update lockfile and sync
just publish   # Build and publish to GitLab package registry
just hook      # Install pre-commit hooks
just unhook    # Uninstall pre-commit hooks
```

Direct equivalents:
```bash
uv run pytest tests/test_foo.py::test_bar  # Single test
uv run python -c "..."                      # Always prefix python with uv run (deps not on system path)
uv run mypy .                               # Type check only
uv run ruff check --fix && uv run ruff format  # Lint only
```

Tests use `--exitfirst` and re-run failures first. Coverage minimum is 50%.

## Architecture

### Namespace Pattern

`AlmaClient` is a plain async class (no framework dependency) composed of `httpx.AsyncClient`, `TokenBucket` (rate limiting), `AdaptiveController` (AIMD backpressure), and `asyncio.Semaphore` (concurrency cap). It exposes functional namespaces as properties:

```
client.users.loans.get(...)
client.users.fees.get(...)
client.users.requests.create(...)
client.bibs.get_item(barcode=...)
client.config.sets.get(...)
client.acq.get_po_line(...)
client.analytics.get_full_report(...)
```

Each namespace class (e.g. `AlmaClientUserLoansNS`) inherits from `BaseNamespace` (`_base.py`) and wraps HTTP calls with domain logic.

### Error Handling

`_validate_response()` is called inside `AlmaClient._execute()` on every response. It delegates to `_handle_error()` in `_utils.py`, which maps Alma's numeric error codes (parsed via `glom` from JSON/XML bodies) to ~50 specific exception types in `exceptions.py`.

Exception hierarchy:
- `APIClientError` (4xx) → specific errors like `BarcodeNotFoundError`, `UserNotFoundError`, `LoanLimitError`
- `APIServerError` (5xx) → server-side failures
- `ThresholdError` (429) → rate limit hit

### Retry & Rate Limiting

Configured in `_client.py`:
- **Retry**: `stamina` handles retries; 3 attempts, exponential backoff (`backoff_factor=0.5`), retries on server errors, rate limits, timeouts
- **stamina hooks are process-global** — `stamina.instrumentation.set_on_retry_hooks()` affects all stamina callers; use a manual attempt counter inside the `retry_context` loop for library-safe retry logging
- **Throttle**: 25 req/sec (configurable via `rate_limit` param)
- **Concurrency**: 150 concurrent requests max

### Response Objects

All JSON responses are wrapped in `Box` (type alias `RESP_TYPE`), enabling dot-notation access: `resp.bib_data.title`.

All Box-returning methods also accept an optional `model=` keyword argument. When provided with a Pydantic model class, the response is passed through `model.model_validate(box_result)` and the typed model is returned instead of `Box`:

```python
bib: BibData = await client.bibs.get_item("98279242", model=BibData)
```

### Logging

Four semantic loggers under the `almapy` root: `almapy.http`, `almapy.retry`, `almapy.throttle`, `almapy.error`. A `NullHandler` is registered in `_logging.py` at import time — the library never forces output.

Per-request correlation IDs are stored in a `contextvars.ContextVar[str]` (`request_id` in `_logging.py`), set to `uuid4().hex` at the start of each `execute()` call and reset in `finally`. Every log call passes `extra={"req_id": request_id.get()}`.

**Key rules when adding log calls:**
- Import `request_id` from `almapy._logging`, never create new loggers outside the four above.
- Always include `extra={"req_id": request_id.get()}` — omitting it breaks `%(req_id)s` formatters.
- Never log API keys or full response bodies.
- **stamina hooks are process-global** — `stamina.instrumentation.set_on_retry_hooks()` affects all stamina callers in the process; use a manual attempt counter inside the `retry_context` loop for library-safe retry logging (see `_client.py:execute()`).

### Endpoints

All API paths are defined in `_endpoints.py` as an enum (`AlmaEndpoint`). URL parameters use `{USER_ID}`, `{MMS_ID}`, etc. placeholder conventions.

### Testing

Tests are pure unit tests — no recording/replay. The `client` fixture in `conftest.py` creates a plain `AlmaClient("test-api-key")`. No `.env` or live API key needed to run tests.

**Gotchas:**
- `--doctest-modules` is active — doctests in source files are collected and run. Bad docstring examples will fail the suite.
- `--typeguard-packages=almapy` enables runtime type checking — type annotation errors surface as test failures.
- Integration tests (`@pytest.mark.integration`) require `ALMA_INTEGRATION=1` env var and a valid API key.

## Key Files

| File | Purpose |
|------|---------|
| `src/almapy/_logging.py` | Shared logging infrastructure — `ContextVar` for correlation IDs, `NullHandler` registration |
| `src/almapy/_client.py` | `AlmaClient` — main entry point, httpx config, namespace wiring |
| `src/almapy/_base.py` | `BaseNamespace` — base class for all namespace objects |
| `src/almapy/_throttle.py` | `TokenBucket`, `AdaptiveController` — rate limiting + AIMD backpressure |
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
- **Version control**: This repo uses [Jujutsu (`jj`)](https://github.com/jj-vcs/jj) — do not use `git commit`. Use `jj describe` to set the commit message on the current working-copy revision, then `jj new` to start a fresh revision. Do not append `Co-Authored-By` or any "generated by Claude" attribution to commit messages.
- **Conventional commits**: Required by commitizen pre-commit hook. Format: `feat(module): description`.
- **Adding exceptions**: New Alma error codes map to new exception classes in `exceptions.py`, matched by numeric code in `_utils.py`'s `_handle_error()`.
- **New API areas**: Create a new `_<area>.py` module with namespace class(es), wire into `AlmaClient` in `_client.py`.
