"""HTTP-level tests for the digital representations namespace."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from niquests_mock import MockRouter

from almapy import AlmaClient, exceptions

_REPS_PATH = "/almaws/v1/bibs/111/representations"


def _query(niquests_mock: MockRouter) -> dict[str, list[str]]:
    url = niquests_mock.calls[-1].request.url
    assert isinstance(url, str)
    return parse_qs(urlsplit(url).query)


class TestRepresentations:
    async def test_get_representations(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.get(path=_REPS_PATH).respond(
            json={
                "representation": [{"id": "999", "label": "Digitised copy"}],
                "total_record_count": 1,
            }
        )
        result = await client.bibs.representations.get_representations("111")
        assert result.total_record_count == 1
        assert result.representation[0].id == "999"
        assert niquests_mock.calls[-1].request.method == "GET"

    async def test_get_representation(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.get(path=f"{_REPS_PATH}/999").respond(
            json={"id": "999", "usage_type": {"value": "DERIVATIVE_COPY"}}
        )
        result = await client.bibs.representations.get_representation("111", "999")
        assert result.usage_type.value == "DERIVATIVE_COPY"
        assert niquests_mock.calls[-1].request.method == "GET"

    async def test_create_representation(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.post(path=_REPS_PATH).respond(json={"id": "999", "label": "Digitised copy"})
        result = await client.bibs.representations.create_representation(
            "111", {"library": {"value": "MAIN"}, "usage_type": {"value": "DERIVATIVE_COPY"}}
        )
        assert result.id == "999"
        req = niquests_mock.calls[-1].request
        assert req.method == "POST"
        assert isinstance(req.body, bytes)
        assert b"DERIVATIVE_COPY" in req.body

    async def test_update_representation(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.put(path=f"{_REPS_PATH}/999").respond(json={"id": "999", "label": "Updated"})
        result = await client.bibs.representations.update_representation(
            "111", "999", {"label": "Updated"}
        )
        assert result.label == "Updated"
        req = niquests_mock.calls[-1].request
        assert req.method == "PUT"
        assert isinstance(req.body, bytes)
        assert b"Updated" in req.body

    async def test_delete_representation_returns_none(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """204 with an empty body must be swallowed, not fed to the JSON parser.

        parser="none" is what makes this pass; a JSON parse of an empty body
        raises MalformedResponseError.
        """
        niquests_mock.delete(path=f"{_REPS_PATH}/999").respond(status_code=204)
        await client.bibs.representations.delete_representation("111", "999")
        assert niquests_mock.calls[-1].request.method == "DELETE"

    async def test_create_representation_maps_402260(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """Alma's 402260 is the routine failure here: it needs its own exception class."""
        niquests_mock.post(path=_REPS_PATH).respond(
            status_code=400,
            json={
                "errorList": {
                    "error": [
                        {
                            "errorCode": "402260",
                            "errorMessage": "Bib record is not assigned to a collection.",
                        }
                    ]
                }
            },
        )
        with pytest.raises(exceptions.BibNotInCollectionError) as exc_info:
            await client.bibs.representations.create_representation("111", {})
        assert exc_info.value.code == "402260"


