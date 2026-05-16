# ===============================
# rate_limiter.py - Async Rate Limiter for Yahoo Finance
# ===============================

import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """Token bucket rate limiter for async contexts"""

    def __init__(self, max_calls: int = 30, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.tokens = float(max_calls)
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
        self.total_waited = 0.0

    async def acquire(self, tokens: int = 1):
        """Acquire tokens, waiting if necessary"""
        async with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Calculate wait time
            wait_time = (tokens - self.tokens) * (self.period / self.max_calls)
            self.total_waited += wait_time
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

            self._refill()
            self.tokens -= tokens

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.max_calls,
            self.tokens + elapsed * (self.max_calls / self.period)
        )
        self.last_refill = now

    @property
    def available(self) -> float:
        self._refill()
        return self.tokens
