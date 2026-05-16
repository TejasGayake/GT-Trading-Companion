# ===============================
# angel_api/rate_limiter.py - Rate Limiter
# ===============================

import time
import threading
from utils.logger import get_logger

class RateLimiter:
    """Token bucket rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 30, period: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.tokens = max_calls
        self.last_refill = time.time()
        self.lock = threading.RLock()
        self.logger = get_logger('RateLimiter')
        self.total_waited = 0
    
    def acquire(self, tokens: int = 1, block: bool = True) -> bool:
        """
        Acquire tokens for API call
        
        Args:
            tokens: Number of tokens to acquire
            block: Whether to block until tokens available
            
        Returns:
            True if tokens acquired, False otherwise
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if not block:
                self.logger.debug(f"Rate limit would block, tokens available: {self.tokens}")
                return False
            
            # Calculate wait time
            wait_time = (tokens - self.tokens) * (self.period / self.max_calls)
            self.total_waited += wait_time
            self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            
            # Release lock while waiting
            self.lock.release()
            time.sleep(wait_time)
            self.lock.acquire()
            
            # Try again
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.max_calls,
            self.tokens + elapsed * (self.max_calls / self.period)
        )
        self.last_refill = now
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get wait time if tokens not available"""
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                return 0
            return (tokens - self.tokens) * (self.period / self.max_calls)
    
    @property
    def available_tokens(self) -> float:
        """Get available tokens"""
        with self.lock:
            self._refill()
            return self.tokens
    
    def reset(self):
        """Reset rate limiter"""
        with self.lock:
            self.tokens = self.max_calls
            self.last_refill = time.time()
            self.total_waited = 0