"""HTTP-level tests for bib-level single-request methods (GET / PUT / POST)."""

from urllib.parse import parse_qs, urlsplit

from niquests_mock import MockRouter

from almapy import AlmaClient

_BASE = "https://api-eu.hosted.exlibrisgroup.com/almaws/v1"


def _query(niquests_mock: MockRouter) -> dict[str, list[str]]:
    url = niquests_mock.calls[-1].request.url
    assert isinstance(url, str)
    return parse_qs(urlsplit(url).query)


class TestBibRequests:
    async def test_get_request_for_bib(self, client: AlmaClient, niquests_mock: MockRouter) -> None:
        niquests_mock.get(f"{_BASE}/bibs/111/requests/222").respond(
            json={"request_id": "222", "request_type": "HOLD"}
        )
        result = await client.bibs.requests.get_request_for_bib("111", "222")
        assert result.request_id == "222"
        assert niquests_mock.calls[-1].request.method == "GET"

    async def test_update_request_for_bib(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.put(f"{_BASE}/bibs/111/requests/222").respond(
            json={"request_id": "222", "comment": "updated"}
        )
        result = await client.bibs.requests.update_request_for_bib(
            "111", "222", {"comment": "updated"}
        )
        assert result.comment == "updated"
        req = niquests_mock.calls[-1].request
        assert req.method == "PUT"
        assert isinstance(req.body, bytes)
        assert b"updated" in req.body

    async def test_process_request_for_bib_defaults(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        # POST carries op/release_item query params, so match on path, not exact URL.
        niquests_mock.post(path="/almaws/v1/bibs/111/requests/222").respond(
            json={"request_id": "222"}
        )
        await client.bibs.requests.process_request_for_bib("111", "222")
        assert niquests_mock.calls[-1].request.method == "POST"
        query = _query(niquests_mock)
        assert query["op"] == ["next_step"]
        assert query["release_item"] == ["False"]

    async def test_process_request_for_bib_release_item(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.post(path="/almaws/v1/bibs/111/requests/222").respond(
            json={"request_id": "222"}
        )
        await client.bibs.requests.process_request_for_bib(
            "111", "222", op="next_step", release_item=True
        )
        query = _query(niquests_mock)
        assert query["release_item"] == ["True"]


class TestBibWriteParameters:
    """Outgoing query strings for bib writes.

    These assert the wire format, not the Python signature: a parameter that is
    spelled correctly in the kwarg but sent under the wrong name is accepted by
    Alma with a 200 and silently ignored, so only the request URL catches it.
    """

    _RECORD = "<bib><record>data</record></bib>"

    async def test_create_bib_sends_from_cz_mms_id(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """Regression: this was sent as to_cz_mms_id, which Alma ignores."""
        niquests_mock.post(path="/almaws/v1/bibs").respond(
            content=self._RECORD, headers={"Content-Type": "application/xml"}
        )

        await client.bibs.create_bib(self._RECORD, from_cz_mms_id="991234")

        query = _query(niquests_mock)
        assert query["from_cz_mms_id"] == ["991234"]
        assert "to_cz_mms_id" not in query

    def _mock_create(self, niquests_mock: MockRouter) -> None:
        niquests_mock.post(path="/almaws/v1/bibs").respond(
            content=self._RECORD, headers={"Content-Type": "application/xml"}
        )

    def _mock_update(self, niquests_mock: MockRouter) -> None:
        niquests_mock.put(path="/almaws/v1/bibs/991234").respond(
            content=self._RECORD, headers={"Content-Type": "application/xml"}
        )

    async def test_create_bib_omits_override_warning_by_default(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """Regression: Alma rejects an explicit override_warning=false unless it is
        paired with validate=true or check_match=true (error 401873), so the
        plain create must not send it at all.
        """
        self._mock_create(niquests_mock)

        await client.bibs.create_bib(self._RECORD)

        assert "override_warning" not in _query(niquests_mock)

    async def test_create_bib_sends_override_warning_false_with_validate(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """Alma's own default is true, so once validation is on the false must be
        explicit or warnings are silently overridden."""
        self._mock_create(niquests_mock)

        await client.bibs.create_bib(self._RECORD, validate=True)

        query = _query(niquests_mock)
        assert query["validate"] == ["True"]
        assert query["override_warning"] == ["False"]

    async def test_create_bib_sends_override_warning_false_with_check_match(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        self._mock_create(niquests_mock)

        await client.bibs.create_bib(self._RECORD, check_match=True)

        query = _query(niquests_mock)
        assert query["check_match"] == ["True"]
        assert query["override_warning"] == ["False"]

    async def test_create_bib_sends_override_warning_true_when_enabled(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        self._mock_create(niquests_mock)

        await client.bibs.create_bib(self._RECORD, override_warning=True)

        assert _query(niquests_mock)["override_warning"] == ["True"]

    async def test_delete_bib_does_not_override_by_default(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        niquests_mock.delete(path="/almaws/v1/bibs/991234").respond(status_code=204)

        await client.bibs.delete_bib("991234")

        assert _query(niquests_mock)["override"] == ["False"]

    async def test_update_bib_omits_override_warning_and_lock_by_default(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        """Same 401873 regression as create_bib – see above."""
        self._mock_update(niquests_mock)

        await client.bibs.update_bib("991234", self._RECORD)

        query = _query(niquests_mock)
        assert "override_warning" not in query
        # override_lock is only sent when explicitly enabled
        assert "override_lock" not in query

    async def test_update_bib_sends_override_warning_false_with_validate(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        self._mock_update(niquests_mock)

        await client.bibs.update_bib("991234", self._RECORD, validate=True)

        query = _query(niquests_mock)
        assert query["validate"] == ["True"]
        assert query["override_warning"] == ["False"]

    async def test_update_bib_sends_override_warning_false_with_check_match(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        self._mock_update(niquests_mock)

        await client.bibs.update_bib("991234", self._RECORD, check_match=True)

        query = _query(niquests_mock)
        assert query["check_match"] == ["True"]
        assert query["override_warning"] == ["False"]

    async def test_update_bib_sends_override_warning_true_when_enabled(
        self, client: AlmaClient, niquests_mock: MockRouter
    ) -> None:
        self._mock_update(niquests_mock)

        await client.bibs.update_bib("991234", self._RECORD, override_warning=True)

        assert _query(niquests_mock)["override_warning"] == ["True"]
