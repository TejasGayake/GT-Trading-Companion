# ===============================
# web_dashboard/backend/main.py - FastAPI Trading Backend
# ===============================

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import sys

# Add parent directories to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..'))

from yahoo_provider import YahooFinanceProvider
from utils.symbol_loader import SymbolLoader
from indicators.calculator import calculate_all_indicators
from utils.logger import get_logger
from config.settings import config
from storage import create_storage
from rate_limiter import AsyncRateLimiter

logger = get_logger('DashboardAPI')


# ===============================
# Data Models
# ===============================

class Token(BaseModel):
    token: str
    symbol: str
    exchange: str = "NSE"


class Watchlist(BaseModel):
    name: str
    tokens: List[str]


class PortfolioHolding(BaseModel):
    token: str
    symbol: str
    quantity: int
    buy_price: float
    buy_date: str = ""
    notes: str = ""


class PortfolioTrade(BaseModel):
    token: str
    symbol: str
    quantity: int
    price: float
    type: str  # "BUY" or "SELL"
    timestamp: str = ""


class TokenData(BaseModel):
    token: str
    symbol: str
    ltp: float
    open: float
    high: float
    low: float
    prev_close: float
    change: float
    change_percent: float
    volume: int
    avg_volume: int
    vwap: float
    sma21: float
    sma40: float
    sma200: float
    ema10: float
    rsi14: float
    supertrend: float
    supertrend_direction: str
    Camarilla_H4: float
    Camarilla_H3: float
    Camarilla_L3: float
    Camarilla_L4: float
    support: float
    resistance: float
    volatility: float
    prev_day_high: float
    prev_day_low: float
    alert: str
    timestamp: datetime


# ===============================
# Application State
# ===============================

class DashboardState:
    def __init__(self):
        self.provider: Optional[YahooFinanceProvider] = None
        self.symbol_loader: Optional[SymbolLoader] = None
        self.websocket_clients: Set[WebSocket] = set()
        self.watchlists: Dict[str, List[str]] = {"Default": []}
        self.user_watchlists: Dict[str, Dict[str, List[str]]] = {}
        self.active_tokens: Set[str] = set()
        self.token_data_cache: Dict[str, dict] = {}
        self.last_broadcast_cache: Dict[str, dict] = {}  # For delta updates
        self.alerts: List[dict] = []
        self.last_update: float = 0
        self.running: bool = False
        self.yahoo_mapping: Dict[str, str] = {}
        self.portfolio: List[dict] = []  # Portfolio holdings
        self.trades: List[dict] = []     # Trade history
        self.refresh_event: asyncio.Event = asyncio.Event()
        self.start_time: float = time.time()
        self.storage = None
        self.rate_limiter: AsyncRateLimiter = AsyncRateLimiter(max_calls=30, period=60)
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.current_user_id: str = "local"
        self.alert_cooldown: Dict[str, float] = {}  # "token:alert_type" -> last_trigger_time
        self.alert_cooldown_seconds: int = 300  # 5 minutes cooldown per alert type per token
        # Metrics
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "ws_messages_sent": 0,
            "poll_cycles": 0,
        }

    async def save_watchlist(self, user_id: Optional[str] = None):
        """Save watchlist via storage backend"""
        uid = user_id or self.current_user_id
        try:
            await self.storage.save(uid, self.watchlists)
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")

    async def load_watchlist(self, user_id: Optional[str] = None):
        """Load watchlist via storage backend"""
        uid = user_id or self.current_user_id
        try:
            loaded = await self.storage.load(uid)
            if loaded:
                self.watchlists = loaded
                logger.info(f"Loaded watchlist: {len(self.watchlists.get('Default', []))} tokens")
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")

    def rebuild_global_watchlists(self):
        """Merge all user watchlists into the global watchlist for polling"""
        merged: Dict[str, List[str]] = {}
        for user_wl in self.user_watchlists.values():
            for name, tokens in user_wl.items():
                if name not in merged:
                    merged[name] = []
                for t in tokens:
                    if t not in merged[name]:
                        merged[name].append(t)
        if merged:
            self.watchlists = merged

    async def broadcast(self, message: dict):
        """Broadcast to all WebSocket clients"""
        disconnected = []
        for ws in self.websocket_clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.websocket_clients.discard(ws)


