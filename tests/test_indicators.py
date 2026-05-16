# ===============================
# test_indicators.py - Test Indicator Calculation
# ===============================

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.credentials import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET
from angel_api.client import AngelAPIClient
from indicators.calculator import IndicatorCalculator
import time
from utils.logger import get_logger


def test_indicators():
    self.logger.debug("Testing Indicator Calculator...")
    
    # Initialize client
    client = AngelAPIClient(API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET)
    calculator = IndicatorCalculator(client)
    
    # Test token 2885 (ITC)
    token = "2885"
    self.logger.debug(f"\nCalculating indicators for token {token}...")
    
    indicators = calculator.calculate_indicators(token, force=True)
    
    if indicators:
        self.logger.info(f"✅ Success!")
        self.logger.debug(f"   RSI14: {indicators.rsi14}")
        self.logger.debug(f"   SMA20: {indicators.sma20}")
        self.logger.debug(f"   SMA40: {indicators.sma40}")
        self.logger.debug(f"   Volume Avg: {indicators.volume_avg}")
        self.logger.debug(f"   VWAP: {indicators.vwap}")
        self.logger.debug(f"   Support: {indicators.support}")
        self.logger.debug(f"   Resistance: {indicators.resistance}")
    else:
        self.logger.error(f"❌ Failed to calculate indicators")
    
    client.close()

if __name__ == "__main__":
    test_indicators()