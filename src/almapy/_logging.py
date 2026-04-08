"""Shared logging infrastructure for almapy.

All modules import `request_id` from here to avoid circular imports.
Callers configure output by adding handlers to `logging.getLogger("almapy")`.
"""

import contextvars
import logging
import uuid

import stamina

# Library best practice: register NullHandler so no output is forced on callers.
# Multiple NullHandlers from module reload are harmless (both discard all records).
logging.getLogger("almapy").addHandler(logging.NullHandler())

# Disable stamina's process-global retry instrumentation; almapy emits retry logs itself.
stamina.instrumentation.set_on_retry_hooks(())

# Suppress debug output from transitive HTTP dependencies to prevent credential leaks.
# niquests and urllib3 log full request URLs at DEBUG level, which can expose apikeys.
# WARNING+ is still propagated (connection errors, SSL warnings remain visible).
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("niquests").setLevel(logging.WARNING)

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
