# ===============================
# angel_api/exceptions.py - Custom Exceptions
# ===============================

class AngelAPIError(Exception):
    """Base exception for Angel API"""
    pass

class AuthenticationError(AngelAPIError):
    """Authentication failed"""
    pass

class RateLimitError(AngelAPIError):
    """Rate limit exceeded"""
    pass

class CircuitBreakerError(AngelAPIError):
    """Circuit breaker is open"""
    pass

class APITimeoutError(AngelAPIError):
    """API request timeout"""
    pass

class InvalidTokenError(AngelAPIError):
    """Invalid token provided"""
    pass

class DataNotFoundError(AngelAPIError):
    """Data not found"""
    pass