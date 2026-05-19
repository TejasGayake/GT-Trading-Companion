# ===============================
# indicators/calculator.py - Fixed with better error handling
# ===============================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import threading
import time

from utils.logger import get_logger
from data.models import IndicatorData


def calculate_all_indicators(candles: List, live_quote: dict, prev_day: dict = None) -> dict:
    """
    Calculate all technical indicators from candle data and live quote.
    This is a standalone function that can be used without IndicatorCalculator class.

    Args:
        candles: List of [timestamp, open, high, low, close, volume] in PAISE
        live_quote: Dict with live quote data in PAISE
        prev_day: Optional dict with previous day OHLC in PAISE for proper Camarilla

    Returns:
        Dict with all indicator values in RUPEES
    """
    if not candles:
        return {}

    # Extract price data (convert paise to rupees)
    closes = [c[4] / 100 for c in candles]
    highs = [c[2] / 100 for c in candles]
    lows = [c[3] / 100 for c in candles]
    volumes = [c[5] for c in candles]

    ltp = live_quote["last_traded_price"] / 100
    volume = live_quote["volume_trade_for_the_day"]

    result = {
        "ltp": ltp,
        "open": live_quote["open_price_of_the_day"] / 100,
        "high": live_quote["high_price_of_the_day"] / 100,
        "low": live_quote["low_price_of_the_day"] / 100,
        "prev_close": live_quote["closed_price"] / 100,
        "volume": volume,
    }

    # Calculate change
    if result["prev_close"] > 0:
        result["change"] = ltp - result["prev_close"]
        result["change_percent"] = (result["change"] / result["prev_close"]) * 100

    # Moving Averages
    if len(closes) >= 8:
        result["sma8"] = sum(closes[-8:]) / 8
    if len(volumes) >= 8:
        result["volume_sma8"] = int(sum(volumes[-8:]) / 8)
    if len(closes) >= 21:
        result["sma21"] = sum(closes[-21:]) / 21
    if len(closes) >= 40:
        result["sma40"] = sum(closes[-40:]) / 40
    if len(closes) >= 200:
        result["sma200"] = sum(closes[-200:]) / 200

    # EMA10
    if len(closes) >= 10:
        multiplier = 2 / (10 + 1)
        ema = closes[0]
        for price in closes[1:]:
            ema = (price - ema) * multiplier + ema
        result["ema10"] = ema

    # RSI (14-period) — Wilder's smoothing
    if len(closes) >= 15:
        total_gain = 0.0
        total_loss = 0.0
        for i in range(-14, 0):
            change = closes[i] - closes[i-1]
            if change > 0:
                total_gain += change
            else:
                total_loss += abs(change)
        avg_gain = total_gain / 14
        avg_loss = total_loss / 14
        if avg_loss == 0:
            result["rsi14"] = 100.0  # All gains → RSI = 100
        elif avg_gain == 0:
            result["rsi14"] = 0.0    # All losses → RSI = 0
        else:
            rs = avg_gain / avg_loss
            result["rsi14"] = 100 - (100 / (1 + rs))

    # VWAP (26-period) - use rupee prices consistent with other indicators
    if len(candles) >= 26:
        total_pv = sum((c[4] / 100) * c[5] for c in candles[-26:])
        total_vol = sum(c[5] for c in candles[-26:])
        result["vwap"] = total_pv / total_vol if total_vol > 0 else ltp

    # Volume average
    if len(volumes) >= 20:
        result["avg_volume"] = int(sum(volumes[-20:]) / 20)
    else:
        result["avg_volume"] = 0  # Skip volume spike alerts when insufficient data

    # Camarilla - use previous day OHLC for proper pivot levels
    if prev_day and prev_day.get('high') and prev_day.get('low') and prev_day.get('close'):
        # Use previous day data (standard Camarilla calculation)
        prev_high = prev_day['high'] / 100
        prev_low = prev_day['low'] / 100
        prev_close = prev_day['close'] / 100
    else:
        # Fallback to current day data if previous day not available
        prev_high = result.get("high", 0)
        prev_low = result.get("low", 0)
        prev_close = result.get("prev_close", 0)

    if prev_close > 0 and prev_high > 0 and prev_low > 0:
        diff = prev_high - prev_low
        result["Camarilla_H4"] = prev_close + (diff * 0.55)
        result["Camarilla_H3"] = prev_close + (diff * 0.275)
        result["Camarilla_L3"] = prev_close - (diff * 0.275)
        result["Camarilla_L4"] = prev_close - (diff * 0.55)

    # Support/Resistance
    if len(closes) >= 20:
        result["resistance"] = max(closes[-20:]) * 1.02
        result["support"] = min(closes[-20:]) * 0.98

    # Previous day high/low from live quote
    result["prev_day_high"] = result.get("high", 0)
    result["prev_day_low"] = result.get("low", 0)

    # Volatility (annualized)
    if len(closes) >= 20:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, min(20, len(closes)))]
        if returns:
            result["volatility"] = float(np.std(returns) * np.sqrt(252) * 100)

    # Supertrend (simplified ATR-based)
    if len(closes) >= 10:
        atr = sum(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(-10, 0)) / 10
        result["supertrend"] = closes[-1] - (3 * atr)
        result["supertrend_direction"] = "BULLISH" if closes[-1] > result["supertrend"] else "BEARISH"

    return result

