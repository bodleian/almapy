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

    def test_no_params_endpoint(self) -> None:
        result = AlmaEndpoint.SETS.build()
        assert result == "/conf/sets"

    def test_no_params_endpoint_explicit_none(self) -> None:
        result = AlmaEndpoint.SETS.build(None)
        assert result == "/conf/sets"

    def test_no_params_endpoint_empty_dict(self) -> None:
        result = AlmaEndpoint.SETS.build({})
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
        """BIB_LOAN had a malformed bracket {LOAN_ID] — verify it's fixed."""
        result = AlmaEndpoint.BIB_LOAN.build({"MMS_ID": "111", "LOAN_ID": "222"})
        assert result == "/bibs/111/loans/222"

    def test_str_enum_value(self) -> None:
        """AlmaEndpoint should be usable as a plain string."""
        assert AlmaEndpoint.USERS == "/users"
        assert isinstance(AlmaEndpoint.USERS, str)
