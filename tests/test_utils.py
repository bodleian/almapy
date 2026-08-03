"""Tests for _validate_response() and _should_retry()."""

import importlib.util
import json
import logging
import pickle  # ruff: ignore[suspicious-pickle-import] – round-tripping our own exceptions in tests
from pathlib import Path

import niquests
import pytest
from box import Box
from niquests.structures import CaseInsensitiveDict

from almapy import exceptions
from almapy._utils import Dumpable, ModelDumpable, _dump_body, _should_retry, _validate_response


def _error_body(code: str, message: str) -> str:
    """Return a JSON error body matching the errorList.error.0 glom path."""
    return json.dumps({"errorList": {"error": [{"errorCode": code, "errorMessage": message}]}})


def _make_response(
    status_code: int,
    body: str = "",
    content_type: str = "application/json",
) -> niquests.Response:
    r = niquests.Response()
    r.status_code = status_code
    r.headers = CaseInsensitiveDict({"Content-Type": content_type})
    r._content = body.encode()
    r._content_consumed = True
    return r


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

    def test_unrecognised_json_body_raises_client_error_for_4xx(self) -> None:
        """Was APIServerError regardless of status, which is retryable – so an
        unrecognised 400 body cost three round-trips before failing."""
        response = _make_response(400, '{"something": "unexpected"}')
        with pytest.raises(exceptions.APIClientError) as exc_info:
            _validate_response(response)
        assert not isinstance(exc_info.value, exceptions.APIServerError)
        assert "unexpected" in str(exc_info.value)

    def test_malformed_json_body_raises_an_almapy_error(self) -> None:
        """Regression: a bare json.JSONDecodeError used to escape, which is not
        an AlmapyError – so the status was lost and the failure was neither
        retried nor recorded by the adaptive controller."""
        response = _make_response(400, "{not valid json}")
        with pytest.raises(exceptions.APIClientError):
            _validate_response(response)

    def test_missing_content_type_treated_as_json(self) -> None:
        """No Content-Type header → falls through to json.loads (correct fallback)."""
        body = _error_body("401861", "User with identifier jsmith was not found.")
        r = niquests.Response()
        r.status_code = 404
        r.headers = CaseInsensitiveDict({})
        r._content = body.encode()
        r._content_consumed = True
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            _validate_response(r)
        assert exc_info.value.user_id == "jsmith"

    def test_content_type_with_charset_suffix_treated_as_json(self) -> None:
        """'application/json; charset=utf-8' != 'text/plain', doesn't contain 'xml' → json.loads path."""
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
        with pytest.raises(exceptions.UserNotFoundError):
            _validate_response(response)

    def test_single_error_dict_maps_to_the_specific_exception(self) -> None:
        """Alma sometimes returns errorList.error as a dict rather than a list.
        That form used to miss the glom chain and degrade to a retryable
        APIServerError("Unknown error"), losing the real error code."""
        body = json.dumps({
            "errorList": {
                "error": {
                    "errorCode": "401861",
                    "errorMessage": "User with identifier jsmith was not found.",
                }
            }
        })
        response = _make_response(404, body)
        with pytest.raises(exceptions.UserNotFoundError):
            _validate_response(response)

    def test_empty_error_message_falls_back_to_code(self) -> None:
        """Empty errorMessage → code is used as the message."""
        body = json.dumps({"errorList": {"error": [{"errorCode": "ABC", "errorMessage": ""}]}})
        response = _make_response(400, body)
        with pytest.raises(exceptions.APIClientError) as exc_info:
            _validate_response(response)
        assert exc_info.value.error == "ABC"
        assert exc_info.value.code == "ABC"

    def test_user_not_found_with_dotted_identifier(self) -> None:
        body = _error_body("401861", "User with identifier john.doe was not found.")
        response = _make_response(404, body)
        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.user_id == "john.doe"

    def test_barcode_brackets_stripped_correctly(self) -> None:
        body = _error_body("401689", "Input barcode [ITEM-42]")
        response = _make_response(400, body)
        with pytest.raises(exceptions.BarcodeNotFoundError) as exc_info:
            _validate_response(response)
        assert exc_info.value.barcode == "ITEM-42"


