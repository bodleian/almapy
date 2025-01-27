"""Fixtures."""

import pytest
from almapy import AlmaClient
from environs import Env
from gracy import GracyReplay
from gracy.replays.storages.sqlite import SQLiteReplayStorage

MOCK = True


@pytest.fixture
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
