"""Alma API client — composed architecture, no gracy dependency."""

import asyncio
from http import HTTPStatus
from typing import Any, Literal

import httpx
import stamina
from box import Box

from almapy._acq import AlmaClientAcqNS
from almapy._analytics import AlmaClientAnalyticsNS
from almapy._base import Parser
from almapy._bibs import AlmaClientBibNS
from almapy._config import AlmaClientConfigNS
from almapy._throttle import AdaptiveController, TokenBucket
from almapy._users import AlmaClientUserNS
from almapy._utils import _RETRYABLE, RESP_TYPE, _parse_xml, _validate_response

_LOCATIONS: dict[str, str] = {
    "America": "https://api-na.hosted.exlibrisgroup.com",
    "Europe": "https://api-eu.hosted.exlibrisgroup.com",
    "Asia Pacific": "https://api-ap.hosted.exlibrisgroup.com",
    "Canada": "https://api-ca.hosted.exlibrisgroup.com",
    "China": "https://api-cn.hosted.exlibrisgroup.com",
}


class AlmaClient:
    """Async API wrapper for the Alma library management system.

    Composed of: httpx.AsyncClient (transport), TokenBucket (rate limiting),
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
        client: httpx.AsyncClient | None = None,
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

        if client is None:
            self._http = httpx.AsyncClient(
                base_url=_LOCATIONS[location] + "/almaws/v1",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"apikey {apikey}",
                },
                follow_redirects=True,
                timeout=httpx.Timeout(30, connect=30, read=90, pool=120),
            )
            self._owns_client = True
        else:
            self._http = client
            self._owns_client = False

        self.users: AlmaClientUserNS = AlmaClientUserNS(self)
        self.bibs: AlmaClientBibNS = AlmaClientBibNS(self)
        self.acq: AlmaClientAcqNS = AlmaClientAcqNS(self)
        self.config: AlmaClientConfigNS = AlmaClientConfigNS(self)
        self.analytics: AlmaClientAnalyticsNS = AlmaClientAnalyticsNS(self)

    async def _execute(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        **kwargs: Any,
    ) -> RESP_TYPE:
        """Semaphore → controller acquire → stamina retries → record outcome."""
        async with self._semaphore:
            await self._controller.acquire()
            try:
                result = await self._raw_request(method, url, parser=parser, **kwargs)
            except Exception:
                self._controller.record_failure()
                raise
            else:
                self._controller.record_success()
                return result

    async def _raw_request(
        self,
        method: str,
        url: str,
        *,
        parser: Parser,
        **kwargs: Any,
    ) -> RESP_TYPE:
        """HTTP request with stamina retries; validate + parse inside retry loop."""
        result: RESP_TYPE | None = None
        async for attempt in stamina.retry_context(
            on=_RETRYABLE,
            attempts=self._retry_attempts,
            timeout=None,
            wait_initial=0.5,
            wait_max=30.0,
            wait_jitter=1.0,
            wait_exp_base=4,
        ):
            with attempt:
                resp = await self._http.request(method, url, **kwargs)
                _validate_response(resp)
                result = self._parse(resp, parser)
        if result is None:
            msg = "stamina made zero attempts"  # unreachable
            raise RuntimeError(msg)
        return result

    def _parse(self, response: httpx.Response, parser: Parser) -> RESP_TYPE:
        """Parse an httpx response according to the requested parser."""
        if parser == "none" or response.status_code == HTTPStatus.NO_CONTENT:
            return Box()
        if parser == "xml":
            return Box(_parse_xml(response.text))
        if parser == "text":
            return Box({"_text": response.text})
        return Box(response.json())

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> "AlmaClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
