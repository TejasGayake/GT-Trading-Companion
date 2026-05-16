"""
Unit tests for the trading dashboard.
Tests indicator calculations, alert logic, and symbol loading.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.calculator import calculate_all_indicators
from utils.symbol_loader import SymbolLoader


class TestCalculateAllIndicators(unittest.TestCase):
    """Test the calculate_all_indicators function"""

    def setUp(self):
        """Create test data"""
        # Sample candles: [timestamp, open, high, low, close, volume] in PAISE
        self.candles = []
        base_price = 100000  # 1000 rupees in paise
        for i in range(30):
            self.candles.append([
                1000000 + i * 300000,  # timestamp
                base_price + i * 100,  # open
                base_price + i * 100 + 500,  # high
                base_price + i * 100 - 500,  # low
                base_price + i * 100 + 200,  # close
                100000 + i * 1000  # volume
            ])

        # Sample live quote in PAISE
        self.live_quote = {
            "last_traded_price": 103200,  # 1032 rupees
            "open_price_of_the_day": 102000,
            "high_price_of_the_day": 104000,
            "low_price_of_the_day": 101000,
            "closed_price": 101500,
            "volume_trade_for_the_day": 500000
        }

    def test_basic_indicators(self):
        """Test that basic indicators are calculated"""
        result = calculate_all_indicators(self.candles, self.live_quote)

        self.assertIn('ltp', result)
        self.assertIn('open', result)
        self.assertIn('high', result)
        self.assertIn('low', result)
        self.assertIn('prev_close', result)
        self.assertIn('volume', result)
        self.assertEqual(result['ltp'], 1032.0)  # 103200 / 100
        self.assertEqual(result['volume'], 500000)

    def test_change_calculation(self):
        """Test price change calculation"""
        result = calculate_all_indicators(self.candles, self.live_quote)

        self.assertIn('change', result)
        self.assertIn('change_percent', result)
        # change = ltp - prev_close = 1032 - 1015 = 17
        self.assertAlmostEqual(result['change'], 17.0, places=1)
        # change_percent = (17 / 1015) * 100 ≈ 1.67%
        self.assertAlmostEqual(result['change_percent'], 1.67, places=1)

    def test_moving_averages(self):
        """Test SMA calculations"""
        result = calculate_all_indicators(self.candles, self.live_quote)

        self.assertIn('sma8', result)
        self.assertIn('sma21', result)
        self.assertIn('volume_sma8', result)

        # SMA8 should be average of last 8 closes
        closes = [c[4] / 100 for c in self.candles]
        expected_sma8 = sum(closes[-8:]) / 8
        self.assertAlmostEqual(result['sma8'], expected_sma8, places=2)

    def test_rsi_calculation(self):
        """Test RSI calculation"""
        # Create candles with mixed up/down moves for proper RSI
        candles = []
        prices = [100, 102, 101, 103, 102, 104, 103, 105, 104, 106, 105, 107, 106, 108, 107, 109, 108, 110, 109, 111]
        for i, price in enumerate(prices):
            candles.append([
                1000000 + i * 300000,
                price * 100 - 200,  # open
                price * 100 + 200,  # high
                price * 100 - 200,  # low
                price * 100,  # close
                100000
            ])

        result = calculate_all_indicators(candles, self.live_quote)

        # RSI requires at least 15 candles with both gains and losses
        if len(candles) >= 15:
            self.assertIn('rsi14', result)
            self.assertGreater(result['rsi14'], 0)
            self.assertLess(result['rsi14'], 100)

    def test_camarilla_with_prev_day(self):
        """Test Camarilla calculation with previous day data"""
        prev_day = {
            'open': 100000,
            'high': 105000,
            'low': 99000,
            'close': 102000,
            'volume': 400000
        }

        result = calculate_all_indicators(self.candles, self.live_quote, prev_day)

        self.assertIn('Camarilla_H4', result)
        self.assertIn('Camarilla_H3', result)
        self.assertIn('Camarilla_L3', result)
        self.assertIn('Camarilla_L4', result)

        # H4 = prev_close + (range * 0.55)
        # range = high - low = 1050 - 990 = 60
        # H4 = 1020 + (60 * 0.55) = 1020 + 33 = 1053
        prev_close = 102000 / 100
        prev_high = 105000 / 100
        prev_low = 99000 / 100
        diff = prev_high - prev_low

        expected_h4 = prev_close + (diff * 0.55)
        self.assertAlmostEqual(result['Camarilla_H4'], expected_h4, places=2)

    def test_camarilla_without_prev_day(self):
        """Test Camarilla falls back to current day when no prev_day"""
        result = calculate_all_indicators(self.candles, self.live_quote, None)

        # Should still calculate using current day data
        self.assertIn('Camarilla_H4', result)

    def test_empty_candles(self):
        """Test with empty candles"""
        result = calculate_all_indicators([], self.live_quote)
        self.assertEqual(result, {})

    def test_volume_spike_threshold(self):
        """Test volume spike detection"""
        # Create candles with consistent volume
        candles = []
        for i in range(25):
            candles.append([
                1000000 + i * 300000,
                100000, 101000, 99000, 100500,
                100000  # consistent volume
            ])

        # Live quote with spike
        quote = {
            "last_traded_price": 100500,
            "open_price_of_the_day": 100000,
            "high_price_of_the_day": 101000,
            "low_price_of_the_day": 99000,
            "closed_price": 100000,
            "volume_trade_for_the_day": 500000  # 5x average
        }

        result = calculate_all_indicators(candles, quote)
        self.assertIn('avg_volume', result)
        # avg_volume should be 0 when < 20 data points, or actual average when >= 20
        if len(candles) >= 20:
            self.assertGreater(result['avg_volume'], 0)


class TestGetAlertCategories(unittest.TestCase):
    """Test the get_alert_categories function"""

    def test_no_alerts(self):
        """Test when no alert conditions are met"""
        from web_dashboard.backend.main import get_alert_categories

        row = {
            'ltp': 100,
            'Camarilla_H4': 110,
            'Camarilla_L4': 90,
            'volume': 1000,
            'avg_volume': 1000,
            'volume_sma8': 1000
        }

        result = get_alert_categories(row)
        self.assertFalse(result['camarilla'])
        self.assertFalse(result['volume_spike'])
        self.assertFalse(result['volume_sma8'])

    def test_camarilla_above_h4(self):
        """Test alert when LTP is above H4"""
        from web_dashboard.backend.main import get_alert_categories

        row = {
            'ltp': 115,
            'Camarilla_H4': 110,
            'Camarilla_L4': 90,
            'volume': 1000,
            'avg_volume': 1000,
            'volume_sma8': 1000
        }

        result = get_alert_categories(row)
        self.assertEqual(result['camarilla'], 'ABOVE H4')

    def test_camarilla_below_l4(self):
        """Test alert when LTP is below L4"""
        from web_dashboard.backend.main import get_alert_categories

        row = {
            'ltp': 85,
            'Camarilla_H4': 110,
            'Camarilla_L4': 90,
            'volume': 1000,
            'avg_volume': 1000,
            'volume_sma8': 1000
        }

        result = get_alert_categories(row)
        self.assertEqual(result['camarilla'], 'BELOW L4')

    def test_volume_spike(self):
        """Test volume spike detection"""
        from web_dashboard.backend.main import get_alert_categories

        row = {
            'ltp': 100,
            'Camarilla_H4': 110,
            'Camarilla_L4': 90,
            'volume': 3000,
            'avg_volume': 1000,
            'volume_sma8': 1000
        }

        result = get_alert_categories(row)
        self.assertTrue(result['volume_spike'])

    def test_volume_spike_no_avg(self):
        """Test volume spike skipped when no avg_volume"""
        from web_dashboard.backend.main import get_alert_categories

        row = {
            'ltp': 100,
            'Camarilla_H4': 110,
            'Camarilla_L4': 90,
            'volume': 3000,
            'avg_volume': 0,
            'volume_sma8': 1000
        }

        result = get_alert_categories(row)
        self.assertFalse(result['volume_spike'])


class TestSymbolLoader(unittest.TestCase):
    """Test the SymbolLoader class"""

    def test_init(self):
        """Test SymbolLoader initialization"""
        loader = SymbolLoader('test.csv')
        self.assertFalse(loader.loaded)
        self.assertEqual(len(loader.token_to_symbol), 0)

    def test_find_csv_missing(self):
        """Test _find_csv returns None when no files exist"""
        loader = SymbolLoader('/nonexistent/path/test.csv')
        result = loader._find_csv()
        self.assertIsNone(result)

    def test_load_missing_file(self):
        """Test load returns False for missing file"""
        loader = SymbolLoader('/nonexistent/path/test.csv')
        result = loader.load()
        self.assertFalse(result)
        self.assertFalse(loader.loaded)


if __name__ == '__main__':
    unittest.main()
