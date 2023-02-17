from typing import Any, Dict, Optional, Union

import httpx
from box import Box
from pyrate_limiter import Duration, Limiter, RequestRate

from almapy.utils import handle_http_error


class Client:
    def __init__(
        self,
        session: httpx.AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        self.con_params = con_params
        self.session = session
        self.rate_limit = RequestRate(rate_limit, Duration.SECOND)
        self.limiter = Limiter(self.rate_limit)

    async def __get_req__(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        xml: bool = False,
    ) -> Union[Box, str]:
        if params is None:
            params = {}
        else:
            params = {k: v for k, v in params.items() if v is not None}

        url = self.con_params["base_url"] + endpoint
        headers = {
            "Accept": f"application/{'xml' if xml else 'json'}",
        }

        async with self.limiter.ratelimit("alma", delay=True):
            r = await self.session.get(url, headers=headers, params=params)
            if r.status_code >= 400:
                handle_http_error(r)
            else:
                r.raise_for_status()

            if xml:
                return r.text
            else:
                return Box(r.json())

    async def __post_req__(
        self,
        endpoint: str,
        data: Union[Box, str],
        xml: bool = False,
        **kwargs: Any,
    ) -> Union[Box, str]:
        url = self.con_params["base_url"] + endpoint

        if kwargs.get("params", {}):
            kwargs["params"] = {k: v for k, v in kwargs.get("params", {}).items() if v is not None}

        headers = {
            "Accept": f"application/{'xml' if xml else 'json'}",
            "Content-Type": f"application/{'xml' if xml else 'json'}",
        }

        if xml:
            r = await self.session.post(url, data=data, headers=headers, **kwargs)
            if r.status_code >= 400:
                handle_http_error(r)
            else:
                r.raise_for_status()
                return r.text
        else:
            r = await self.session.post(url, json=data.to_dict(), headers=headers, **kwargs)
            if r.status_code >= 400:
                handle_http_error(r)
            else:
                r.raise_for_status()

            return Box(r.json())

    async def __delete_req__(self, endpoint: str, **kwargs: Any) -> bool:
        url = self.con_params["base_url"] + endpoint

        if kwargs.get("params", {}):
            kwargs["params"] = {k: v for k, v in kwargs.get("params", {}).items() if v is not None}

        async with self.limiter.ratelimit("alma", delay=True):
            r = await self.session.delete(url, **kwargs)
            if r.status_code >= 400:
                handle_http_error(r)
            else:
                return r.status_code == 204

    async def __put_req__(
        self,
        endpoint: str,
        data: Union[Box, str],
        xml: bool = False,
        **kwargs: Any,
    ) -> Union[Box, str]:
        url = self.con_params["base_url"] + endpoint

        if kwargs.get("params", {}):
            kwargs["params"] = {k: v for k, v in kwargs.get("params", {}).items() if v is not None}

        headers = {
            "Accept": f"application/{'xml' if xml else 'json'}",
            "Content-Type": f"application/{'xml' if xml else 'json'}",
        }

        async with self.limiter.ratelimit("alma", delay=True):
            if xml:
                r = await self.session.put(url, data=data, headers=headers, **kwargs)
                if r.status_code >= 400:
                    handle_http_error(r)
                else:
                    r.raise_for_status()
                    return r.text
            else:
                r = await self.session.put(url, json=data.to_dict(), headers=headers, **kwargs)
                if r.status_code >= 400:
                    handle_http_error(r)
                else:
                    r.raise_for_status()

                return Box(r.json())
