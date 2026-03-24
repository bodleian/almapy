"""Fixtures."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from environs import Env

from almapy import AlmaClient

_BARCODES_FILE = Path(__file__).parent / "barcodes.txt"


@pytest.fixture
def client() -> AlmaClient:
    """Fixture to set up an AlmaClient with a placeholder API key."""
    return AlmaClient("test-api-key")


def _load_api_key() -> str:
    env = Env()
    env.read_env(str(Path(__file__).parent / ".env"), override=False)
    return os.environ.get("API_KEY", "")


def _require_integration() -> None:
    if not os.environ.get("ALMA_INTEGRATION"):
        pytest.skip("Set ALMA_INTEGRATION=1 to run integration tests")


@pytest.fixture
async def integration_client() -> AsyncGenerator[AlmaClient, None]:
    """Real AlmaClient at default rate (25 req/s). Function-scoped to avoid throttle state leakage."""
    _require_integration()
    api_key = _load_api_key() or pytest.skip("API_KEY not set in tests/.env")
    async with AlmaClient(api_key) as client:
        yield client


@pytest.fixture(scope="session")
async def fast_integration_client() -> AsyncGenerator[AlmaClient, None]:
    """Real AlmaClient at 200 req/s to provoke 429s. Session-scoped so backoff state carries into recovery test."""
    _require_integration()
    api_key = _load_api_key() or pytest.skip("API_KEY not set in tests/.env")
    async with AlmaClient(api_key, rate_limit=200.0) as client:
        yield client


@pytest.fixture(scope="session")
def barcodes() -> list[str]:
    """Item barcodes loaded from tests/barcodes.txt (one per line, # lines ignored)."""
    if not _BARCODES_FILE.exists():
        pytest.skip("tests/barcodes.txt not found; add one barcode per line")
    lines = _BARCODES_FILE.read_text().splitlines()
    result = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    if not result:
        pytest.skip("tests/barcodes.txt is empty")
    return result
