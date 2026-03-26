"""Tests for almapy._logging — shared logging infrastructure."""

import logging

from almapy._logging import new_request_id, request_id


def test_null_handler_registered() -> None:
    """almapy root logger must have NullHandler — library must not force output."""
    handlers = logging.getLogger("almapy").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)


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
