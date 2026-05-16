# ===============================
# utils/validators.py - Data Validators
# ===============================

import re
from typing import Union, Optional, Any
from datetime import datetime

def validate_token(token: str) -> bool:
    """Validate token format"""
    if not token or not isinstance(token, str):
        return False
    return bool(re.match(r'^\d+$', token.strip()))

def validate_exchange_type(exchange: int) -> bool:
    """Validate exchange type"""
    return exchange in [1, 2]  # 1=NSE, 2=BSE

def validate_excel_format(token_str: str) -> bool:
    """Validate Excel format (TOKEN-EXCHANGE)"""
    if not token_str or not isinstance(token_str, str):
        return False
    
    pattern = r'^\d+-\d+$'
    return bool(re.match(pattern, token_str.strip()))

def validate_price(price: Union[int, float, None]) -> bool:
    """Validate price value"""
    if price is None:
        return False
    try:
        price = float(price)
        return price >= 0
    except:
        return False

def validate_volume(volume: Union[int, float, None]) -> bool:
    """Validate volume value"""
    if volume is None:
        return False
    try:
        volume = int(volume)
        return volume >= 0
    except:
        return False

def validate_tick_data(data: dict) -> bool:
    """Validate tick data message"""
    required_fields = ['token', 'last_traded_price', 'exchange_timestamp']
    
    for field in required_fields:
        if field not in data:
            return False
    
    return True

def validate_candle_data(candles: list) -> bool:
    """Validate candle data"""
    if not candles or not isinstance(candles, list):
        return False
    
    required_length = 6  # timestamp, open, high, low, close, volume
    
    for candle in candles:
        if not isinstance(candle, list) or len(candle) != required_length:
            return False
        
        # Check numeric values
        for i in range(1, 6):  # Skip timestamp
            try:
                float(candle[i])
            except:
                return False
    
    return True