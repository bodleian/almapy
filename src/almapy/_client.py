"""Alma API client — composed architecture, no gracy dependency."""

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal, overload
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import niquests
import stamina
from box import Box

from almapy._acq import AlmaClientAcqNS
from almapy._analytics import AlmaClientAnalyticsNS
from almapy._base import Parser
from almapy._bibs import AlmaClientBibNS
from almapy._config import AlmaClientConfigNS
from almapy._logging import new_request_id, request_id
from almapy._primo import AlmaClientPrimoNS
from almapy._throttle import AdaptiveController, TokenBucket
from almapy._users import AlmaClientUserNS
from almapy._utils import (
    RESP_TYPE,
    Dumpable,
    _ModelT,
    _parse_xml,
    _should_retry,
    _validate_response,
)

_http_log = logging.getLogger("almapy.http")
_retry_log = logging.getLogger("almapy.retry")


def _sanitize_url(url: str) -> str:
    """Strip the ``apikey`` query parameter from a URL before logging."""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    filtered = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() != "apikey"]
    return urlunparse(parsed._replace(query=urlencode(filtered)))


_LOCATIONS: dict[str, str] = {
    "America": "https://api-na.hosted.exlibrisgroup.com",
    "Europe": "https://api-eu.hosted.exlibrisgroup.com",
    "Asia Pacific": "https://api-ap.hosted.exlibrisgroup.com",
    "Canada": "https://api-ca.hosted.exlibrisgroup.com",
    "China": "https://api-cn.hosted.exlibrisgroup.com",
}


