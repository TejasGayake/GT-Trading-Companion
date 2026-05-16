# ===============================
# utils/helpers.py - Helper Functions
# ===============================

import re
from datetime import datetime, timedelta
from typing import Union, Optional, List, Dict, Any
import pandas as pd
import numpy as np

def parse_token(token_str: str) -> tuple:
    """
    Parse token string to extract token and exchange
    
    Args:
        token_str: String like "3045-1" or "3045"
    
    Returns:
        Tuple of (token, exchange_type)
    """
    if "-" in token_str:
        token, exch = token_str.split("-")
        return token.strip(), int(exch)
    return token_str.strip(), 1  # Default to NSE

def format_token(token: str, exchange: int = 1) -> str:
    """Format token for Excel"""
    return f"{token}-{exchange}"

def safe_divide(a: Union[int, float], b: Union[int, float], default: float = 0) -> float:
    """Safe division to avoid division by zero"""
    try:
        if b and b != 0:
            return a / b
        return default
    except:
        return default

def round_if_number(value: Any, decimals: int = 2) -> Any:
    """Round if value is a number, otherwise return as is"""
    if isinstance(value, (int, float)):
        return round(value, decimals)
    return value

def timestamp_to_time(ts: int) -> str:
    """Convert timestamp to time string"""
    try:
        return datetime.fromtimestamp(ts/1000).strftime("%H:%M:%S")
    except:
        return ""

def calculate_change(current: float, previous: float) -> tuple:
    """Calculate absolute and percentage change"""
    if previous == 0:
        return 0, 0
    abs_change = current - previous
    pct_change = (abs_change / previous) * 100
    return round(abs_change, 2), round(pct_change, 2)

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def get_market_status() -> dict:
    """Get current market status"""
    now = datetime.now()
    
    # Market hours: 9:15 AM to 3:30 PM, Monday to Friday
    is_weekday = now.weekday() < 5  # 0-4 = Monday-Friday
    
    market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    is_market_hours = is_weekday and market_start <= now <= market_end
    
    return {
        "is_market_open": is_market_hours,
        "is_weekday": is_weekday,
        "current_time": now,
        "next_open": market_start + timedelta(days=1) if now > market_end else market_start,
        "next_close": market_end
    }