class TestRepresentationFiles:
    async def test_get_files(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.get(path=f"{_REPS_PATH}/999/files").respond(
            json={"representation_file": [{"pid": "888", "label": "Page 1"}]}
        )
        result = await client.bibs.representations.get_files("111", "999")
        assert result.representation_file[0].pid == "888"
        assert niquests_mock.calls[-1].request.method == "GET"

    async def test_get_file(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.get(path=f"{_REPS_PATH}/999/files/888").respond(
            json={"pid": "888", "path": "01UNI_INST/storage/alma/page1.jpg"}
        )
        result = await client.bibs.representations.get_file("111", "999", "888")
        assert result.pid == "888"

    async def test_create_file(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.post(path=f"{_REPS_PATH}/999/files").respond(json={"pid": "888"})
        result = await client.bibs.representations.create_file(
            "111", "999", {"path": "01UNI_INST/upload/scratch/1234/page1.jpg"}
        )
        assert result.pid == "888"
        req = niquests_mock.calls[-1].request
        assert req.method == "POST"
        assert isinstance(req.body, bytes)
        assert b"upload/scratch" in req.body

    async def test_update_file(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.put(path=f"{_REPS_PATH}/999/files/888").respond(
            json={"pid": "888", "label": "Title page"}
        )
        result = await client.bibs.representations.update_file(
            "111", "999", "888", {"label": "Title page"}
        )
        assert result.label == "Title page"
        assert niquests_mock.calls[-1].request.method == "PUT"

    async def test_delete_file_returns_none(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """As for delete_representation: an empty 204 body must not reach the parser."""
        niquests_mock.delete(path=f"{_REPS_PATH}/999/files/888").respond(status_code=204)
        await client.bibs.representations.delete_file("111", "999", "888")
        assert niquests_mock.calls[-1].request.method == "DELETE"


class TestRepresentationParameters:
    """Outgoing query strings for the representation calls.

    These assert the wire format, not the Python signature. Alma ignores an
    unrecognised query parameter and answers 200, so a parameter spelled correctly
    in the kwarg but wrongly on the wire is invisible except in the request URL.
    The bib-disposition parameter is the live hazard: it is ``bibs`` here, but
    ``bib`` on the holding and item endpoints.
    """

    async def test_list_defaults_omit_originating_record_id(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(path=_REPS_PATH).respond(json={"total_record_count": 0})
        await client.bibs.representations.get_representations("111")
        query = _query(niquests_mock)
        assert query["limit"] == ["10"]
        assert query["offset"] == ["0"]
        assert query["use_updated_terminology"] == ["False"]
        assert "originating_record_id" not in query

    async def test_list_sends_originating_record_id_when_given(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(path=_REPS_PATH).respond(json={"total_record_count": 0})
        await client.bibs.representations.get_representations(
            "111", originating_record_id="remote-42", limit=100, use_updated_terminology=True
        )
        query = _query(niquests_mock)
        assert query["originating_record_id"] == ["remote-42"]
        assert query["limit"] == ["100"]
        assert query["use_updated_terminology"] == ["True"]

    async def test_create_sends_generate_label(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.post(path=_REPS_PATH).respond(json={"id": "999"})
        await client.bibs.representations.create_representation("111", {}, generate_label=True)
        assert _query(niquests_mock)["generate_label"] == ["True"]

    async def test_update_sends_bibs_not_bib(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.put(path=f"{_REPS_PATH}/999").respond(json={"id": "999"})
        await client.bibs.representations.update_representation(
            "111", "999", {}, handle_bib="suppress"
        )
        query = _query(niquests_mock)
        assert query["bibs"] == ["suppress"]
        assert "bib" not in query

    async def test_delete_representation_defaults_are_conservative(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.delete(path=f"{_REPS_PATH}/999").respond(status_code=204)
        await client.bibs.representations.delete_representation("111", "999")
        query = _query(niquests_mock)
        assert query["override"] == ["False"]
        assert query["bibs"] == ["retain"]

    async def test_delete_representation_sends_overrides(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.delete(path=f"{_REPS_PATH}/999").respond(status_code=204)
        await client.bibs.representations.delete_representation(
            "111", "999", override=True, handle_bib="delete"
        )
        query = _query(niquests_mock)
        assert query["override"] == ["True"]
        assert query["bibs"] == ["delete"]

    async def test_files_omit_expand_by_default(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """expand=url costs Alma a signed-URL mint, so it must not be sent unasked."""
        niquests_mock.get(path=f"{_REPS_PATH}/999/files").respond(json={})
        await client.bibs.representations.get_files("111", "999")
        assert "expand" not in _query(niquests_mock)

    async def test_files_send_expand_url_when_asked(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(path=f"{_REPS_PATH}/999/files").respond(json={})
        await client.bibs.representations.get_files("111", "999", expand_url=True)
        assert _query(niquests_mock)["expand"] == ["url"]

    async def test_file_sends_expand_url_when_asked(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.get(path=f"{_REPS_PATH}/999/files/888").respond(json={})
        await client.bibs.representations.get_file("111", "999", "888", expand_url=True)
        assert _query(niquests_mock)["expand"] == ["url"]

    async def test_delete_file_sends_both_dispositions(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.delete(path=f"{_REPS_PATH}/999/files/888").respond(status_code=204)
        await client.bibs.representations.delete_file(
            "111", "999", "888", handle_representation="delete", handle_bib="suppress"
        )
        query = _query(niquests_mock)
        assert query["representations"] == ["delete"]
        assert query["bibs"] == ["suppress"]

    async def test_create_file_timeout_is_not_a_query_param(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """timeout= is a transport knob, so it must never reach Alma as a parameter."""
        niquests_mock.post(path=f"{_REPS_PATH}/999/files").respond(json={"pid": "888"})
        await client.bibs.representations.create_file("111", "999", {"path": "x"}, timeout=120)
        assert "timeout" not in _query(niquests_mock)
        req = niquests_mock.calls[-1].request
        assert isinstance(req.body, bytes)
        assert json.loads(req.body) == {"path": "x"}
