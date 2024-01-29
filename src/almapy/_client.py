from __future__ import annotations

import logging
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal

from box import Box
from gracy import (
    ConcurrentRequestLimit,
    GracefulRetry,
    GracefulThrottle,
    Gracy,
    GracyConfig,
    LogEvent,
    LogLevel,
    ThrottleRule,
)
from httpx import (
    URL,
    Headers,
    Limits,
    Timeout,
    TimeoutException,
)

from almapy._acq import AlmaClientAcqNS  # noqa: TCH001
from almapy._analytics import AlmaClientAnalyticsNS  # noqa: TCH001
from almapy._bibs import AlmaClientBibNS  # noqa: TCH001
from almapy._config import AlmaClientConfigNS  # noqa: TCH001
from almapy._endpoints import AlmaEndpoint
from almapy._users import AlmaClientUserNS  # noqa: TCH001
from almapy._utils import AlmaErrorValidator
from almapy.exceptions import APIServerError, ThresholdError

if TYPE_CHECKING:
    import httpx
    from gracy import GracyReplay

logging.getLogger("httpx").setLevel(logging.CRITICAL)


class AlmaClient(Gracy[AlmaEndpoint]):
    """An API wrapper client for Alma."""

    class Config:
        BASE_URL = ""  # We set it dynamically instead, based on country.
        REQUEST_TIMEOUT = 60.0
        SETTINGS = GracyConfig(
            allowed_status_code={
                HTTPStatus.BAD_REQUEST,
                HTTPStatus.NOT_FOUND,
                HTTPStatus.FOUND,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                HTTPStatus.BAD_GATEWAY,
                HTTPStatus.SERVICE_UNAVAILABLE,
                HTTPStatus.GATEWAY_TIMEOUT,
                HTTPStatus.TOO_MANY_REQUESTS,
            },
            parser={
                HTTPStatus.OK: lambda resp: Box(resp.json()),
            },
            retry=GracefulRetry(
                delay=1,
                max_attempts=5,
                delay_modifier=3,
                retry_on={
                    APIServerError,
                    ThresholdError,
                    TimeoutException,
                },
                log_before=LogEvent(LogLevel.WARNING),
                log_after=None,
                log_exhausted=LogEvent(LogLevel.ERROR),
                behavior="break",
            ),
            throttling=GracefulThrottle(
                rules=[
                    ThrottleRule(
                        url_pattern=r".*", max_requests=25, per_time_range=timedelta(seconds=1)
                    ),
                ],
            ),
            concurrent_requests=ConcurrentRequestLimit(
                limit=199,
                log_limit_reached=LogEvent(LogLevel.WARNING),
                log_limit_freed=LogEvent(LogLevel.INFO),
            ),
            validators=AlmaErrorValidator(),
        )

    def __init__(
        self,
        apikey: str,
        location: Literal["America", "Europe", "Asia Pacific", "Canada", "China"] = "Europe",
        replay: GracyReplay | None = None,
        *,
        rate_limit: int = 25,
        concurrent_requests: int = 199,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        self._apikey = apikey
        locations = {
            "America": "https://api-na.hosted.exlibrisgroup.com",
            "Europe": "https://api-eu.hosted.exlibrisgroup.com",
            "Asia Pacific": "https://api-ap.hosted.exlibrisgroup.com",
            "Canada": "https://api-ca.hosted.exlibrisgroup.com",
            "China": "https://api-cn.hosted.exlibrisgroup.com",
        }
        if location not in locations:
            msg = f'Invalid location. Must be one of {", ".join(locations.keys())}.'
            raise ValueError(msg)
        self._location_url = URL(locations[location] + "/almaws/v1")
        self.Config.SETTINGS.throttling.rules = [
            ThrottleRule(
                url_pattern=r".*", max_requests=rate_limit, per_time_range=timedelta(seconds=1)
            )
        ]
        self.Config.SETTINGS.concurrent_requests.limit = concurrent_requests
        super().__init__(replay, debug, **kwargs)

    def _create_client(self, **kwargs: Any) -> httpx.AsyncClient:
        client = super()._create_client(**kwargs)
        client.base_url = self._location_url
        client.headers = Headers({
            "Accept": "application/json",
            "Authorization": f"apikey {self._apikey}",
        })
        client.follow_redirects = True
        client.limits = Limits(
            max_keepalive_connections=20, max_connections=200, keepalive_expiry=120
        )
        client.timeout = Timeout(30, connect=60, read=120, pool=120)
        return client

    users: AlmaClientUserNS
    bibs: AlmaClientBibNS
    acq: AlmaClientAcqNS
    config: AlmaClientConfigNS
    analytics: AlmaClientAnalyticsNS
