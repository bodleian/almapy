"""Primo Search namespace, exposed at AlmaClient.primo."""

from typing import Any, Literal, overload

from almapy._base import BaseNamespace
from almapy._utils import RESP_TYPE, _ModelT

_Sort = Literal["rank", "title", "author", "date", "date_d", "date_a"]


class AlmaClientPrimoNS(BaseNamespace):
    """Namespace for the Primo Search API, exposed at AlmaClient.primo.

    Reaches the same regional gateway as Alma with the same API key, but on the
    ``/primo/v1`` base path rather than Alma's ``/almaws/v1``.
    """

    @overload
    async def search(
        self,
        q: str,
        vid: str,
        tab: str,
        scope: str,
        *,
        limit: int = ...,
        offset: int = ...,
        sort: _Sort = ...,
        lang: str = ...,
        q_include: str | None = ...,
        q_exclude: str | None = ...,
        multi_facets: str | None = ...,
        from_date: str | None = ...,
        personalization: str | None = ...,
        journals: str | None = ...,
        databases: str | None = ...,
        con_voc: bool = ...,
        skip_delivery: bool = ...,
        disable_split_facets: bool = ...,
        newspapers_search: bool = ...,
        pc_availability: bool = ...,
        model: type[_ModelT],
    ) -> _ModelT: ...

    @overload
    async def search(
        self,
        q: str,
        vid: str,
        tab: str,
        scope: str,
        *,
        limit: int = ...,
        offset: int = ...,
        sort: _Sort = ...,
        lang: str = ...,
        q_include: str | None = ...,
        q_exclude: str | None = ...,
        multi_facets: str | None = ...,
        from_date: str | None = ...,
        personalization: str | None = ...,
        journals: str | None = ...,
        databases: str | None = ...,
        con_voc: bool = ...,
        skip_delivery: bool = ...,
        disable_split_facets: bool = ...,
        newspapers_search: bool = ...,
        pc_availability: bool = ...,
        model: None = ...,
    ) -> RESP_TYPE: ...

    async def search(
        self,
        q: str,
        vid: str,
        tab: str,
        scope: str,
        *,
        limit: int = 10,
        offset: int = 0,
        sort: _Sort = "rank",
        lang: str = "eng",
        q_include: str | None = None,
        q_exclude: str | None = None,
        multi_facets: str | None = None,
        from_date: str | None = None,
        personalization: str | None = None,
        journals: str | None = None,
        databases: str | None = None,
        con_voc: bool = True,
        skip_delivery: bool = True,
        disable_split_facets: bool = True,
        newspapers_search: bool = False,
        pc_availability: bool = True,
        model: Any = None,
    ) -> Any:
        """Issue a Primo discovery search.

        Snake_case keyword arguments are translated to the camelCase query
        parameters the Primo API expects. Parameters left as ``None`` are
        omitted from the request (niquests drops ``None`` values).
        """
        params: dict[str, Any] = {
            "q": q,
            "vid": vid,
            "tab": tab,
            "scope": scope,
            "limit": limit,
            "offset": offset,
            "sort": sort,
            "lang": lang,
            "qInclude": q_include,
            "qExclude": q_exclude,
            "multiFacets": multi_facets,
            "fromDate": from_date,
            "personalization": personalization,
            "journals": journals,
            "databases": databases,
            "conVoc": con_voc,
            "skipDelivery": skip_delivery,
            "disableSplitFacets": disable_split_facets,
            "newspapersSearch": newspapers_search,
            "pcAvailability": pc_availability,
        }
        url = f"{self._client._gateway}/primo/v1/search"
        return await self._client.execute("GET", url, parser="json", params=params, model=model)