class AlmaClient:
    """Async API wrapper for the Alma library management system.

    Composed of: niquests.AsyncSession (transport), TokenBucket (rate limiting),
    AdaptiveController (AIMD backpressure), asyncio.Semaphore (concurrency cap).
    """

    def __init__(
        self,
        apikey: str,
        location: Literal["America", "Europe", "Asia Pacific", "Canada", "China"] = "Europe",
        *,
        rate_limit: float = 25.0,
        concurrent_requests: int = 150,
        retry_attempts: int = 3,
        backoff_factor: float = 0.5,
        recovery_increment: float = 1.0,
        recovery_window: float = 10.0,
        cooldown: float = 5.0,
        max_wait: float | None = None,
        client: niquests.AsyncSession | None = None,
    ) -> None:
        if not apikey:
            msg = "apikey must be provided"
            raise ValueError(msg)
        if location not in _LOCATIONS:
            msg = f"Invalid location. Must be one of {', '.join(_LOCATIONS)}."
            raise ValueError(msg)

        self._retry_attempts = retry_attempts
        self._bucket = TokenBucket(rate=rate_limit)
        self._controller = AdaptiveController(
            bucket=self._bucket,
            max_rate=rate_limit,
            backoff_factor=backoff_factor,
            recovery_increment=recovery_increment,
            recovery_window=recovery_window,
            cooldown=cooldown,
            max_wait=max_wait,
        )
        self._semaphore = asyncio.Semaphore(concurrent_requests)
        # Regional gateway root (before the /almaws/v1 suffix) — the Primo
        # namespace targets /primo/v1 on this same host with the same key.
        self._gateway = _LOCATIONS[location]

        if client is None:
            pool_size = max(10, concurrent_requests)
            self._http = niquests.AsyncSession(
                base_url=_LOCATIONS[location] + "/almaws/v1",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"apikey {apikey}",
                },
                timeout=(30, 90),
                pool_connections=pool_size,
                pool_maxsize=pool_size,
                disable_http2=True,
                disable_http3=True,
            )
            self._owns_client = True
        else:
            self._http = client
            self._owns_client = False
        self._closed = False

        self.users: AlmaClientUserNS = AlmaClientUserNS(self)
        self.bibs: AlmaClientBibNS = AlmaClientBibNS(self)
        self.acq: AlmaClientAcqNS = AlmaClientAcqNS(self)
        self.config: AlmaClientConfigNS = AlmaClientConfigNS(self)
        self.analytics: AlmaClientAnalyticsNS = AlmaClientAnalyticsNS(self)
        self.primo: AlmaClientPrimoNS = AlmaClientPrimoNS(self)

    @overload
    async def execute(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        model: type[_ModelT],
        **kwargs: Any,
    ) -> _ModelT: ...

    @overload
    async def execute(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        model: None = ...,
        **kwargs: Any,
    ) -> RESP_TYPE: ...

    async def execute(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        model: Any = None,
        validate: Callable[[niquests.Response], None] = _validate_response,
        **kwargs: Any,
    ) -> Any:
        """Stamina retry loop; semaphore + controller acquired per attempt.

        Semaphore is released between attempts so backoff sleeps do not pin
        concurrency slots. record_failure is only called for retryable exceptions.
        """
        if isinstance(kwargs.get("json"), Dumpable):
            kwargs["json"] = kwargs["json"].dump(mode="json")
        token = request_id.set(new_request_id())
        try:
            result: Any = None
            attempt_num: int = 0
            last_exc: Exception | None = None
            async for attempt in stamina.retry_context(
                on=_should_retry,
                attempts=self._retry_attempts,
                timeout=None,
                wait_initial=0.5,
                wait_max=30.0,
                wait_jitter=1.0,
                wait_exp_base=4,
            ):
                with attempt:
                    attempt_num += 1
                    if attempt_num > 1:
                        assert last_exc is not None  # always set before attempt_num > 1
                        _retry_log.warning(
                            "Retry %d/%d: %s %s - %s",
                            attempt_num,
                            self._retry_attempts,
                            method,
                            _sanitize_url(url),
                            type(last_exc).__name__,
                            extra={
                                "req_id": request_id.get(),
                                "attempt": attempt_num,
                                "max_attempts": self._retry_attempts,
                                "exc_type": type(last_exc).__name__,
                            },
                        )
                    async with self._semaphore:
                        await self._controller.acquire()
                        start = time.monotonic()
                        safe_url = _sanitize_url(url)
                        _http_log.debug(
                            "%s %s",
                            method,
                            safe_url,
                            extra={"req_id": request_id.get(), "method": method, "url": safe_url},
                        )
                        try:
                            resp = await self._http.request(method, url, **kwargs)
                            validate(resp)
                            elapsed_ms = (time.monotonic() - start) * 1000
                            # Response log only fires on success — almapy.error covers failures
                            _http_log.debug(
                                "%s %s -> %d (%.0fms)",
                                method,
                                safe_url,
                                resp.status_code,
                                elapsed_ms,
                                extra={
                                    "req_id": request_id.get(),
                                    "method": method,
                                    "url": safe_url,
                                    "status_code": resp.status_code,
                                    "elapsed_ms": round(elapsed_ms, 1),
                                },
                            )
                            result = self._parse(resp, parser)
                            if model is not None:
                                result = model.model_validate(result)
                        except Exception as exc:
                            last_exc = exc
                            if _should_retry(exc):
                                self._controller.record_failure()
                            raise
                        else:
                            self._controller.record_success()
            if result is None:
                msg = "stamina made zero attempts"  # unreachable
                raise RuntimeError(msg)
            return result
        finally:
            request_id.reset(token)

    def __del__(self) -> None:
        """Schedule cleanup when the client is abandoned without being explicitly closed."""
        http = getattr(self, "_http", None)
        if (
            not getattr(self, "_owns_client", False)
            or http is None
            or getattr(self, "_closed", False)
        ):
            return
        with contextlib.suppress(RuntimeError):
            asyncio.get_running_loop().create_task(self.aclose())

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._http.close()
            self._closed = True

    async def __aenter__(self) -> "AlmaClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    @staticmethod
    def _parse(response: niquests.Response, parser: Parser) -> RESP_TYPE | str:
        """Parse a niquests response according to the requested parser."""
        if parser == "none" or response.status_code == HTTPStatus.NO_CONTENT:
            return Box()
        assert response.text is not None
        if parser == "xml":
            return Box(_parse_xml(response.text))
        if parser == "text":
            return response.text
        return Box(response.json())