class TestLoanBlockedErrorFallback:
    def test_non_matching_message_all_attributes_empty(self) -> None:
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
        """A 400 raises APIClientError, not APIServerError – the latter is
        retryable, so an unrecognised client error used to be retried."""
        response = _make_response(400, '{"something": "unexpected"}')
        with (
            caplog.at_level(logging.WARNING, logger="almapy.error"),
            pytest.raises(exceptions.APIClientError),
        ):
            _validate_response(response)
        records = [r for r in caplog.records if r.name == "almapy.error"]
        assert len(records) == 1
        assert "unrecognised error body" in records[0].message

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
    def test_urllib3_transport_assertion_is_retryable(self, tmp_path: Path) -> None:
        module_path = tmp_path / "site-packages" / "urllib3" / "backend" / "_async" / "hface.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("def boom():\n    raise AssertionError()\n")

        spec = importlib.util.spec_from_file_location("fake_urllib3_hface", module_path)
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with pytest.raises(AssertionError) as exc_info:
            module.boom()

        assert _should_retry(exc_info.value) is True

    def test_non_urllib3_assertion_is_not_retryable(self) -> None:
        with pytest.raises(AssertionError) as exc_info:
            raise AssertionError()

        assert _should_retry(exc_info.value) is False

    def test_urllib3_http1_reuse_runtime_error_is_retryable(self, tmp_path: Path) -> None:
        module_path = tmp_path / "site-packages" / "urllib3" / "contrib" / "hface.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text(
            "def boom():\n"
            "    raise RuntimeError(\n"
            "        'Cannot generate a new stream ID because the connection is not idle. '\n"
            "        'HTTP/1.1 is not multiplexed and we do not support HTTP pipelining.'\n"
            "    )\n"
        )

        spec = importlib.util.spec_from_file_location("fake_urllib3_http1", module_path)
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with pytest.raises(RuntimeError) as exc_info:
            module.boom()

        assert _should_retry(exc_info.value) is True

    def test_urllib3_async_pending_signal_value_error_is_retryable(self, tmp_path: Path) -> None:
        module_path = (
            tmp_path / "site-packages" / "urllib3" / "util" / "_async" / "traffic_police.py"
        )
        module_path.parent.mkdir(parents=True)
        module_path.write_text(
            "def boom():\n"
            "    raise ValueError('AsyncPendingSignal(owner_task=<Task cancelling>, event=<Event>, "
            "target_conn_or_pool=None, target_obj_id=None, conn_or_pool=None, "
            "states=(<TrafficState.USED: 1>, <TrafficState.IDLE: 0>)) is not in deque')\n"
        )

        spec = importlib.util.spec_from_file_location("fake_urllib3_tp", module_path)
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with pytest.raises(ValueError) as exc_info:
            module.boom()

        assert _should_retry(exc_info.value) is True

    def test_api_server_error_is_retryable(self) -> None:
        exc = exceptions.APIServerError("500", "server error")
        assert _should_retry(exc) is True

    def test_threshold_error_is_retryable(self) -> None:
        exc = exceptions.ThresholdError("429", "rate limited")
        assert _should_retry(exc) is True

    def test_threshold_error_is_not_api_server_error(self) -> None:
        exc = exceptions.ThresholdError("429", "rate limited")
        assert not isinstance(exc, exceptions.APIServerError)

    def test_connect_error_is_retryable(self) -> None:
        exc = niquests.ConnectionError("connection refused")
        assert _should_retry(exc) is True

    def test_timeout_is_retryable(self) -> None:
        exc = niquests.Timeout("timed out")
        assert _should_retry(exc) is True

    def test_read_timeout_is_retryable(self) -> None:
        exc = niquests.ReadTimeout("read timed out")
        assert _should_retry(exc) is True

    def test_chunked_encoding_error_is_retryable(self) -> None:
        """niquests.ChunkedEncodingError replaces httpx.RemoteProtocolError for dropped connections."""
        exc = niquests.exceptions.ChunkedEncodingError("server dropped connection")
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


