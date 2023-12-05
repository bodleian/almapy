"""Tests for almapy.users."""

import pytest
from environs import Env
from gracy.replays.storages._base import GracyReplay
from gracy.replays.storages.sqlite import SQLiteReplayStorage

from almapy import AlmaClient

MOCK = True


@pytest.fixture()
def client() -> AlmaClient:
    """Fixture to set up an AlmaClient, in either record or replay mode."""
    if MOCK:
        mode = GracyReplay("replay", SQLiteReplayStorage("alma.sqlite3", dir=".gracy"))
    else:
        mode = GracyReplay("record", SQLiteReplayStorage("alma.sqlite3", dir=".gracy"))
    env = Env()
    env.read_env(".env")
    client = AlmaClient(env("API_KEY", ""), replay=mode)
    return client


class TestUserLoans:
    """User loan tests."""

    @staticmethod
    @pytest.mark.asyncio()
    async def test_get_loans(client: AlmaClient) -> None:
        """Test whether the get_loans method works."""
        resp = await client.user.loans.get_loans("ben.olis", loan_status="Complete")
        assert resp.item_loan


class TestUser:
    """User tests."""

    @staticmethod
    @pytest.mark.asyncio()
    async def test_get_user(client: AlmaClient) -> None:
        """Test whether the get_user method retrieves a user correctly."""
        resp = await client.user.get_user("ben.olis")
        assert resp.primary_id == "ben.olis"
