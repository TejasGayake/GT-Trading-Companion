# ===============================
# angel_api/client.py - Using SmartConnect
# ===============================

from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, List, Dict
import time

from utils.logger import get_logger

class AngelAPIClient:
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self.logger = get_logger('AngelAPIClient')
        
        # SmartConnect instance
        self.smartApi = None
        self.auth_token = None
        self.feed_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Symbol mapping
        self.symbols = {}
        self.token_to_symbol = {}
        
        # Common symbols fallback
        self.common_symbols = {
            "2885": "ITC", "3045": "RELIANCE", "1594": "TCS", "11536": "HDFC",
            "1660": "INFY", "17818": "HDFCBANK", "1394": "ICICIBANK", "4963": "SBIN"
        }
    
    def login(self) -> bool:
        """Login using SmartConnect"""
        try:
            self.smartApi = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret).now()
            
            self.logger.info(f"Logging in with TOTP: {totp}")
            
            session = self.smartApi.generateSession(
                clientCode=self.client_id,
                password=self.password,
                totp=totp
            )
            
            if session.get("status"):
                self.auth_token = session["data"]["jwtToken"]
                self.refresh_token = session["data"]["refreshToken"]
                self.feed_token = self.smartApi.getfeedToken()
                self.token_expiry = datetime.now() + timedelta(hours=1)
                
                self.logger.info("✅ Login successful")
                return True
            else:
                self.logger.error(f"❌ Login failed: {session}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False
    
    def get_candles(self, token: str, days: int = 5) -> Optional[List]:
        """Get historical candles using SmartConnect"""
        if not self.smartApi and not self.login():
            return None
        
        try:
            clean_token = str(token).split('.')[0]
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            params = {
                "exchange": "NSE",
                "symboltoken": clean_token,
                "interval": "FIVE_MINUTE",
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M")
            }
            
            self.logger.info(f"Fetching candles for {clean_token}")
            res = self.smartApi.getCandleData(params)
            
            if res and res.get("status"):
                data = res.get("data", [])
                self.logger.info(f"Got {len(data)} candles")
                return data
            else:
                self.logger.warning(f"No data for {clean_token}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching candles: {e}")
            return None
    
    def get_symbol(self, token: str) -> str:
        """Get symbol name"""
        clean_token = str(token).split('.')[0]
        return self.common_symbols.get(clean_token, f"TKN-{clean_token}")
    
    def load_symbol_master(self) -> bool:
        """Load symbols (simplified)"""
        self.logger.info(f"Loaded {len(self.common_symbols)} common symbols")
        return True
    
    def close(self):
        """Cleanup"""
        self.logger.info("Client closed")