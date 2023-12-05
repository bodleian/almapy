"""Tests for generic client functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from almapy import AlmaClient


class TestThrottling:
    """Test rate limiting."""

    def test_default(self, client: AlmaClient) -> None:
        """Test the baked-in 25/s limit."""