class IndicatorCalculator:
    """Indicator calculations with caching"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = get_logger('IndicatorCalculator')
        
        # Cache
        self.cache = {}  # token -> (IndicatorData, timestamp)
        self.cache_duration = 300  # 5 minutes
        self.cache_lock = threading.RLock()
        
        # Track API calls
        self.api_calls = 0
        self.failed_calls = 0
        
        # Default values for when API fails
        self.default_indicators = {
            'sma21': 0, 'sma40': 0, 'sma200': 0, 'rsi14': 50,
            'vwap': 0, 'prev_high': 0, 'prev_low': 0,
            'volume_avg': 0, 'volatility': 0, 'support': 0, 'resistance': 0
        }

    def calculate_indicators(self, token: str, force: bool = False) -> Optional[IndicatorData]:
        """Calculate indicators for a token"""
        current_time = datetime.now()
        clean_token = str(token).split('.')[0]

        # Check cache
        if not force:
            with self.cache_lock:
                if clean_token in self.cache:
                    data, timestamp = self.cache[clean_token]
                    if (current_time - timestamp).seconds < self.cache_duration:
                        self.logger.debug(f"Cache hit for {clean_token}")
                        return data

        try:
            self.logger.info(f"📊 Fetching indicators for token {clean_token}")

            # Fetch candles from API
            candles = self.api_client.get_candles(clean_token, days=5)
            self.api_calls += 1

            if not candles:
                self.logger.warning(f"⚠️ No candle data for {clean_token}")
                self.failed_calls += 1
                return self._create_default_indicators(clean_token, current_time)

            if len(candles) < 21:
                self.logger.warning(f"⚠️ Insufficient candles for {clean_token}: got {len(candles)}, need at least 21")
                self.failed_calls += 1
                # Still try to calculate with what we have
                if len(candles) > 0:
                    result = self._calculate_from_candles(clean_token, candles, current_time)
                    self.logger.info(f"✅ Calculated indicators for {clean_token} with limited data ({len(candles)} candles)")
                else:
                    result = self._create_default_indicators(clean_token, current_time)
            else:
                # Calculate indicators from candles
                result = self._calculate_from_candles(clean_token, candles, current_time)
                self.logger.info(f"✅ Successfully calculated indicators for {clean_token} with {len(candles)} candles")

            # Log the calculated values for debugging
            if result:
                self.logger.info(f"📊 {clean_token} indicators - Volume Avg: {result.volume_avg}, SMA21: {result.sma21:.2f}, RSI14: {result.rsi14:.1f}")

            # Update cache
            with self.cache_lock:
                self.cache[clean_token] = (result, current_time)

            return result

        except Exception as e:
            self.logger.error(f"❌ Error calculating indicators for {clean_token}: {e}")
            import traceback
            traceback.print_exc()
            self.failed_calls += 1
            return self._create_default_indicators(clean_token, current_time)

    def _calculate_from_candles(self, token: str, candles: List, current_time: datetime) -> IndicatorData:
        """Calculate indicators from candle data"""
        try:
            self.logger.info(f"🔧 Calculating indicators from {len(candles)} candles for {token}")

            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])

            # Convert to numeric
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col])

            self.logger.info(f"📊 DataFrame shape: {df.shape}")

            # Calculate all indicators
            indicators = {}

            # Moving averages - CHANGED SMA20 to SMA21
            indicators['sma21'] = self._safe_series(df['close'].rolling(21).mean())
            indicators['sma40'] = self._safe_series(df['close'].rolling(40).mean())
            indicators['sma200'] = self._safe_series(df['close'].rolling(200).mean())

            
            # Calculate EMA10
            indicators['ema10'] = self._calculate_ema(df['close'], 10)

            # Calculate Supertrend (ATR 13, multiplier 3)
            indicators['supertrend'] = self._calculate_supertrend(df, period=13, multiplier=3)

            # Calculate Camarilla H4/L4
            h4, l4 = self._calculate_camarilla(df)
            indicators['camarilla_h4'] = h4
            indicators['camarilla_l4'] = l4

            # Get previous day's data (using second last candle)
            if len(df) >= 2:
                indicators['prev_day_high'] = float(df['high'].iloc[-2])
                indicators['prev_day_low'] = float(df['low'].iloc[-2])
            else:
                indicators['prev_day_high'] = 0
                indicators['prev_day_low'] = 0

            # RSI (14 periods)
            indicators['rsi14'] = self._calculate_rsi(df['close'])

            # VWAP
            indicators['vwap'] = self._calculate_vwap(df)

            # Previous day high/low
            indicators['prev_high'] = float(df['high'].iloc[-2]) if len(df) > 1 else float(df['high'].iloc[-1])
            indicators['prev_low'] = float(df['low'].iloc[-2]) if len(df) > 1 else float(df['low'].iloc[-1])

            # Average volume (21 days) - CHANGED from 20 to 21
            volume_series = df['volume'].tail(21)
            indicators['volume_avg'] = float(volume_series.mean()) if len(volume_series) > 0 else 0

            # Volatility (21 days annualized) - CHANGED from 20 to 21
            returns = df['close'].pct_change().dropna()
            indicators['volatility'] = float(returns.tail(21).std() * np.sqrt(252)) if len(returns) > 5 else 0

            # Support and resistance (21 days) - CHANGED from 20 to 21
            indicators['support'] = float(df['low'].tail(21).min())
            indicators['resistance'] = float(df['high'].tail(21).max())

            # Log individual calculations for debugging
            self.logger.info(f"📈 {token} calculation results:")
            self.logger.info(f"   - SMA21: {indicators['sma21']:.2f}")
            self.logger.info(f"   - SMA40: {indicators['sma40']:.2f}")
            self.logger.info(f"   - SMA200: {indicators['sma200']:.2f}")
            self.logger.info(f"   - EMA10: {indicators['ema10']:.2f}")
            self.logger.info(f"   - Supertrend: {indicators['supertrend']:.2f}")
            self.logger.info(f"   - CAM H4: {indicators['camarilla_h4']:.2f}")
            self.logger.info(f"   - CAM L4: {indicators['camarilla_l4']:.2f}")
            self.logger.info(f"   - RSI14: {indicators['rsi14']:.1f}")
            self.logger.info(f"   - VWAP: {indicators['vwap']:.2f}")
            self.logger.info(f"   - Volume Avg: {indicators['volume_avg']:.0f}")
            self.logger.info(f"   - Support: {indicators['support']:.2f}")
            self.logger.info(f"   - Resistance: {indicators['resistance']:.2f}")

            # Create result - CHANGED sma20 to sma21
            return IndicatorData(
                token=token,
                timestamp=current_time,
                sma21=indicators.get('sma21', 0),
                sma40=indicators.get('sma40', 0),
                sma200=indicators.get('sma200', 0),
                ema10=indicators.get('ema10', 0),
                supertrend=indicators.get('supertrend', 0),
                camarilla_h4=indicators.get('camarilla_h4', 0),
                camarilla_l4=indicators.get('camarilla_l4', 0),
                prev_day_high=indicators.get('prev_day_high', 0),
                prev_day_low=indicators.get('prev_day_low', 0),
                rsi14=indicators.get('rsi14', 50),
                vwap=indicators.get('vwap', 0),
                prev_high=indicators.get('prev_high', 0),
                prev_low=indicators.get('prev_low', 0),
                volume_avg=indicators.get('volume_avg', 0),
                volatility=indicators.get('volatility', 0),
                support=indicators.get('support', 0),
                resistance=indicators.get('resistance', 0)
            )

        except Exception as e:
            self.logger.error(f"❌ Error in _calculate_from_candles for {token}: {e}")
            import traceback
            traceback.print_exc()
            return self._create_default_indicators(token, current_time)

    def _create_default_indicators(self, token: str, current_time: datetime) -> IndicatorData:
        """Create default indicators when calculation fails"""
        self.logger.warning(f"⚠️ Using default indicators for {token}")
        return IndicatorData(
            token=token,
            timestamp=current_time,
            sma21=0,
            sma40=0,
            sma200=0,
            ema10=0, supertrend=0, camarilla_h4=0, camarilla_l4=0,  # NEW FIELDS
            prev_day_high=0, prev_day_low=0,
            rsi14=50,
            vwap=0,
            prev_high=0,
            prev_low=0,
            volume_avg=0,
            volatility=0,
            support=0,
            resistance=0
        )    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        except:
            return 50
    
    def _calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP"""
        try:
            tp = (df['high'] + df['low'] + df['close']) / 3
            vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
            return float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else 0
        except:
            return 0

    #===========================================================
    def _calculate_ema(self, prices: pd.Series, period: int = 10) -> float:
        """
        Calculate Exponential Moving Average

        Args:
            prices: Series of closing prices
            period: EMA period (default 10 as required)

        Returns:
            Latest EMA value
        """
        try:
            if len(prices) < period:
                return 0

            # Calculate multiplier: 2 / (period + 1)
            # For period 10: 2 / 11 = 0.1818
            multiplier = 2 / (period + 1)

            # Start with SMA for the first value
            sma = prices.iloc[:period].mean()
            ema_values = [sma]

            # Calculate EMA for remaining values
            for i in range(period, len(prices)):
                ema = (prices.iloc[i] - ema_values[-1]) * multiplier + ema_values[-1]
                ema_values.append(ema)

            result = float(ema_values[-1])
            self.logger.debug(f"EMA{period}: {result:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"Error calculating EMA: {e}")
            return 0
        
    # ------------------------------------------------------
    def _calculate_supertrend(self, df: pd.DataFrame, period: int = 13, multiplier: float = 3) -> float:
        """
        Calculate Supertrend indicator

        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ATR period (default 13 as required)
            multiplier: Multiplier (default 3 as required)

        Returns:
            Current Supertrend value
        """
        try:
            if len(df) < period + 5:  # Need enough data
                return 0

            # Make a copy to avoid modifying original
            df = df.copy()

            # Calculate True Range
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['close'].shift(1))
            df['tr3'] = abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

            # Calculate ATR with period 13
            df['atr'] = df['tr'].rolling(window=period).mean()

            # Calculate basic bands
            df['hl_avg'] = (df['high'] + df['low']) / 2
            df['upper_band'] = df['hl_avg'] + (multiplier * df['atr'])
            df['lower_band'] = df['hl_avg'] - (multiplier * df['atr'])

            # Initialize Supertrend arrays
            df['supertrend'] = 0.0
            df['trend'] = 1  # 1 for uptrend, -1 for downtrend

            # Calculate final bands and supertrend
            for i in range(1, len(df)):
                # Upper band logic
                if df['upper_band'].iloc[i] < df['upper_band'].iloc[i-1] or df['close'].iloc[i-1] > df['upper_band'].iloc[i-1]:
                    df.loc[df.index[i], 'final_upper'] = df['upper_band'].iloc[i]
                else:
                    df.loc[df.index[i], 'final_upper'] = df['upper_band'].iloc[i-1]

                # Lower band logic
                if df['lower_band'].iloc[i] > df['lower_band'].iloc[i-1] or df['close'].iloc[i-1] < df['lower_band'].iloc[i-1]:
                    df.loc[df.index[i], 'final_lower'] = df['lower_band'].iloc[i]
                else:
                    df.loc[df.index[i], 'final_lower'] = df['lower_band'].iloc[i-1]

                # Determine trend
                if df['close'].iloc[i] > df['final_upper'].iloc[i-1]:
                    df.loc[df.index[i], 'trend'] = 1
                elif df['close'].iloc[i] < df['final_lower'].iloc[i-1]:
                    df.loc[df.index[i], 'trend'] = -1
                else:
                    df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]

                # Set supertrend value
                if df['trend'].iloc[i] == 1:
                    df.loc[df.index[i], 'supertrend'] = df['final_lower'].iloc[i]
                else:
                    df.loc[df.index[i], 'supertrend'] = df['final_upper'].iloc[i]

            # Get latest value
            result = float(df['supertrend'].iloc[-1]) if not pd.isna(df['supertrend'].iloc[-1]) else 0
            self.logger.debug(f"Supertrend (ATR13, mult3): {result:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"Error calculating Supertrend: {e}")
            return 0
        
    # ------------------------------------------------------
    def _calculate_camarilla(self, df: pd.DataFrame) -> tuple:
        """
        Calculate Camarilla pivot points (only H4 and L4)

        Args:
            df: DataFrame with 'high', 'low', 'close' columns

        Returns:
            Tuple of (H4, L4)
        """
        try:
            if len(df) < 2:
                return 0, 0

            # Get previous day's data (last complete candle before current)
            # Using second last candle for previous day
            prev_high = float(df['high'].iloc[-2])
            prev_low = float(df['low'].iloc[-2])
            prev_close = float(df['close'].iloc[-2])

            # Calculate daily range
            daily_range = prev_high - prev_low

            # Calculate H4 and L4 (using 0.55 multiplier)
            h4 = prev_close + (daily_range * 0.55)
            l4 = prev_close - (daily_range * 0.55)

            self.logger.debug(f"Camarilla - H4: {h4:.2f}, L4: {l4:.2f}")
            return round(h4, 2), round(l4, 2)

        except Exception as e:
            self.logger.error(f"Error calculating Camarilla: {e}")
            return 0, 0


    #=========================================================== 

    
    def _safe_series(self, series: pd.Series) -> float:
        """Safely get last value from series"""
        try:
            if len(series) > 0 and not pd.isna(series.iloc[-1]):
                return float(series.iloc[-1])
            return 0
        except:
            return 0
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self.cache_lock:
            return {
                'size': len(self.cache),
                'api_calls': self.api_calls,
                'failed_calls': self.failed_calls
            }