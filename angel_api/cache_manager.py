# ===============================
# angel_api/cache_manager.py - Cache Manager
# ===============================

import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict
from utils.logger import get_logger

class CacheManager:
    """Simple cache manager with TTL and LRU eviction"""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache manager
        
        Args:
            ttl: Time to live in seconds
            max_size: Maximum number of items in cache
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache = OrderedDict()  # key -> (value, timestamp)
        self.lock = threading.RLock()
        self.logger = get_logger('CacheManager')
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    self.logger.debug(f"Cache hit for {key}")
                    return value
                else:
                    # Expired
                    del self.cache[key]
                    self.logger.debug(f"Cache expired for {key}")
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # Evict oldest if at max size
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
                self.evictions += 1
                self.logger.debug(f"Cache eviction, size: {len(self.cache)}")
            
            self.cache[key] = (value, time.time())
            self.cache.move_to_end(key)
            self.logger.debug(f"Cached {key}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.logger.debug(f"Deleted {key} from cache")
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.logger.info("Cache cleared")
    
    def cleanup(self):
        """Remove expired entries"""
        with self.lock:
            now = time.time()
            expired = [
                k for k, (_, ts) in self.cache.items() 
                if now - ts >= self.ttl
            ]
            for k in expired:
                del self.cache[k]
            
            if expired:
                self.logger.debug(f"Cleaned up {len(expired)} expired entries")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'evictions': self.evictions,
                'ttl': self.ttl
            }