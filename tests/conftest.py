"""Fixtures."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from environs import Env
from typeguard import install_import_hook

# Must run before almapy is imported anywhere. --typeguard-packages relies on
# the plugin's hook being installed before the first import, but conftest is
# imported earlier than that, so the flag silently did nothing and every run
# printed InstrumentationWarning: "cannot check these packages because they are
# already imported: almapy". Installing the hook here is order-independent.
install_import_hook("almapy")

from almapy import AlmaClient  # noqa: E402 — must follow install_import_hook

# Integration credentials and patron data live OUTSIDE tests/ on purpose: tests/
# is packaged into the sdist, so anything dropped in there rides along into a
# published artifact. Both paths below are gitignored and never shipped.
_ROOT = Path(__file__).parent.parent
_ENV_FILE = _ROOT / ".env"
_BARCODES_FILE = _ROOT / ".testdata" / "barcodes.txt"


@pytest.fixture
def client() -> AlmaClient:
    """Fixture to set up an AlmaClient with a placeholder API key."""
    return AlmaClient("test-api-key")


def _load_env() -> Env:
    """Load .env into an Env instance.

    environs >= 15 loads into the Env's own store rather than os.environ, so the
    values must be read back off this object — os.environ.get() returns nothing.
    """
    env = Env()
    env.read_env(str(_ENV_FILE), override=False)
    return env


def _load_api_key() -> str:
    return _load_env().str("API_KEY", "")


@pytest.fixture(scope="session")
def repeat_count() -> int:
    """Barcodes to use per integration test — INTEGRATION_REPEAT_COUNT, default 50."""
    return max(1, _load_env().int("INTEGRATION_REPEAT_COUNT", 50))


def _require_integration() -> None:
    if not os.environ.get("ALMA_INTEGRATION"):
        pytest.skip("Set ALMA_INTEGRATION=1 to run integration tests")


@pytest.fixture
async def integration_client() -> AsyncGenerator[AlmaClient, None]:
    """Real AlmaClient at default rate (25 req/s). Function-scoped to avoid throttle state leakage."""
    _require_integration()
    api_key = _load_api_key() or pytest.skip("API_KEY not set in .env (see .env.example)")
    async with AlmaClient(api_key) as client:
        yield client


@pytest.fixture(scope="session")
async def fast_integration_client() -> AsyncGenerator[AlmaClient, None]:
    """Real AlmaClient at 200 req/s to provoke 429s. Session-scoped so backoff state carries into recovery test."""
    _require_integration()
    api_key = _load_api_key() or pytest.skip("API_KEY not set in .env (see .env.example)")
    async with AlmaClient(api_key, rate_limit=200.0) as client:
        yield client


@pytest.fixture(scope="session")
def barcodes() -> list[str]:
    """Item barcodes loaded from .testdata/barcodes.txt (one per line, # lines ignored)."""
    if not _BARCODES_FILE.exists():
        pytest.skip(f"{_BARCODES_FILE} not found; add one item barcode per line")
    lines = _BARCODES_FILE.read_text().splitlines()
    result = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    if not result:
        pytest.skip(f"{_BARCODES_FILE} is empty")
    return result
