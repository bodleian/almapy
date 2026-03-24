"""Tests for _validate_response() and _should_retry()."""

import httpx
import pytest

from almapy import exceptions
from almapy._utils import _should_retry, _validate_response


def _error_body(code: str, message: str) -> str:
    """Return a JSON error body matching the errorList.error.0 glom path."""
    import json

    return json.dumps({"errorList": {"error": [{"errorCode": code, "errorMessage": message}]}})


def _make_response(
    status_code: int,
    body: str = "",
    content_type: str = "application/json",
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers={"Content-Type": content_type},
        content=body.encode(),
    )


class TestValidateResponse:
    def test_200_is_no_op(self) -> None:
        response = _make_response(200)
        _validate_response(response)  # must not raise

    def test_201_is_no_op(self) -> None:
        response = _make_response(201)
        _validate_response(response)

    def test_204_is_no_op(self) -> None:
        response = _make_response(204)
        _validate_response(response)

    def test_400_raises_api_client_error(self) -> None:
        response = _make_response(400, _error_body("ABC", "bad input"))
        with pytest.raises(exceptions.APIClientError):
            _validate_response(response)

    def test_404_raises_user_not_found(self) -> None:
        body = _error_body("401861", "User with identifier jsmith was not found.")
        response = _make_response(404, body)
        with pytest.raises(exceptions.UserNotFoundError):
            _validate_response(response)

    def test_429_raises_threshold_error(self) -> None:
        body = _error_body("429", "rate limited")
        response = _make_response(429, body)
        with pytest.raises(exceptions.ThresholdError):
            _validate_response(response)

    def test_500_raises_api_server_error(self) -> None:
        body = _error_body("500", "server error")
        response = _make_response(500, body)
        with pytest.raises(exceptions.APIServerError):
            _validate_response(response)

    def test_known_barcode_error_code(self) -> None:
        body = _error_body("401689", "Input barcode [ABC]")
        response = _make_response(400, body)
        with pytest.raises(exceptions.BarcodeNotFoundError):
            _validate_response(response)

    def test_plain_text_500_raises_api_server_error(self) -> None:
        response = _make_response(500, "internal error", content_type="text/plain")
        with pytest.raises(exceptions.APIServerError):
            _validate_response(response)


class TestShouldRetry:
    def test_api_server_error_is_retryable(self) -> None:
        exc = exceptions.APIServerError("500", "server error")
        assert _should_retry(exc) is True

    def test_threshold_error_is_retryable(self) -> None:
        exc = exceptions.ThresholdError("429", "rate limited")
        assert _should_retry(exc) is True

    def test_threshold_error_is_not_api_server_error(self) -> None:
        """ThresholdError must not inherit APIServerError — retry logic is explicit in _RETRYABLE."""
        exc = exceptions.ThresholdError("429", "rate limited")
        assert not isinstance(exc, exceptions.APIServerError)

    def test_connect_error_is_retryable(self) -> None:
        exc = httpx.ConnectError("connection refused")
        assert _should_retry(exc) is True

    def test_timeout_exception_is_retryable(self) -> None:
        exc = httpx.TimeoutException("timed out")
        assert _should_retry(exc) is True

    def test_read_timeout_is_retryable(self) -> None:
        exc = httpx.ReadTimeout("read timed out")
        assert _should_retry(exc) is True

    def test_remote_protocol_error_is_retryable(self) -> None:
        exc = httpx.RemoteProtocolError("server dropped connection")
        assert _should_retry(exc) is True

    def test_api_client_error_is_not_retryable(self) -> None:
        exc = exceptions.APIClientError("400", "bad request")
        assert _should_retry(exc) is False

    def test_barcode_not_found_is_not_retryable(self) -> None:
        exc = exceptions.BarcodeNotFoundError("401689", "Input barcode [ABC]")
        assert _should_retry(exc) is False

    def test_value_error_is_not_retryable(self) -> None:
        assert _should_retry(ValueError("bad")) is False

    def test_runtime_error_is_not_retryable(self) -> None:
        assert _should_retry(RuntimeError("oops")) is False
