from __future__ import annotations

from typing import Any

import xmltodict
from gracy import GracyNamespace

from almapy._endpoints import AlmaEndpoint


def headers_to_dict(headers: list[dict[str, Any]]) -> dict[str, Any]:
    return {header["@name"]: header["@saw-sql:columnHeading"] for header in headers}


class AlmaClientAnalyticsNS(GracyNamespace[AlmaEndpoint]):
    """Namespace for analytics functionality."""

    async def get_raw_report(
        self,
        path: str,
        limit: int = 100,
        *,
        token: str | None = None,
        report_filter: str | None = None,
    ) -> str:
        params = {
            "path": path,
            "limit": limit,
            "token": token,
            "filter": report_filter,
        }
        resp: str = await self.get(
            AlmaEndpoint.REPORTS,
            params=params,
            headers={"Accept": "application/xml"},
        )
        return resp

    async def get_full_report(
        self,
        path: str,
        limit: int = 100,
        header_override: dict[str, str] | None = None,
        report_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        initial_response = await self.get_raw_report(path, limit, report_filter=report_filter)
        parsed_response = xmltodict.parse(initial_response)
        finished = parsed_response["report"]["QueryResult"]["IsFinished"]
        result = parsed_response["report"]["QueryResult"]["ResultXml"]["rowset"]["Row"]
        headers = parsed_response["report"]["QueryResult"]["ResultXml"]["rowset"]["xsd:schema"][
            "xsd:complexType"
        ]["xsd:sequence"]["xsd:element"]
        headers = headers_to_dict(headers)
        if header_override:
            headers.update(header_override)

        while finished == "false":
            token = parsed_response["report"]["QueryResult"]["ResumptionToken"]
            resp = await self.get_raw_report(path, limit, token=token, report_filter=report_filter)
            parsed_resp = xmltodict.parse(resp)
            finished = parsed_resp["report"]["QueryResult"]["IsFinished"]
            result.extend(parsed_resp["report"]["QueryResult"]["ResultXml"]["rowset"]["Row"])

        data = [{headers[k]: v for k, v in row.items() if k != "Column0"} for row in result]
        return data
