# Getting started

## Install

```bash
uv add almapy
# or
pip install almapy
```

Requires Python 3.11+. The package is typed (`py.typed`), so mypy and your
editor see the full API without stubs.

## Your first request

`AlmaClient` is an async context manager. `location` selects the regional
gateway – `"Europe"` (the default), `"America"`, `"Asia Pacific"`, `"Canada"` or
`"China"`.

```python
import asyncio
import os

from almapy import AlmaClient


async def main() -> None:
    async with AlmaClient(apikey=os.environ["ALMA_API_KEY"], location="Europe") as client:
        item = await client.bibs.get_item("39001234567890")
        print(item.bib_data.title)


asyncio.run(main())
```

!!! warning "Always close the client"

    Use `async with`, or call `await client.aclose()` yourself. The client owns
    a connection pool; abandoning it without closing leaks connections. If you
    need a client whose lifetime you manage – a FastAPI dependency, say – hold
    it open for the application's lifespan and close it on shutdown, rather than
    creating one per request.

## Reusing one client

The client holds the rate limiter and the connection pool, so **create one and
share it**. A client per request defeats both: each new client starts with a
full token bucket, so the institution's rate limit gets exceeded even though
each individual client is behaving.

```python
async with AlmaClient(apikey=key) as client:
    barcodes = ["39001234567890", "39001234567891", "39001234567892"]
    items = await asyncio.gather(*(client.bibs.get_item(b) for b in barcodes))
```

Concurrency is capped at 150 in-flight requests and throttled to 25 requests per
second by default, so `asyncio.gather` over a large list is safe – almapy paces
it for you. See [Rate limiting](rate-limiting.md).

## Configuring the client

```python
client = AlmaClient(
    apikey=key,
    location="Europe",
    rate_limit=25.0,  # requests per second
    concurrent_requests=150,  # in-flight cap
    retry_attempts=3,
)
```

Lower `rate_limit` if you share the institution's API quota with other
applications – Alma's limit is institution-wide, not per-key. The remaining
keyword arguments (`backoff_factor`, `recovery_increment`, `recovery_window`,
`cooldown`, `max_wait`) tune the adaptive backpressure and are covered in
[Rate limiting](rate-limiting.md).

### Supplying your own session

Pass `client=` to reuse an existing `niquests.AsyncSession` – useful for
injecting a mock in tests, or sharing a pool. almapy applies its `base_url` and
auth header with `setdefault` semantics, so a session you have configured
yourself keeps its own values, and it will not close a session it does not own.

```python
import niquests

session = niquests.AsyncSession()
async with AlmaClient(apikey=key, client=session) as client:
    ...
```

## Next steps

- [Responses](responses.md) – how to read what comes back.
- [Errors](errors.md) – what to catch.
- [API reference](../api/client.md) – every namespace and method.
