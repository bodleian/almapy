"""Tests for namespace error re-raise paths and input validation guards."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from box import Box

from almapy import AlmaClient, exceptions

# ---------------------------------------------------------------------------
# Shared XML fixtures for analytics tests
# ---------------------------------------------------------------------------

_XMLNS = 'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:saw-sql="urn:saw-sql"'

_PAGE1_XML = f"""<report><QueryResult>
  <IsFinished>false</IsFinished>
  <ResumptionToken>TOKEN123</ResumptionToken>
  <ResultXml><rowset {_XMLNS}>
    <xsd:schema><xsd:complexType><xsd:sequence>
      <xsd:element name="Column0" saw-sql:columnHeading="RowNum"/>
      <xsd:element name="Column1" saw-sql:columnHeading="Title"/>
    </xsd:sequence></xsd:complexType></xsd:schema>
    <Row><Column0>0</Column0><Column1>Book A</Column1></Row>
  </rowset></ResultXml>
</QueryResult></report>"""

# Page 2 must have multiple rows so xmltodict returns a list (not dict)
_PAGE2_XML = f"""<report><QueryResult>
  <IsFinished>true</IsFinished>
  <ResumptionToken>TOKEN123</ResumptionToken>
  <ResultXml><rowset {_XMLNS}>
    <xsd:schema><xsd:complexType><xsd:sequence>
      <xsd:element name="Column0" saw-sql:columnHeading="RowNum"/>
      <xsd:element name="Column1" saw-sql:columnHeading="Title"/>
    </xsd:sequence></xsd:complexType></xsd:schema>
    <Row><Column0>1</Column0><Column1>Book B</Column1></Row>
    <Row><Column0>2</Column0><Column1>Book C</Column1></Row>
  </rowset></ResultXml>
</QueryResult></report>"""

_SINGLE_ROW_XML = f"""<report><QueryResult>
  <IsFinished>true</IsFinished>
  <ResumptionToken></ResumptionToken>
  <ResultXml><rowset {_XMLNS}>
    <xsd:schema><xsd:complexType><xsd:sequence>
      <xsd:element name="Column0" saw-sql:columnHeading="RowNum"/>
      <xsd:element name="Column1" saw-sql:columnHeading="Title"/>
    </xsd:sequence></xsd:complexType></xsd:schema>
    <Row><Column0>0</Column0><Column1>Only Book</Column1></Row>
  </rowset></ResultXml>
