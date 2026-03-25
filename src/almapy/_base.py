"""Base namespace for Alma API client namespaces."""

from collections.abc import Mapping
from typing import Any, Literal, Protocol, cast, overload

from almapy._endpoints import AlmaEndpoint
from almapy._utils import RESP_TYPE, _ModelT

Parser = Literal["json", "xml", "none", "text"]


class _AlmaExecutable(Protocol):
    """Protocol for the execute method AlmaClient provides."""

    @overload
    async def execute(
        self, method: str, url: str, *, parser: Parser, model: type[_ModelT], **kwargs: Any
    ) -> _ModelT: ...

    @overload
    async def execute(
        self, method: str, url: str, *, parser: Parser, model: None = ..., **kwargs: Any
    ) -> RESP_TYPE: ...

    async def execute(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        model: Any = None,
        **kwargs: Any,
    ) -> Any: ...


class BaseNamespace:  # noqa: B903
    """Base class for AlmaClient namespace objects.

    Replaces GracyNamespace. Owns URL building via AlmaEndpoint.build() and
    delegates HTTP execution to AlmaClient.execute().
    """

    def __init__(self, client: _AlmaExecutable) -> None:
        self._client = client

    @overload
    async def _get(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: type[_ModelT],
        parser: Parser = ...,
        **kwargs: Any,
    ) -> _ModelT: ...

    @overload
    async def _get(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: None = ...,
        parser: Parser = ...,
        **kwargs: Any,
    ) -> RESP_TYPE: ...

    async def _get(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: Any = None,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> Any:
        return await self._client.execute(
            "GET", endpoint.build(path), parser=parser, model=model, **kwargs
        )

    @overload
    async def _post(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: type[_ModelT],
        parser: Parser = ...,
        **kwargs: Any,
    ) -> _ModelT: ...

    @overload
    async def _post(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: None = ...,
        parser: Parser = ...,
        **kwargs: Any,
    ) -> RESP_TYPE: ...

    async def _post(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: Any = None,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> Any:
        return await self._client.execute(
            "POST", endpoint.build(path), parser=parser, model=model, **kwargs
        )

    @overload
    async def _put(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: type[_ModelT],
        parser: Parser = ...,
        **kwargs: Any,
    ) -> _ModelT: ...

    @overload
    async def _put(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: None = ...,
        parser: Parser = ...,
        **kwargs: Any,
    ) -> RESP_TYPE: ...

    async def _put(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: Any = None,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> Any:
        return await self._client.execute(
            "PUT", endpoint.build(path), parser=parser, model=model, **kwargs
        )

    @overload
    async def _delete(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: type[_ModelT],
        parser: Parser = ...,
        **kwargs: Any,
    ) -> _ModelT: ...

    @overload
    async def _delete(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: None = ...,
        parser: Parser = ...,
        **kwargs: Any,
    ) -> RESP_TYPE: ...

    async def _delete(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        *,
        model: Any = None,
        parser: Parser = "json",
        **kwargs: Any,
    ) -> Any:
        return await self._client.execute(
            "DELETE", endpoint.build(path), parser=parser, model=model, **kwargs
        )

    async def _get_text(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """GET returning raw response text (e.g., MARC XML records)."""
        result: Any = await self._get(endpoint, path, parser="text", **kwargs)
        return cast(str, result)

    async def _post_text(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """POST returning raw response text."""
        result: Any = await self._post(endpoint, path, parser="text", **kwargs)
        return cast(str, result)

    async def _put_text(
        self,
        endpoint: AlmaEndpoint,
        path: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """PUT returning raw response text."""
        result: Any = await self._put(endpoint, path, parser="text", **kwargs)
        return cast(str, result)
