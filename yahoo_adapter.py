# ===============================
# yahoo_adapter.py - Angel One API Compatible Adapter
# ===============================
"""
Adapter to make Yahoo Finance work with existing Angel One API interface.
Drop-in replacement for AngelAPIClient.
"""

from typing import Optional, List, Dict

from yahoo_provider import YahooFinanceProvider, get_provider
from yahoo_websocket import LiveDataStream, start_stream, subscribe, get_stream
from utils.logger import get_logger


class YahooAdapter:
    """
    Drop-in replacement for AngelAPIClient using Yahoo Finance.
    Provides the same interface as AngelAPIClient.
    """

    def __init__(self, symbol_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize Yahoo Finance adapter.

        Args:
            symbol_mapping: Optional dict mapping token -> Yahoo symbol
        """
        self.logger = get_logger('YahooAdapter')

        # Initialize provider with symbol mapping
        self.provider = get_provider(symbol_mapping)

        # Also store mapping directly
        self.symbol_mapping = symbol_mapping or {}
        if symbol_mapping:
            self.provider.set_symbol_mapping(symbol_mapping)

        # Login is not needed for Yahoo Finance
        self.auth_token = "yahoo_no_auth_needed"
        self.feed_token = "yahoo_no_feed_token"
        self.refresh_token = "yahoo_no_refresh_token"

        # For compatibility - represent as logged in
        self._logged_in = True

        self.logger.info("✅ YahooAdapter initialized (no login required)")

    def login(self) -> bool:
        """Login - not needed for Yahoo Finance, always returns True"""
        self.logger.info("Yahoo Finance doesn't require login")
        return True

    def get_candles(self, token: str, days: int = 5) -> Optional[List]:
        """
        Get historical candles.

        Args:
            token: Token number like '5097'
            days: Number of days of data

        Returns:
            List of candles in Angel One format: [timestamp, open, high, low, close, volume]
        """
        return self.provider.get_candles(token, days=days)

    def get_symbol(self, token: str) -> str:
        """Get symbol name from token"""
        return self.provider.get_symbol(token)

    def load_symbol_master(self) -> bool:
        """Load symbols"""
        return self.provider.load_symbol_master()

    def close(self):
        """Cleanup"""
        self.provider.close()
        self.logger.info("YahooAdapter closed")

    # Additional methods for compatibility
    def get_live_quote(self, token: str) -> Optional[Dict]:
        """Get live quote for a token"""
        return self.provider.get_live_quote(token)

    def get_quotes_batch(self, tokens: List[str]) -> Dict[str, Dict]:
        """Get quotes for multiple tokens"""
        return self.provider.get_quotes_batch(tokens)


# Factory function for compatibility
def create_yahoo_client(symbol_mapping: Optional[Dict[str, str]] = None) -> YahooAdapter:
    """Create Yahoo Finance client with optional symbol mapping"""
    return YahooAdapter(symbol_mapping)


# Alias for easy migration
AngelAPIClient = YahooAdapter  # Drop-in replacement


# Export the websocket functions with same names as angel_api
__all__ = [
    'YahooAdapter',
    'YahooFinanceProvider',
    'LiveDataStream',
    'create_yahoo_client',
    'AngelAPIClient',  # Alias for drop-in replacement
    'start_stream',
    'subscribe',
    'get_stream'
]