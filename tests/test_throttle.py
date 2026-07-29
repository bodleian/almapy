"""Tests for TokenBucket and AdaptiveController."""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch

import pytest

from almapy._throttle import AdaptiveController, TokenBucket


class TestTokenBucket:
    def test_rejects_zero_rate(self) -> None:
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucket(0)

    def test_rejects_negative_rate(self) -> None:
        with pytest.raises(ValueError, match="rate must be positive"):
            TokenBucket(-1)

    @pytest.mark.asyncio
    async def test_acquire_immediate(self) -> None:
        bucket = TokenBucket(10.0)
        start = time.monotonic()
        await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1
        # Direct attribute access to verify exactly 1 token was consumed:
        # _tokens starts at 10.0, minus 1 consumed, plus tiny refill ≈ 9.0
        assert 8.5 <= bucket._tokens <= 9.1

    def test_rate_setter(self) -> None:
        bucket = TokenBucket(25.0)
        bucket.rate = 10.0
        assert bucket.rate == pytest.approx(10.0)
        # Direct attribute access to verify token consumption invariant:
        # setter does self._tokens = min(self._tokens, value) → min(25.0, 10.0)
        assert bucket._tokens == pytest.approx(10.0)

    def test_rate_setter_rejects_zero(self) -> None:
        bucket = TokenBucket(25.0)
        with pytest.raises(ValueError, match="rate must be positive"):
            bucket.rate = 0

    def test_rate_setter_rejects_negative(self) -> None:
        bucket = TokenBucket(25.0)
        with pytest.raises(ValueError, match="rate must be positive"):
            bucket.rate = -5

    @pytest.mark.asyncio
    async def test_rate_setter_caps_tokens(self) -> None:
        """If rate is lowered, existing token count should be capped at new rate."""
        bucket = TokenBucket(10.0)  # starts with 10 tokens
        bucket.rate = 3.0  # cap tokens at 3
        # Should be able to acquire 3 immediately
        for _ in range(3):
            await bucket.acquire()
        # 4th should require waiting
        start = time.monotonic()
        await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed > 0.1

    @pytest.mark.asyncio
    async def test_acquire_waits_when_empty(self) -> None:
        """At rate=5, exhaust 5 tokens then verify 6th waits ~0.2s."""
        bucket = TokenBucket(5.0)
        # Exhaust all tokens
        for _ in range(5):
            await bucket.acquire()
        # Next acquire must wait
        start = time.monotonic()
        await bucket.acquire()
        elapsed = time.monotonic() - start
        assert 0.1 < elapsed < 0.5
        # After waiting and consuming one newly-generated token, bucket should be near 0
        # Direct attribute access to verify token consumption invariant
        assert bucket._tokens <= 0.2

    @pytest.mark.asyncio
    async def test_concurrent_acquire_no_overdraw(self) -> None:
        """Multiple concurrent acquires should not consume more tokens than available."""
        bucket = TokenBucket(5.0)  # 5 tokens available
        # Launch 10 concurrent acquires — 5 should be immediate, 5 should wait
        start = time.monotonic()
        await asyncio.gather(*[bucket.acquire() for _ in range(10)])
        elapsed = time.monotonic() - start
        # Must have taken at least ~1s to serve all 10 at rate=5/s
        assert elapsed > 0.8
        # Must not have been excessively serialized (deadlock/starvation guard)
        assert elapsed < 3.0
        # Direct attribute access to verify tokens near 0 after all consumed
        assert bucket._tokens <= 0.5


