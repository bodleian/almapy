"""Adaptive rate limiting with AIMD backpressure.

Three separated concerns:
- TokenBucket: async token-bucket rate limiter with mutable rate
- AdaptiveController: AIMD logic adjusting a TokenBucket's rate
- asyncio.Semaphore: concurrency cap (used directly, no wrapper needed)
"""

import asyncio
import time

from almapy.exceptions import ThrottleTimeoutError


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
        return self._rate

    @rate.setter
    def rate(self, value: float) -> None:
        if value <= 0:
            msg = f"rate must be positive, got {value}"
            raise ValueError(msg)
        self._rate = value
        self._tokens = min(self._tokens, value)

    async def acquire(self) -> None:
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
        self._last_recovery: float = 0.0

    @property
    def current_rate(self) -> float:
        return self._bucket.rate

    async def acquire(self) -> None:
        try:
            async with asyncio.timeout(self._max_wait):
                cool = self._cooling_until - time.monotonic()
                if cool > 0:
                    await asyncio.sleep(cool)
                await self._bucket.acquire()
        except TimeoutError as exc:
            raise ThrottleTimeoutError from exc

    def record_failure(self) -> None:
        now = time.monotonic()
        if now < self._cooling_until:
            return
        new_rate = max(self._min_rate, self._bucket.rate * self._backoff_factor)
        self._bucket.rate = new_rate
        self._cooling_until = now + self._cooldown

    def record_success(self) -> None:
        now = time.monotonic()
        if now < self._cooling_until:
            return
        if self._bucket.rate >= self._max_rate:
            return
        if now - self._last_recovery < self._recovery_window:
            return
        self._bucket.rate = min(self._max_rate, self._bucket.rate + self._recovery_increment)
        self._last_recovery = now
