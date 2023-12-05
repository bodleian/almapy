"""Tests for almapy.users."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from almapy import AlmaClient


class TestUserLoans:
    """User loan tests."""

    @staticmethod
    @pytest.mark.asyncio()
    async def test_get_loans(client: AlmaClient) -> None:
        """Test whether the get_loans method works."""
        resp = await client.users.loans.get_loans("ben.olis", loan_status="Complete")
        assert resp.item_loan


class TestUser:
    """User tests."""

    @staticmethod
    @pytest.mark.asyncio()
    async def test_get_user(client: AlmaClient) -> None:
        """Test whether the get_user method retrieves a user correctly."""
        resp = await client.users.get_user("ben.olis")
        assert resp.primary_id == "ben.olis"
