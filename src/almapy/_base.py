"""Base namespace for Alma API client namespaces."""

from collections.abc import Mapping
from typing import Any, Literal, Protocol

from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE

Parser = Literal["json", "xml", "none", "text"]


class _AlmaExecutable(Protocol):
    """Protocol for the execute method AlmaClient provides."""

    async def _execute(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        **kwargs: Any,
    ) -> RESP_TYPE: ...


class BaseNamespace:  # noqa: B903
    """Base class for AlmaClient namespace objects.

    Replaces GracyNamespace. Owns URL building via AlmaEndpoint.build() and
    delegates HTTP execution to AlmaClient._execute().
    """

    __slots__ = ("_client",)

    def __init__(self, client: _AlmaExecutable) -> None:
        self._client = client

    async def _get(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> RESP_TYPE:
        return await self._client._execute("GET", endpoint.build(path), parser=parser, **kwargs)

    async def _post(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> RESP_TYPE:
        return await self._client._execute("POST", endpoint.build(path), parser=parser, **kwargs)

    async def _put(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> RESP_TYPE:
        return await self._client._execute("PUT", endpoint.build(path), parser=parser, **kwargs)

    async def _delete(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> RESP_TYPE:
        return await self._client._execute("DELETE", endpoint.build(path), parser=parser, **kwargs)

    async def _get_text(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """GET returning raw response text (e.g., MARC XML records)."""
        result = await self._get(endpoint, path, parser="text", **kwargs)
        text: str = result["_text"]
        return text

    async def _post_text(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """POST returning raw response text."""
        result = await self._post(endpoint, path, parser="text", **kwargs)
        text: str = result["_text"]
        return text

    async def _put_text(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """PUT returning raw response text."""
        result = await self._put(endpoint, path, parser="text", **kwargs)
        text: str = result["_text"]
        return text
