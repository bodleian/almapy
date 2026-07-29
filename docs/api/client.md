# Client

`AlmaClient` is the entry point. It is a plain async class — no framework
dependency — composing a `niquests.AsyncSession` for transport, a `TokenBucket`
for rate limiting, an `AdaptiveController` for backpressure, and an
`asyncio.Semaphore` to cap concurrency.

Use it as an async context manager so the underlying session is closed:

```python
async with AlmaClient("your-api-key") as client:
    ...
```

::: almapy._client.AlmaClient
