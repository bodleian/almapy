# Rate limiting

Alma enforces an institution-wide API quota. almapy stays under it with three
mechanisms that work together, so in most cases you can fire off a large
`asyncio.gather` and let the library pace it.

## The three layers

| Layer | Default | What it does |
|---|---|---|
| `TokenBucket` | 25 req/s | Paces requests, allowing a one-second burst |
| `AdaptiveController` | – | Cuts the rate when Alma pushes back, recovers it gradually |
| `asyncio.Semaphore` | 150 | Caps requests in flight at any moment |

```python
client = AlmaClient(
    apikey=key,
    rate_limit=25.0,
    concurrent_requests=150,
)
```

Lower `rate_limit` if you share the institution's quota with other
applications – Alma's limit is institution-wide, not per-key, so a well-behaved
almapy client can still be starved by something else.

## Adaptive backpressure

The controller cuts the rate sharply on failure and restores it slowly on
success:

- **On failure**, the rate is multiplied by `backoff_factor` (default `0.5`),
  never below `min_rate`. A `cooldown` (default 5s) then starts, during which
  further failures are ignored – a burst of concurrent failures from one
  incident cuts the rate once, not once per request.
- **On success**, `recovery_increment` (default `1.0`) is added, at most once per
  `recovery_window` (default 10s), up to the configured maximum. The rate climbs
  back gradually rather than jumping to full speed after one success.

```python
client = AlmaClient(
    apikey=key,
    rate_limit=25.0,
    backoff_factor=0.5,  # halve on failure
    recovery_increment=1.0,  # +1 req/s per window
    recovery_window=10.0,  # at most once per 10s
    cooldown=5.0,  # ignore failures for 5s after a cut
    max_wait=None,  # unbounded wait for a token
)
```

Set `max_wait` to bound how long a call will sit waiting for a token. When it
elapses, `ThrottleTimeoutError` is raised locally – no request is sent. It
subclasses `TimeoutError` as well as `AlmapyError`.

!!! note "Backpressure is deliberately method-agnostic"

    A 5xx or 429 depresses the rate regardless of which verb provoked it, even
    on a POST that will *not* itself be replayed. The reasoning: a server error
    says something about Alma's health whoever asked, and the point of
    backpressure is to stop making it worse.

## Retries

Failed requests are retried 3 times by default (`retry_attempts`), with
exponential backoff seeded by `backoff_factor`. Server errors, rate limits and
timeouts are retried.

### Writes are not replayed on ambiguous failures

This is the part worth understanding, because it is a deliberate departure from
"retry everything".

When a POST fails on a read timeout or a 5xx, there is no way to tell from the
client whether Alma applied the write before the response was lost. Replaying it
*might* be harmless, or it might create a second loan, request or PO line. So
almapy gates retries on the HTTP method:

| Verb | Retried on |
|---|---|
| GET, HEAD, OPTIONS, PUT, DELETE | The full transient set – 5xx, an unparseable 2xx body, 429, connect and read timeouts, dropped connections |
| POST, PATCH | Only `ThresholdError` (429 – the gateway rejected it outright) and `ConnectTimeout` (no connection was ever established) |

Both of the POST cases prove the request never landed, so replaying is safe.
Everything else is left to fail rather than risk a duplicate.

### Overriding per call

The namespace methods do not expose this. `retry=` is a parameter of
`AlmaClient.execute`, the low-level call they are all built on, so overriding the
default means dropping down to it:

```python
from almapy._endpoints import AlmaEndpoint

# retry=True opts a write back into the full transient set – only do this where
# a duplicate would be harmless.
await client.execute(
    "POST",
    AlmaEndpoint.USER_LOANS.build({"USER_ID": "12345678"}),
    parser="json",
    retry=True,
)
```

`retry=False` disables retries for a single request instead.

The other arguments are just what any raw call needs and have nothing to do with
retries: the HTTP verb, the URL, and `parser`, which selects how the response
body is decoded – `"json"`, `"xml"`, `"text"`, or `"none"` for an empty body.

## Watching it work

The `almapy.throttle` logger reports every rate change:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s [%(req_id)s] %(message)s",
)
logging.getLogger("almapy.throttle").setLevel(logging.INFO)
```

```
WARNING almapy.throttle [a1b2c3] AdaptiveController: rate cut 25.0 -> 12.5 req/s (failure)
INFO    almapy.throttle [d4e5f6] AdaptiveController: rate recovered 12.5 -> 13.5 req/s
```

Both records carry `old_rate` and `new_rate` as structured `extra` fields. See
[Logging](logging.md).

## Reference

The internals are documented in [Advanced](../api/advanced.md).
