# ===============================
# utils/logger.py - Clean Terminal Version
# ===============================

import logging
import logging.handlers
from pathlib import Path
import sys

class LoggerSetup:
    """Centralized logging with clean terminal output"""
    
    _instances = {}
    
    def __init__(self, name: str = "LiveFeed", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture everything
        self.logger.propagate = False
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add handlers
        self._add_file_handler()      # ALL logs go to file
        self._add_console_handler()    # ONLY important logs to console
    
    def _add_file_handler(self):
        """File handler - gets ALL debug logs"""
        log_file = self.log_dir / f"{self.name.lower()}.log"
        
        fh = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        fh.setLevel(logging.DEBUG)  # Everything goes to file
        
        # Detailed formatter for file
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        
        self.logger.addHandler(fh)
    
    def _add_console_handler(self):
        """Console handler - ONLY important messages"""
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)  # Only INFO and above (WARNING, ERROR)
        
        # Simple formatter for console
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        ch.setFormatter(formatter)
        
        self.logger.addHandler(ch)
    
    @classmethod
    def get_logger(cls, name: str = "LiveFeed") -> logging.Logger:
        """Get or create logger instance"""
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name].logger

# Convenience function
def get_logger(name: str = "LiveFeed") -> logging.Logger:
    return LoggerSetup.get_logger(name)