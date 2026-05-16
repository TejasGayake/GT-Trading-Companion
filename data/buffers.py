# ===============================
# data/buffers.py - Circular Buffers
# ===============================

from collections import deque
import threading
from typing import List, Any, Optional
from datetime import datetime, timedelta
from data.models import TickData, CandleData

class CircularBuffer:
    """Thread-safe circular buffer for tick storage"""
    
    def __init__(self, maxlen: int = 1000):
        self.buffer = deque(maxlen=maxlen)
        self.lock = threading.RLock()
        self.maxlen = maxlen
    
    def append(self, item: Any):
        """Append item to buffer"""
        with self.lock:
            self.buffer.append(item)
    
    def extend(self, items: List[Any]):
        """Extend buffer with multiple items"""
        with self.lock:
            self.buffer.extend(items)
    
    def get_all(self) -> List[Any]:
        """Get all items"""
        with self.lock:
            return list(self.buffer)
    
    def get_last(self, n: int) -> List[Any]:
        """Get last n items"""
        with self.lock:
            return list(self.buffer)[-n:]
    
    def get_since(self, timestamp: datetime) -> List[Any]:
        """Get items since timestamp"""
        with self.lock:
            return [item for item in self.buffer 
                   if hasattr(item, 'timestamp') and item.timestamp >= timestamp]
    
    def clear(self):
        """Clear buffer"""
        with self.lock:
            self.buffer.clear()
    
    @property
    def size(self) -> int:
        """Get current size"""
        with self.lock:
            return len(self.buffer)
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full"""
        with self.lock:
            return len(self.buffer) == self.maxlen

class TickBuffer(CircularBuffer):
    """Specialized buffer for tick data"""
    
    def __init__(self, maxlen: int = 1000):
        super().__init__(maxlen)
    
    def get_price_history(self, minutes: int = 5) -> List[float]:
        """Get price history for last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        ticks = self.get_since(cutoff)
        return [t.ltp for t in ticks]
    
    def get_volume_history(self, minutes: int = 5) -> List[int]:
        """Get volume history for last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        ticks = self.get_since(cutoff)
        return [t.volume for t in ticks]
    
    def get_last_price(self) -> Optional[float]:
        """Get last price"""
        last = self.get_last(1)
        return last[0].ltp if last else None

class CandleBuffer(CircularBuffer):
    """Specialized buffer for candle data"""
    
    def __init__(self, maxlen: int = 500):
        super().__init__(maxlen)
    
    def to_dataframe(self):
        """Convert to pandas DataFrame"""
        import pandas as pd
        candles = self.get_all()
        
        if not candles:
            return pd.DataFrame()
        
        data = [{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles]
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


 