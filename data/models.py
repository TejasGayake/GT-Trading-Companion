# ===============================
# data/models.py - UPDATED with new indicators
# ===============================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class ExchangeType(Enum):
    """Exchange types"""
    NSE = 1
    BSE = 2
    
    def __str__(self):
        return self.name

@dataclass
class TickData:
    """Real-time tick data"""
    token: str
    symbol: str
    ltp: float
    volume: int
    timestamp: datetime
    open: float = 0
    high: float = 0
    low: float = 0
    close: float = 0
    change: float = 0
    change_percent: float = 0
    exchange: str = "NSE"
    exchange_type: int = 1
    week_52_high: float = 0  
    week_52_low: float = 0   
    
    @classmethod
    def from_message(cls, msg: dict, symbol_func) -> 'TickData':
        """Create TickData from WebSocket message"""
        token = str(msg["token"])
        
        # Get symbol using the provided function
        if callable(symbol_func):
            symbol = symbol_func(token)
        else:
            symbol = token
        
        ltp = msg.get("last_traded_price", 0) / 100
        prev = msg.get("closed_price", 0) / 100
        change = ltp - prev
        change_pct = (change / prev * 100) if prev else 0
        
        # Extract 52-week data (divide by 100 to convert from paise to rupees)
        week_52_high = msg.get("52_week_high_price", 0) / 100
        week_52_low = msg.get("52_week_low_price", 0) / 100
        
        return cls(
            token=token,
            symbol=symbol,
            ltp=round(ltp, 2),
            volume=msg.get("volume_trade_for_the_day", 0),
            timestamp=datetime.fromtimestamp(msg["exchange_timestamp"]/1000),
            open=msg.get("open_price_of_the_day", 0)/100,
            high=msg.get("high_price_of_the_day", 0)/100,
            low=msg.get("low_price_of_the_day", 0)/100,
            close=prev,
            change=round(change, 2),
            change_percent=round(change_pct, 2),
            week_52_high=round(week_52_high, 2), 
            week_52_low=round(week_52_low, 2)      
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'token': self.token,
            'symbol': self.symbol,
            'ltp': self.ltp,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'change': self.change,
            'change_percent': self.change_percent
        }

@dataclass
class IndicatorData:
    """Technical indicator data - UPDATED with new fields"""
    token: str
    timestamp: datetime
    sma21: float = 0          # ← CHANGED from sma20
    sma40: float = 0
    sma200: float = 0
    ema10: float = 0           # ← NEW
    supertrend: float = 0      # ← NEW
    camarilla_h4: float = 0    # ← NEW
    camarilla_l4: float = 0    # ← NEW
    prev_day_high: float = 0
    prev_day_low: float = 0
    rsi14: float = 50
    vwap: float = 0
    prev_high: float = 0
    prev_low: float = 0
    volume_avg: float = 0
    volatility: float = 0
    support: float = 0
    resistance: float = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary with rounded values"""
        return {
            'sma21': round(self.sma21, 2) if self.sma21 else 0,
            'sma40': round(self.sma40, 2) if self.sma40 else 0,
            'sma200': round(self.sma200, 2) if self.sma200 else 0,
            'ema10': round(self.ema10, 2) if self.ema10 else 0,
            'supertrend': round(self.supertrend, 2) if self.supertrend else 0,
            'camarilla_h4': round(self.camarilla_h4, 2) if self.camarilla_h4 else 0,
            'camarilla_l4': round(self.camarilla_l4, 2) if self.camarilla_l4 else 0,
            'rsi14': round(self.rsi14, 2) if self.rsi14 else 50,
            'vwap': round(self.vwap, 2) if self.vwap else 0,
            'prev_high': round(self.prev_high, 2) if self.prev_high else 0,
            'prev_low': round(self.prev_low, 2) if self.prev_low else 0,
            'volume_avg': round(self.volume_avg) if self.volume_avg else 0,
            'volatility': round(self.volatility * 100, 2) if self.volatility else 0,
            'support': round(self.support, 2) if self.support else 0,
            'resistance': round(self.resistance, 2) if self.resistance else 0
        }

@dataclass
class CandleData:
    """Historical candle data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    @classmethod
    def from_api(cls, data: list) -> 'CandleData':
        """Create from API response"""
        return cls(
            timestamp=datetime.fromisoformat(data[0].replace('T', ' ')),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=int(data[5])
        )