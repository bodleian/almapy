# Logging

almapy uses stdlib `logging` and follows library best practice: a `NullHandler`
is registered on the `almapy` root logger at import time, so **no output is
produced unless you configure handlers**. The library never writes to your
console uninvited.

## The four loggers

| Logger | Level | Event | Extra fields |
|--------|-------|-------|--------------|
| `almapy.http` | DEBUG | Request sent | `method`, `url` |
| `almapy.http` | DEBUG | Response received | `method`, `url`, `status_code`, `elapsed_ms` |
| `almapy.retry` | WARNING | Retry attempt | `attempt`, `max_attempts`, `exc_type` |
| `almapy.throttle` | DEBUG | TokenBucket wait | `wait_secs`, `tokens_available` |
| `almapy.throttle` | WARNING | Rate cut (AIMD backoff) | `old_rate`, `new_rate` |
| `almapy.throttle` | INFO | Rate recovery | `old_rate`, `new_rate` |
| `almapy.error` | WARNING | Alma error before raising | `status_code`, `alma_code` (where applicable) |

They are semantic rather than per-module, so you can turn on exactly the
category you care about — retries without the full HTTP firehose, say.

## Correlation IDs

Every record carries a `req_id` field: a `uuid4().hex` set at the start of each
`execute()` call and reset in `finally`. It lives in a `contextvars.ContextVar`,
so it survives across `await` boundaries and stays correct under concurrency.

Use it to reassemble the story of a single request — its retries, its throttle
waits, and the error it finally raised — out of interleaved output from 150
concurrent calls.

## Turning it on

```python
import logging

# Everything
logging.getLogger("almapy").setLevel(logging.DEBUG)
logging.getLogger("almapy").addHandler(logging.StreamHandler())

# Or just one area — retry warnings only
logging.getLogger("almapy.retry").setLevel(logging.WARNING)
logging.getLogger("almapy.retry").addHandler(logging.StreamHandler())
```

To include the correlation ID in your output:

```python
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s %(name)s [%(req_id)s] %(message)s"))
logging.getLogger("almapy").addHandler(handler)
```

!!! warning "`%(req_id)s` needs every record to carry it"

    A formatter referencing `%(req_id)s` raises `KeyError` on any record from
    another library. Either scope the handler to the `almapy` logger as above,
    or use a filter that defaults the field.

## What is never logged

API keys and full response bodies are never written to logs. Error records
carry Alma's status code and numeric error code, and unparseable bodies are
truncated to a 500-character excerpt.

## structlog

All extra fields flow into structlog automatically via `ExtraAdder()`:

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
        structlog.stdlib.ExtraAdder(),  # pulls req_id, status_code, elapsed_ms
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ],
    processor=structlog.processors.JSONRenderer(),
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger("almapy").addHandler(handler)
logging.getLogger("almapy").setLevel(logging.DEBUG)
```

Each record then renders as JSON with `req_id`, `status_code` and `elapsed_ms`
as first-class keys, ready for your log aggregator.
