# ===============================
# indicators/alerts.py - Alert System
# ===============================

from collections import deque
import threading
from datetime import datetime
from typing import List, Dict, Optional
from utils.logger import get_logger
from data.models import TickData, IndicatorData
from data.buffers import TickBuffer

class AlertSystem:
    """Real-time alert generation"""
    
    def __init__(self, thresholds: Dict = None):
        self.logger = get_logger('AlertSystem')
        
        # Alert storage
        self.alerts = deque(maxlen=1000)
        self.lock = threading.RLock()
        
        # Default thresholds
        self.thresholds = thresholds or {
            'volume_spike': 2.5,      # 2.5x average volume
            'price_jump': 3.0,        # 3% price jump
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'volume_min': 10000,       # Minimum volume for alerts
            'price_min': 10            # Minimum price for alerts
        }
    
    def check_tick(self, tick: TickData, indicators: IndicatorData, 
                   buffer: Optional[TickBuffer] = None) -> List[str]:
        """Check for alert conditions"""
        alerts = []
        
        try:
            # Skip if price too low
            if tick.ltp < self.thresholds['price_min']:
                return alerts
            
            # Volume spike
            if indicators.volume_avg > 0:
                volume_ratio = tick.volume / indicators.volume_avg
                if volume_ratio > self.thresholds['volume_spike']:
                    alert = {
                        'type': 'VOLUME_SPIKE',
                        'message': f"Volume spike: {volume_ratio:.1f}x average",
                        'severity': 'HIGH' if volume_ratio > 5 else 'MEDIUM'
                    }
                    alerts.append(self._format_alert(alert))
                    self._store_alert(tick, alert)
            
            # Price jump
            if abs(tick.change_percent) > self.thresholds['price_jump']:
                direction = "UP" if tick.change_percent > 0 else "DOWN"
                alert = {
                    'type': 'PRICE_JUMP',
                    'message': f"Price {direction} {abs(tick.change_percent):.1f}%",
                    'severity': 'HIGH' if abs(tick.change_percent) > 5 else 'MEDIUM'
                }
                alerts.append(self._format_alert(alert))
                self._store_alert(tick, alert)
            
            # RSI levels
            if indicators.rsi14 < self.thresholds['rsi_oversold']:
                alert = {
                    'type': 'RSI_OVERSOLD',
                    'message': f"RSI oversold: {indicators.rsi14:.1f}",
                    'severity': 'MEDIUM'
                }
                alerts.append(self._format_alert(alert))
                self._store_alert(tick, alert)
                
            elif indicators.rsi14 > self.thresholds['rsi_overbought']:
                alert = {
                    'type': 'RSI_OVERBOUGHT',
                    'message': f"RSI overbought: {indicators.rsi14:.1f}",
                    'severity': 'MEDIUM'
                }
                alerts.append(self._format_alert(alert))
                self._store_alert(tick, alert)
            
            # Support/Resistance breaks
            if tick.ltp < indicators.support and indicators.support > 0:
                alert = {
                    'type': 'SUPPORT_BREAK',
                    'message': f"Broke support: {indicators.support:.2f}",
                    'severity': 'HIGH'
                }
                alerts.append(self._format_alert(alert))
                self._store_alert(tick, alert)
                
            elif tick.ltp > indicators.resistance and indicators.resistance > 0:
                alert = {
                    'type': 'RESISTANCE_BREAK',
                    'message': f"Broke resistance: {indicators.resistance:.2f}",
                    'severity': 'HIGH'
                }
                alerts.append(self._format_alert(alert))
                self._store_alert(tick, alert)
            
            # Consecutive candles (if buffer available)
            if buffer and buffer.size >= 3:
                alerts.extend(self._check_patterns(tick, buffer))
            
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
        
        return alerts
    
    def _check_patterns(self, tick: TickData, buffer: TickBuffer) -> List[str]:
        """Check for candlestick patterns"""
        alerts = []
        
        try:
            last_ticks = buffer.get_last(10)
            if len(last_ticks) < 3:
                return alerts
            
            # Get last few prices
            prices = [t.ltp for t in last_ticks[-3:]]
            
            # Three white soldiers (bullish)
            if all(prices[i] > prices[i-1] for i in range(1, 3)):
                alerts.append(self._format_alert({
                    'type': 'PATTERN',
                    'message': "Three white soldiers (bullish)",
                    'severity': 'MEDIUM'
                }))
            
            # Three black crows (bearish)
            elif all(prices[i] < prices[i-1] for i in range(1, 3)):
                alerts.append(self._format_alert({
                    'type': 'PATTERN',
                    'message': "Three black crows (bearish)",
                    'severity': 'MEDIUM'
                }))
            
        except Exception as e:
            self.logger.error(f"Error checking patterns: {e}")
        
        return alerts
    
    def _format_alert(self, alert: Dict) -> str:
        """Format alert for display"""
        emoji = {
            'VOLUME_SPIKE': '📊',
            'PRICE_JUMP': '⚡',
            'RSI_OVERSOLD': '📉',
            'RSI_OVERBOUGHT': '📈',
            'SUPPORT_BREAK': '🔻',
            'RESISTANCE_BREAK': '🔺',
            'PATTERN': '📐'
        }.get(alert['type'], '🔔')
        
        return f"{emoji} {alert['message']}"
    
    def _store_alert(self, tick: TickData, alert: Dict):
        """Store alert in history"""
        with self.lock:
            self.alerts.append({
                'token': tick.token,
                'symbol': tick.symbol,
                'timestamp': tick.timestamp,
                'ltp': tick.ltp,
                'type': alert['type'],
                'message': alert['message'],
                'severity': alert.get('severity', 'LOW')
            })
    
    def get_recent_alerts(self, n: int = 10) -> List[Dict]:
        """Get recent alerts"""
        with self.lock:
            return list(self.alerts)[-n:]
    
    def get_alerts_by_token(self, token: str, n: int = 10) -> List[Dict]:
        """Get alerts for specific token"""
        with self.lock:
            token_alerts = [a for a in self.alerts if a['token'] == token]
            return token_alerts[-n:]
    
    def clear_alerts(self):
        """Clear all alerts"""
        with self.lock:
            self.alerts.clear()
            self.logger.info("Alerts cleared")