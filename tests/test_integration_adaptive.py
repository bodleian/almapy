"""Integration tests: validate adaptive rate-limiting against the real Alma API.

Tests are skipped unless ALMA_INTEGRATION=1 is set (enforced by the fixtures).
Barcodes are loaded from tests/barcodes.txt (one per line).

Test ordering matters: test_backoff_triggered_by_api must run before
test_recovery_after_backoff because they share the session-scoped
fast_integration_client whose throttle state carries between them.
pytest collects class methods in definition order (Python 3.7+ dict ordering),
so the order here is intentional.
"""

import asyncio
import os
import time
from collections.abc import Callable

import pytest

from almapy import AlmaClient
from almapy.exceptions import BarcodeNotFoundError


def _repeat_count() -> int:
    """Number of barcodes to use per test. Reads INTEGRATION_REPEAT_COUNT from env (default 50)."""
    val = os.environ.get("INTEGRATION_REPEAT_COUNT", "50")
    try:
        return max(1, int(val))
    except ValueError:
        return 50


@pytest.mark.integration
class TestAdaptiveRateLimit:
    async def test_volume_all_succeed(
        self, integration_client: AlmaClient, barcodes: list[str]
    ) -> None:
        """All barcodes return item_data at the default rate limit with no errors."""
        targets = barcodes[: _repeat_count()]

        async def fetch(barcode: str) -> None:
            try:
                result = await integration_client.bibs.get_item(barcode)
            except BarcodeNotFoundError as exc:
                pytest.fail(f"Barcode {barcode!r} not found — check tests/barcodes.txt: {exc}")
            assert "item_data" in result, f"item_data missing from response for barcode {barcode!r}"

        await asyncio.gather(*(fetch(b) for b in targets))

    async def test_throughput_within_cap(
        self, integration_client: AlmaClient, barcodes: list[str]
    ) -> None:
        """Elapsed time proves TokenBucket is enforcing the configured rate cap.

        The TokenBucket starts with burst capacity == rate tokens, so the first
        `rate` requests fire immediately. The remaining (n - rate) requests are
        throttled. Minimum elapsed = (n - rate) / rate seconds.
        """
        targets = barcodes[: _repeat_count()]
        n = len(targets)
        rate: float = integration_client._controller._max_rate

        t0 = time.monotonic()
        await asyncio.gather(*(integration_client.bibs.get_item(b) for b in targets))
        elapsed = time.monotonic() - t0

        # Only meaningful when we exceed the burst capacity
        if n > rate:
            min_expected = (n - rate) / rate * 0.9  # 10% tolerance for scheduling jitter
            assert elapsed >= min_expected, (
                f"Completed {n} requests in {elapsed:.2f}s; "
                f"expected >= {min_expected:.2f}s at {rate} req/s — "
                "TokenBucket may not be enforcing the cap"
            )

    async def test_backoff_triggered_by_api(
        self, fast_integration_client: AlmaClient, barcodes: list[str]
    ) -> None:
        """Burst at rate_limit=200 should trigger real 429s and depress current_rate.

        Uses an observation-only spy on record_failure (no behaviour change) and
        a background sampler to capture current_rate mid-burst.
        """
        count = max(_repeat_count() * 4, 200)
        targets = [barcodes[i % len(barcodes)] for i in range(count)]

        failure_count = 0
        original_rf: Callable[[], None] = fast_integration_client._controller.record_failure

        def _spy_record_failure() -> None:
            nonlocal failure_count
            failure_count += 1
            original_rf()

        fast_integration_client._controller.record_failure = _spy_record_failure  # type: ignore[method-assign]

        sampled_rates: list[float] = []
        stop_event = asyncio.Event()

        async def _sample_rates() -> None:
            while not stop_event.is_set():
                sampled_rates.append(fast_integration_client._controller.current_rate)
                await asyncio.sleep(0.05)

        initial_rate: float = fast_integration_client._controller.current_rate
        sampler = asyncio.create_task(_sample_rates())
        try:
            await asyncio.gather(*(fast_integration_client.bibs.get_item(b) for b in targets))
        finally:
            stop_event.set()
            await sampler
            fast_integration_client._controller.record_failure = original_rf  # type: ignore[method-assign]

        if failure_count == 0:
            pytest.xfail(
                "API did not return any 429s during this run — cannot validate backoff behaviour"
            )

        assert failure_count > 0, "Expected record_failure() to be called at least once"

        # Guard against empty sample list (burst completed before first 50ms tick)
        min_sampled = min(sampled_rates) if sampled_rates else initial_rate
        assert min_sampled < initial_rate, (
            f"Rate never dropped below initial {initial_rate:.1f} req/s mid-burst "
            f"(min sampled: {min_sampled:.1f}); backoff may not be working"
        )

    async def test_recovery_after_backoff(
        self, fast_integration_client: AlmaClient, barcodes: list[str]
    ) -> None:
        """After cooldown + recovery_window, current_rate climbs above the post-backoff level.

        Relies on fast_integration_client being session-scoped so the depressed rate
        from test_backoff_triggered_by_api is still visible here.
        """
        depressed_rate: float = fast_integration_client._controller.current_rate
        max_rate: float = fast_integration_client._controller._max_rate

        if depressed_rate >= max_rate:
            pytest.skip(
                "Rate is at max — no prior backoff detected "
                "(was test_backoff_triggered_by_api skipped or xfailed?)"
            )

        cooldown: float = fast_integration_client._controller._cooldown
        recovery_window: float = fast_integration_client._controller._recovery_window
        wait_secs = cooldown + recovery_window + 1.0  # extra second buffer

        await asyncio.sleep(wait_secs)

        # Fire successful requests to trigger record_success() recovery increments
        recovery_targets = [barcodes[i % len(barcodes)] for i in range(20)]
        await asyncio.gather(*(fast_integration_client.bibs.get_item(b) for b in recovery_targets))

        recovered_rate: float = fast_integration_client._controller.current_rate
        assert recovered_rate > depressed_rate, (
            f"Rate did not recover: was {depressed_rate:.1f} req/s, "
            f"still {recovered_rate:.1f} req/s after {wait_secs:.0f}s wait "
            f"and {len(recovery_targets)} successful requests"
        )
