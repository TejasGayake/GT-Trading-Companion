# ===============================
# config/app_config.py - Application Configuration
# ===============================

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
BACKUP_DIR = BASE_DIR / "token_backups"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Ensure directories exist
for dir_path in [BACKUP_DIR, LOG_DIR, CONFIG_DIR]:
    dir_path.mkdir(exist_ok=True)

# Angel API Credentials
ANGEL_CONFIG = {
    "API_KEY": "pguY4t7F",
    "CLIENT_ID": "AAAD452109",
    "PASSWORD": "4212",
    "TOTP_SECRET": "36ZX2GTMYYSS7PIJNWJNTME344"
}

# Excel Configuration
EXCEL_CONFIG = {
    "FILE_NAME": "Live_Feed_Data.xlsx",
    "CHECK_INTERVAL": 1.0,  # seconds
    "TICK_BATCH_SIZE": 100,
    "MAX_WORKERS": 4
}

# API Configuration
API_CONFIG = {
    "CACHE_DURATION": 300,  # 5 minutes
    "RATE_LIMIT_CALLS": 30,  # calls per minute
    "RATE_LIMIT_PERIOD": 60,  # seconds
    "CONNECTION_POOL_SIZE": 20,
    "REQUEST_TIMEOUT": 15,  # seconds
    "MAX_RETRIES": 3
}

# Alert Thresholds
ALERT_CONFIG = {
    "VOLUME_SPIKE": 2.5,      # 2.5x average volume
    "PRICE_JUMP": 3.0,        # 3% price jump
    "RSI_OVERSOLD": 30,
    "RSI_OVERBOUGHT": 70
}

# Logging Configuration
LOG_CONFIG = {
    "LEVEL": "INFO",
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "FILE": LOG_DIR / "live_feed.log",
    "MAX_BYTES": 10 * 1024 * 1024,  # 10MB
    "BACKUP_COUNT": 5
}