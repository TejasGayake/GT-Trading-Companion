# ===============================
# yahoo_websocket.py - Polling-based Live Data Stream
# ===============================
"""
Polling-based WebSocket replacement for Yahoo Finance.
Provides real-time data updates using background polling.
"""

import threading
import time
from typing import Callable, List, Dict, Optional
from queue import Queue, Empty

from utils.logger import get_logger
from yahoo_provider import YahooFinanceProvider, get_provider


class LiveDataStream:
    """
    Polling-based live data stream that mimics WebSocket behavior.
    """

    def __init__(self, update_interval: float = 2.0):
        """
        Initialize the live data stream.

        Args:
            update_interval: Polling interval in seconds (default 2.0)
        """
        self.logger = get_logger('LiveDataStream')
        self.update_interval = update_interval

        # State
        self.running = False
        self.subscribed_tokens: set = set()
        self.callback: Optional[Callable] = None
        self.stream_thread: Optional[threading.Thread] = None
        self.provider: Optional[YahooFinanceProvider] = None

        # Rate limiting
        self.max_retries = 3
        self.retry_delay = 5
        self._consecutive_errors = 0
        self._last_successful_poll = 0

        # Thread safety
        self._lock = threading.Lock()

        self.logger.info(f"LiveDataStream initialized (polling every {update_interval}s)")

    def set_provider(self, provider: YahooFinanceProvider):
        """Set the data provider"""
        self.provider = provider

    def start_stream(self, callback: Callable) -> bool:
        """
        Start the live data stream.

        Args:
            callback: Function to call with each tick

        Returns:
            bool: True if stream started successfully
        """
        if self.running:
            self.logger.warning("Stream already running")
            return True

        self.callback = callback
        self.running = True

        # Get provider if not set
        if self.provider is None:
            self.provider = get_provider()

        self.stream_thread = threading.Thread(
            target=self._run_stream,
            args=(callback,),
            daemon=True
        )
        self.stream_thread.start()

        self.logger.info("✅ Live data stream started")
        return True

    def _run_stream(self, callback: Callable):
        """Background thread that polls for data"""
        self.logger.info("Starting live data polling thread...")

        while self.running:
            try:
                if not self.subscribed_tokens:
                    time.sleep(1)
                    continue

                # Poll each subscribed token
                with self._lock:
                    tokens_to_poll = list(self.subscribed_tokens)

                for token in tokens_to_poll:
                    if not self.running:
                        break

                    try:
                        quote = self.provider.get_live_quote(token)
                        if quote:
                            # Call the callback with tick data
                            callback(quote)
                            self._consecutive_errors = 0
                            self._last_successful_poll = time.time()
                        else:
                            self.logger.warning(f"No quote for token {token}")

                    except Exception as e:
                        self.logger.error(f"Error polling {token}: {e}")
                        self._consecutive_errors += 1

                # Wait before next poll cycle
                time.sleep(self.update_interval)

            except Exception as e:
                self.logger.error(f"Stream error: {e}")
                self._consecutive_errors += 1

                if self._consecutive_errors >= self.max_retries:
                    self.logger.error("Max retries reached, stopping stream")
                    self.running = False
                    break

                time.sleep(self.retry_delay)

        self.logger.info("Live data stream stopped")

    def subscribe(self, token_list: List[Dict]) -> bool:
        """
        Subscribe to tokens.

        Args:
            token_list: List of dicts with format [{'exchangeType': 1, 'tokens': [...]}]
                       (matches Angel One's subscribe function format)

        Returns:
            bool: True if subscription successful
        """
        if not token_list:
            self.logger.warning("Empty token list provided")
            return False

        with self._lock:
            # Extract tokens from the list
            for item in token_list:
                exchange_type = item.get('exchangeType', 1)
                tokens = item.get('tokens', [])

                for token in tokens:
                    # Clean token (remove .0 if present)
                    clean_token = str(token).split('.')[0]
                    self.subscribed_tokens.add(clean_token)

        self.logger.info(f"✅ Subscribed to {len(self.subscribed_tokens)} tokens: {list(self.subscribed_tokens)[:10]}...")
        return True

    def add_token(self, token: str):
        """Add a single token to subscription"""
        with self._lock:
            clean_token = str(token).split('.')[0]
            self.subscribed_tokens.add(clean_token)
            self.logger.info(f"Added token {clean_token} to subscription")

    def remove_token(self, token: str):
        """Remove a token from subscription"""
        with self._lock:
            clean_token = str(token).split('.')[0]
            self.subscribed_tokens.discard(clean_token)
            self.logger.info(f"Removed token {clean_token} from subscription")

    def get_subscribed_tokens(self) -> List[str]:
        """Get list of currently subscribed tokens"""
        with self._lock:
            return list(self.subscribed_tokens)

    def is_running(self) -> bool:
        """Check if stream is running"""
        return self.running

    def stop(self):
        """Stop the data stream"""
        self.running = False

        if self.stream_thread:
            self.stream_thread.join(timeout=5)

        self.logger.info("🛑 Live data stream stopped")

    def get_stats(self) -> Dict:
        """Get stream statistics"""
        return {
            "running": self.running,
            "subscribed_tokens": len(self.subscribed_tokens),
            "consecutive_errors": self._consecutive_errors,
            "last_successful_poll": self._last_successful_poll,
            "update_interval": self.update_interval
        }


# Global instance for compatibility with existing code
_live_data_stream = LiveDataStream()


def start_stream(callback: Callable) -> bool:
    """Start live data stream (compatible with angel_api signature)"""
    return _live_data_stream.start_stream(callback)


def subscribe(token_list: List[Dict]) -> bool:
    """Subscribe to tokens (compatible with angel_api signature)"""
    return _live_data_stream.subscribe(token_list)


def get_stream() -> LiveDataStream:
    """Get the live data stream instance"""
    return _live_data_stream