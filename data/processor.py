# ===============================
# data/processor.py - Complete Tick Processor with All Fixes
# ===============================

import threading
import queue
import time
from typing import Set, List, Dict, Optional, Callable
from datetime import datetime

from utils.logger import get_logger
from data.models import TickData, IndicatorData
from data.buffers import TickBuffer

class TickProcessor:
    """Process incoming ticks - NO Excel calls, only queue updates"""
    
    def __init__(self, indicator_calculator, alert_system, api_client=None, symbol_loader=None):
        """
        Initialize tick processor
        
        Args:
            indicator_calculator: IndicatorCalculator instance
            alert_system: AlertSystem instance
            api_client: AngelAPIClient instance (for symbol lookup)
            symbol_loader: SymbolLoader instance (for Excel symbol mapping)
        """
        self.indicator_calc = indicator_calculator
        self.alert_system = alert_system
        self.api_client = api_client
        self.symbol_loader = symbol_loader
        self.logger = get_logger('TickProcessor')
        
        # ========================================================
        # STEP 2: Queues - INCREASED for 200+ tokens
        # ========================================================
        self.tick_queue = queue.Queue(maxsize=50000)   # Was 10000
        self.excel_queue = queue.Queue(maxsize=50000)  # Was 10000
        
        # State
        self.active_tokens = set()
        self.token_buffers = {}
        self.running = False
        
        # Threads
        self.processor_thread = None
        
        # Statistics
        self.ticks_processed = 0
        self.last_print = time.time()
        self.token_tick_count = {}
        
        # ========================================================
        # STEP 1: Batch size - INCREASED for 200+ tokens
        # ========================================================
        self.batch_size = 100  # Was 20
        
        # Common symbols for fallback (if API client not available)
        self.common_symbols = {
            "2885": "ITC",
            "3045": "RELIANCE",
            "1594": "TCS",
            "11536": "HDFC",
            "1660": "INFY",
            "17818": "HDFCBANK",
            "1394": "ICICIBANK",
            "4963": "SBIN",
            "3499": "TATAMOTORS",
            "10738": "TATASTEEL",
            "3501": "TATAPOWER",
            "3401": "SUNPHARMA",
            "14977": "BHARTIARTL",
            "2475": "KOTAKBANK",
            "11630": "WIPRO",
            "10940": "TECHM",
            "1901": "BAJFINANCE",
            "317": "BAJAJFINSV",
            "11915": "MARUTI",
            "910": "M&M",
            "1035": "ASIANPAINT",
            "881": "HINDUNILVR",
            "17963": "NESTLE",
            "467": "BRITANNIA",
            "1232": "TITAN",
            "1348": "ULTRACEMCO",
            "10789": "GRASIM",
            "1512": "JSWSTEEL",
            "11723": "NTPC",
            "11532": "ONGC",
            "247": "POWERGRID",
            "3493": "SHREECEM",
            "4373": "SBILIFE",
            "12167": "ICICIPRULI",
            "6351": "DIVISLAB",
            "12038": "DRREDDY",
            "3751": "CIPLA",
            "1245": "UPL",
            "3791": "EICHERMOT",
            "323": "BPCL",
        }
    
    def _get_symbol(self, token: str) -> str:
        """Get symbol name for token"""
        clean_token = str(token).split('.')[0]
        
        # 1. Use symbol loader from Excel FIRST (highest priority)
        if hasattr(self, 'symbol_loader') and self.symbol_loader and hasattr(self.symbol_loader, 'loaded') and self.symbol_loader.loaded:
            try:
                excel_symbol = self.symbol_loader.get_symbol(clean_token)
                if excel_symbol and not excel_symbol.startswith("TKN-"):
                    self.logger.debug(f"Symbol from loader: {clean_token} → {excel_symbol}")
                    return excel_symbol
            except Exception as e:
                self.logger.debug(f"Symbol loader error for {clean_token}: {e}")
        
        # 2. Try API client second
        if self.api_client and hasattr(self.api_client, 'get_symbol'):
            try:
                symbol = self.api_client.get_symbol(clean_token)
                if symbol and symbol != clean_token and not symbol.startswith("TKN-"):
                    self.logger.debug(f"Symbol from API: {clean_token} → {symbol}")
                    return symbol
            except Exception as e:
                self.logger.debug(f"API symbol error for {clean_token}: {e}")
        
        # 3. Fallback to common symbols dictionary
        if clean_token in self.common_symbols:
            self.logger.debug(f"Symbol from common: {clean_token} → {self.common_symbols[clean_token]}")
            return self.common_symbols[clean_token]
        
        # 4. Ultimate fallback
        self.logger.debug(f"Symbol fallback TKN- for {clean_token}")
        return f"TKN-{clean_token}"
    
    def start(self):
        """Start processor thread"""
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.processor_thread.start()
        self.logger.info("Tick processor started")
    
    def stop(self):
        """Stop processor"""
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        self.logger.info("Tick processor stopped")
    
    def add_tick(self, msg: dict):
        """Add tick to queue"""
        try:
            self.tick_queue.put(msg, timeout=1)
        except queue.Full:
            self.logger.warning("Tick queue full, dropping tick")
    
    def get_excel_updates(self):
        """Get queued updates for Excel (call from main thread only)"""
        updates = []
        while not self.excel_queue.empty():
            try:
                updates.append(self.excel_queue.get_nowait())
            except queue.Empty:
                break
        return updates
    
    # ========================================================
    # STEP 3: Updated _process_loop with DEBUG logging
    # ========================================================
    def _process_loop(self):
        """Processing loop - runs in background thread - OPTIMIZED"""
        self.logger.info("Processing loop started")
        
        while self.running:
            try:
                # Process ticks in LARGER batches (STEP 1)
                batch_count = 0
                while batch_count < self.batch_size and not self.tick_queue.empty():
                    try:
                        msg = self.tick_queue.get(timeout=0.1)
                        self._process_tick(msg)
                        self.ticks_processed += 1
                        batch_count += 1
                    except queue.Empty:
                        break
                
                # Log stats occasionally - CHANGED TO DEBUG (STEP 3)
                if time.time() - self.last_print > 60:  # Changed to 60 seconds
                    queue_size = self.tick_queue.qsize()
                    self.logger.debug(f"Stats - Total ticks: {self.ticks_processed}, "
                                   f"Queue: {queue_size}, "
                                   f"Active tokens: {len(self.active_tokens)}")
                    
                    if self.token_tick_count:
                        # Only log top 10 tokens
                        top_tokens = sorted(self.token_tick_count.items(), 
                                           key=lambda x: x[1], reverse=True)[:10]
                        self.logger.debug(f"Top tokens by ticks: {dict(top_tokens)}")
                    
                    self.last_print = time.time()
                
                # Small sleep to prevent CPU overload
                time.sleep(0.005)  # 5ms instead of 10ms
                
            except Exception as e:
                self.logger.error(f"Process loop error: {e}")
                time.sleep(0.1)  # Shorter sleep on error
    
    # ========================================================
    # STEP 3: Updated _process_tick with DEBUG logging
    # ========================================================
    def _process_tick(self, msg: dict):
        """Process a single tick - OPTIMIZED"""
        try:
            token = str(msg["token"])
            
            # Skip if not active
            if token not in self.active_tokens:
                return
            
            # Track counts
            if token not in self.token_tick_count:
                self.token_tick_count[token] = 0
            self.token_tick_count[token] += 1
            
            # Get symbol name
            symbol = self._get_symbol(token)
            
            # Create tick data with symbol function
            tick = TickData.from_message(msg, lambda t: self._get_symbol(t))
            
            # Store in buffer
            if token not in self.token_buffers:
                self.token_buffers[token] = TickBuffer(maxlen=1000)
                self.logger.debug(f"Created buffer for token {token} ({symbol})")  # DEBUG
            self.token_buffers[token].append(tick)
            
            # Get indicators - this returns an IndicatorData object
            indicators = self.indicator_calc.calculate_indicators(token)
            
            # Debug first few ticks only - CHANGED TO DEBUG (STEP 3)
            if self.token_tick_count[token] <= 1:
                if indicators:
                    self.logger.debug(f"Indicators for {symbol}: "  # DEBUG
                                   f"RSI={indicators.rsi14:.1f}, "
                                   f"SMA21={indicators.sma21:.2f}, "
                                   f"Volume Avg={indicators.volume_avg:.0f}")
            
            # Check alerts
            alerts = []
            if indicators:
                alerts = self.alert_system.check_tick(tick, indicators, self.token_buffers[token])
            
            # Always ensure we have an IndicatorData object
            if indicators is None:
                indicators = IndicatorData(
                    token=token,
                    timestamp=datetime.now(),
                    sma21=0, sma40=0, sma200=0, rsi14=50,
                    ema10=0, supertrend=0, camarilla_h4=0, camarilla_l4=0,
                    vwap=0, prev_high=0, prev_low=0,
                    volume_avg=0, volatility=0, support=0, resistance=0
                )
            
            # 52-week data - keep as INFO (important for debugging)
            if self.token_tick_count[token] <= 3:
                self.logger.info(f"52-week data for {symbol}: High={tick.week_52_high}, Low={tick.week_52_low}")
            
            # Queue for Excel (to be processed by main thread)
            self.excel_queue.put((tick, indicators, alerts))
            
            # Log first few ticks - CHANGED TO DEBUG (STEP 3)
            if self.token_tick_count[token] <= 3:
                self.logger.debug(f"Tick for {symbol}: LTP={tick.ltp}, Change={tick.change}%")  # DEBUG
            
        except Exception as e:
            self.logger.error(f"Error processing tick for {msg.get('token', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
    
    def update_subscriptions(self, new_tokens: Set[str]):
        """Update active tokens"""
        old_tokens = self.active_tokens
        self.active_tokens = new_tokens
        
        added = new_tokens - old_tokens
        removed = old_tokens - new_tokens
        
        if added:
            self.logger.info(f"Added {len(added)} new tokens")
            for token in added:
                self.token_tick_count[token] = 0
        
        if removed:
            self.logger.info(f"Removed {len(removed)} tokens")
            for token in removed:
                if token in self.token_buffers:
                    del self.token_buffers[token]
                if token in self.token_tick_count:
                    del self.token_tick_count[token]
        
        self.logger.info(f"Active tokens: {len(self.active_tokens)}")
    
    def get_buffer(self, token: str) -> Optional[TickBuffer]:
        """Get buffer for token"""
        return self.token_buffers.get(token)
    
    def get_stats(self) -> dict:
        """Get processor statistics"""
        return {
            'ticks_processed': self.ticks_processed,
            'active_tokens': len(self.active_tokens),
            'queue_size': self.tick_queue.qsize(),
            'excel_queue_size': self.excel_queue.qsize(),
            'buffers': len(self.token_buffers),
        }