class TestAdaptiveController:
    def test_rejects_invalid_rates(self) -> None:
        bucket = TokenBucket(10.0)
        with pytest.raises(ValueError, match="min_rate <= max_rate"):
            AdaptiveController(bucket, max_rate=5.0, min_rate=10.0)

    def test_record_failure_halves_rate(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0)
        ctrl.record_failure()
        assert bucket.rate == pytest.approx(10.0)

    def test_record_failure_respects_min_rate(self) -> None:
        bucket = TokenBucket(2.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0, min_rate=2.0)
        bucket.rate = 2.0
        ctrl.record_failure()
        assert bucket.rate == pytest.approx(2.0)  # can't go below min_rate

    def test_cooldown_suppresses_failure(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0, cooldown=10.0)
        ctrl.record_failure()  # halves to 10, starts cooldown
        assert bucket.rate == pytest.approx(10.0)
        ctrl.record_failure()  # should be suppressed (still in cooldown)
        assert bucket.rate == pytest.approx(10.0)  # unchanged

    def test_cooldown_suppresses_success(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0, cooldown=10.0)
        ctrl.record_failure()  # halves to 10, starts cooldown
        ctrl.record_success()  # should be suppressed (still in cooldown)
        assert bucket.rate == pytest.approx(10.0)  # unchanged

    def test_recovery_is_time_gated(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(
            bucket,
            max_rate=20.0,
            recovery_increment=1.0,
            recovery_window=100.0,  # very long window — second call won't recover
            cooldown=0.0,  # no cooldown so we can test recovery directly
        )
        bucket.rate = 10.0
        ctrl.record_success()  # first: should increase
        assert bucket.rate == pytest.approx(11.0)
        ctrl.record_success()  # second: too soon, should be no-op
        assert bucket.rate == pytest.approx(11.0)

    def test_recovery_adds_increment(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(
            bucket,
            max_rate=20.0,
            recovery_increment=2.0,
            recovery_window=0.0,  # allow immediate recovery
            cooldown=0.0,
        )
        bucket.rate = 10.0
        ctrl.record_success()
        assert bucket.rate == pytest.approx(12.0)

    def test_recovery_capped_at_max(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(
            bucket,
            max_rate=20.0,
            recovery_increment=5.0,
            recovery_window=0.0,
            cooldown=0.0,
        )
        bucket.rate = 18.0
        ctrl.record_success()
        assert bucket.rate == pytest.approx(20.0)  # capped, not 23

    @pytest.mark.asyncio
    async def test_acquire_waits_cooldown(self) -> None:
        bucket = TokenBucket(100.0)  # high rate so token wait is negligible
        ctrl = AdaptiveController(bucket, max_rate=100.0, cooldown=0.3)
        ctrl.record_failure()
        start = time.monotonic()
        await ctrl.acquire()
        elapsed = time.monotonic() - start
        assert elapsed > 0.2

    @pytest.mark.asyncio
    async def test_max_wait_raises(self) -> None:
        from almapy.exceptions import ThrottleTimeoutError

        bucket = TokenBucket(100.0)
        ctrl = AdaptiveController(bucket, max_rate=100.0, cooldown=10.0, max_wait=0.1)
        ctrl.record_failure()  # sets 10s cooldown
        with pytest.raises(ThrottleTimeoutError):
            await ctrl.acquire()

    @pytest.mark.asyncio
    async def test_max_wait_none_unlimited(self) -> None:
        """max_wait=None should not raise — asyncio.timeout(None) is a no-op."""
        bucket = TokenBucket(100.0)
        ctrl = AdaptiveController(bucket, max_rate=100.0, cooldown=0.05, max_wait=None)
        ctrl.record_failure()
        # Should complete after short cooldown, not raise
        await ctrl.acquire()

    def test_concurrent_failures_dont_compound(self) -> None:
        """Multiple failures during cooldown should not compound — rate halves once."""
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0, cooldown=10.0)
        # Simulate 10 concurrent failures
        for _ in range(10):
            ctrl.record_failure()
        # Rate should be halved once (10.0), not halved 10 times
        assert bucket.rate == pytest.approx(10.0)

    def test_current_rate_property(self) -> None:
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0)
        assert ctrl.current_rate == pytest.approx(20.0)
        ctrl.record_failure()
        assert ctrl.current_rate == pytest.approx(10.0)


class TestThrottleLogging:
    @pytest.mark.asyncio
    async def test_token_bucket_wait_emits_no_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """TokenBucket wait path is silent — no DEBUG noise on every throttled request."""
        bucket = TokenBucket(1.0)
        bucket._tokens = 0.0  # force wait path
        with (
            caplog.at_level(logging.DEBUG, logger="almapy.throttle"),
            patch("almapy._throttle.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            with pytest.raises(asyncio.CancelledError):
                await bucket.acquire()
        records = [r for r in caplog.records if r.name == "almapy.throttle"]
        assert len(records) == 0

    def test_record_failure_logs_rate_cut(self, caplog: pytest.LogCaptureFixture) -> None:
        """record_failure logs WARNING with old and new rate."""
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0)
        with caplog.at_level(logging.WARNING, logger="almapy.throttle"):
            ctrl.record_failure()
        records = [r for r in caplog.records if r.name == "almapy.throttle"]
        assert len(records) == 1
        assert "rate cut" in records[0].message
        assert "20.0" in records[0].message
        assert "10.0" in records[0].message

    def test_record_success_logs_recovery(self, caplog: pytest.LogCaptureFixture) -> None:
        """record_success logs INFO with old and new rate."""
        bucket = TokenBucket(10.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0, recovery_window=0.0)
        with caplog.at_level(logging.INFO, logger="almapy.throttle"):
            ctrl.record_success()
        records = [r for r in caplog.records if r.name == "almapy.throttle"]
        assert len(records) == 1
        assert "recovered" in records[0].message

    def test_record_failure_suppressed_during_cooldown_does_not_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When in cooldown, record_failure returns early — no log emitted."""
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0)
        ctrl.record_failure()  # starts cooldown
        caplog.clear()  # discard the first failure log; only check the suppressed call
        with caplog.at_level(logging.WARNING, logger="almapy.throttle"):
            ctrl.record_failure()  # suppressed by cooldown — no log
        records = [r for r in caplog.records if r.name == "almapy.throttle"]
        assert len(records) == 0

    def test_log_records_carry_req_id_field(self, caplog: pytest.LogCaptureFixture) -> None:
        """almapy.throttle records must carry req_id (empty string outside execute())."""
        bucket = TokenBucket(20.0)
        ctrl = AdaptiveController(bucket, max_rate=20.0)
        with caplog.at_level(logging.WARNING, logger="almapy.throttle"):
            ctrl.record_failure()
        for record in caplog.records:
            assert hasattr(record, "req_id"), f"Missing req_id on {record.name}"
            assert isinstance(getattr(record, "req_id", None), str)


class TestRecoveryIsIndependentOfMachineUptime:
    """Recovery gating must not depend on time.monotonic()'s epoch.

    monotonic() counts from an arbitrary reference — boot time on Linux — so
    initialising _last_recovery to 0.0 meant "the first recovery is allowed once
    the machine has been up longer than recovery_window". That passed on any
    developer machine with meaningful uptime and failed on freshly booted CI
    runners, appearing as a Python-version flake because the matrix jobs landed
    on runners with different uptimes.
    """

    @pytest.mark.parametrize("uptime", [0.0, 0.5, 12.0, 99.0, 100.0, 500_000.0])
    def test_first_recovery_happens_at_any_uptime(self, uptime: float) -> None:
        with patch("almapy._throttle.time.monotonic", return_value=uptime):
            bucket = TokenBucket(20.0)
            ctrl = AdaptiveController(
                bucket,
                max_rate=20.0,
                recovery_increment=1.0,
                recovery_window=100.0,
                cooldown=0.0,
            )
            bucket.rate = 10.0
            ctrl.record_success()

        assert bucket.rate == pytest.approx(11.0), (
            f"first recovery refused at uptime {uptime}s — gating depends on the "
            f"monotonic epoch rather than on elapsed time"
        )

    def test_second_recovery_within_the_window_is_still_refused(self) -> None:
        """The gate must still work; -inf only unblocks the *first* recovery."""
        with patch("almapy._throttle.time.monotonic", return_value=5.0):
            bucket = TokenBucket(20.0)
            ctrl = AdaptiveController(
                bucket,
                max_rate=20.0,
                recovery_increment=1.0,
                recovery_window=100.0,
                cooldown=0.0,
            )
            bucket.rate = 10.0
            ctrl.record_success()
            assert bucket.rate == pytest.approx(11.0)
            ctrl.record_success()
            assert bucket.rate == pytest.approx(11.0), "recovered twice inside the window"
