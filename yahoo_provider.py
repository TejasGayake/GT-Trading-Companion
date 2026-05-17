# ===============================
# yahoo_provider.py - Yahoo Finance Data Provider
# ===============================
"""
Yahoo Finance provider for replacing Angel One API.
No API key required, no static IP needed.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List, Dict
import time
import threading

from utils.logger import get_logger


def _retry_on_rate_limit(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator that retries Yahoo API calls with exponential backoff on 429/rate limit errors."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            self = args[0]  # First arg is self (YahooFinanceProvider)
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    if "too many requests" in error_str or "429" in error_str or "rate limit" in error_str:
                        last_error = e
                        delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s
                        self.logger.warning(f"Rate limited on {func.__name__}, retry {attempt+1}/{max_retries} after {delay:.0f}s")
                        time.sleep(delay)
                    else:
                        raise  # Non-rate-limit error, propagate immediately
            # All retries exhausted
            raise last_error
        return wrapper
    return decorator


class YahooFinanceProvider:
    """Yahoo Finance data provider with caching"""

    def __init__(self, symbol_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize provider with optional symbol mapping.

        Args:
            symbol_mapping: Dict mapping token -> Yahoo symbol (e.g., {"5097": "ETERNAL.NS"})
        """
        self.logger = get_logger('YahooFinanceProvider')
        self.symbol_mapping = symbol_mapping or {}

        # Caching
        self._candle_cache: Dict[str, tuple] = {}  # (timestamp, data)
        self._quote_cache: Dict[str, tuple] = {}   # (timestamp, data)
        self._prev_day_cache: Dict[str, tuple] = {}  # (timestamp, data) for previous day
        self.CACHE_DURATION = 120  # 2 minutes for candles
        self.QUOTE_CACHE_DURATION = 10  # 10 seconds for quotes (was 2s, caused excessive API hits)
        self.PREV_DAY_CACHE_DURATION = 3600  # 1 hour for previous day data

        self.logger.info("YahooFinanceProvider initialized (no API key needed)")

    def set_symbol_mapping(self, mapping: Dict[str, str]):
        """Set the token to symbol mapping"""
        self.symbol_mapping = mapping
        self.logger.info(f"Set {len(mapping)} token -> symbol mappings")

    def get_yahoo_symbol(self, token: str) -> str:
        """Convert token to Yahoo symbol"""
        # Check mapping first
        if token in self.symbol_mapping:
            return self.symbol_mapping[token]

        # Default: add .NS suffix
        return f"{token}.NS"

    @_retry_on_rate_limit(max_retries=3, base_delay=2.0)
    def get_candles(self, token: str, days: int = 5, interval: str = "5m") -> Optional[List]:
        """
        Fetch historical candles matching Angel One format.

        Args:
            token: Token number like '5097'
            days: Number of days of data
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 1d)

        Returns:
            List of candles in format: [timestamp, open, high, low, close, volume]
            or None on error
        """
        # Check cache
        cache_key = f"candles_{token}_{interval}_{days}"
        if cache_key in self._candle_cache:
            ts, data = self._candle_cache[cache_key]
            if time.time() - ts < self.CACHE_DURATION:
                self.logger.debug(f"Using cached candles for {token}")
                return data

        try:
            yahoo_symbol = self.get_yahoo_symbol(token)
            self.logger.info(f"Fetching candles for {token} -> {yahoo_symbol}")

            # Fetch data
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(period=f"{days}d", interval=interval)

            if df.empty:
                self.logger.warning(f"No data returned for {yahoo_symbol}")
                return []

            # Convert to Angel One format: [timestamp, open, high, low, close, volume]
            candles = []
            for idx, row in df.iterrows():
                # Convert to milliseconds
                timestamp = int(idx.timestamp() * 1000)

                # Convert prices from rupees to paise
                open_price = int(row['Open'] * 100)
                high_price = int(row['High'] * 100)
                low_price = int(row['Low'] * 100)
                close_price = int(row['Close'] * 100)
                volume = int(row['Volume'])

                candles.append([timestamp, open_price, high_price, low_price, close_price, volume])

            # Cache the result
            self._candle_cache[cache_key] = (time.time(), candles)

            self.logger.info(f"Got {len(candles)} candles for {token}")
            return candles

        except Exception as e:
            self.logger.error(f"Error fetching candles for {token}: {e}")
            return None

    @_retry_on_rate_limit(max_retries=3, base_delay=2.0)
    def get_previous_day_candles(self, token: str) -> Optional[Dict]:
        """
        Get previous day's OHLC for Camarilla pivot calculation.

        Args:
            token: Token number

        Returns:
            Dict with 'open', 'high', 'low', 'close' in PAISE, or None on error
        """
        # Check cache
        cache_key = f"prev_day_{token}"
        if cache_key in self._prev_day_cache:
            ts, data = self._prev_day_cache[cache_key]
            if time.time() - ts < self.PREV_DAY_CACHE_DURATION:
                return data

        try:
            yahoo_symbol = self.get_yahoo_symbol(token)
            ticker = yf.Ticker(yahoo_symbol)

            # Get last 2 days of daily data
            df = ticker.history(period="2d", interval="1d")
            if df.empty or len(df) < 1:
                return None

            # Use the first day (previous trading day)
            prev_day = df.iloc[0] if len(df) > 1 else df.iloc[-1]

            result = {
                'open': int(prev_day['Open'] * 100),
                'high': int(prev_day['High'] * 100),
                'low': int(prev_day['Low'] * 100),
                'close': int(prev_day['Close'] * 100),
                'volume': int(prev_day['Volume'])
            }

            # Cache the result
            self._prev_day_cache[cache_key] = (time.time(), result)
            return result

        except Exception as e:
            self.logger.error(f"Error fetching previous day data for {token}: {e}")
            return None

    @_retry_on_rate_limit(max_retries=3, base_delay=2.0)
    def get_live_quote(self, token: str) -> Optional[Dict]:
        """
        Get current live quote for a token.

        Args:
            token: Token number

        Returns:
            Dictionary with tick data matching Angel One format (prices in PAISE)
        """
        # Check cache (shorter duration for quotes)
        if token in self._quote_cache:
            ts, data = self._quote_cache[token]
            if time.time() - ts < self.QUOTE_CACHE_DURATION:
                return data

        try:
            yahoo_symbol = self.get_yahoo_symbol(token)

            # Fetch live quote
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.fast_info

            # Handle case where fast_info is None
            if info is None:
                self.logger.warning(f"No fast_info available for {yahoo_symbol}, using ticker.info")
                ticker_info = ticker.info
                if ticker_info is None:
                    self.logger.warning(f"No info available for {yahoo_symbol}")
                    return None
                current_price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice') or 0
                open_price = ticker_info.get('open', current_price)
                high_price = ticker_info.get('dayHigh', current_price)
                low_price = ticker_info.get('dayLow', current_price)
                close_price = ticker_info.get('previousClose', current_price)
                volume = ticker_info.get('volume', 0) or 0
                fifty_two_week_high = ticker_info.get('fiftyTwoWeekHigh', current_price * 1.2) or current_price * 1.2
                fifty_two_week_low = ticker_info.get('fiftyTwoWeekLow', current_price * 0.8) or current_price * 0.8
                avg_price = ticker_info.get('averageVolume', current_price) or current_price
            else:
                # Get current price
                current_price = info.last_price or 0
                if current_price == 0:
                    # Try different attribute
                    current_price = info.previous_close or 0

                # Get other data
                open_price = info.open or current_price
                high_price = info.day_high or current_price
                low_price = info.day_low or current_price
                # Get previous close from history for accuracy (fast_info can be stale)
                close_price = current_price  # fallback
                try:
                    hist_df = ticker.history(period="2d", interval="1d")
                    if not hist_df.empty and len(hist_df) >= 2:
                        close_price = float(hist_df['Close'].iloc[-2])
                    elif not hist_df.empty and len(hist_df) == 1:
                        close_price = float(hist_df['Close'].iloc[0])
                    else:
                        close_price = info.previous_close or current_price
                except Exception:
                    close_price = info.previous_close or current_price

                # Volume - use different methods as FastInfo varies by version
                try:
                    volume = info.volume or 0
                except AttributeError:
                    # Try alternative: get from ticker.info
                    ticker_info = ticker.info
                    volume = ticker_info.get('volume', 0) or 0 if ticker_info else 0

                # 52 week high/low - use getattr to handle version differences
                fifty_two_week_high = getattr(info, 'fifty_two_week_high', None)
                if fifty_two_week_high is None:
                    ticker_info = ticker.info
                    fifty_two_week_high = ticker_info.get('fiftyTwoWeekHigh', current_price * 1.2) or current_price * 1.2 if ticker_info else current_price * 1.2

                fifty_two_week_low = getattr(info, 'fifty_two_week_low', None)
                if fifty_two_week_low is None:
                    ticker_info = ticker.info
                    fifty_two_week_low = ticker_info.get('fiftyTwoWeekLow', current_price * 0.8) or current_price * 0.8 if ticker_info else current_price * 0.8

                # Average traded price (use current as fallback)
                avg_price = getattr(info, 'average_volume', 0) or current_price

            # Get exchange timestamp
            exchange_timestamp = int(time.time() * 1000)

            # Build response in Angel One format
            quote = {
                "token": token,
                "last_traded_price": int(current_price * 100),  # Convert to paise
                "volume_trade_for_the_day": int(volume),
                "exchange_timestamp": exchange_timestamp,
                "open_price_of_the_day": int(open_price * 100),
                "high_price_of_the_day": int(high_price * 100),
                "low_price_of_the_day": int(low_price * 100),
                "closed_price": int(close_price * 100),
                "average_traded_price": int(avg_price * 100),
                "52_week_high_price": int(fifty_two_week_high * 100),
                "52_week_low_price": int(fifty_two_week_low * 100)
            }

            # Cache the result
            self._quote_cache[token] = (time.time(), quote)

            return quote

        except Exception as e:
            self.logger.error(f"Error fetching quote for {token}: {e}")
            return None

    def get_quotes_batch(self, tokens: List[str]) -> Dict[str, Dict]:
        """Get quotes for multiple tokens efficiently"""
        results = {}

        # Use threading for parallel fetch (optional optimization)
        for token in tokens:
            quote = self.get_live_quote(token)
            if quote:
                results[token] = quote

        return results

    def get_symbol(self, token: str) -> str:
        """Get symbol name from token"""
        if token in self.symbol_mapping:
            symbol = self.symbol_mapping[token]
            # Remove .NS suffix for display
            return symbol.replace('.NS', '')
        return f"TKN-{token}"

    def load_symbol_master(self) -> bool:
        """Load symbols - simplified for Yahoo Finance"""
        self.logger.info(f"Yahoo Finance - using {len(self.symbol_mapping)} symbol mappings")
        return True

    def is_quote_cache_fresh(self, token: str) -> bool:
        """Check if quote cache is still fresh (avoids unnecessary API calls)"""
        if token in self._quote_cache:
            ts, _ = self._quote_cache[token]
            return time.time() - ts < self.QUOTE_CACHE_DURATION
        return False

    def is_candle_cache_fresh(self, token: str, interval: str = "5m", days: int = 5) -> bool:
        """Check if candle cache is still fresh"""
        cache_key = f"candles_{token}_{interval}_{days}"
        if cache_key in self._candle_cache:
            ts, _ = self._candle_cache[cache_key]
            return time.time() - ts < self.CACHE_DURATION
        return False

    def is_prev_day_cache_fresh(self, token: str) -> bool:
        """Check if previous day cache is still fresh"""
        cache_key = f"prev_day_{token}"
        if cache_key in self._prev_day_cache:
            ts, _ = self._prev_day_cache[cache_key]
            return time.time() - ts < self.PREV_DAY_CACHE_DURATION
        return False

    def get_cached_quote(self, token: str) -> Optional[Dict]:
        """Get quote from cache if fresh, otherwise None"""
        if token in self._quote_cache:
            ts, data = self._quote_cache[token]
            if time.time() - ts < self.QUOTE_CACHE_DURATION:
                return data
        return None

    def get_cached_candles(self, token: str, interval: str = "5m", days: int = 5) -> Optional[List]:
        """Get candles from cache if fresh, otherwise None"""
        cache_key = f"candles_{token}_{interval}_{days}"
        if cache_key in self._candle_cache:
            ts, data = self._candle_cache[cache_key]
            if time.time() - ts < self.CACHE_DURATION:
                return data
        return None

    def get_cached_prev_day(self, token: str) -> Optional[Dict]:
        """Get previous day data from cache if fresh, otherwise None"""
        cache_key = f"prev_day_{token}"
        if cache_key in self._prev_day_cache:
            ts, data = self._prev_day_cache[cache_key]
            if time.time() - ts < self.PREV_DAY_CACHE_DURATION:
                return data
        return None

    def close(self):
        """Cleanup"""
        self.logger.info("YahooFinanceProvider closed")
        self._candle_cache.clear()
        self._quote_cache.clear()


# Singleton instance (will be initialized with symbol mapping)
_provider_instance = None


def get_provider(symbol_mapping: Optional[Dict[str, str]] = None) -> YahooFinanceProvider:
    """Get or create the provider singleton"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = YahooFinanceProvider(symbol_mapping)
    return _provider_instance