class _FakeModel:
    """Structurally satisfies Dumpable without importing or inheriting almapy."""

    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self._payload = payload or {"primary_id": "jdoe"}

    def dump(self, mode: str = "json") -> dict[str, object]:
        return self._payload


class _FakeModelDump:
    """Pydantic-shaped: exposes model_dump() but no dump()."""

    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self._payload = payload or {"primary_id": "jdoe"}

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        return self._payload


class _FakeBothDump:
    """Exposes both; dump() must win so a deliberate wire shape is not bypassed."""

    def dump(self, mode: str = "json") -> dict[str, object]:
        return {"via": "dump"}

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        return {"via": "model_dump"}


class TestDumpableProtocol:
    def test_object_with_compatible_dump_satisfies_protocol(self) -> None:
        """An object exposing dump(mode) -> dict is a Dumpable at runtime."""
        assert isinstance(_FakeModel(), Dumpable) is True

    def test_plain_dict_does_not_satisfy_protocol(self) -> None:
        """A plain dict has no dump() method, so it is not Dumpable."""
        assert isinstance({"primary_id": "jdoe"}, Dumpable) is False

    def test_model_dump_object_satisfies_model_dumpable_only(self) -> None:
        """A pydantic-shaped object is ModelDumpable but not Dumpable."""
        obj = _FakeModelDump()
        assert isinstance(obj, ModelDumpable) is True
        assert isinstance(obj, Dumpable) is False

    def test_box_satisfies_neither(self) -> None:
        """Guards config.sets.create, which takes a Box body that must pass through."""
        box = Box({"name": "a set"})
        assert isinstance(box, Dumpable) is False
        assert isinstance(box, ModelDumpable) is False


class TestDumpBody:
    def test_dict_passes_through_unchanged(self) -> None:
        body = {"primary_id": "jdoe"}
        assert _dump_body(body) is body

    def test_box_passes_through_unchanged(self) -> None:
        body = Box({"name": "a set"})
        assert _dump_body(body) is body

    def test_dump_object_is_converted(self) -> None:
        assert _dump_body(_FakeModel({"a": 1})) == {"a": 1}

    def test_model_dump_object_is_converted(self) -> None:
        """Regression: a plain pydantic BaseModel used to need a dump() shim."""
        assert _dump_body(_FakeModelDump({"b": 2})) == {"b": 2}

    def test_dump_takes_precedence_over_model_dump(self) -> None:
        assert _dump_body(_FakeBothDump()) == {"via": "dump"}


