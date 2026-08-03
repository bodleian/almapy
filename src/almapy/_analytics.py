"""Analytics namespace – running Alma Analytics (OBI) reports.

Reached as ``client.analytics``. Alma returns analytics results as XML rather than
JSON, and paginates them with a resumption token, so this namespace is the one
place in almapy that does not return ``Box`` objects: use
[`get_full_report`][almapy._analytics.AlmaClientAnalyticsNS.get_full_report] for
parsed rows, or [`get_raw_report`][almapy._analytics.AlmaClientAnalyticsNS.get_raw_report]
for the XML itself.
"""

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

    Accepts the single-column dict form as well as a list – a report with one
    non-Column0 column previously raised TypeError here.
    """
    return {header["@name"]: header["@saw-sql:columnHeading"] for header in _as_list(headers)}


class AlmaClientAnalyticsNS(BaseNamespace):
    """Namespace for analytics functionality.

    Available as ``client.analytics``. Unlike the other namespaces these methods
    return XML text or plain dictionaries rather than ``Box`` objects, and so do
    not accept a ``model=`` argument.
    """

    async def get_raw_report(
        self,
        path: str,
        limit: int = 100,
        *,
        token: str | None = None,
        report_filter: str | None = None,
    ) -> str:
        """Fetch one page of an Analytics report as raw XML.

        This is a single request – it does not follow the resumption token. Use
        [`get_full_report`][almapy._analytics.AlmaClientAnalyticsNS.get_full_report]
        unless you need the untouched XML or want to drive pagination yourself.

        Args:
            path: Full path to the report in Alma Analytics, e.g.
                ``/shared/Institution/Reports/My Report``.
            limit: Rows per page. Alma caps this at 1000 and rounds down to a
                multiple of 25.
            token: Resumption token from a previous page. When supplied, Alma
                ignores ``path`` and returns the next page of that result set.
            report_filter: An OBI XML filter expression applied to the report.

        Returns:
            The raw XML body, including the ``IsFinished`` flag and
            ``ResumptionToken`` needed to page through the result set.

        Raises:
            APIClientError: If the report path does not exist or the filter is
                malformed.

        Examples:
            ```python
            xml = await client.analytics.get_raw_report(
                "/shared/Institution/Reports/Loans by Library", limit=500
            )
            ```
        """
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
        """Run an Analytics report and return every row, following pagination.

        Repeatedly requests pages using Alma's resumption token until ``IsFinished``
        is true, then maps each row onto the report's column headings. Alma's
        internal ``Column0`` row index is dropped.

        Note that a large report costs one API request per ``limit`` rows, all of
        which count against the institution's daily quota.

        Args:
            path: Full path to the report in Alma Analytics, e.g.
                ``/shared/Institution/Reports/My Report``.
            limit: Rows per page. Alma caps this at 1000 and rounds down to a
                multiple of 25. Raise it to reduce the number of requests.
            header_override: Replaces individual column headings after they are read
                from the report schema, keyed by Alma's internal column name
                (``Column1``, ``Column2``, ...). Useful when a report ships with
                blank or duplicate headings.
            report_filter: An OBI XML filter expression applied to the report.

        Returns:
            One dictionary per row, keyed by column heading. Values are strings –
            Analytics does not type its output, so numbers and dates arrive as text.

        Raises:
            APIClientError: If the report path does not exist or the filter is
                malformed.
            KeyError: If a row contains a column absent from the report schema and no
                ``header_override`` supplies a heading for it.

        Examples:
            ```python
            rows = await client.analytics.get_full_report(
                "/shared/Institution/Reports/Loans by Library",
                limit=1000,
                header_override={"Column1": "Library Code"},
            )
            for row in rows:
                print(row["Library Code"], row["Loans"])
            ```
        """
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
            # raised KeyError – reachable by any report whose total is just over
            # a multiple of `limit`.
            page = parsed_resp["report"]["QueryResult"]["ResultXml"]["rowset"]
            result.extend(_as_list(page.get("Row")))

        data = [{headers[k]: v for k, v in row.items() if k != "Column0"} for row in result]
        return data