state = DashboardState()


# ===============================
# Alert Functions
# ===============================

def get_alert_categories(row: dict) -> dict:
    """Categorize alerts into different types"""
    if not row:
        return {"camarilla": False, "volume_spike": False, "volume_sma8": False}

    ltp = row.get("ltp", 0)
    h4 = row.get("Camarilla_H4", 0)
    l4 = row.get("Camarilla_L4", 0)
    vol = row.get("volume", 0)

    categories = {
        "camarilla": False,
        "volume_spike": False,
        "volume_sma8": False
    }

    # Camarilla alerts: LTP crosses H4 or L4
    if h4 and ltp > h4:
        categories["camarilla"] = "ABOVE H4"
    elif l4 and ltp < l4:
        categories["camarilla"] = "BELOW L4"

    # Volume Spike: volume > configured threshold * avg_volume (skip if no avg_volume data)
    avg_vol = row.get("avg_volume", 0)
    volume_spike_threshold = config.ALERT_THRESHOLDS.get('volume_spike', 2.5)
    if avg_vol > 0 and vol > avg_vol * volume_spike_threshold:
        categories["volume_spike"] = True

    # Volume SMA8: volume > 3x volume SMA8 (compare volume to volume, not price)
    vol_sma8 = row.get("volume_sma8", 0)
    if vol_sma8 and vol_sma8 > 0 and vol > vol_sma8 * 3:
        categories["volume_sma8"] = True

    return categories


def check_alerts(token: str, data: dict) -> Optional[str]:
    """Check if any alert conditions are met - for single alert column"""
    if not data:
        return None

    ltp = data.get("ltp", 0)
    h4 = data.get("Camarilla_H4", 0)
    l4 = data.get("Camarilla_L4", 0)
    rsi = data.get("rsi14", 0)
    vol = data.get("volume", 0)
    avg_vol = data.get("avg_volume", 1)

    if h4 and ltp > h4:
        return "ABOVE H4"
    elif l4 and ltp < l4:
        return "BELOW L4"
    elif rsi > config.ALERT_THRESHOLDS.get('rsi_overbought', 70):
        return "OVERBOUGHT"
    elif rsi < config.ALERT_THRESHOLDS.get('rsi_oversold', 30):
        return "OVERSOLD"
    elif avg_vol > 0 and vol > avg_vol * config.ALERT_THRESHOLDS.get('volume_spike', 2.5):
        return "VOLUME SPIKE"

    return None


# ===============================
# Alert Categories Builder
# ===============================

def _build_alert_categories() -> dict:
    """Build alert categories from current token data cache"""
    camarilla_stocks = []
    volume_spike_stocks = []
    volume_sma8_stocks = []

    for token, row in state.token_data_cache.items():
        categories = get_alert_categories(row)
        stock_info = {
            "token": token,
            "symbol": row.get("symbol", ""),
            "ltp": row.get("ltp", 0),
            "volume": row.get("volume", 0),
            "sma8": row.get("sma8", 0),
            "Camarilla_H4": row.get("Camarilla_H4", 0),
            "Camarilla_L4": row.get("Camarilla_L4", 0),
            "condition": categories.get("camarilla", False)
        }

        if categories.get("camarilla"):
            camarilla_stocks.append(stock_info)
        if categories.get("volume_spike"):
            volume_spike_stocks.append({
                "token": token,
                "symbol": row.get("symbol", ""),
                "ltp": row.get("ltp", 0),
                "volume": row.get("volume", 0),
                "avg_volume": row.get("avg_volume", 0)
            })
        if categories.get("volume_sma8"):
            volume_sma8_stocks.append({
                "token": token,
                "symbol": row.get("symbol", ""),
                "ltp": row.get("ltp", 0),
                "volume": row.get("volume", 0),
                "volume_sma8": row.get("volume_sma8", 0)
            })

    return {
        "camarilla": camarilla_stocks,
        "volume_spike": volume_spike_stocks,
        "volume_sma8": volume_sma8_stocks
    }