class TestUnparseableErrorBodies:
    """Not every error body is Alma's JSON.

    A bare JSONDecodeError escaping _raise_for_error_body is not an AlmapyError,
    so the status code was lost, _should_retry returned False and
    record_failure never fired – defeating retry and backpressure on exactly
    the transient gateway failures they exist for.
    """

    @staticmethod
    def _response(status: int, body: str, content_type: str | None) -> niquests.Response:
        r = niquests.Response()
        r.status_code = status
        r.headers = CaseInsensitiveDict({"Content-Type": content_type} if content_type else {})
        r._content = body.encode()
        r._content_consumed = True
        return r

    @pytest.mark.parametrize(
        ("label", "status", "body", "content_type"),
        [
            ("html proxy page", 502, "<html>Bad Gateway</html>", "text/html"),
            ("empty body, no content-type", 503, "", None),
            # An exact-equality check on Content-Type never matched this.
            ("text/plain with charset", 500, "boom", "text/plain;charset=UTF-8"),
        ],
    )
    def test_non_json_5xx_is_retryable_almapy_error(
        self, label: str, status: int, body: str, content_type: str | None
    ) -> None:
        with pytest.raises(exceptions.APIServerError) as exc_info:
            _validate_response(self._response(status, body, content_type))
        assert _should_retry(exc_info.value) is True, label

    def test_empty_body_gets_a_placeholder_message(self) -> None:
        with pytest.raises(exceptions.APIServerError, match="<empty body>"):
            _validate_response(self._response(503, "   ", None))

    def test_unrecognised_4xx_body_is_a_client_error_not_retried(self) -> None:
        """Was hardcoded to APIServerError, which is retryable – so an
        unparseable 404 cost three round-trips and depressed the rate limit."""
        with pytest.raises(exceptions.APIClientError) as exc_info:
            _validate_response(self._response(404, '{"nope": true}', "application/json"))
        assert not isinstance(exc_info.value, exceptions.APIServerError)
        assert _should_retry(exc_info.value) is False

    def test_error_list_as_dict_still_maps_to_the_specific_exception(self) -> None:
        """Alma sometimes sends errorList.error as an object rather than a list."""
        body = '{"errorList": {"error": {"errorCode": "401861", "errorMessage": "no user"}}}'
        with pytest.raises(exceptions.UserNotFoundError):
            _validate_response(self._response(404, body, "application/json"))


class TestExceptionRobustness:
    """Constructors must not raise, and instances must survive a process boundary."""

    @pytest.mark.parametrize(
        ("cls", "args"),
        [
            (exceptions.APIClientError, ("401861", "User not found.")),
            (exceptions.APIServerError, ("500", "boom")),
            (exceptions.ThresholdError, ("429", "too many")),
            (
                exceptions.UserNotFoundError,
                ("401861", "User with identifier jsmith was not found."),
            ),
            (exceptions.BarcodeNotFoundError, ("401689", "Input barcode [ABC]")),
            (exceptions.MMSIdNotFoundError, ("402203", "Input parameters mmsId 99123456789 bad.")),
            (exceptions.UserMissingFieldError, ("missing primary_id", "jdoe")),
            (exceptions.CannotRenewError, ("cannot renew", "L123")),
            (exceptions.InvalidCodeError, ("Invalid item_policy 'LOAN14'",)),
        ],
    )
    def test_round_trips_through_pickle(self, cls: type[Exception], args: tuple[str, ...]) -> None:
        """Exception.__reduce__ pickles as cls(*args), so args must mirror the
        constructor. It did not, so unpickling any almapy exception raised
        TypeError – replacing the real error behind a process pool or Celery."""
        original = cls(*args)
        restored = pickle.loads(pickle.dumps(original))  # ruff: ignore[suspicious-pickle-usage]
        assert type(restored) is cls
        assert str(restored) == str(original)

    def test_str_agrees_with_message(self) -> None:
        exc = exceptions.BarcodeNotFoundError("401689", "Input barcode [ABC]")
        assert str(exc) == exc.message

    @pytest.mark.parametrize("msg", ["Not found.", "", "402203", "short", "no digits here at all"])
    def test_mms_parser_never_raises(self, msg: str) -> None:
        """msg.split(' ')[3] raised IndexError from inside the error handler,
        which is not an AlmapyError – destroying the real API error."""
        assert exceptions.MMSIdNotFoundError("402203", msg).mms == ""

    @pytest.mark.parametrize(
        ("msg", "expected"),
        [
            # The real production format, reverse-engineered from a live 401689:
            # the barcode ends the message followed by a full stop, no delimiters.
            # The old slice stripped one char from each end, silently truncating
            # the barcode's first character.
            ("No items found for barcode 98279242.", "98279242"),
            ("Input barcode [ABC]", "ABC"),
            ("Input barcode [ITEM-42]", "ITEM-42"),
            ("No items found for barcode '98279242'.", "98279242"),
            ("401689", ""),  # empty errorMessage is replaced by the code upstream
            ("", ""),
        ],
    )
    def test_barcode_parser_handles_real_and_degenerate_messages(
        self, msg: str, expected: str
    ) -> None:
        assert exceptions.BarcodeNotFoundError("401689", msg).barcode == expected


