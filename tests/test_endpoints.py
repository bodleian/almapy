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
