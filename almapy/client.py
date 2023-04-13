from typing import Any, Dict, Literal, Optional, Union, overload

import httpx
from box import Box
from pyrate_limiter import Duration, Limiter, RequestRate
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from almapy.utils import APIServerError, handle_http_error


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

    @overload
    async def __get_req__(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Box:
        ...

    @overload
    async def __get_req__(
        self,
        endpoint: str,
        xml: Literal[False],
        params: Optional[Dict[str, Any]] = None,
    ) -> Box:
        ...

    @overload
    async def __get_req__(
        self,
        endpoint: str,
        xml: Literal[True],
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        ...

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(APIServerError),
    )
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

    @overload
    async def __post_req__(
        self,
        endpoint: str,
        data: Box,
        xml: Literal[False],
        **kwargs: Any,
    ) -> Box:
        ...

    @overload
    async def __post_req__(self, endpoint: str, data: str, xml: Literal[True], **kwargs: Any) -> str:
        ...

    @overload
    async def __post_req__(self, endpoint: str, data: Optional[Box] = None, **kwargs: Any) -> Box:
        ...

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(APIServerError),
    )
    async def __post_req__(
        self,
        endpoint: str,
        data: Union[Box, str, None] = None,
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
                if data and type(data) != str:
                    raise ValueError("Body data must be a string when using xml")
                r = await self.session.post(url, content=data, headers=headers, **kwargs)
                if r.status_code >= 400:
                    handle_http_error(r)
                else:
                    r.raise_for_status()
                    return r.text
            else:
                if data and type(data) != Box:
                    raise ValueError("Body data must be a Box when using json")
                if data:
                    body = data.to_dict()
                else:
                    body = None
                r = await self.session.post(url, json=body, headers=headers, **kwargs)
                if r.status_code >= 400:
                    handle_http_error(r)
                else:
                    r.raise_for_status()

                return Box(r.json())

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(APIServerError),
    )
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

    @overload
    async def __put_req__(
        self,
        endpoint: str,
        data: Box,
        xml: Literal[False],
        **kwargs: Any,
    ) -> Box:
        ...

    @overload
    async def __put_req__(self, endpoint: str, data: str, xml: Literal[True], **kwargs: Any) -> str:
        ...

    @overload
    async def __put_req__(self, endpoint: str, data: Optional[Box] = None, **kwargs: Any) -> Box:
        ...

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(APIServerError),
    )
    async def __put_req__(
        self,
        endpoint: str,
        data: Union[Box, str, None] = None,
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
                if type(data) != str:
                    raise ValueError("Body data must be a string when using xml")
                r = await self.session.put(url, content=data, headers=headers, **kwargs)
                if r.status_code >= 400:
                    handle_http_error(r)
                else:
                    r.raise_for_status()
                    return r.text
            else:
                if type(data) != Box:
                    raise ValueError("Body data must be a Box when using json")
                r = await self.session.put(url, json=data.to_dict(), headers=headers, **kwargs)
                if r.status_code >= 400:
                    handle_http_error(r)
                else:
                    r.raise_for_status()

                return Box(r.json())
