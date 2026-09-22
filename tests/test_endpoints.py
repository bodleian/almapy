"""Tests for AlmaEndpoint.build()."""

import pytest

from almapy._endpoints import AlmaEndpoint


class TestBuild:
    def test_with_correct_params(self) -> None:
        result = AlmaEndpoint.USER_LOANS.build({"USER_ID": "jsmith"})
        assert result == "/users/jsmith/loans"

    def test_multiple_params(self) -> None:
        result = AlmaEndpoint.ITEM.build({
            "MMS_ID": "123",
            "HOLDING_ID": "456",
            "ITEM_PID": "789",
        })
        assert result == "/bibs/123/holdings/456/items/789"

    @pytest.mark.parametrize(
        "params,use_default",
        [
            (None, True),
            (None, False),
            ({}, False),
        ],
        ids=["no_arg", "explicit_none", "empty_dict"],
    )
    def test_no_params_endpoint(self, params: dict[str, str] | None, use_default: bool) -> None:
        result = AlmaEndpoint.SETS.build() if use_default else AlmaEndpoint.SETS.build(params)
        assert result == "/conf/sets"

    def test_missing_params_raises(self) -> None:
        with pytest.raises(ValueError, match="missing path params"):
            AlmaEndpoint.USER_LOANS.build({})

    def test_missing_some_params_raises(self) -> None:
        with pytest.raises(ValueError, match="missing path params"):
            AlmaEndpoint.ITEM.build({"MMS_ID": "123"})

    def test_extra_params_raises(self) -> None:
        with pytest.raises(ValueError, match="unexpected path params"):
            AlmaEndpoint.SETS.build({"BOGUS": "value"})

    def test_extra_alongside_valid_raises(self) -> None:
        with pytest.raises(ValueError, match="unexpected path params"):
            AlmaEndpoint.USER.build({"USER_ID": "jsmith", "EXTRA": "nope"})

    def test_bib_loan_fixed(self) -> None:
        """BIB_LOAN had a malformed bracket {LOAN_ID] – verify it's fixed."""
        result = AlmaEndpoint.BIB_LOAN.build({"MMS_ID": "111", "LOAN_ID": "222"})
        assert result == "/bibs/111/loans/222"

    def test_bib_request_single(self) -> None:
        result = AlmaEndpoint.BIB_REQUEST.build({"MMS_ID": "111", "REQUEST_ID": "222"})
        assert result == "/bibs/111/requests/222"

    def test_representation_collection_and_single(self) -> None:
        assert AlmaEndpoint.REPRESENTATIONS.build({"MMS_ID": "111"}) == "/bibs/111/representations"
        assert (
            AlmaEndpoint.REPRESENTATION.build({"MMS_ID": "111", "REP_ID": "999"})
            == "/bibs/111/representations/999"
        )

    def test_representation_files(self) -> None:
        assert (
            AlmaEndpoint.REPRESENTATION_FILES.build({"MMS_ID": "111", "REP_ID": "999"})
            == "/bibs/111/representations/999/files"
        )
        assert (
            AlmaEndpoint.REPRESENTATION_FILE.build({
                "MMS_ID": "111",
                "REP_ID": "999",
                "FILE_ID": "888",
            })
            == "/bibs/111/representations/999/files/888"
        )

    def test_representation_file_id_is_encoded(self) -> None:
        """A file ID carrying a slash must not invent a path segment."""
        assert (
            AlmaEndpoint.REPRESENTATION_FILE.build({
                "MMS_ID": "111",
                "REP_ID": "999",
                "FILE_ID": "a/b",
            })
            == "/bibs/111/representations/999/files/a%2Fb"
        )


class TestPathParameterEncoding:
    """Path parameters are percent-encoded so they cannot act as URL syntax.

    Alma "other IDs", card numbers and barcodes are free text arriving from
    upstream systems, so the silently-wrong-record case is realistic rather
    than adversarial.
    """

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("jsmith", "/users/jsmith"),
            # The fragment never reaches the server: this fetched user "smith".
            ("smith#1", "/users/smith%231"),
            # Hit a different route entirely.
            ("a/b", "/users/a%2Fb"),
            # Became a query string.
            ("x?apikey=other", "/users/x%3Fapikey%3Dother"),
            ("a b", "/users/a%20b"),
            ("100%pure", "/users/100%25pure"),
        ],
    )
    def test_reserved_characters_are_encoded(self, raw: str, expected: str) -> None:
        assert AlmaEndpoint.USER.build({"USER_ID": raw}) == expected

    def test_ordinary_identifiers_are_unchanged(self) -> None:
        """Encoding must not disturb the overwhelmingly common case."""
        assert (
            AlmaEndpoint.ITEM.build({"MMS_ID": "991234567", "HOLDING_ID": "22", "ITEM_PID": "23"})
            == "/bibs/991234567/holdings/22/items/23"
        )


class TestSlashBearingIdentifiers:
    """A PO line number keeps its slash, because that is where Alma keeps it.

    Migrated orders are numbered `<order>/<line>`, and Alma addresses the record
    at a path with the slash raw – its own search results give the record's
    `link` as `/acq/po-lines/204029292/0005`. Encoded to `%2F`, the Ex Libris
    gateway refuses the request at the connector, before Alma sees it.
    """

    def test_po_line_number_keeps_its_slash(self) -> None:
        assert (
            AlmaEndpoint.PO_LINE.build({"PO_LINE_ID": "204029292/0005"})
            == "/acq/po-lines/204029292/0005"
        )

    def test_po_line_item_keeps_its_slash(self) -> None:
        assert (
            AlmaEndpoint.PO_LINE_ITEM.build({"PO_LINE_ID": "204029292/0005", "ITEM_PID": "23"})
            == "/acq/po-lines/204029292/0005/items/23"
        )

    def test_ordinary_po_line_number_is_unchanged(self) -> None:
        """The overwhelmingly common case must not be disturbed."""
        assert AlmaEndpoint.PO_LINE.build({"PO_LINE_ID": "POL-12345"}) == "/acq/po-lines/POL-12345"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("a b/c", "/acq/po-lines/a%20b/c"),
            ("a#1/c", "/acq/po-lines/a%231/c"),
            ("a?apikey=other/c", "/acq/po-lines/a%3Fapikey%3Dother/c"),
        ],
    )
    def test_the_slash_is_the_only_exception(self, raw: str, expected: str) -> None:
        """Each segment either side of a slash is still encoded strictly."""
        assert AlmaEndpoint.PO_LINE.build({"PO_LINE_ID": raw}) == expected

    @pytest.mark.parametrize(
        "raw",
        ["../../users/jsmith", "a/../b", "a//b", "/a", "a/", ".", ".."],
        ids=["traversal", "inner_dots", "empty_inner", "leading", "trailing", "dot", "dotdot"],
    )
    def test_path_rewriting_segments_are_refused(self, raw: str) -> None:
        """Letting the slash through is only safe while it cannot rewrite the path."""
        with pytest.raises(ValueError, match="empty or relative path segment"):
            AlmaEndpoint.PO_LINE.build({"PO_LINE_ID": raw})

    def test_the_exception_is_narrow(self) -> None:
        """Every other identifier space still encodes its slash."""
        assert AlmaEndpoint.USER.build({"USER_ID": "a/b"}) == "/users/a%2Fb"
