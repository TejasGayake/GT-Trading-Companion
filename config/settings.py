# ===============================
# config/settings.py - Application Settings
# ===============================

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class AppConfig:
    """Application configuration"""

    # Excel settings
    EXCEL_FILE: str = "Live_Feed_Data.xlsx"
    EXCEL_CHECK_INTERVAL: float = 1.0
    TICK_BATCH_SIZE: int = 100

    # API settings
    CACHE_DURATION: int = 300  # 5 minutes
    RATE_LIMIT_CALLS: int = 30
    RATE_LIMIT_PERIOD: int = 60
    CONNECTION_POOL_SIZE: int = 20
    REQUEST_TIMEOUT: int = 15
    MAX_RETRIES: int = 3

    # Dashboard settings
    POLL_INTERVAL: float = 2.0  # seconds between data polls
    MAX_WATCHLIST_TOKENS: int = 200  # max tokens per watchlist
    CANDLE_CACHE_DURATION: int = 60  # seconds to cache candle data
    
    # Alert thresholds
    ALERT_THRESHOLDS: Dict = field(default_factory=lambda: {
        'volume_spike': 2.5,
        'price_jump': 3.0,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'volume_min': 10000,
        'price_min': 10
    })
    
    # Backup settings
    BACKUP_DIR: str = "token_backups"
    AUTO_BACKUP_INTERVAL: int = 1800  # 30 minutes
    BACKUP_RETENTION_DAYS: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/live_feed.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5

# Global instance
config = AppConfig()