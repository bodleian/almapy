"""Adaptive rate limiting with AIMD backpressure.

Three separated concerns:
- TokenBucket: async token-bucket rate limiter with mutable rate
- AdaptiveController: AIMD logic adjusting a TokenBucket's rate
- asyncio.Semaphore: concurrency cap (used directly, no wrapper needed)
"""

import asyncio
import logging
import time

from almapy._logging import request_id
from almapy.exceptions import ThrottleTimeoutError

_throttle_log = logging.getLogger("almapy.throttle")


class TokenBucket:
    """Async token-bucket rate limiter with mutable rate.

    Invariants:
        0 < rate
        0 <= _tokens <= rate  (burst capacity == rate, i.e. 1 second of tokens)
        _lock serialises refill + consume so concurrent callers cannot overdraw
    """

    def __init__(self, rate: float) -> None:
        if rate <= 0:
            msg = f"rate must be positive, got {rate}"
            raise ValueError(msg)
        self._rate = rate
        self._tokens = rate
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def rate(self) -> float:
        """Current refill rate in tokens (requests) per second.

        Setting it clamps the outstanding token count to the new rate, so lowering
        the rate takes effect immediately rather than after an accumulated burst is
        spent.

        Raises:
            ValueError: If set to zero or a negative value.
        """
        return self._rate

    @rate.setter
    def rate(self, value: float) -> None:
        if value <= 0:
            msg = f"rate must be positive, got {value}"
            raise ValueError(msg)
        self._rate = value
        self._tokens = min(self._tokens, value)

    async def acquire(self) -> None:
        """Consume one token, waiting for the bucket to refill if it is empty.

        Never times out – it waits as long as necessary. Use
        [`AdaptiveController.acquire`][almapy._throttle.AdaptiveController.acquire]
        for a bounded wait.
        """
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = 1.0 - self._tokens
                wait = deficit / self._rate
            await asyncio.sleep(wait)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
        self._last_refill = now


class AdaptiveController:
    """AIMD-style controller: halve rate on failure, +recovery_increment per recovery_window on success.

    Invariants:
        0 < min_rate <= max_rate
        During cooldown: neither record_failure nor record_success adjusts the rate
        Recovery is time-gated: at most one +recovery_increment per recovery_window
    """

    def __init__(
        self,
        bucket: TokenBucket,
        max_rate: float,
        *,
        backoff_factor: float = 0.5,
        recovery_increment: float = 1.0,
        recovery_window: float = 10.0,
        cooldown: float = 5.0,
        max_wait: float | None = None,
        min_rate: float = 1.0,
    ) -> None:
        if not (0 < min_rate <= max_rate):
            msg = f"require 0 < min_rate <= max_rate, got min_rate={min_rate}, max_rate={max_rate}"
            raise ValueError(msg)
        self._bucket = bucket
        self._max_rate = max_rate
        self._backoff_factor = backoff_factor
        self._recovery_increment = recovery_increment
        self._recovery_window = recovery_window
        self._cooldown = cooldown
        self._max_wait = max_wait
        self._min_rate = min_rate
        self._cooling_until: float = 0.0
        # "never recovered", not "recovered at monotonic zero". time.monotonic()
        # counts from an arbitrary epoch – process or boot time depending on the
        # platform – so 0.0 made the first recovery wait until the epoch was
        # older than recovery_window. On a freshly booted host that delayed it
        # for no reason, and it made the recovery tests depend on machine uptime.
        self._last_recovery: float = float("-inf")

    @property
    def current_rate(self) -> float:
        """The rate the underlying bucket is currently running at, in requests/second.

        Read-only, and lower than the configured maximum whenever backpressure has
        cut it. Useful for monitoring – logging it, or exporting it as a metric.
        """
        return self._bucket.rate

    async def acquire(self) -> None:
        """Wait for cooldown to elapse, then consume one token from the bucket.

        Raises:
            ThrottleTimeoutError: If ``max_wait`` was configured and elapsed before a
                token became available. Subclasses ``TimeoutError``, so
                ``except TimeoutError`` catches it too.
        """
        try:
            async with asyncio.timeout(self._max_wait):
                cool = self._cooling_until - time.monotonic()
                if cool > 0:
                    await asyncio.sleep(cool)
                await self._bucket.acquire()
        except TimeoutError as exc:
            raise ThrottleTimeoutError from exc

    def record_failure(self) -> None:
        """Report a transient failure, cutting the rate multiplicatively.

        Multiplies the rate by ``backoff_factor`` (never below ``min_rate``) and
        starts a cooldown, during which further failures are ignored – a burst of
        concurrent failures from one incident cuts the rate once, not once per
        request.

        Called for any failure ``_should_retry`` recognises, deliberately including
        those on POST and PATCH requests that will not themselves be replayed: a 5xx
        says something about Alma's health whichever verb provoked it.
        """
        now = time.monotonic()
        if now < self._cooling_until:
            return  # suppressed – no log
        old_rate = self._bucket.rate
        new_rate = max(self._min_rate, old_rate * self._backoff_factor)
        self._bucket.rate = new_rate
        self._cooling_until = now + self._cooldown
        _throttle_log.warning(
            "AdaptiveController: rate cut %.1f -> %.1f req/s (failure)",
            old_rate,
            new_rate,
            extra={"req_id": request_id.get(), "old_rate": old_rate, "new_rate": new_rate},
        )

    def record_success(self) -> None:
        """Report a successful request, recovering the rate additively.

        Adds ``recovery_increment`` to the rate, up to ``max_rate``. Recovery is
        time-gated to at most once per ``recovery_window`` and suppressed entirely
        during cooldown, so the rate climbs back gradually rather than jumping
        straight to the maximum after one success.
        """
        now = time.monotonic()
        if now < self._cooling_until:
            return  # suppressed – no log
        if self._bucket.rate >= self._max_rate:
            return  # already at max – no log
        if now - self._last_recovery < self._recovery_window:
            return  # too soon – no log
        old_rate = self._bucket.rate
        self._bucket.rate = min(self._max_rate, old_rate + self._recovery_increment)
        self._last_recovery = now
        _throttle_log.info(
            "AdaptiveController: rate recovered %.1f -> %.1f req/s",
            old_rate,
            self._bucket.rate,
            extra={"req_id": request_id.get(), "old_rate": old_rate, "new_rate": self._bucket.rate},
        )
