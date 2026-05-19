# ===============================
# storage.py - Watchlist Persistence Abstraction
# ===============================

import json
import os
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class WatchlistStorage:
    """Base class for watchlist persistence"""

    async def load(self, user_id: str) -> Dict[str, List[str]]:
        raise NotImplementedError

    async def save(self, user_id: str, watchlists: Dict[str, List[str]]) -> None:
        raise NotImplementedError


class FileWatchlistStorage(WatchlistStorage):
    """File-based watchlist storage (local fallback)"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._lock = asyncio.Lock()

    async def load(self, user_id: str) -> Dict[str, List[str]]:
        def _read():
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, 'r') as f:
                        return json.load(f)
            except Exception as e:
                logger.error(f"Error loading watchlist from file: {e}")
            return {"Default": []}
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read)

    async def save(self, user_id: str, watchlists: Dict[str, List[str]]) -> None:
        async with self._lock:
            def _write():
                try:
                    with open(self.filepath, 'w') as f:
                        json.dump(watchlists, f)
                except Exception as e:
                    logger.error(f"Error saving watchlist to file: {e}")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _write)


class SupabaseWatchlistStorage(WatchlistStorage):
    """Supabase-backed watchlist storage for cloud deployment"""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.base_url = supabase_url.rstrip('/')
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self._client = None

    def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def load(self, user_id: str) -> Dict[str, List[str]]:
        try:
            client = self._get_client()
            resp = await client.get(
                f"{self.base_url}/rest/v1/watchlists",
                headers=self.headers,
                params={"user_id": f"eq.{user_id}", "select": "name,tokens"}
            )
            resp.raise_for_status()
            rows = resp.json()

            if not rows:
                return {"Default": []}

            return {row["name"]: row["tokens"] for row in rows}
        except Exception as e:
            logger.error(f"Error loading watchlist from Supabase: {e}")
            return {"Default": []}

    async def save(self, user_id: str, watchlists: Dict[str, List[str]]) -> None:
        try:
            client = self._get_client()
            rows = []
            for name, tokens in watchlists.items():
                rows.append({
                    "user_id": user_id,
                    "name": name,
                    "tokens": tokens
                })

            resp = await client.post(
                f"{self.base_url}/rest/v1/watchlists",
                headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
                params={"on_conflict": "user_id,name"},
                json=rows
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error saving watchlist to Supabase: {e}")


def create_storage() -> WatchlistStorage:
    """Factory: returns Supabase storage if env vars are set, else file storage"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if supabase_url and supabase_key:
        logger.info("Using Supabase watchlist storage")
        return SupabaseWatchlistStorage(supabase_url, supabase_key)

    logger.info("Using file-based watchlist storage")
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
    return FileWatchlistStorage(filepath)
