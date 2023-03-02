"""An API wrapper library for Ex Libris' Alma"""
from typing import Any, Dict

import asyncio

import httpx
from loguru import logger

from almapy.analytics import SubClientAnalytics
from almapy.bibs import SubClientBibs
from almapy.config import SubClientConfig
from almapy.users import SubClientUsers
from almapy.utils import ArgError

logger.disable("almapy")


class AlmaClient:
    def __init__(self, apikey: str, location: str = "Europe", rate_limit: int = 20) -> None:
        self.rate_limit = rate_limit
        self.con_params: Dict[str, Any] = {"headers": {"Accept": "application/json"}}

        locations: Dict[str, str] = {
            "America": "https://api-na.hosted.exlibrisgroup.com",
            "Europe": "https://api-eu.hosted.exlibrisgroup.com",
            "Asia Pacific": "https://api-ap.hosted.exlibrisgroup.com",
            "Canada": "https://api-ca.hosted.exlibrisgroup.com",
            "China": "https://api-cn.hosted.exlibrisgroup.com",
        }
        if location not in locations.keys():
            raise ArgError(msg=f'Invalid location. Must be one of {", ".join(locations.keys())}.')
        self.con_params["location"] = location
        self.con_params["headers"] = {
            "Accept": "application/json",
            "Authorization": f"apikey {apikey}",
        }
        self.con_params["base_url"] = locations[location]

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=200, keepalive_expiry=120)

        self.session = httpx.AsyncClient(
            headers=self.con_params["headers"], limits=limits, timeout=60, follow_redirects=True
        )

        self.users = SubClientUsers(self.session, self.con_params, self.rate_limit)
        self.config = SubClientConfig(self.session, self.con_params, self.rate_limit)
        self.bibs = SubClientBibs(self.session, self.con_params, self.rate_limit)
        self.analytics = SubClientAnalytics(self.session, self.con_params, self.rate_limit)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.sleep(1)
        await self.session.aclose()
        if exc_val:
            raise exc_val
        else:
            return False

    def __del__(self):
        # Close connection when this client is destroyed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.session.aclose())
            else:
                loop.run_until_complete(self.session.aclose())
        except Exception:
            pass
