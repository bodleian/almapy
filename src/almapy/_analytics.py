from typing import Any

import xmltodict

from almapy._base import BaseNamespace
from almapy._endpoints import AlmaEndpoint


def _as_list(value: Any) -> list[Any]:
    """Normalise xmltodict's repeated-element handling.

    xmltodict returns a list for repeated elements, a bare dict when exactly one
    is present, and nothing at all when there are none. Every site that iterates
    rows or columns has to go through here: iterating the dict form yields its
    keys as strings, which fails later with a confusing AttributeError rather
    than at the point of the mistake.
    """
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def headers_to_dict(headers: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    """Map Alma's internal column names to their report headings.

    Accepts the single-column dict form as well as a list — a report with one
    non-Column0 column previously raised TypeError here.
    """
    return {header["@name"]: header["@saw-sql:columnHeading"] for header in _as_list(headers)}


class AlmaClientAnalyticsNS(BaseNamespace):
    """Namespace for analytics functionality."""

    async def get_raw_report(
        self,
        path: str,
        limit: int = 100,
        *,
        token: str | None = None,
        report_filter: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"path": path, "limit": limit}
        if report_filter:
            params["filter"] = report_filter
        if token:
            params["token"] = token
        return await self._get_text(
            AlmaEndpoint.REPORTS,
            params=params,
            headers={"Accept": "application/xml"},
        )

    async def get_full_report(
        self,
        path: str,
        limit: int = 100,
        header_override: dict[str, str] | None = None,
        report_filter: str | None = None,
    ) -> list[dict[str, str]]:
        initial_response = await self.get_raw_report(path, limit, report_filter=report_filter)
        parsed_resp = xmltodict.parse(initial_response)
        finished = parsed_resp["report"]["QueryResult"]["IsFinished"]
        rowset = parsed_resp["report"]["QueryResult"]["ResultXml"]["rowset"]
        result = _as_list(rowset.get("Row"))
        headers = headers_to_dict(
            rowset["xsd:schema"]["xsd:complexType"]["xsd:sequence"]["xsd:element"]
        )
        if header_override:
            headers.update(header_override)
        token = parsed_resp["report"]["QueryResult"]["ResumptionToken"]

        while finished == "false":
            resp = await self.get_raw_report(path, limit, token=token, report_filter=report_filter)
            parsed_resp = xmltodict.parse(resp)
            finished = parsed_resp["report"]["QueryResult"]["IsFinished"]
            # Same coercion as the first page. Indexing ["Row"] directly meant a
            # final page with one row raised AttributeError and one with no rows
            # raised KeyError — reachable by any report whose total is just over
            # a multiple of `limit`.
            page = parsed_resp["report"]["QueryResult"]["ResultXml"]["rowset"]
            result.extend(_as_list(page.get("Row")))

        data = [{headers[k]: v for k, v in row.items() if k != "Column0"} for row in result]
        return data
