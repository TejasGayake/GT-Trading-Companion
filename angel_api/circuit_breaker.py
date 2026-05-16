# ===============================
# angel_api/circuit_breaker.py - Circuit Breaker
# ===============================

import time
import threading
from enum import Enum
from utils.logger import get_logger
from angel_api.exceptions import CircuitBreakerError

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker pattern for API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 half_open_limit: int = 3):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            half_open_limit: Number of test requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_limit = half_open_limit
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_successes = 0
        self.last_failure_time = None
        self.lock = threading.RLock()
        self.logger = get_logger('CircuitBreaker')
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    self.logger.info("Circuit breaker half-open, testing recovery")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN (failures: {self.failure_count})"
                    )
            
            if self.state == CircuitState.HALF_OPEN and self.half_open_successes >= self.half_open_limit:
                self._transition_to(CircuitState.CLOSED)
                self.logger.info("Circuit breaker closed - recovery successful")
        
        try:
            result = func(*args, **kwargs)
            
            with self.lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.half_open_successes += 1
                    if self.half_open_successes >= self.half_open_limit:
                        self._transition_to(CircuitState.CLOSED)
                        self.logger.info("Circuit breaker closed - recovery successful")
            
            return result
            
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == CircuitState.HALF_OPEN:
                    self._transition_to(CircuitState.OPEN)
                    self.logger.warning(f"Test request failed, circuit re-opened")
                elif self.failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    self.logger.warning(
                        f"Circuit breaker OPEN after {self.failure_count} failures"
                    )
            
            raise e
    
    def _transition_to(self, new_state: CircuitState):
        """Transition to new state"""
        self.state = new_state
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.half_open_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.half_open_successes = 0
    
    def reset(self):
        """Reset circuit breaker"""
        with self.lock:
            self._transition_to(CircuitState.CLOSED)
            self.last_failure_time = None
            self.logger.info("Circuit breaker reset")
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self.state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed"""
        return self.state == CircuitState.CLOSED
    
    def get_state(self) -> dict:
        """Get current state"""
        with self.lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure': self.last_failure_time,
                'recovery_timeout': self.recovery_timeout
            }