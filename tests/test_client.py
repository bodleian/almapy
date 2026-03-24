"""Tests for AlmaClient._execute and _parse."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

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

        await client._execute("GET", "/users", parser="json")

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
            await client._execute("GET", "/users", parser="json")

        client._controller.record_failure.assert_called()
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

        with pytest.raises(exceptions.UserNotFoundError):
            await client._execute("GET", "/users/jsmith", parser="json")

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
            await client._execute("GET", "/users", parser="json")

        client._controller.record_failure.assert_called()
        client._controller.record_success.assert_not_called()


class TestParse:
    def test_json_parser(self, client: AlmaClient) -> None:
        resp = _make_response(200, '{"title": "Dune"}')
        result = client._parse(resp, "json")
        assert result.title == "Dune"

    def test_text_parser(self, client: AlmaClient) -> None:
        resp = _make_response(200, "raw text", content_type="text/plain")
        result = client._parse(resp, "text")
        assert result["_text"] == "raw text"

    def test_none_parser(self, client: AlmaClient) -> None:
        resp = _make_response(200, '{"ignored": true}')
        result = client._parse(resp, "none")
        assert result == {}

    def test_no_content_returns_empty(self, client: AlmaClient) -> None:
        resp = _make_response(204)
        result = client._parse(resp, "json")
        assert result == {}
