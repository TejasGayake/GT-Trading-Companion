# ===============================
# angel_api/websocket_wrapper.py - Fixed with proper logger import
# ===============================

import threading
import time
from typing import Callable, List, Dict, Any, Optional

# Import your custom logger
from utils.logger import get_logger

# Create logger using your custom logger module
logger = get_logger('WebSocketWrapper')

# Try to import original swv7
try:
    import swv7 as original_swv7
    HAS_ORIGINAL = True
    logger.info(f"✅ Found swv7.py")
    # Check what functions are available
    logger.info(f"   Available functions: {[f for f in dir(original_swv7) if not f.startswith('_')]}")
    
except ImportError as e:
    HAS_ORIGINAL = False
    logger.warning(f"⚠️ swv7.py not found: {e}")

class WebSocketWrapper:
    """Wrapper for swv7 WebSocket functionality"""
    
    def __init__(self):
        self.connected = False
        self.subscribed_tokens = set()
        self.callback = None
        self.ws_thread = None
        self.running = False
        logger.info("WebSocketWrapper initialized")
    
    def start_stream(self, callback: Callable):
        """Start WebSocket stream"""
        self.callback = callback
        self.running = True
        logger.info("Starting WebSocket stream...")
        
        if HAS_ORIGINAL:
            if hasattr(original_swv7, 'start_stream'):
                logger.info("Using original swv7.start_stream")
                self.ws_thread = threading.Thread(
                    target=original_swv7.start_stream,
                    args=(callback,),
                    daemon=True
                )
            elif hasattr(original_swv7, 'run'):
                logger.info("Using original swv7.run")
                self.ws_thread = threading.Thread(
                    target=original_swv7.run,
                    args=(callback,),
                    daemon=True
                )
            else:
                logger.error("No suitable stream function found in swv7")
                self._start_mock_stream(callback)
                return
        else:
            logger.info("Starting mock WebSocket (no real data)")
            self._start_mock_stream(callback)
            return
        
        self.ws_thread.start()
        logger.info("WebSocket thread started")
    
    def _start_mock_stream(self, callback):
        """Start mock stream"""
        self.ws_thread = threading.Thread(
            target=self._run_mock,
            args=(callback,),
            daemon=True
        )
        self.ws_thread.start()
        logger.info("Mock WebSocket started")
    
    def _run_mock(self, callback):
        """Mock stream for testing - generates fake data"""
        logger.info("Mock WebSocket running (generating test data)")
        import random
        
        while self.running:
            try:
                # Generate fake tick data for subscribed tokens
                for token in self.subscribed_tokens:
                    # Clean token (remove .0 if present)
                    clean_token = str(token).split('.')[0]
                    
                    # Generate realistic looking data
                    base_price = 2500 if clean_token == "3045" else 3500
                    
                    msg = {
                        "token": clean_token,
                        "last_traded_price": random.randint(base_price - 50, base_price + 50) * 100,
                        "volume_trade_for_the_day": random.randint(1000, 50000),
                        "exchange_timestamp": int(time.time() * 1000),
                        "open_price_of_the_day": base_price * 100,
                        "high_price_of_the_day": (base_price + random.randint(10, 30)) * 100,
                        "low_price_of_the_day": (base_price - random.randint(10, 30)) * 100,
                        "closed_price": base_price * 100,
                        "average_traded_price": base_price * 100,
                        "52_week_high_price": (base_price + 500) * 100,
                        "52_week_low_price": (base_price - 500) * 100
                    }
                    callback(msg)
                
                time.sleep(1)  # Send data every second
                
            except Exception as e:
                logger.error(f"Error in mock stream: {e}")
                time.sleep(5)
    
    def subscribe(self, token_list: List[Dict]):
        """Subscribe to tokens"""
        if not token_list:
            return
        
        # Clean tokens (remove .0)
        cleaned_list = []
        for item in token_list:
            tokens = [str(t).split('.')[0] for t in item.get('tokens', [])]
            cleaned_list.append({
                "exchangeType": item.get('exchangeType', 1),
                "tokens": tokens
            })
        
        # Update local subscription set
        for item in cleaned_list:
            for token in item.get('tokens', []):
                self.subscribed_tokens.add(token)
        
        logger.info(f"Local subscription set: {self.subscribed_tokens}")
        
        # Try to subscribe via original swv7
        if HAS_ORIGINAL and hasattr(original_swv7, 'subscribe'):
            try:
                original_swv7.subscribe(cleaned_list)
                logger.info(f"✅ Subscribed via original swv7 to {len(self.subscribed_tokens)} tokens")
            except Exception as e:
                logger.error(f"❌ Subscription error: {e}")
        else:
            logger.info(f"✅ Mock subscribed to {len(self.subscribed_tokens)} tokens")
    
    def stop(self):
        """Stop WebSocket"""
        self.running = False
        if self.ws_thread:
            self.ws_thread.join(timeout=5)
        logger.info("WebSocket stopped")

# Create global instance
_websocket_wrapper = WebSocketWrapper()

# Export functions
def start_stream(callback):
    return _websocket_wrapper.start_stream(callback)

def subscribe(token_list):
    return _websocket_wrapper.subscribe(token_list)
