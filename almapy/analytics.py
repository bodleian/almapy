from typing import Any, Dict, List, Optional

import xmltodict
from httpx import AsyncClient

from almapy.client import Client


def headers_to_dict(headers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {header["@name"]: header["@saw-sql:columnHeading"] for header in headers}


class SubClientAnalytics(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/analytics"

    async def get_raw_report(
        self, path: str, limit: int = 100, token: Optional[str] = None, filter: Optional[str] = None
    ) -> str:
        params = {
            "path": path,
            "limit": limit,
            "token": token,
            "filter": filter,
        }
        return await self.__get_req__(self.con_params["api_endpoint"] + "/reports", params=params, xml=True)

    async def get_full_report(
        self,
        path: str,
        limit: int = 100,
        header_override: Optional[Dict[str, str]] = None,
        filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        initial_response = await self.get_raw_report(path, limit, filter)
        parsed_response = xmltodict.parse(initial_response)
        finished = parsed_response["report"]["QueryResult"]["IsFinished"]
        result = parsed_response["report"]["QueryResult"]["ResultXml"]["rowset"]["Row"]
        headers = parsed_response["report"]["QueryResult"]["ResultXml"]["rowset"]["xsd:schema"]["xsd:complexType"][
            "xsd:sequence"
        ]["xsd:element"]
        headers = headers_to_dict(headers)
        if header_override:
            headers.update(header_override)

        while finished == "false":
            token = parsed_response["report"]["QueryResult"]["ResumptionToken"]
            resp = await self.get_raw_report(path, limit, token, filter)
            parsed_resp = xmltodict.parse(resp)
            finished = parsed_resp["report"]["QueryResult"]["IsFinished"]
            result.extend(parsed_resp["report"]["QueryResult"]["ResultXml"]["rowset"]["Row"])

        data = [{headers[k]: v for k, v in row.items() if k != "Column0"} for row in result]
        return data
