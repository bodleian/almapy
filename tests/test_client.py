"""Tests for AlmaClient.execute and _parse."""

import json
import logging
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import niquests
import pytest
from box import Box
from niquests.structures import CaseInsensitiveDict
from niquests_mock import MockRouter, build_response

from almapy import AlmaClient, exceptions

_BASE = "https://api-eu.hosted.exlibrisgroup.com/almaws/v1"


def _responder_sequence(
    *specs: dict[str, Any],
) -> Callable[[niquests.PreparedRequest], niquests.Response]:
    """side_effect that returns each response spec in turn, repeating the last.

    niquests-mock has no response queue, so sequential per-attempt responses
    (e.g. 500 then 200 across a retry) are modelled with a stateful responder.
    """
    state = {"i": 0}

    def responder(request: niquests.PreparedRequest) -> niquests.Response:
        spec = specs[min(state["i"], len(specs) - 1)]
        state["i"] += 1
        return build_response(request, **spec)

    return responder


def _make_response(
    status_code: int, body: str = "", content_type: str = "application/json"
) -> niquests.Response:
    """Build a niquests.Response for use in _parse() unit tests only.

    Not for execute() tests — use the niquests_mock fixture to register URLs instead.
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
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(f"{_BASE}/users").respond(json={"foo": "bar"})
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        await client.execute("GET", "/users", parser="json")

        client._controller.record_success.assert_called_once()
        client._controller.record_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_retryable_error_calls_record_failure(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(f"{_BASE}/users").mock(side_effect=niquests.ConnectionError("refused"))
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(niquests.ConnectionError):
            await client.execute("GET", "/users", parser="json")

        # retry_attempts=3: ConnectionError is retryable, record_failure called once per attempt
        assert client._controller.record_failure.call_count == 3
        client._controller.record_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_retryable_4xx_does_not_call_record_failure(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        body = json.dumps({
            "errorList": {"error": [{"errorCode": "401861", "errorMessage": "User not found."}]}
        })
        niquests_mock.get(f"{_BASE}/users/jsmith").respond(status_code=404, json=json.loads(body))
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            await client.execute("GET", "/users/jsmith", parser="json")

        assert exc_info.value.user_id == ""
        client._controller.record_failure.assert_not_called()
        client._controller.record_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_5xx_calls_record_failure(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(f"{_BASE}/users").respond(
            status_code=500,
            json={"errorList": {"error": [{"errorCode": "500", "errorMessage": "Server error"}]}},
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
        """Uses a real session: AsyncMock(spec=...) accepts any attribute and so
        hid the fact that an injected session was never configured at all."""
        session = niquests.AsyncSession()
        session.close = AsyncMock()  # type: ignore[method-assign]
        client = AlmaClient("test-api-key", client=session)
        assert client._owns_client is False
        await client.aclose()
        session.close.assert_not_called()
        assert client._closed is False

    @pytest.mark.asyncio
    async def test_context_manager_closes_owned_client_on_exit(self) -> None:
        client = AlmaClient("test-api-key")
        async with client:
            pass
        assert client._closed is True

    @pytest.mark.asyncio
    async def test_execute_retries_correct_number_of_times(self, niquests_mock: MockRouter) -> None:
        client = AlmaClient("test-api-key", retry_attempts=2)
        niquests_mock.get(f"{_BASE}/users").mock(side_effect=niquests.ConnectionError("refused"))
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(niquests.ConnectionError):
            await client.execute("GET", "/users", parser="json")

        assert len(niquests_mock.calls) == 2


class TestExecuteModelValidation:
    @pytest.mark.asyncio
    async def test_model_none_returns_box(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(f"{_BASE}/users").respond(json={"foo": "bar"})
        result = await client.execute("GET", "/users", parser="json", model=None)
        assert isinstance(result, Box)
        assert result.foo == "bar"

    @pytest.mark.asyncio
    async def test_model_provided_calls_model_validate(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(f"{_BASE}/users").respond(json={"foo": "bar"})
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
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(f"{_BASE}/users").respond(json={"foo": "bar"})
        mock_model = MagicMock()
        mock_model.model_validate.side_effect = ValueError("bad data")

        with pytest.raises(ValueError, match="bad data"):
            await client.execute("GET", "/users", parser="json", model=mock_model)

    @pytest.mark.asyncio
    async def test_model_receives_empty_box_on_no_content(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """204 No Content → Box() is passed to model_validate (not skipped)."""
        niquests_mock.get(f"{_BASE}/users").respond(status_code=204)
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
        self, client: AlmaClient, niquests_mock: MockRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """almapy.http emits exactly 2 DEBUG records per successful request."""
        niquests_mock.get(f"{_BASE}/users").respond(json={"foo": "bar"})
        with caplog.at_level(logging.DEBUG, logger="almapy.http"):
            await client.execute("GET", "/users", parser="json")
        records = [r for r in caplog.records if r.name == "almapy.http"]
        assert len(records) == 2
        assert "GET" in records[0].message and "/users" in records[0].message
        assert "200" in records[1].message

    @pytest.mark.asyncio
    async def test_log_records_carry_req_id(
        self, client: AlmaClient, niquests_mock: MockRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Every log record emitted inside execute() must have a non-empty req_id."""
        niquests_mock.get(f"{_BASE}/users").respond(json={"foo": "bar"})
        with caplog.at_level(logging.DEBUG, logger="almapy.http"):
            await client.execute("GET", "/users", parser="json")
        for record in caplog.records:
            assert hasattr(record, "req_id"), f"Missing req_id on {record.name} record"
            assert getattr(record, "req_id", "") != "", "req_id must be non-empty inside execute()"

    @pytest.mark.asyncio
    async def test_req_ids_are_unique_across_calls(
        self, client: AlmaClient, niquests_mock: MockRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Each execute() call must generate a distinct req_id."""
        niquests_mock.get(f"{_BASE}/users/1").respond(json={"foo": "bar"})
        niquests_mock.get(f"{_BASE}/users/2").respond(json={"foo": "bar"})
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
        self, niquests_mock: MockRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """almapy.retry emits a WARNING on retry (not on first attempt)."""
        client = AlmaClient("test-api-key", retry_attempts=2)
        niquests_mock.get(f"{_BASE}/bibs/123").mock(
            side_effect=_responder_sequence(
                {
                    "status_code": 500,
                    "json": {
                        "errorList": {
                            "error": [{"errorCode": "500", "errorMessage": "Server error"}]
                        }
                    },
                },
                {"status_code": 200, "json": {"ok": True}},
            )
        )
        with caplog.at_level(logging.WARNING, logger="almapy.retry"):
            await client.execute("GET", "/bibs/123", parser="json")
        retry_records = [r for r in caplog.records if r.name == "almapy.retry"]
        assert len(retry_records) == 1
        assert "Retry 2/" in retry_records[0].message
        assert "APIServerError" in retry_records[0].message

    @pytest.mark.asyncio
    async def test_stamina_retry_logger_is_suppressed(
        self, niquests_mock: MockRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Retry logging must come from almapy.retry only, never stamina."""
        client = AlmaClient("test-api-key", retry_attempts=2)
        niquests_mock.get(f"{_BASE}/bibs/123").mock(
            side_effect=_responder_sequence(
                {
                    "status_code": 500,
                    "json": {
                        "errorList": {
                            "error": [{"errorCode": "500", "errorMessage": "Server error"}]
                        }
                    },
                },
                {"status_code": 200, "json": {"ok": True}},
            )
        )

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
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """A dict json= body reaches the HTTP client untouched (catches: over-eager conversion)."""
        niquests_mock.post(f"{_BASE}/users").respond(json={"ok": True})
        body = {"primary_id": "jdoe", "first_name": "Jane"}

        await client.execute("POST", "/users", parser="json", json=body)

        sent = niquests_mock.calls[0].request.body
        assert isinstance(sent, bytes)
        assert json.loads(sent) == body

    @pytest.mark.asyncio
    async def test_dumpable_body_is_converted_via_dump_json(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """A Dumpable json= body is serialized via .dump(mode="json") before sending."""
        niquests_mock.post(f"{_BASE}/users").respond(json={"ok": True})
        payload = {"primary_id": "jdoe", "first_name": "Jane"}
        model = _FakeModel(payload)

        await client.execute("POST", "/users", parser="json", json=model)

        sent = niquests_mock.calls[0].request.body
        assert isinstance(sent, bytes)
        assert json.loads(sent) == payload
        assert model.dump_modes == ["json"]

    @pytest.mark.asyncio
    async def test_dumpable_converted_once_before_retry_loop(
        self, niquests_mock: MockRouter
    ) -> None:
        """.dump() runs exactly once even when the request retries (catches: per-attempt dump).

        Uses a 429, the one failure a POST is still replayed on — a connection
        error or 5xx on a write is deliberately not retried.
        """
        client = AlmaClient("test-api-key", retry_attempts=3)
        niquests_mock.post(f"{_BASE}/users").respond(
            status_code=429,
            json={"errorList": {"error": [{"errorCode": "TOO_MANY", "errorMessage": "slow down"}]}},
        )
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()
        model = _FakeModel({"primary_id": "jdoe"})

        with pytest.raises(exceptions.ThresholdError):
            await client.execute("POST", "/users", parser="json", json=model)

        assert len(niquests_mock.calls) == 3
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
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.put(f"{_BASE}/bibs/99/holdings/22").respond(
            content=self._XML, headers={"Content-Type": "application/xml"}
        )

        result = await client.bibs.update_holding("99", "22", self._XML)

        assert result == self._XML
        assert niquests_mock.calls[0].request.body == self._XML

    @pytest.mark.asyncio
    async def test_create_holding_sends_raw_body(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.post(f"{_BASE}/bibs/99/holdings").respond(
            content=self._XML, headers={"Content-Type": "application/xml"}
        )

        result = await client.bibs.create_holding("99", self._XML)

        assert result == self._XML
        assert niquests_mock.calls[0].request.body == self._XML


class TestWriteRetryPolicy:
    """Non-idempotent verbs must not be replayed on ambiguous failures.

    A read timeout, connection error or 5xx on a POST usually means Alma applied
    the write and the response was lost, so a replay creates a second loan,
    request or PO line. Only failures that prove the request never landed — a
    429 rejection or a connect timeout — stay retryable for writes.
    """

    @staticmethod
    def _mocked(attempts: int = 3) -> AlmaClient:
        client = AlmaClient("test-api-key", retry_attempts=attempts)
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()
        return client

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["POST", "PATCH"])
    async def test_write_not_retried_on_connection_error(
        self, niquests_mock: MockRouter, method: str
    ) -> None:
        client = self._mocked()
        niquests_mock.request(method, f"{_BASE}/users").mock(
            side_effect=niquests.ConnectionError("reset")
        )

        with pytest.raises(niquests.ConnectionError):
            await client.execute(method, "/users", parser="json")

        assert len(niquests_mock.calls) == 1

    @pytest.mark.asyncio
    async def test_write_not_retried_on_read_timeout(self, niquests_mock: MockRouter) -> None:
        """The dangerous case: Alma created the record, the response never arrived."""
        client = self._mocked()
        niquests_mock.post(f"{_BASE}/users").mock(side_effect=niquests.ReadTimeout("timed out"))

        with pytest.raises(niquests.ReadTimeout):
            await client.execute("POST", "/users", parser="json")

        assert len(niquests_mock.calls) == 1

    @pytest.mark.asyncio
    async def test_write_not_retried_on_server_error(self, niquests_mock: MockRouter) -> None:
        client = self._mocked()
        niquests_mock.post(f"{_BASE}/users").respond(
            status_code=500,
            json={"errorList": {"error": [{"errorCode": "500", "errorMessage": "boom"}]}},
        )

        with pytest.raises(exceptions.APIServerError):
            await client.execute("POST", "/users", parser="json")

        assert len(niquests_mock.calls) == 1

    @pytest.mark.asyncio
    async def test_write_still_retried_on_429(self, niquests_mock: MockRouter) -> None:
        """A 429 is a gateway rejection — Alma never saw the body, so replay is safe."""
        client = self._mocked()
        niquests_mock.post(f"{_BASE}/users").respond(
            status_code=429,
            json={"errorList": {"error": [{"errorCode": "TOO_MANY", "errorMessage": "slow down"}]}},
        )

        with pytest.raises(exceptions.ThresholdError):
            await client.execute("POST", "/users", parser="json")

        assert len(niquests_mock.calls) == 3

    @pytest.mark.asyncio
    async def test_write_still_retried_on_connect_timeout(self, niquests_mock: MockRouter) -> None:
        """No connection was established, so the request cannot have been applied."""
        client = self._mocked()
        niquests_mock.post(f"{_BASE}/users").mock(side_effect=niquests.ConnectTimeout("no route"))

        with pytest.raises(niquests.ConnectTimeout):
            await client.execute("POST", "/users", parser="json")

        assert len(niquests_mock.calls) == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
    async def test_idempotent_methods_still_retry(
        self, niquests_mock: MockRouter, method: str
    ) -> None:
        client = self._mocked()
        niquests_mock.request(method, f"{_BASE}/users").mock(
            side_effect=niquests.ConnectionError("reset")
        )

        with pytest.raises(niquests.ConnectionError):
            await client.execute(method, "/users", parser="json")

        assert len(niquests_mock.calls) == 3

    @pytest.mark.asyncio
    async def test_retry_true_opts_a_write_back_in(self, niquests_mock: MockRouter) -> None:
        client = self._mocked()
        niquests_mock.post(f"{_BASE}/users").mock(side_effect=niquests.ConnectionError("reset"))

        with pytest.raises(niquests.ConnectionError):
            await client.execute("POST", "/users", parser="json", retry=True)

        assert len(niquests_mock.calls) == 3

    @pytest.mark.asyncio
    async def test_retry_false_disables_retries_for_a_read(self, niquests_mock: MockRouter) -> None:
        client = self._mocked()
        niquests_mock.get(f"{_BASE}/users").mock(side_effect=niquests.ConnectionError("reset"))

        with pytest.raises(niquests.ConnectionError):
            await client.execute("GET", "/users", parser="json", retry=False)

        assert len(niquests_mock.calls) == 1

    @pytest.mark.asyncio
    async def test_backpressure_still_records_failure_for_unretried_write(
        self, niquests_mock: MockRouter
    ) -> None:
        """Not replaying the request must not blind the adaptive rate limiter."""
        client = AlmaClient("test-api-key", retry_attempts=3)
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()
        niquests_mock.post(f"{_BASE}/users").respond(
            status_code=500,
            json={"errorList": {"error": [{"errorCode": "500", "errorMessage": "boom"}]}},
        )

        with pytest.raises(exceptions.APIServerError):
            await client.execute("POST", "/users", parser="json")

        assert client._controller.record_failure.call_count == 1


class TestModelDumpBodies:
    """A plain pydantic-shaped model works as a request body with no dump() shim.

    Reads call model_validate(), which pydantic provides natively; writes call
    dump(), which it does not. Accepting model_dump() removes that asymmetry.
    """

    class _PydanticShaped:
        """Exposes only model_dump(), exactly as pydantic v2 does."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload
            self.modes: list[str] = []

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            self.modes.append(mode)
            return self._payload

    @pytest.mark.asyncio
    async def test_model_dump_body_is_sent_as_json(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.post(f"{_BASE}/users").respond(json={"ok": True})
        payload = {"primary_id": "jdoe", "first_name": "Jane"}
        model = self._PydanticShaped(payload)

        await client.execute("POST", "/users", parser="json", json=model)

        sent = niquests_mock.calls[0].request.body
        assert isinstance(sent, bytes)
        assert json.loads(sent) == payload
        assert model.modes == ["json"]

    @pytest.mark.asyncio
    async def test_dict_body_is_untouched(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """_dump_body is now called for every json= body, so dicts must pass through."""
        niquests_mock.post(f"{_BASE}/users").respond(json={"ok": True})
        payload = {"primary_id": "jdoe"}

        await client.execute("POST", "/users", parser="json", json=payload)

        sent = niquests_mock.calls[0].request.body
        assert isinstance(sent, bytes)
        assert json.loads(sent) == payload

    @pytest.mark.asyncio
    async def test_box_body_is_untouched(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """config.sets.create takes a Box; it satisfies neither protocol."""
        niquests_mock.post(f"{_BASE}/conf/sets").respond(json={"ok": True})

        await client.config.sets.create(Box({"name": "a set"}))

        sent = niquests_mock.calls[0].request.body
        assert isinstance(sent, bytes)
        assert json.loads(sent) == {"name": "a set"}


class TestInjectedSession:
    """A session passed via client= must be usable, not just stored.

    Endpoints are relative paths, so an unconfigured injected session made every
    call fail with MissingSchema. The original test used AsyncMock(spec=...),
    which accepts any URL and so never exercised this.
    """

    @pytest.mark.asyncio
    async def test_bare_session_is_configured_and_works(self, niquests_mock: MockRouter) -> None:
        client = AlmaClient("my-key", client=niquests.AsyncSession())

        assert client._http.base_url == _BASE
        assert client._http.headers["Authorization"] == "apikey my-key"

        niquests_mock.get(path="/almaws/v1/users/jsmith").respond(json={"primary_id": "jsmith"})
        resp = await client.users.get_user("jsmith")

        assert resp.primary_id == "jsmith"
        url = niquests_mock.calls[-1].request.url
        assert url is not None and url.startswith(_BASE)

    @pytest.mark.asyncio
    async def test_preconfigured_session_keeps_its_own_values(self) -> None:
        """Overriding these would defeat the purpose of injecting a session."""
        session = niquests.AsyncSession(base_url="https://example.test/v1")
        session.headers["Authorization"] = "apikey caller-supplied"

        client = AlmaClient("my-key", client=session)

        assert client._http.base_url == "https://example.test/v1"
        assert client._http.headers["Authorization"] == "apikey caller-supplied"

    @pytest.mark.asyncio
    async def test_injected_session_location_is_respected(self) -> None:
        client = AlmaClient("my-key", location="America", client=niquests.AsyncSession())
        assert client._http.base_url == "https://api-na.hosted.exlibrisgroup.com/almaws/v1"
