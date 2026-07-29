"""Shared logging infrastructure for almapy.

All modules import `request_id` from here to avoid circular imports.
Callers configure output by adding handlers to `logging.getLogger("almapy")`.
"""

import contextvars
import logging
import uuid

# Library best practice: register NullHandler so no output is forced on callers.
# Multiple NullHandlers from module reload are harmless (both discard all records).
logging.getLogger("almapy").addHandler(logging.NullHandler())


class _DropStaminaRetryLog(logging.Filter):
    """Suppress stamina's built-in 'stamina.retry_scheduled' record; almapy logs retries itself."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.msg != "stamina.retry_scheduled"


# Attached to the "stamina" logger directly, where LoggingOnRetryHook emits the record, so the
# filter always runs regardless of hook state. This is deliberately a filter rather than
# stamina.instrumentation.set_on_retry_hooks(()): that call is process-global and
# last-writer-wins, so it would disable retry instrumentation for every other stamina user
# in the application. Idempotent enough: duplicate filters from module reload all drop the
# same record harmlessly.
logging.getLogger("stamina").addFilter(_DropStaminaRetryLog())

_NOISY_TRANSPORT_LOGGERS = ("urllib3", "niquests")


def _quieten_transport_loggers() -> None:
    """Default the transport loggers to WARNING without overriding the application.

    urllib3 and niquests emit a record per connection and per request at DEBUG.
    At almapy's default of 25 req/s that buries an application's own output, so
    WARNING is the level nearly everyone wants.

    A library must not silently undo a deliberate choice, though, so only
    loggers still at NOTSET — meaning nothing has called setLevel on them — are
    touched. An application that configures either logger, before or after
    importing almapy, keeps its own setting.

    Note this does still win over a bare ``logging.basicConfig(level=DEBUG)``,
    which sets the level on the root logger rather than on these. To see
    transport debug output, set it on the logger itself:

        logging.getLogger("urllib3").setLevel(logging.DEBUG)
    """
    for name in _NOISY_TRANSPORT_LOGGERS:
        logger = logging.getLogger(name)
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.WARNING)


_quieten_transport_loggers()

# Per-request correlation ID. Set at the start of AlmaClient._execute(),
# reset in finally. Unique across process restarts (full UUID128 as 32 hex chars).
# Default is "" (empty string) — callers using %(req_id)s in formatters will see
# a blank field when called outside _execute() context. Do NOT change to None
# as that would break %(req_id)s string formatting.
request_id: contextvars.ContextVar[str] = contextvars.ContextVar("almapy_req_id", default="")


def new_request_id() -> str:
    """Generate a unique request correlation ID (UUID4 hex, 32 chars).

    Uses the full UUID128 as a hex string — unique across process restarts,
    no external dependency. 32 chars = 128 bits of randomness, no truncation.
    """
    return uuid.uuid4().hex
