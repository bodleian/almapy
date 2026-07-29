# almapy

[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Introduction
This is a wrapper library for the Alma API. The design goal is to smooth off some of the rough edges of the APIs to make them easier to use.

The library is async, using [niquests](https://niquests.readthedocs.io/) under the hood (HTTP/2 and HTTP/3 are disabled — Alma's gateway does not benefit from them and they complicate connection reuse under load).

Notable QoL:
- Takes care of rate-limiting.
- Retries server errors (including rate limit errors) automatically, for reads.
  Writes are only replayed on failures that prove Alma never processed the
  request — a 429 rejection or a connect timeout — so a lost response cannot
  turn into a duplicate loan, request or PO line. Pass `retry=True` to a write
  to opt back into full retries.
- Handles some weird edge cases like incorrect response types.
- Adds more informative exceptions than just HTTP status codes, based on Ex Libris' own error codes.

Convenient methods, namespaced by functional area, are available for a lot of common endpoints, but these are not comprehensive and are added as needed. Said methods don't try to do anything fancy with parameters or responses as of yet.

### Response types

Most methods return JSON wrapped in a [Box](https://github.com/cdgriffith/Box), which makes Ex Libris' rather XMLish JSON less verbose to work with — `resp.bib_data.title` rather than `resp["bib_data"]["title"]`.

Seven methods return the raw response body as a `str`, because they deal in MARC XML records that would be mangled by a round-trip through JSON:

| Method | Returns |
|--------|---------|
| `bibs.get_bib`, `bibs.create_bib`, `bibs.update_bib` | MARC XML record |
| `bibs.get_holding`, `bibs.create_holding`, `bibs.update_holding` | MARC XML holding |
| `analytics.get_raw_report` | Analytics report XML |

Everything else, letters included, returns a `Box`.

`Box` is a pragmatic default, not the only option: pass `model=` to any Box-returning method and you get a validated instance of that type back instead — see [Typed requests and responses](#typed-requests-and-responses).

## Getting started

### An API key

Alma API keys come from the [Ex Libris Developer Network](https://developers.exlibrisgroup.com/), not from Alma itself. Sign in with your institutional account, create an application, then add the API areas you need (Bibs, Users, Acquisitions, Configuration, Analytics) to it. Each area is granted **Read-only** or **Read/write** separately — grant read-only unless you specifically need writes.

Keys are bound to one environment. A sandbox key will not work against production and vice versa.

### Choosing a region

Alma is served from five regional gateways, and a key only works against its own region. `location` defaults to `"Europe"`, so **institutions outside Europe must set it explicitly**:

| `location` | Gateway |
|------------|---------|
| `"America"` | `api-na.hosted.exlibrisgroup.com` |
| `"Europe"` (default) | `api-eu.hosted.exlibrisgroup.com` |
| `"Asia Pacific"` | `api-ap.hosted.exlibrisgroup.com` |
| `"Canada"` | `api-ca.hosted.exlibrisgroup.com` |
| `"China"` | `api-cn.hosted.exlibrisgroup.com` |

### Install

```bash
pip install almapy
# or
uv add almapy
```

### Quickstart

```python
import asyncio

from almapy import AlmaClient
from almapy.exceptions import APIClientError, APIServerError

BARCODES = ["98279242", "24569754", "345782365"]


async def main() -> None:
    async with AlmaClient(apikey="KEY", location="Europe", rate_limit=10) as client:
        tasks = [client.bibs.get_item(barcode) for barcode in BARCODES]

        # Collect everything, keeping failures as exception objects rather than
        # letting the first one cancel the rest.
        for barcode, result in zip(
            BARCODES, await asyncio.gather(*tasks, return_exceptions=True), strict=True
        ):
            match result:
                case APIServerError():
                    print(f"{barcode}: server error: {result}")
                case APIClientError():
                    print(f"{barcode}: client error: {result}")
                case _:
                    print(f"{barcode}: {result.bib_data.title}")


if __name__ == "__main__":
    asyncio.run(main())
```

Use `async with` (or call `await client.aclose()` yourself). The client owns a connection pool; abandoning it without closing leaks connections.

To handle results as they arrive rather than waiting for the slowest:

```python
async def main() -> None:
    async with AlmaClient(apikey="KEY") as client:
        tasks = [client.bibs.get_item(barcode) for barcode in BARCODES]
        for coro in asyncio.as_completed(tasks):
            try:
                resp = await coro
            except APIClientError as exc:
                print(f"Client error: {exc}")
            else:
                print(resp.bib_data.title)
```

## Typed requests and responses

almapy adds no modelling dependency of its own. Both directions are duck-typed, so any
class exposing the right method works — pydantic, attrs, msgspec or hand-rolled.

### Responses

All Box-returning methods accept an optional `model=` keyword argument. When supplied,
the raw `Box` response is passed to `model.model_validate()` and the validated instance
is returned. Any class with a `model_validate` classmethod works.

The seven [raw-`str` methods](#response-types) are the exception: they hand back a MARC
XML document rather than a `Box`, so there is nothing to validate and they take no
`model=` argument.

```python
from pydantic import BaseModel
from almapy import AlmaClient


class BibData(BaseModel):
    mms_id: str
    title: str | None = None


async def main():
    async with AlmaClient(apikey="KEY") as client:
        # Returns BibData instead of Box
        bib: BibData = await client.bibs.get_item("98279242", model=BibData)
        print(bib.title)

        # Default behaviour unchanged — still returns Box
        raw = await client.bibs.get_item("98279242")
        print(raw.bib_data.title)
```

### Request bodies

Write methods take a plain `dict`, or any object exposing either
`model_dump(mode="json")` or `dump(mode="json")`. `model_dump` is pydantic v2's own API,
so a `BaseModel` works directly — no shim needed, and still no pydantic dependency on
almapy's side. Both checks are `runtime_checkable` Protocols, so they are purely
structural — nothing needs to import from almapy or inherit from it:

```python
class UserUpdate(BaseModel):
    first_name: str


async def main():
    async with AlmaClient(apikey="KEY") as client:
        await client.users.update_user("jsmith", {"first_name": "Jane"})
        await client.users.update_user("jsmith", UserUpdate(first_name="Jane"))
```

almapy serialises once, before the retry loop, and sends the result as the JSON body.
If an object exposes both methods `dump` wins, on the grounds that a model carrying a
custom `dump` is expressing a deliberate wire shape that should not be bypassed.

This applies to JSON writes only. The MARC XML methods take a `str`.

## Logging

almapy uses stdlib `logging` and follows library best practice: a `NullHandler` is registered on the `almapy` root logger so no output is produced unless the caller configures handlers.

Four semantic loggers are available:

| Logger | Level | Event | Extra fields |
|--------|-------|-------|--------------|
| `almapy.http` | DEBUG | Request sent | `method`, `url` |
| `almapy.http` | DEBUG | Response received | `method`, `url`, `status_code`, `elapsed_ms` |
| `almapy.retry` | WARNING | Retry attempt | `attempt`, `max_attempts`, `exc_type` |
| `almapy.throttle` | DEBUG | TokenBucket wait | `wait_secs`, `tokens_available` |
| `almapy.throttle` | WARNING | Rate cut (AIMD backoff) | `old_rate`, `new_rate` |
| `almapy.throttle` | INFO | Rate recovery | `old_rate`, `new_rate` |
| `almapy.error` | WARNING | Alma error before raising | `status_code`, `alma_code` (where applicable) |

Every log record also carries a `req_id` field — a `uuid4().hex` correlation ID set at the start of each `execute()` call and reset in `finally`. Use it to correlate retries, throttle events, and errors for a single request.

To enable logging in your application:

```python
import logging

# Show all almapy debug output
logging.getLogger("almapy").setLevel(logging.DEBUG)
logging.getLogger("almapy").addHandler(logging.StreamHandler())

# Or filter to a specific area — e.g. only retry warnings
logging.getLogger("almapy.retry").setLevel(logging.WARNING)
logging.getLogger("almapy.retry").addHandler(logging.StreamHandler())
```

To include the correlation ID in your formatter:

```python
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s %(name)s [%(req_id)s] %(message)s"))
logging.getLogger("almapy").addHandler(handler)
```

### structlog integration

All extra fields flow automatically into structlog via `ExtraAdder()`:

```python
import logging
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

formatter = structlog.stdlib.ProcessorFormatter(
    foreign_pre_chain=[
        structlog.stdlib.ExtraAdder(),  # pulls req_id, status_code, elapsed_ms, etc.
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ],
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.JSONRenderer(),
    ],
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger("almapy").addHandler(handler)
logging.getLogger("almapy").setLevel(logging.DEBUG)
```
