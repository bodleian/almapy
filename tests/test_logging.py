"""Tests for almapy._logging — shared logging infrastructure."""

import contextlib
import logging
import subprocess  # noqa: S404 — import-time behaviour needs a fresh interpreter
import sys
import textwrap

import pytest
import stamina

from almapy._logging import new_request_id, request_id


def test_null_handler_registered() -> None:
    """almapy root logger must have NullHandler — library must not force output."""
    handlers = logging.getLogger("almapy").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)


def test_stamina_retry_log_suppressed_even_when_hooks_reenabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """almapy emits its own retry logs; stamina's must stay suppressed.

    Importing almapy disables stamina's hooks, but they are process-global and
    last-writer-wins. The logging filter on the 'stamina' logger is the
    order-independent backstop, so re-enabling defaults must NOT leak the log.
    """
    stamina.instrumentation.set_on_retry_hooks(None)  # re-enable stamina defaults
    try:
        retry_msg = "trigger a scheduled retry"

        @stamina.retry(on=ValueError, attempts=2, wait_initial=0.001)
        def boom() -> None:
            raise ValueError(retry_msg)

        with caplog.at_level(logging.WARNING, logger="stamina"), contextlib.suppress(ValueError):
            boom()

        assert not any(r.msg == "stamina.retry_scheduled" for r in caplog.records)
    finally:
        stamina.instrumentation.set_on_retry_hooks(())  # restore almapy's suppression


def test_new_request_id_is_unique() -> None:
    """1000 IDs must all be distinct — full UUID4, no truncation or counter reset."""
    ids = {new_request_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_new_request_id_length() -> None:
    """uuid4().hex produces exactly 32 hex chars (full UUID128, no dashes)."""
    assert len(new_request_id()) == 32


def test_new_request_id_is_hex() -> None:
    """ID must be valid hexadecimal — confirms uuid4().hex, not some other format."""
    rid = new_request_id()
    assert all(c in "0123456789abcdef" for c in rid)


def test_request_id_contextvar_default_is_empty_string() -> None:
    """Default must be empty string, not None — ensures %(req_id)s formatting works."""
    assert request_id.get() == ""


def test_request_id_contextvar_is_settable() -> None:
    """ContextVar must accept and return a string value."""
    token = request_id.set("test-id")
    try:
        assert request_id.get() == "test-id"
    finally:
        request_id.reset(token)


def test_request_id_contextvar_resets_correctly() -> None:
    """reset() must restore the previous value, not just clear to default."""
    outer_token = request_id.set("outer")
    try:
        inner_token = request_id.set("inner")
        assert request_id.get() == "inner"
        request_id.reset(inner_token)
        assert request_id.get() == "outer"
    finally:
        request_id.reset(outer_token)


class TestTransportLoggerDefaults:
    """almapy quietens urllib3/niquests without overriding the host application.

    Both emit a record per request at DEBUG, which is unusable noise at almapy's
    default rate — but a library silently undoing an application's explicit
    logging configuration is worse. Only NOTSET loggers are defaulted.
    """

    @staticmethod
    def _levels_after_import(preamble: str) -> dict[str, str]:
        """Import almapy in a fresh interpreter, after running `preamble`."""
        code = textwrap.dedent(f"""
            import logging
            {preamble}
            import almapy  # noqa: F401
            import stamina.instrumentation as si
            for name in ("urllib3", "niquests"):
                print(name, logging.getLevelName(logging.getLogger(name).level))
            print("stamina_hooks_disabled", si.get_on_retry_hooks() == ())
        """)
        out = subprocess.run(  # noqa: S603
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout.split()
        return dict(zip(out[::2], out[1::2], strict=True))

    def test_unconfigured_loggers_default_to_warning(self) -> None:
        levels = self._levels_after_import("")
        assert levels["urllib3"] == "WARNING"
        assert levels["niquests"] == "WARNING"

    def test_explicit_application_level_is_not_overridden(self) -> None:
        """Regression: almapy used to clobber this unconditionally."""
        levels = self._levels_after_import('logging.getLogger("urllib3").setLevel(logging.DEBUG)')
        assert levels["urllib3"] == "DEBUG"
        assert levels["niquests"] == "WARNING"

    def test_import_does_not_disable_stamina_instrumentation(self) -> None:
        """set_on_retry_hooks is process-global; disabling it broke every other user."""
        levels = self._levels_after_import("")
        assert levels["stamina_hooks_disabled"] == "False"
