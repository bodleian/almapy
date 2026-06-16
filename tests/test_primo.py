"""Tests for the Primo Search namespace (client.primo.search)."""

from urllib.parse import parse_qs, urlparse

import pytest
import responses
from box import Box
from pydantic import BaseModel

from almapy import AlmaClient
from almapy._primo import AlmaClientPrimoNS
from tests._niquests_mock import NiquestsMock

_PRIMO_URL = "https://api-eu.hosted.exlibrisgroup.com/primo/v1/search"


def _query(rsps: NiquestsMock) -> dict[str, list[str]]:
    """Parsed query string of the single recorded request."""
    assert len(rsps.calls) == 1
    return parse_qs(urlparse(rsps.calls[0].request.url).query)


class TestNamespacePresence:
    def test_namespace_exists(self, client: AlmaClient) -> None:
        assert isinstance(client.primo, AlmaClientPrimoNS)

    def test_search_is_coroutine(self, client: AlmaClient) -> None:
        import inspect

        assert inspect.iscoroutinefunction(client.primo.search)


class TestRequestRouting:
    @pytest.mark.asyncio
    async def test_targets_primo_base_path_not_almaws(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        """The absolute Primo URL is used, not Alma's /almaws/v1 base path."""
        rsps.add(responses.GET, _PRIMO_URL, json={"docs": []})
        await client.primo.search(q="any,contains,dickens", vid="V", tab="T", scope="S")
        parsed = urlparse(rsps.calls[0].request.url)
        assert parsed.path == "/primo/v1/search"
        assert parsed.netloc == "api-eu.hosted.exlibrisgroup.com"

    @pytest.mark.asyncio
    async def test_carries_apikey_header(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"docs": []})
        await client.primo.search(q="q", vid="V", tab="T", scope="S")
        assert rsps.calls[0].request.headers["Authorization"] == "apikey test-api-key"


class TestRequiredParams:
    @pytest.mark.asyncio
    async def test_required_params_forwarded(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"docs": []})
        await client.primo.search(q="any,contains,dickens", vid="V1", tab="T1", scope="S1")
        q = _query(rsps)
        assert q["q"] == ["any,contains,dickens"]
        assert q["vid"] == ["V1"]
        assert q["tab"] == ["T1"]
        assert q["scope"] == ["S1"]


class TestOptionalParams:
    @pytest.mark.asyncio
    async def test_defaults_match_primo_api(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"docs": []})
        await client.primo.search(q="q", vid="V", tab="T", scope="S")
        q = _query(rsps)
        assert q["limit"] == ["10"]
        assert q["offset"] == ["0"]
        assert q["sort"] == ["rank"]
        assert q["lang"] == ["eng"]

    @pytest.mark.asyncio
    async def test_omitted_optionals_absent(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"docs": []})
        await client.primo.search(q="q", vid="V", tab="T", scope="S")
        q = _query(rsps)
        for absent in ("qInclude", "qExclude", "multiFacets", "fromDate", "personalization"):
            assert absent not in q

    @pytest.mark.asyncio
    async def test_snake_case_mapped_to_camel_case(
        self, client: AlmaClient, rsps: NiquestsMock
    ) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"docs": []})
        await client.primo.search(
            q="q",
            vid="V",
            tab="T",
            scope="S",
            q_include="facet_rtype,include,books",
            from_date="20240101000000",
            newspapers_search=True,
        )
        q = _query(rsps)
        assert q["qInclude"] == ["facet_rtype,include,books"]
        assert q["fromDate"] == ["20240101000000"]
        assert q["newspapersSearch"] == ["True"]
        # original snake_case keys must not leak onto the wire
        assert "q_include" not in q
        assert "from_date" not in q


class _PrimoResult(BaseModel):
    info: dict[str, int]


class TestResponseWrapping:
    @pytest.mark.asyncio
    async def test_default_returns_box(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"info": {"total": 3}})
        result = await client.primo.search(q="q", vid="V", tab="T", scope="S")
        assert isinstance(result, Box)
        assert result.info.total == 3

    @pytest.mark.asyncio
    async def test_model_validates_response(self, client: AlmaClient, rsps: NiquestsMock) -> None:
        rsps.add(responses.GET, _PRIMO_URL, json={"info": {"total": 3}})
        result = await client.primo.search(q="q", vid="V", tab="T", scope="S", model=_PrimoResult)
        assert isinstance(result, _PrimoResult)
        assert result.info == {"total": 3}
