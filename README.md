# almapy

[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Introduction
This is a wrapper library for the Alma API. The design goal is to smooth off some of the rough edges of the APIs to make them easier to use.

The library is async, using httpx under the hood.

Notable QoL:
- Takes care of rate-limiting.
- Retries server errors (including rate limit errors) automatically.
- Handles some weird edge cases like incorrect response types.
- Adds more informative exceptions than just HTTP status codes, based on Ex Libris' own error codes.

Convenient methods, namespaced by functional area, are available for a lot of common endpoints, but these are not comprehensive and are added as needed. Said methods don't try to do anything fancy with parameters or responses as of yet.

All methods return JSON in the form of a [Box](https://github.com/cdgriffith/Box), except where XML clearly makes more sense (holdings, letters). Box is used to make Ex Libris' rather XMLish JSON less verbose to work with. In the longer term the hope is to have specific classes for every response type, and this is underway in a separate project, but it will take a long time.

## Quickstart
```bash
poetry add  "git+https://gitlab.bodleian.ox.ac.uk/bodl3011/almapy.git"
```


```python
import asyncio
from almapy import AlmaClient
from almapy.exceptions import APIClientError, APIServerError

BARCODES = ["98279242", "24569754", "345782365"]


async def fetch_item(client: AlmaClient, barcode: str):
    resp = await client.bibs.get_item(barcode)
    return resp


async def main():
    client = AlmaClient(apikey="KEY", rate_limit=10)
    tasks = [fetch_item(client, barcode) for barcode in BARCODES]

    # Option One
    results = asyncio.gather(
        *tasks
    )  # Can use return_exceptions=True to include exceptions in the list instead of interrupting
    for result in results:
        print(result.bib_data.title)

    # Option Two
    for result in asyncio.as_completed(tasks):
        try:
            resp = await result
            print(resp.bib_data.title)
        except APIServerError as e:
            print(f"Server error: {e}")
        except APIClientError as e:
            print(f"Client error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Pydantic model validation

All Box-returning methods accept an optional `model=` keyword argument. When supplied,
the raw `Box` response is passed to `model.model_validate()` and the validated instance
is returned. No pydantic dependency is added to almapy — validation is duck-typed, so
any class with a `model_validate` classmethod works.

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

## Logging

almapy uses stdlib `logging` and follows library best practice: a `NullHandler` is registered on the `almapy` root logger so no output is produced unless the caller configures handlers.

Four semantic loggers are available:

| Logger | Level | Event |
|--------|-------|-------|
| `almapy.http` | DEBUG | Request sent and response received (method, URL, status, elapsed ms) |
| `almapy.retry` | WARNING | Retry attempt N/M with exception type and backoff |
| `almapy.throttle` | DEBUG | TokenBucket wait (seconds, tokens available) |
| `almapy.throttle` | WARNING | Rate cut by adaptive controller (old → new req/s) |
| `almapy.throttle` | INFO | Rate recovery (old → new req/s) |
| `almapy.error` | WARNING | Alma error code and message before raising exception |

Every log record carries a `req_id` field — a `uuid4().hex` correlation ID set at the start of each `execute()` call and reset in `finally`. Use it to correlate retries, throttle events, and errors for a single request.

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

## TODO
- [ ] Better documentation
- [ ] More endpoints
- [ ] Specific response types