# ===============================
# Adaptive Polling
# ===============================

def is_market_open() -> bool:
    """Check if NSE market is open (9:15 AM - 3:30 PM, Mon-Fri IST)"""
    from datetime import timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    if now.weekday() >= 5:  # Weekend
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def get_adaptive_interval() -> float:
    """Calculate poll interval based on market hours and volatility"""
    if not is_market_open():
        return 30.0  # Slow polling when market closed

    # Calculate volatility from recent price changes
    changes = []
    for data in state.token_data_cache.values():
        change_pct = data.get("change_percent", 0)
        if change_pct is not None:
            changes.append(abs(change_pct))

    if not changes:
        return config.POLL_INTERVAL

    avg_change = sum(changes) / len(changes)

    if avg_change > 2.0:    # High volatility
        return 2.0
    elif avg_change > 1.0:  # Medium volatility
        return 3.0
    elif avg_change > 0.5:  # Low volatility
        return 5.0
    else:                   # Very quiet
        return 10.0


async def poll_data():
    """Background task to poll data and broadcast"""
    while state.running:
        try:
            tokens = state.watchlists.get("Default", [])[:200]  # Limit to 200

            loop = asyncio.get_event_loop()

            for token in tokens:
                try:
                    # Get live quote — always fetch (short cache, needs freshness)
                    await state.rate_limiter.acquire()
                    quote = await loop.run_in_executor(
                        state.executor, state.provider.get_live_quote, token
                    )
                    if not quote:
                        # Update error in cache if token exists
                        if token in state.token_data_cache:
                            state.token_data_cache[token]["last_error"] = "No quote data"
                            state.token_data_cache[token]["error_count"] = state.token_data_cache[token].get("error_count", 0) + 1
                        continue

                    # Get candles — only fetch when cache is stale (saves API calls)
                    candles = state.provider.get_cached_candles(token)
                    if candles is None:
                        await state.rate_limiter.acquire()
                        candles = await loop.run_in_executor(
                            state.executor, state.provider.get_candles, token, 5, "5m"
                        )

                    # Get previous day data — only fetch when cache is stale (1h cache)
                    prev_day = state.provider.get_cached_prev_day(token)
                    if prev_day is None:
                        await state.rate_limiter.acquire()
                        prev_day = await loop.run_in_executor(
                            state.executor, state.provider.get_previous_day_candles, token
                        )

                    # Calculate indicators
                    indicators = calculate_all_indicators(candles, quote, prev_day)

                    # Get symbol
                    symbol = state.provider.get_symbol(token)

                    # Build row data
                    row = {
                        "token": token,
                        "symbol": symbol,
                        **indicators,
                        "alert": check_alerts(token, indicators),
                        "timestamp": datetime.now().isoformat(),
                        "last_error": None,
                        "error_count": 0
                    }

                    # Store in cache
                    state.token_data_cache[token] = row

                    # Check for new alerts with cooldown
                    if row.get("alert"):
                        # Extract alert type from condition string (e.g., "VOLUME SPIKE" from "VOLUME SPIKE - 3.2x")
                        alert_type = row["alert"].split(" - ")[0].split(":")[0].strip()
                        cooldown_key = f"{token}:{alert_type}"
                        now = time.time()

                        # Check cooldown
                        last_triggered = state.alert_cooldown.get(cooldown_key, 0)
                        if now - last_triggered > state.alert_cooldown_seconds:
                            # Update cooldown
                            state.alert_cooldown[cooldown_key] = now

                            state.alerts.append({
                                "token": token,
                                "symbol": symbol,
                                "condition": row["alert"],
                                "ltp": row["ltp"],
                                "h4": row.get("Camarilla_H4", 0),
                                "l4": row.get("Camarilla_L4", 0),
                                "triggered_at": datetime.now().isoformat(),
                                "status": "active"
                            })

                            # Cap alerts to prevent memory leak
                            if len(state.alerts) > 1000:
                                state.alerts = state.alerts[-500:]

                            # Broadcast alert
                            await state.broadcast({
                                "type": "alert",
                                "data": state.alerts[-1]
                            })

                except Exception as e:
                    logger.error(f"Error processing {token}: {e}")
                    # Track error in cache
                    if token in state.token_data_cache:
                        state.token_data_cache[token]["last_error"] = str(e)
                        state.token_data_cache[token]["error_count"] = state.token_data_cache[token].get("error_count", 0) + 1

            # Broadcast delta updates (only changed tokens)
            state.last_update = time.time()
            state.metrics["poll_cycles"] += 1

            # Find changed tokens by comparing with last broadcast
            changed_tokens = []
            for token, row in state.token_data_cache.items():
                last = state.last_broadcast_cache.get(token)
                if last is None or last != row:
                    changed_tokens.append(row)

            # Only broadcast if there are changes or new connections
            if changed_tokens:
                message = {
                    "type": "update",
                    "data": list(state.token_data_cache.values()),
                    "delta": changed_tokens,
                    "timestamp": state.last_update,
                    "alert_categories": _build_alert_categories()
                }
                await state.broadcast(message)
                state.metrics["ws_messages_sent"] += len(state.websocket_clients)

                # Update last broadcast cache
                state.last_broadcast_cache = {k: dict(v) for k, v in state.token_data_cache.items()}

            # Wait for refresh signal or timeout (adaptive interval)
            interval = get_adaptive_interval()
            state.refresh_event.clear()
            try:
                await asyncio.wait_for(state.refresh_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue polling

        except Exception as e:
            logger.error(f"Poll error: {e}")
            await asyncio.sleep(5)


# ===============================
# Lifespan
# ===============================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Trading Dashboard API...")

    # Initialize storage
    state.storage = create_storage()

    # Initialize
    symbol_csv_path = os.path.join(project_root, "..", "symbol_mapping.csv")
    state.symbol_loader = SymbolLoader(symbol_csv_path)
    state.symbol_loader.load()

    # Build Yahoo mapping
    state.yahoo_mapping = {}
    for token, symbol in state.symbol_loader.token_to_symbol.items():
        yahoo_symbol = symbol.replace('-EQ', '').replace('-NS', '') + '.NS'
        state.yahoo_mapping[token] = yahoo_symbol

    state.provider = YahooFinanceProvider(state.yahoo_mapping)

    # Load saved watchlist (start empty if no saved watchlist)
    await state.load_watchlist()
    if not state.watchlists.get("Default"):
        state.watchlists["Default"] = []  # Start empty - user adds stocks

    # Load portfolio
    _load_portfolio()

    # Start polling
    state.running = True
    asyncio.create_task(poll_data())

    yield

    # Shutdown
    state.running = False
    state.executor.shutdown(wait=False)
    logger.info("API stopped")


# ===============================
# FastAPI App
# ===============================

app = FastAPI(title="Trading Dashboard API", lifespan=lifespan)

# CORS - configurable via env var for cloud deployment
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================
# WebSocket
# ===============================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = Query("local")):
    await websocket.accept()
    state.websocket_clients.add(websocket)

    try:
        # Load user's watchlists from storage
        user_wl = await state.storage.load(user_id)
        state.user_watchlists[user_id] = user_wl
        state.rebuild_global_watchlists()

        # Send initial data
        await websocket.send_json({
            "type": "init",
            "data": list(state.token_data_cache.values()),
            "watchlists": user_wl,
            "alerts": state.alerts[-50:],
            "alert_categories": _build_alert_categories()
        })

        # Keep alive
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "subscribe":
                watchlist = msg.get("watchlist", "Default")
                # If action is refresh, trigger immediate data fetch
                if msg.get("action") == "refresh":
                    state.refresh_event.set()
                await websocket.send_json({
                    "type": "subscribed",
                    "watchlist": watchlist,
                    "tokens": state.watchlists.get(watchlist, [])
                })

    except WebSocketDisconnect:
        state.websocket_clients.discard(websocket)
        # Clean up user watchlist tracking
        state.user_watchlists.pop(user_id, None)
        state.rebuild_global_watchlists()


# ===============================
# REST API
# ===============================

@app.get("/")
async def root():
    # Serve the static HTML dashboard
    html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")
    if os.path.exists(html_path):
        from fastapi.responses import FileResponse
        return FileResponse(html_path)
    return {"status": "running", "service": "Trading Dashboard API"}


@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health():
    return {
        "status": "healthy",
        "last_update": state.last_update,
        "active_tokens": len(state.token_data_cache),
        "connected_clients": len(state.websocket_clients),
        "users_online": len(state.user_watchlists),
        "uptime": time.time() - state.start_time,
        "poll_running": state.running
    }


@app.get("/api/metrics")
async def metrics():
    """Performance metrics endpoint"""
    import sys
    uptime = time.time() - state.start_time
    return {
        "uptime_seconds": round(uptime, 1),
        "uptime_human": f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s",
        "active_tokens": len(state.token_data_cache),
        "connected_clients": len(state.websocket_clients),
        "users_online": len(state.user_watchlists),
        "total_alerts": len(state.alerts),
        "portfolio_holdings": len(state.portfolio),
        "poll_cycles": state.metrics["poll_cycles"],
        "ws_messages_sent": state.metrics["ws_messages_sent"],
        "cache_size_tokens": len(state.token_data_cache),
        "cache_size_broadcast": len(state.last_broadcast_cache),
        "memory_mb": round(sys.getsizeof(state.token_data_cache) / 1024 / 1024, 2),
        "rate_limiter_calls": state.rate_limiter.calls if hasattr(state.rate_limiter, 'calls') else 0,
    }


@app.get("/api/data")
async def get_all_data():
    """Get all current data"""
    return {
        "data": list(state.token_data_cache.values()),
        "timestamp": state.last_update
    }


@app.get("/api/data/{token}")
async def get_token_data(token: str):
    """Get data for specific token"""
    if token not in state.token_data_cache:
        raise HTTPException(status_code=404, detail="Token not found")
    return state.token_data_cache[token]


@app.get("/api/candles/{token}")
async def get_candles(token: str, days: int = 5, interval: str = "5m"):
    """Get historical candles"""
    loop = asyncio.get_event_loop()
    candles = await loop.run_in_executor(
        state.executor, state.provider.get_candles, token, days, interval
    )

    chart_data = []
    for c in candles:
        chart_data.append({
            "time": c[0] // 1000,
            "open": c[1] / 100,
            "high": c[2] / 100,
            "low": c[3] / 100,
            "close": c[4] / 100,
            "volume": c[5]
        })

    return {
        "token": token,
        "symbol": state.provider.get_symbol(token),
        "candles": chart_data
    }


@app.get("/api/alerts")
async def get_alerts():
    """Get active alerts"""
    active = [a for a in state.alerts if a.get("status") == "active"]
    return {"alerts": active, "count": len(active)}


@app.get("/api/alerts/history")
async def get_alerts_history(limit: int = 50):
    """Get alert history"""
    return {"alerts": state.alerts[-limit:], "count": len(state.alerts)}


@app.get("/api/watchlists")
async def get_watchlists():
    """Get all watchlists"""
    return {"watchlists": state.watchlists}


@app.post("/api/watchlists")
async def save_watchlist(watchlist: Watchlist):
    """Save watchlist"""
    state.watchlists[watchlist.name] = watchlist.tokens
    return {"success": True, "name": watchlist.name}


@app.delete("/api/watchlists/{name}")
async def delete_watchlist(name: str):
    """Delete a watchlist (cannot delete Default)"""
    if name == "Default":
        raise HTTPException(status_code=400, detail="Cannot delete Default watchlist")
    if name in state.watchlists:
        del state.watchlists[name]
    # Remove from all user watchlists
    for user_wl in state.user_watchlists.values():
        user_wl.pop(name, None)
    await state.save_watchlist()
    return {"success": True, "deleted": name}


@app.post("/api/tokens/add")
async def add_token(token: str, watchlist: str = "Default", user_id: str = Query("local")):
    """Add token to watchlist and trigger immediate data fetch"""
    if watchlist not in state.watchlists:
        state.watchlists[watchlist] = []

    if token not in state.watchlists[watchlist]:
        state.watchlists[watchlist].append(token)

    # Update per-user watchlist and persist
    if user_id not in state.user_watchlists:
        state.user_watchlists[user_id] = {"Default": []}
    if watchlist not in state.user_watchlists[user_id]:
        state.user_watchlists[user_id][watchlist] = []
    if token not in state.user_watchlists[user_id][watchlist]:
        state.user_watchlists[user_id][watchlist].append(token)
    await state.save_watchlist(user_id)

    # Fetch data for the new token immediately (non-blocking, rate-limited)
    try:
        loop = asyncio.get_event_loop()
        await state.rate_limiter.acquire()
        quote = await loop.run_in_executor(
            state.executor, state.provider.get_live_quote, token
        )
        if quote:
            candles = state.provider.get_cached_candles(token)
            if candles is None:
                await state.rate_limiter.acquire()
                candles = await loop.run_in_executor(
                    state.executor, state.provider.get_candles, token, 5, "5m"
                )
            prev_day = state.provider.get_cached_prev_day(token)
            if prev_day is None:
                await state.rate_limiter.acquire()
                prev_day = await loop.run_in_executor(
                    state.executor, state.provider.get_previous_day_candles, token
                )
            indicators = calculate_all_indicators(candles, quote, prev_day)
            symbol = state.provider.get_symbol(token)

            row = {
                "token": token,
                "symbol": symbol,
                **indicators,
                "alert": check_alerts(token, indicators),
                "timestamp": datetime.now().isoformat()
            }
            state.token_data_cache[token] = row

            # Broadcast update to all clients immediately
            await state.broadcast({
                "type": "update",
                "data": list(state.token_data_cache.values()),
                "timestamp": time.time(),
                "alert_categories": _build_alert_categories()
            })
    except Exception as e:
        logger.error(f"Error fetching data for new token {token}: {e}")

    # Signal the poll loop to run immediately
    state.refresh_event.set()

    return {"success": True, "token": token, "symbol": state.symbol_loader.token_to_symbol.get(token, "")}


@app.delete("/api/tokens/{token}")
async def remove_token(token: str, watchlist: str = "Default", user_id: str = Query("local")):
    """Remove token from watchlist (idempotent - returns success even if already removed)"""
    if token in state.watchlists.get(watchlist, []):
        state.watchlists[watchlist].remove(token)

    # Update per-user watchlist and persist
    if user_id in state.user_watchlists:
        wl = state.user_watchlists[user_id].get(watchlist, [])
        if token in wl:
            wl.remove(token)
    await state.save_watchlist(user_id)

    # Also remove from cache if present
    state.token_data_cache.pop(token, None)
    return {"success": True}


@app.get("/api/instruments")
async def get_instruments():
    """Get all available instruments"""
    return {
        "instruments": [
            {"token": t, "symbol": s.replace('-EQ', '').replace('-NS', ''), "yahoo": state.yahoo_mapping.get(t, "")}
            for t, s in state.symbol_loader.token_to_symbol.items()
        ]
    }


@app.get("/api/symbols/search")
async def search_symbols(q: str = ""):
    """Search symbols by name"""
    all_symbols = [
        {"token": t, "symbol": s.replace('-EQ', '').replace('-NS', '')}
        for t, s in state.symbol_loader.token_to_symbol.items()
    ]

    if not q:
        return {"symbols": all_symbols[:100]}  # Return first 100 if no search

    q_lower = q.lower()
    filtered = [s for s in all_symbols if q_lower in s["symbol"].lower()]
    return {"symbols": filtered[:50]}  # Return max 50 results


@app.post("/api/alerts/clear")
async def clear_alerts():
    """Clear active alerts"""
    for alert in state.alerts:
        if alert.get("status") == "active":
            alert["status"] = "resolved"
            alert["resolved_at"] = datetime.now().isoformat()
    return {"success": True}


# ===============================
# Portfolio API
# ===============================

@app.get("/api/portfolio")
async def get_portfolio():
    """Get portfolio holdings with current prices and P&L"""
    result = []
    for holding in state.portfolio:
        token = holding.get("token", "")
        current_data = state.token_data_cache.get(token, {})
        current_price = current_data.get("ltp", holding.get("buy_price", 0))
        quantity = holding.get("quantity", 0)
        buy_price = holding.get("buy_price", 0)
        current_value = quantity * current_price
        invested_value = quantity * buy_price
        pnl = current_value - invested_value
        pnl_percent = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0

        result.append({
            **holding,
            "current_price": current_price,
            "current_value": round(current_value, 2),
            "invested_value": round(invested_value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "symbol": current_data.get("symbol", holding.get("symbol", ""))
        })

    total_invested = sum(h["invested_value"] for h in result)
    total_current = sum(h["current_value"] for h in result)
    total_pnl = total_current - total_invested

    return {
        "holdings": result,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
            "holdings_count": len(result)
        }
    }


@app.post("/api/portfolio")
async def add_holding(holding: PortfolioHolding):
    """Add a portfolio holding"""
    # Check if token already exists, update if so
    for i, h in enumerate(state.portfolio):
        if h.get("token") == holding.token:
            # Average buy price calculation
            old_qty = h.get("quantity", 0)
            old_price = h.get("buy_price", 0)
            new_qty = holding.quantity
            new_price = holding.buy_price
            total_qty = old_qty + new_qty
            if total_qty > 0:
                avg_price = (old_qty * old_price + new_qty * new_price) / total_qty
            else:
                avg_price = new_price
            state.portfolio[i]["quantity"] = total_qty
            state.portfolio[i]["buy_price"] = round(avg_price, 2)
            break
    else:
        state.portfolio.append(holding.dict())

    # Log trade
    state.trades.append({
        **holding.dict(),
        "type": "BUY",
        "timestamp": datetime.now().isoformat()
    })

    # Save to file
    _save_portfolio()
    return {"success": True, "holdings": len(state.portfolio)}


@app.delete("/api/portfolio/{token}")
async def remove_holding(token: str, quantity: int = Query(0)):
    """Remove a holding (partial or full)"""
    for i, h in enumerate(state.portfolio):
        if h.get("token") == token:
            if quantity <= 0 or quantity >= h.get("quantity", 0):
                # Remove completely
                removed = state.portfolio.pop(i)
                state.trades.append({
                    **removed,
                    "type": "SELL",
                    "quantity": removed.get("quantity", 0),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Partial sell
                state.portfolio[i]["quantity"] -= quantity
                state.trades.append({
                    **h,
                    "type": "SELL",
                    "quantity": quantity,
                    "timestamp": datetime.now().isoformat()
                })
            break
    _save_portfolio()
    return {"success": True}


@app.get("/api/portfolio/trades")
async def get_trades(limit: int = Query(50)):
    """Get trade history"""
    return {"trades": state.trades[-limit:]}


def _save_portfolio():
    """Save portfolio to local file"""
    try:
        portfolio_path = os.path.join(project_root, "..", "web_dashboard", "backend", "portfolio.json")
        with open(portfolio_path, 'w') as f:
            json.dump({"holdings": state.portfolio, "trades": state.trades}, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")


def _load_portfolio():
    """Load portfolio from local file"""
    try:
        portfolio_path = os.path.join(project_root, "..", "web_dashboard", "backend", "portfolio.json")
        if os.path.exists(portfolio_path):
            with open(portfolio_path, 'r') as f:
                data = json.load(f)
                state.portfolio = data.get("holdings", [])
                state.trades = data.get("trades", [])
                logger.info(f"Loaded portfolio: {len(state.portfolio)} holdings")
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)