"""Fixtures."""

import pytest

from almapy import AlmaClient


@pytest.fixture
def client() -> AlmaClient:
    """Fixture to set up an AlmaClient with a placeholder API key."""
    return AlmaClient("test-api-key")
