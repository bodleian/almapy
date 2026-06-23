"""Tests for AlmaClient.execute and _parse."""

import json
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import niquests
import pytest
import responses
from box import Box
from niquests.structures import CaseInsensitiveDict

from almapy import AlmaClient, exceptions
from tests._niquests_mock import NiquestsMock

_BASE = "https://api-eu.hosted.exlibrisgroup.com/almaws/v1"


def _make_response(
    status_code: int, body: str = "", content_type: str = "application/json"
) -> niquests.Response:
    """Build a niquests.Response for use in _parse() unit tests only.

    Not for execute() tests — use the rsps fixture to register URLs instead.
    """
    r = niquests.Response()
    r.status_code = status_code
    r.headers = CaseInsensitiveDict({"Content-Type": content_type})
    r._content = body.encode()
    r._content_consumed = True
    return r


class TestExecuteOutcomeRecording:
    @pytest.mark.asyncio
    async def test_success_calls_record_success(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(responses.GET, f"{_BASE}/users", json={"foo": "bar"})
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        await client.execute("GET", "/users", parser="json")

        client._controller.record_success.assert_called_once()
        client._controller.record_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_retryable_error_calls_record_failure(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(responses.GET, f"{_BASE}/users", body=niquests.ConnectionError("refused"))
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(niquests.ConnectionError):
            await client.execute("GET", "/users", parser="json")

        # retry_attempts=3: ConnectionError is retryable, record_failure called once per attempt
        assert client._controller.record_failure.call_count == 3
        client._controller.record_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_retryable_4xx_does_not_call_record_failure(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        body = json.dumps({
            "errorList": {"error": [{"errorCode": "401861", "errorMessage": "User not found."}]}
        })
        rsps.add(responses.GET, f"{_BASE}/users/jsmith", json=json.loads(body), status=404)
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            await client.execute("GET", "/users/jsmith", parser="json")

        assert exc_info.value.user_id == ""
        client._controller.record_failure.assert_not_called()
        client._controller.record_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_5xx_calls_record_failure(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(
            responses.GET,
            f"{_BASE}/users",
            json={"errorList": {"error": [{"errorCode": "500", "errorMessage": "Server error"}]}},
            status=500,
        )
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(exceptions.APIServerError):
            await client.execute("GET", "/users", parser="json")

        # retry_attempts=3: APIServerError is retryable, record_failure called once per attempt
        assert client._controller.record_failure.call_count == 3
        client._controller.record_success.assert_not_called()


class TestParse:
    def test_json_parser(self, client: AlmaClient) -> None:
        resp = _make_response(200, '{"title": "Dune"}')
        result = client._parse(resp, "json")
        assert result.title == "Dune"

    def test_text_parser(self, client: AlmaClient) -> None:
        resp = _make_response(200, "raw text", content_type="text/plain")
        result = client._parse(resp, "text")
        assert result == "raw text"

    def test_none_parser(self, client: AlmaClient) -> None:
        resp = _make_response(200, '{"ignored": true}')
        result = client._parse(resp, "none")
        assert result == {}

    def test_no_content_returns_empty(self, client: AlmaClient) -> None:
        resp = _make_response(204)
        result = client._parse(resp, "json")
        assert result == {}

    def test_xml_parser(self, client: AlmaClient) -> None:
        xml_body = "<root><item>hello</item></root>"
        resp = _make_response(200, xml_body, content_type="application/xml")
        result = client._parse(resp, "xml")
        assert isinstance(result, Box)
        assert result.root.item == "hello"


class TestAlmaClientInternals:
    def test_empty_apikey_raises(self) -> None:
        with pytest.raises(ValueError, match="apikey must be provided"):
            AlmaClient("")

    def test_invalid_location_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid location"):
            AlmaClient("test-api-key", location="Antarctica")  # type: ignore[arg-type]

    def test_owned_session_pool_matches_concurrency(self) -> None:
        client = AlmaClient("test-api-key", concurrent_requests=150)
        https_adapter = client._http.adapters["https://"]
        assert client._http._pool_connections == 150
        assert client._http._pool_maxsize == 150
        assert https_adapter.poolmanager._num_pools == 150  # type: ignore[attr-defined]
        assert https_adapter.poolmanager.connection_pool_kw["maxsize"] == 150  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_aclose_closes_owned_client(self) -> None:
        client = AlmaClient("test-api-key")
        assert client._owns_client is True
        await client.aclose()
        assert client._closed is True

    @pytest.mark.asyncio
    async def test_aclose_does_not_close_external_client(self) -> None:
        mock_session = AsyncMock(spec=niquests.AsyncSession)
        client = AlmaClient("test-api-key", client=mock_session)
        assert client._owns_client is False
        await client.aclose()
        mock_session.close.assert_not_called()
        assert client._closed is False

    @pytest.mark.asyncio
    async def test_context_manager_closes_owned_client_on_exit(self) -> None:
        client = AlmaClient("test-api-key")
        async with client:
            pass
        assert client._closed is True

    @pytest.mark.asyncio
    async def test_execute_retries_correct_number_of_times(self, rsps: NiquestsMock) -> None:
        client = AlmaClient("test-api-key", retry_attempts=2)
        rsps.add(responses.GET, f"{_BASE}/users", body=niquests.ConnectionError("refused"))
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(niquests.ConnectionError):
            await client.execute("GET", "/users", parser="json")

        assert len(rsps.calls) == 2


class TestExecuteModelValidation:
    @pytest.mark.asyncio
    async def test_model_none_returns_box(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, f"{_BASE}/users", json={"foo": "bar"})
        result = await client.execute("GET", "/users", parser="json", model=None)
        assert isinstance(result, Box)
        assert result.foo == "bar"

    @pytest.mark.asyncio
    async def test_model_provided_calls_model_validate(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(responses.GET, f"{_BASE}/users", json={"foo": "bar"})
        mock_model = MagicMock()
        mock_model.model_validate.return_value = "validated_instance"

        result: str = await client.execute("GET", "/users", parser="json", model=mock_model)

        assert result == "validated_instance"
        mock_model.model_validate.assert_called_once()
        call_arg = mock_model.model_validate.call_args[0][0]
        assert isinstance(call_arg, Box)
        assert call_arg.foo == "bar"

    @pytest.mark.asyncio
    async def test_model_validate_exception_propagates(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(responses.GET, f"{_BASE}/users", json={"foo": "bar"})
        mock_model = MagicMock()
        mock_model.model_validate.side_effect = ValueError("bad data")

        with pytest.raises(ValueError, match="bad data"):
            await client.execute("GET", "/users", parser="json", model=mock_model)

    @pytest.mark.asyncio
    async def test_model_receives_empty_box_on_no_content(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        """204 No Content → Box() is passed to model_validate (not skipped)."""
        rsps.add(responses.GET, f"{_BASE}/users", status=204, body="")
        mock_model = MagicMock()
        mock_model.model_validate.return_value = "empty_model"

        result: str = await client.execute("GET", "/users", parser="json", model=mock_model)

        assert result == "empty_model"
        call_arg = mock_model.model_validate.call_args[0][0]
        assert isinstance(call_arg, Box)
        assert len(call_arg) == 0


class TestExecuteLogging:
    @pytest.mark.asyncio
    async def test_http_logger_emits_request_and_response(
        self, client: AlmaClient, rsps: NiquestsMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """almapy.http emits exactly 2 DEBUG records per successful request."""
        rsps.add(responses.GET, f"{_BASE}/users", json={"foo": "bar"})
        with caplog.at_level(logging.DEBUG, logger="almapy.http"):
            await client.execute("GET", "/users", parser="json")
        records = [r for r in caplog.records if r.name == "almapy.http"]
        assert len(records) == 2
        assert "GET" in records[0].message and "/users" in records[0].message
        assert "200" in records[1].message

    @pytest.mark.asyncio
    async def test_log_records_carry_req_id(
        self, client: AlmaClient, rsps: NiquestsMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Every log record emitted inside execute() must have a non-empty req_id."""
        rsps.add(responses.GET, f"{_BASE}/users", json={"foo": "bar"})
        with caplog.at_level(logging.DEBUG, logger="almapy.http"):
            await client.execute("GET", "/users", parser="json")
        for record in caplog.records:
            assert hasattr(record, "req_id"), f"Missing req_id on {record.name} record"
            assert getattr(record, "req_id", "") != "", "req_id must be non-empty inside execute()"

    @pytest.mark.asyncio
    async def test_req_ids_are_unique_across_calls(
        self, client: AlmaClient, rsps: NiquestsMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Each execute() call must generate a distinct req_id."""
        rsps.add(responses.GET, f"{_BASE}/users/1", json={"foo": "bar"})
        rsps.add(responses.GET, f"{_BASE}/users/2", json={"foo": "bar"})
        req_ids: list[str] = []
        with caplog.at_level(logging.DEBUG, logger="almapy.http"):
            await client.execute("GET", "/users/1", parser="json")
            req_ids.append(getattr(caplog.records[-1], "req_id", ""))
            caplog.clear()
            await client.execute("GET", "/users/2", parser="json")
            req_ids.append(getattr(caplog.records[-1], "req_id", ""))
        assert req_ids[0] != req_ids[1]

    @pytest.mark.asyncio
    async def test_retry_logger_warns_on_second_attempt(
        self, rsps: NiquestsMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """almapy.retry emits a WARNING on retry (not on first attempt)."""
        client = AlmaClient("test-api-key", retry_attempts=2)
        rsps.add(
            responses.GET,
            f"{_BASE}/bibs/123",
            json={"errorList": {"error": [{"errorCode": "500", "errorMessage": "Server error"}]}},
            status=500,
        )
        rsps.add(responses.GET, f"{_BASE}/bibs/123", json={"ok": True})
        with caplog.at_level(logging.WARNING, logger="almapy.retry"):
            await client.execute("GET", "/bibs/123", parser="json")
        retry_records = [r for r in caplog.records if r.name == "almapy.retry"]
        assert len(retry_records) == 1
        assert "Retry 2/" in retry_records[0].message
        assert "APIServerError" in retry_records[0].message

    @pytest.mark.asyncio
    async def test_stamina_retry_logger_is_suppressed(
        self, rsps: NiquestsMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Retry logging must come from almapy.retry only, never stamina."""
        client = AlmaClient("test-api-key", retry_attempts=2)
        rsps.add(
            responses.GET,
            f"{_BASE}/bibs/123",
            json={"errorList": {"error": [{"errorCode": "500", "errorMessage": "Server error"}]}},
            status=500,
        )
        rsps.add(responses.GET, f"{_BASE}/bibs/123", json={"ok": True})

        with caplog.at_level(logging.WARNING):
            await client.execute("GET", "/bibs/123", parser="json")

        assert [r for r in caplog.records if r.name == "almapy.retry"]
        assert [r for r in caplog.records if r.name == "stamina"] == []


class TestSanitizeUrl:
    """Unit tests for the _sanitize_url helper."""

    def test_no_query_string_unchanged(self) -> None:
        """Relative paths without query strings pass through untouched."""
        from almapy._client import _sanitize_url

        assert _sanitize_url("/bibs/123") == "/bibs/123"

    def test_strips_apikey_only_param(self) -> None:
        """URL with only apikey= becomes a bare path (catches: apikey exposure)."""
        from almapy._client import _sanitize_url

        assert _sanitize_url("/bibs/123?apikey=supersecret") == "/bibs/123"

    def test_strips_apikey_preserves_other_params(self) -> None:
        """apikey is removed but other query params are kept (catches: over-stripping)."""
        from almapy._client import _sanitize_url

        result = _sanitize_url("/bibs/123?apikey=supersecret&limit=10&offset=0")
        assert "apikey" not in result
        assert "limit=10" in result
        assert "offset=0" in result

    def test_strips_apikey_case_insensitive(self) -> None:
        """APIKEY= and ApiKey= are also stripped (catches: case-bypass)."""
        from almapy._client import _sanitize_url

        assert _sanitize_url("/bibs/123?APIKEY=supersecret") == "/bibs/123"


class _FakeModel:
    """Dumpable test double: records the mode each .dump() is called with."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.dump_modes: list[str] = []

    def dump(self, mode: str = "json") -> dict[str, Any]:
        self.dump_modes.append(mode)
        return self._payload


class TestExecuteDumpableConversion:
    @pytest.mark.asyncio
    async def test_plain_dict_body_passes_through_unchanged(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        """A dict json= body reaches the HTTP client untouched (catches: over-eager conversion)."""
        rsps.add(responses.POST, f"{_BASE}/users", json={"ok": True})
        body = {"primary_id": "jdoe", "first_name": "Jane"}

        await client.execute("POST", "/users", parser="json", json=body)

        assert json.loads(rsps.calls[0].request.body) == body

    @pytest.mark.asyncio
    async def test_dumpable_body_is_converted_via_dump_json(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        """A Dumpable json= body is serialized via .dump(mode="json") before sending."""
        rsps.add(responses.POST, f"{_BASE}/users", json={"ok": True})
        payload = {"primary_id": "jdoe", "first_name": "Jane"}
        model = _FakeModel(payload)

        await client.execute("POST", "/users", parser="json", json=model)

        assert json.loads(rsps.calls[0].request.body) == payload
        assert model.dump_modes == ["json"]

    @pytest.mark.asyncio
    async def test_dumpable_converted_once_before_retry_loop(self, rsps: NiquestsMock) -> None:
        """.dump() runs exactly once even when the request retries (catches: per-attempt dump)."""
        client = AlmaClient("test-api-key", retry_attempts=3)
        rsps.add(responses.POST, f"{_BASE}/users", body=niquests.ConnectionError("refused"))
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()
        model = _FakeModel({"primary_id": "jdoe"})

        with pytest.raises(niquests.ConnectionError):
            await client.execute("POST", "/users", parser="json", json=model)

        assert len(rsps.calls) == 3
        assert model.dump_modes == ["json"]


class TestRawBodyWrites:
    """Raw XML body writes must reach niquests via data=, not content=.

    niquests.request() has no content= parameter (that is httpx terminology);
    passing it raises TypeError before any request is sent. These tests drive
    the full namespace -> execute -> niquests.request path so the wrong kwarg
    name surfaces as a failure rather than only at runtime against live Alma.
    """

    _XML = "<holding><record>data</record></holding>"

    @pytest.mark.asyncio
    async def test_update_holding_sends_raw_body(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(
            responses.PUT,
            f"{_BASE}/bibs/99/holdings/22",
            body=self._XML,
            content_type="application/xml",
        )

        result = await client.bibs.update_holding("99", "22", self._XML)

        assert result == self._XML
        assert rsps.calls[0].request.body == self._XML

    @pytest.mark.asyncio
    async def test_create_holding_sends_raw_body(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(
            responses.POST,
            f"{_BASE}/bibs/99/holdings",
            body=self._XML,
            content_type="application/xml",
        )

        result = await client.bibs.create_holding("99", self._XML)

        assert result == self._XML
        assert rsps.calls[0].request.body == self._XML
