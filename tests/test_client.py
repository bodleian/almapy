"""Tests for AlmaClient.execute and _parse."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from box import Box

from almapy import AlmaClient, exceptions


def _make_response(
    status_code: int, body: str = "", content_type: str = "application/json"
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers={"Content-Type": content_type},
        content=body.encode(),
    )


@pytest.fixture
def mock_http() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def client(mock_http: AsyncMock) -> AlmaClient:
    return AlmaClient("test-api-key", client=mock_http)


class TestExecuteOutcomeRecording:
    @pytest.mark.asyncio
    async def test_success_calls_record_success(
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        mock_http.request.return_value = _make_response(200, '{"foo": "bar"}')
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        await client.execute("GET", "/users", parser="json")

        client._controller.record_success.assert_called_once()
        client._controller.record_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_retryable_error_calls_record_failure(
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        mock_http.request.side_effect = httpx.ConnectError("refused")
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(httpx.ConnectError):
            await client.execute("GET", "/users", parser="json")

        # retry_attempts=3: ConnectError is retryable, record_failure called once per attempt
        assert client._controller.record_failure.call_count == 3
        client._controller.record_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_retryable_4xx_does_not_call_record_failure(
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        import json

        body = json.dumps({
            "errorList": {"error": [{"errorCode": "401861", "errorMessage": "User not found."}]}
        })
        mock_http.request.return_value = _make_response(404, body)
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(exceptions.UserNotFoundError) as exc_info:
            await client.execute("GET", "/users/jsmith", parser="json")

        assert exc_info.value.user_id == ""
        client._controller.record_failure.assert_not_called()
        client._controller.record_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_5xx_calls_record_failure(self, client: AlmaClient, mock_http: AsyncMock) -> None:
        import json

        body = json.dumps({
            "errorList": {"error": [{"errorCode": "500", "errorMessage": "Server error"}]}
        })
        mock_http.request.return_value = _make_response(500, body)
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

    @pytest.mark.asyncio
    async def test_aclose_closes_owned_client(self) -> None:
        # AlmaClient without external client owns its httpx instance
        client = AlmaClient("test-api-key")
        assert client._owns_client is True
        await client.aclose()
        assert client._http.is_closed

    @pytest.mark.asyncio
    async def test_aclose_does_not_close_external_client(
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        # Fixture injects mock_http → AlmaClient does NOT own it
        assert client._owns_client is False
        await client.aclose()
        mock_http.aclose.assert_not_called()

    @pytest.mark.asyncio
    async def test_context_manager_closes_owned_client_on_exit(self) -> None:
        client = AlmaClient("test-api-key")
        async with client:
            pass
        assert client._http.is_closed

    @pytest.mark.asyncio
    async def test_execute_retries_correct_number_of_times(self, mock_http: AsyncMock) -> None:
        # Use retry_attempts=2 for speed (avoids multi-second backoff from 3 attempts)
        client = AlmaClient("test-api-key", client=mock_http, retry_attempts=2)
        mock_http.request.side_effect = httpx.ConnectError("refused")
        client._controller = MagicMock()
        client._controller.acquire = AsyncMock()

        with pytest.raises(httpx.ConnectError):
            await client.execute("GET", "/users", parser="json")

        # retry_attempts=2: httpx.request called exactly 2 times
        assert mock_http.request.call_count == 2


class TestExecuteModelValidation:
    @pytest.mark.asyncio
    async def test_model_none_returns_box(self, client: AlmaClient, mock_http: AsyncMock) -> None:
        mock_http.request.return_value = _make_response(200, '{"foo": "bar"}')
        result = await client.execute("GET", "/users", parser="json", model=None)
        assert isinstance(result, Box)
        assert result.foo == "bar"

    @pytest.mark.asyncio
    async def test_model_provided_calls_model_validate(
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        mock_http.request.return_value = _make_response(200, '{"foo": "bar"}')
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
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        mock_http.request.return_value = _make_response(200, '{"foo": "bar"}')
        mock_model = MagicMock()
        mock_model.model_validate.side_effect = ValueError("bad data")

        with pytest.raises(ValueError, match="bad data"):
            await client.execute("GET", "/users", parser="json", model=mock_model)

    @pytest.mark.asyncio
    async def test_model_receives_empty_box_on_no_content(
        self, client: AlmaClient, mock_http: AsyncMock
    ) -> None:
        """204 No Content → Box() is passed to model_validate (not skipped)."""
        mock_http.request.return_value = _make_response(204, "")
        mock_model = MagicMock()
        mock_model.model_validate.return_value = "empty_model"

        result: str = await client.execute("GET", "/users", parser="json", model=mock_model)

        assert result == "empty_model"
        call_arg = mock_model.model_validate.call_args[0][0]
        assert isinstance(call_arg, Box)
        assert len(call_arg) == 0
