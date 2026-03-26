"""Tests for _validate_response() and _should_retry()."""

import json
import logging

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
    def test_400_raises_api_client_error(self) -> None:
        response = _make_response(400, _error_body("ABC", "bad input"))
        with pytest.raises(exceptions.APIClientError) as exc_info:
            _validate_response(response)
        assert exc_info.value.code == "ABC"
        assert exc_info.value.error == "bad input"

    def test_404_raises_user_not_found(self) -> None:
        body = _error_body("401861", "User with identifier jsmith was not found.")
        response = _make_response(404, body)
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.user_id == "jsmith"

    def test_429_raises_threshold_error(self) -> None:
        body = _error_body("429", "rate limited")
        response = _make_response(429, body)
        with pytest.raises(exceptions.ThresholdError):
            _validate_response(response)

    def test_500_raises_api_server_error(self) -> None:
        body = _error_body("500", "server error")
        response = _make_response(500, body)
        with pytest.raises(exceptions.APIServerError) as exc_info:
            _validate_response(response)
        assert exc_info.value.code == "500"
        assert exc_info.value.error == "server error"

    def test_known_barcode_error_code(self) -> None:
        body = _error_body("401689", "Input barcode [ABC]")
        response = _make_response(400, body)
        with pytest.raises(exceptions.BarcodeNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.barcode == "ABC"

    def test_plain_text_500_raises_api_server_error(self) -> None:
        response = _make_response(500, "internal error", content_type="text/plain")
        with pytest.raises(exceptions.APIServerError):
            _validate_response(response)

    def test_xml_error_body_raises_correct_exception(self) -> None:
        xml_body = (
            "<web_service_result>"
            "<errorList><error>"
            "<errorCode>401861</errorCode>"
            "<errorMessage>User with identifier jsmith was not found.</errorMessage>"
            "</error></errorList>"
            "</web_service_result>"
        )
        response = _make_response(404, xml_body, content_type="application/xml")
        with pytest.raises(exceptions.UserNotFoundError):
            _validate_response(response)

    def test_unrecognised_json_body_raises_api_server_error(self) -> None:
        response = _make_response(400, '{"something": "unexpected"}')
        with pytest.raises(exceptions.APIServerError, match="Unknown error"):
            _validate_response(response)

    def test_malformed_json_body_on_4xx_propagates_decode_error(self) -> None:
        """json.JSONDecodeError propagates raw — callers must handle this if catching only APIClientError."""
        response = _make_response(400, "{not valid json}")
        with pytest.raises(json.JSONDecodeError):
            _validate_response(response)

    def test_missing_content_type_treated_as_json(self) -> None:
        """No Content-Type header → falls through to json.loads (correct fallback)."""
        body = _error_body("401861", "User with identifier jsmith was not found.")
        response = httpx.Response(status_code=404, content=body.encode())
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.user_id == "jsmith"

    def test_content_type_with_charset_suffix_treated_as_json(self) -> None:
        """'application/json; charset=utf-8' ≠ 'text/plain', doesn't contain 'xml' → json.loads path."""
        body = _error_body("401861", "User with identifier jsmith was not found.")
        response = _make_response(404, body, content_type="application/json; charset=utf-8")
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.user_id == "jsmith"

    def test_xml_with_ampersand_in_url_parsed_via_retry(self) -> None:
        """Unescaped & in URL triggers ExpatError; _parse_xml re.sub retry path must recover."""
        xml_body = (
            "<web_service_result>"
            "<errorList><error>"
            "<errorCode>401861</errorCode>"
            "<errorMessage>See https://api.example.com/info?a=1&b=2</errorMessage>"
            "</error></errorList>"
            "</web_service_result>"
        )
        response = _make_response(404, xml_body, content_type="application/xml")
        # Must not raise ExpatError — the retry path in _parse_xml handles it
        with pytest.raises(exceptions.UserNotFoundError):
            _validate_response(response)

    def test_single_error_dict_raises_api_server_error(self) -> None:
        """Alma sometimes returns errorList.error as a dict (not list). Glom path mismatch → Unknown error."""
        body = json.dumps({
            "errorList": {
                "error": {
                    "errorCode": "401861",
                    "errorMessage": "User with identifier jsmith was not found.",
                }
            }
        })
        response = _make_response(404, body)
        # Known limitation: single-dict error body hits GlomError fallback
        with pytest.raises(exceptions.APIServerError, match="Unknown error"):
            _validate_response(response)

    def test_empty_error_message_falls_back_to_code(self) -> None:
        """Empty errorMessage → code is used as the message (line: message = code if not message)."""
        body = json.dumps({"errorList": {"error": [{"errorCode": "ABC", "errorMessage": ""}]}})
        response = _make_response(400, body)
        with pytest.raises(exceptions.APIClientError) as exc_info:
            _validate_response(response)
        assert exc_info.value.error == "ABC"
        assert exc_info.value.code == "ABC"

    def test_user_not_found_with_dotted_identifier(self) -> None:
        """UserNotFoundError regex [A-Za-z0-9._-]+ now matches dotted/hyphenated identifiers."""
        body = _error_body("401861", "User with identifier john.doe was not found.")
        response = _make_response(404, body)
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.user_id == "john.doe"

    def test_barcode_brackets_stripped_correctly(self) -> None:
        """BarcodeNotFoundError strips both [ and ] from '[ABC]' → 'ABC' (fixed from [0:-1] to [1:-1])."""
        body = _error_body("401689", "Input barcode [ITEM-42]")
        response = _make_response(400, body)
        with pytest.raises(exceptions.BarcodeNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.barcode == "ITEM-42"


class TestLoanBlockedErrorFallback:
    def test_non_matching_message_all_attributes_empty(self) -> None:
        """LoanBlockedError fallback: regex no-match sets all 4 domain attrs to empty string."""
        exc = exceptions.LoanBlockedError("401201", "This message does not match the pattern")
        assert exc.type == ""
        assert exc.description == ""
        assert exc.note == ""
        assert exc.scope == ""


class TestErrorLogging:
    def test_json_error_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        body = _error_body("401861", "User with identifier jsmith was not found.")
        response = _make_response(404, body)
        with (
            caplog.at_level(logging.WARNING, logger="almapy.error"),
            pytest.raises(exceptions.UserNotFoundError),
        ):
            _validate_response(response)
        records = [r for r in caplog.records if r.name == "almapy.error"]
        assert len(records) == 1
        assert "401861" in records[0].message

    def test_plain_text_error_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        response = _make_response(500, "internal error", content_type="text/plain")
        with (
            caplog.at_level(logging.WARNING, logger="almapy.error"),
            pytest.raises(exceptions.APIServerError),
        ):
            _validate_response(response)
        records = [r for r in caplog.records if r.name == "almapy.error"]
        assert len(records) == 1
        assert "500" in records[0].message

    def test_unparseable_body_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        response = _make_response(400, '{"something": "unexpected"}')
        with (
            caplog.at_level(logging.WARNING, logger="almapy.error"),
            pytest.raises(exceptions.APIServerError),
        ):
            _validate_response(response)
        records = [r for r in caplog.records if r.name == "almapy.error"]
        assert len(records) == 1
        assert "unparseable" in records[0].message

    def test_error_log_records_have_req_id(self, caplog: pytest.LogCaptureFixture) -> None:
        body = _error_body("401861", "User with identifier jsmith was not found.")
        response = _make_response(404, body)
        with (
            caplog.at_level(logging.WARNING, logger="almapy.error"),
            pytest.raises(exceptions.UserNotFoundError),
        ):
            _validate_response(response)
        for record in caplog.records:
            assert hasattr(record, "req_id")


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