</QueryResult></report>"""


@pytest.fixture
def client() -> AlmaClient:
    return AlmaClient("test-api-key")


class TestUpdateUserErrors:
    @pytest.mark.asyncio
    async def test_missing_field_raises_with_user_id(self, client: AlmaClient) -> None:
        """Code 401664 re-raised as UserMissingFieldError with user_id set."""
        api_err = exceptions.APIClientError("401664", "Missing mandatory field: primary_id")
        with (
            patch.object(client, "_execute", new=AsyncMock(side_effect=api_err)),
            pytest.raises(exceptions.UserMissingFieldError) as exc_info,
        ):
            await client.users.update_user("jsmith", {"primary_id": "jsmith"})
        assert exc_info.value.user_id == "jsmith"
        assert "Missing mandatory field" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_non_401664_error_propagates_unchanged(self, client: AlmaClient) -> None:
        """Other APIClientErrors must not be swallowed as UserMissingFieldError."""
        api_err = exceptions.APIClientError("401861", "User not found")
        with (
            patch.object(client, "_execute", new=AsyncMock(side_effect=api_err)),
            pytest.raises(exceptions.APIClientError) as exc_info,
        ):
            await client.users.update_user("jsmith", {})
        assert type(exc_info.value) is exceptions.APIClientError
        assert exc_info.value.code == "401861"


class TestCreateUserErrors:
    @pytest.mark.asyncio
    async def test_missing_field_raises_with_primary_id(self, client: AlmaClient) -> None:
        """create_user extracts user_id from user['primary_id'], not from a param."""
        api_err = exceptions.APIClientError("401664", "Missing mandatory field")
        user: dict[str, Any] = {"primary_id": "jnewuser"}
        with (
            patch.object(client, "_execute", new=AsyncMock(side_effect=api_err)),
            pytest.raises(exceptions.UserMissingFieldError) as exc_info,
        ):
            await client.users.create_user(user)
        assert exc_info.value.user_id == "jnewuser"


class TestRenewLoanErrors:
    @pytest.mark.asyncio
    async def test_cannot_renew_sets_loan_id(self, client: AlmaClient) -> None:
        """Code 401822 re-raised as CannotRenewError with loan_id set."""
        api_err = exceptions.APIClientError("401822", "Cannot renew loan")
        with (
            patch.object(client, "_execute", new=AsyncMock(side_effect=api_err)),
            pytest.raises(exceptions.CannotRenewError) as exc_info,
        ):
            await client.users.loans.renew_loan("jsmith", "LOAN-123")
        assert exc_info.value.loan_id == "LOAN-123"
        assert "Cannot renew" in exc_info.value.message


class TestCreateRequestGuard:
    @pytest.mark.asyncio
    async def test_both_ids_raises(self, client: AlmaClient) -> None:
        """Both mms_id and item_id provided → ValueError before _execute is called."""
        with pytest.raises(ValueError, match="exactly one of mms_id or item_id"):
            await client.users.requests.create_request("jsmith", {}, mms_id="111", item_id="222")

    @pytest.mark.asyncio
    async def test_neither_id_raises(self, client: AlmaClient) -> None:
        """Neither mms_id nor item_id provided → ValueError before _execute is called."""
        with pytest.raises(ValueError, match="exactly one of mms_id or item_id"):
            await client.users.requests.create_request("jsmith", {}, mms_id="", item_id="")


class TestUpdateItemErrors:
    @pytest.mark.asyncio
    async def test_invalid_code_raises(self, client: AlmaClient) -> None:
        """RequestFailedError with 'Invalid X code: Y' message → InvalidCodeError."""
        # e.message is "{msg} [{code}]" from _AlmaError, so regex captures "ABC [400]"
        rf_err = exceptions.RequestFailedError("400", "Request failed: Invalid Library code: ABC")
        with (
            patch.object(client, "_execute", new=AsyncMock(side_effect=rf_err)),
            pytest.raises(exceptions.InvalidCodeError) as exc_info,
        ):
            await client.bibs.update_item("MMS1", "HOLD1", "ITEM1", {})
        assert "Invalid Library" in exc_info.value.message


class TestAnalyticsPagination:
    @pytest.mark.asyncio
    async def test_get_full_report_paginates(self, client: AlmaClient) -> None:
        """get_full_report fetches multiple pages until IsFinished == 'true'."""
        with patch.object(
            client.analytics,
            "get_raw_report",
            new=AsyncMock(side_effect=[_PAGE1_XML, _PAGE2_XML]),
        ):
            result = await client.analytics.get_full_report("/some/path")
        # 1 row from page1 + 2 rows from page2
        assert len(result) == 3
        # Header mapping: Column1 → "Title"; Column0 filtered out
        assert result[0] == {"Title": "Book A"}
        assert result[1] == {"Title": "Book B"}
        assert result[2] == {"Title": "Book C"}

    @pytest.mark.asyncio
    async def test_get_full_report_single_row_returns_list(self, client: AlmaClient) -> None:
        """xmltodict returns a dict for a single <Row>; get_full_report must coerce to list."""
        with patch.object(
            client.analytics,
            "get_raw_report",
            new=AsyncMock(return_value=_SINGLE_ROW_XML),
        ):
            result = await client.analytics.get_full_report("/some/path")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == {"Title": "Only Book"}


class TestBaseNamespaceModelParam:
    @pytest.mark.asyncio
    async def test_get_passes_model_to_execute(self, client: AlmaClient) -> None:
        """_get must forward model= kwarg to _execute."""
        from almapy._endpoints import AlmaEndpoint

        mock_model = MagicMock()
        with patch.object(client, "_execute", new=AsyncMock(return_value=Box())) as mock_exec:
            await client.users._get(AlmaEndpoint.USERS, model=mock_model)
        assert mock_exec.call_args.kwargs.get("model") is mock_model