class TestMessageParsers:
    """Every attribute below is scraped from Alma's prose error message.

    These parsers degrade silently – a wording change yields an empty attribute
    rather than an error – so both the match and the no-match path need pinning.
    The formats here are assumptions unless marked otherwise; the integration
    tests in test_integration_errors.py check them against the live API.
    """

    def test_loan_not_found_extracts_id(self) -> None:
        exc = exceptions.LoanNotFoundError("401823", "Loan ID 12345 does not exist.")
        assert exc.loan_id == "12345"

    @pytest.mark.parametrize(
        "msg", ["", "Loan not found.", "401823", "Loan ID abc does not exist."]
    )
    def test_loan_not_found_falls_back_to_empty(self, msg: str) -> None:
        assert exceptions.LoanNotFoundError("401823", msg).loan_id == ""

    def test_invalid_field_extracts_name_and_value(self) -> None:
        exc = exceptions.InvalidFieldError(
            "40166404", "Given field user_group has invalid value STAFF, blah."
        )
        assert (exc.field_name, exc.field_value) == ("user_group", "STAFF")
        assert exc.message == "Invalid field value 'STAFF' for field 'user_group' [40166404]"

    @pytest.mark.parametrize("msg", ["", "Invalid field.", "40166404"])
    def test_invalid_field_falls_back_and_keeps_the_original_message(self, msg: str) -> None:
        exc = exceptions.InvalidFieldError("40166404", msg)
        assert (exc.field_name, exc.field_value) == ("", "")
        assert exc.error == msg  # the raw message must survive an unparsed format

    def test_loan_blocked_extracts_all_four_fields(self) -> None:
        exc = exceptions.LoanBlockedError(
            "401201", "OVERDUE  -   Too many overdue items. See desk. Scope: LIBRARY"
        )
        assert exc.type == "OVERDUE"
        assert exc.description == "Too many overdue items"
        assert exc.scope == "LIBRARY"

    @pytest.mark.parametrize("msg", ["", "Blocked.", "401201"])
    def test_loan_blocked_falls_back_to_empty_fields(self, msg: str) -> None:
        exc = exceptions.LoanBlockedError("401201", msg)
        assert (exc.type, exc.description, exc.note, exc.scope) == ("", "", "", "")

    def test_user_not_found_extracts_identifier(self) -> None:
        exc = exceptions.UserNotFoundError("401861", "User with identifier jsmith was not found.")
        assert exc.user_id == "jsmith"

    @pytest.mark.parametrize("msg", ["", "No such user.", "401861"])
    def test_user_not_found_falls_back_to_empty(self, msg: str) -> None:
        assert exceptions.UserNotFoundError("401861", msg).user_id == ""

    def test_po_update_failed_strips_the_alma_prefix(self) -> None:
        exc = exceptions.POUpdateFailedError(
            "401876", "Failed to update the PO Line. Error: vendor is closed"
        )
        assert exc.message == "vendor is closed"

    @pytest.mark.parametrize(
        ("cls", "args"),
        [
            (exceptions.BarcodeNotFoundError, ("401689", "")),
            (exceptions.MMSIdNotFoundError, ("402203", "")),
            (exceptions.LoanBlockedError, ("401201", "")),
            (exceptions.InvalidFieldError, ("40166404", "")),
            (exceptions.UserNotFoundError, ("401861", "")),
            (exceptions.LoanNotFoundError, ("401823", "")),
            (exceptions.POUpdateFailedError, ("401876", "")),
        ],
    )
    def test_no_parser_raises_on_a_degenerate_message(
        self, cls: type[Exception], args: tuple[str, ...]
    ) -> None:
        """A constructor that raises destroys the API error it was describing,
        because it runs inside _raise_for_error_body."""
        assert isinstance(cls(*args), exceptions.APIClientError)
