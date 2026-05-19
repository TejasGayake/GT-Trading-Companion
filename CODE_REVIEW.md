# GT Trading Companion — Code Review Report

> **Date:** 2026-05-19
> **Commit reviewed:** `1e77408` (latest on master)
> **Reviewer:** Senior SWE audit (automated)

---

## Executive Summary

GT Trading Companion is a functional real-time NSE trading dashboard with a solid feature set — watchlists, alerts, charts, heat maps, portfolio tracking — all built on free Yahoo Finance data. However, it is **not production-ready** in its current form. The backend has no authentication (every endpoint is public), contains blocking I/O inside async handlers, has unbounded memory growth in alert and cache structures, and ships with no tests, no CI/CD, and no containerization. The frontend has 30+ individual `useState` calls that cause re-render storms on every WebSocket message, a module-level WebSocket variable that breaks React's reactivity model, and an incorrect RSI calculation that produces wrong indicator values. The polling architecture is fundamentally limited by Yahoo Finance's ~6s HTTP latency floor — sub-second updates are impossible without switching to a push-based API. The codebase is a strong personal project but needs ~3-4 weeks of hardening before it could handle real users or real money.

---

## 1. Code Quality & Architecture

### 1.1 Blocking Calls Inside Async Functions 🟠 High

**`main.py:1117-1138`** — `_save_portfolio()` and `_load_portfolio()` use synchronous `open()`, `json.dump()`, `json.load()` and are called directly from async route handlers without `run_in_executor`. This blocks the entire event loop during file I/O.

**`storage.py:33-44`** — `FileWatchlistStorage.load()` and `save()` are declared `async` but perform synchronous file I/O. Every watchlist load/save freezes all connected WebSocket clients.

**Fix:**
```python
# Before (blocks event loop):
async def load(self, user_id: str = "local"):
    with open(self.file_path, 'r') as f:
        return json.load(f)

# After:
async def load(self, user_id: str = "local"):
    loop = asyncio.get_running_loop()
    def _read():
        with open(self.file_path, 'r') as f:
            return json.load(f)
    return await loop.run_in_executor(None, _read)
```

### 1.2 WebSocket Architecture — Polling vs Streaming 🟡 Medium

The current architecture is **polling-based**: a background `poll_data()` task fetches from Yahoo Finance every ~7s, then broadcasts to all WebSocket clients via `state.broadcast()`. This is not a true streaming WebSocket — it's a push wrapper around periodic HTTP polling.

**Latency comparison:**

| Approach | Source Latency | Broadcast Latency | Total Staleness |
|----------|---------------|-------------------|-----------------|
| Current (Yahoo polling) | 5-8s per batch | <100ms (WebSocket) | **6-9 seconds** |
| True streaming (Angel One Kite WS) | <200ms | <100ms | **<300ms** |
| Hybrid (Yahoo + Twelve Data WS) | <1s (Twelve Data) | <100ms | **<1.2s** |

Sub-second updates are impossible with Yahoo Finance. The `yf.download()` call itself takes 5-6 seconds of server-side latency that cannot be optimized away.

### 1.3 Batch Fetching — Correct but Missing Retry 🟠 High

`yahoo_provider.py:296` — `get_quotes_batch()` and `get_prev_day_batch()` use `yf.download()` correctly for batch fetching (single HTTP call for all symbols). However, they are **not decorated with `@_retry_on_rate_limit`**. A single 429 during batch fetch fails the entire batch with no retry, while individual methods like `get_live_quote` do retry.

**Fix:**
```python
@_retry_on_rate_limit(max_retries=3, base_delay=2.0)
def get_quotes_batch(self, tokens: List[str]) -> Dict[str, Dict]:
    # ... existing implementation
```

### 1.4 Deprecated API Usage 🟢 Low

`main.py:341,360,690` — Uses `asyncio.get_event_loop()` which is deprecated in Python 3.10+. Should use `asyncio.get_running_loop()`.

---

## 2. Performance Optimisation

### 2.1 Minimum Theoretical Latency 🟡 Medium

The current poll cycle consists of:

| Step | Duration |
|------|----------|
| `yf.download()` for quotes (13 symbols) | ~6s |
| `yf.download()` for prev_day (every 10th cycle) | ~1.5s (concurrent) |
| Per-token candle fetch (when cache stale, 2min TTL) | ~1-2s |
| Indicator calculation | <100ms |
| WebSocket broadcast | <50ms |
| Adaptive interval pause | 1s |
| **Total per cycle** | **~7-8s** |

The hard floor is Yahoo Finance's HTTP response time (~6s for a batch of 13 symbols). The `get_adaptive_interval()` returning `1.0` is already minimal — reducing it further has no effect since the batch call dominates.

### 2.2 Concurrent Batch Execution — Already Implemented ✅

The latest commit (`1e77408`) runs `get_quotes_batch` and `get_prev_day_batch` concurrently via `asyncio.gather`. Prev_day is cached for 1 hour and only fetched every 10 cycles. This is optimal for the Yahoo Finance constraint.

### 2.3 Memory Leaks 🟠 High

**`main.py:111-129`** — Three unbounded structures:
- `state.alerts` — grows without bound (trim to 500 after 1000 is not eviction, just delayed overflow)
- `state.alert_cooldown` — entries are never evicted; over weeks this grows indefinitely
- `state.token_data_cache` / `state.last_broadcast_cache` — never pruned for tokens removed from watchlists

**`yahoo_provider.py:57-59`** — `_candle_cache`, `_quote_cache`, `_prev_day_cache` are plain dicts with no size limit. Over a long-running session with many different tokens, these grow without bound. The `close()` method clears them but is never called from the shutdown path.

**Fix:**
```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, maxsize=1000):
        self._cache = OrderedDict()
        self._maxsize = maxsize

    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key, value):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)
```

---

## 3. Error Handling & Resilience

### 3.1 Retry Decorator — Missing Jitter 🟡 Medium

`yahoo_provider.py:19-40` — The `_retry_on_rate_limit` decorator uses exponential backoff (2s, 4s, 8s) but no **jitter**. Multiple concurrent processes retrying at the same intervals will cause a thundering herd on Yahoo's servers.

**Fix:**
```python
import random

def _retry_on_rate_limit(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            self = args[0]
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    if "too many requests" in error_str or "429" in error_str or "rate limit" in error_str:
                        last_error = e
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)  # jitter
                        self.logger.warning(f"Rate limited, retry {attempt+1}/{max_retries} after {delay:.1f}s")
                        time.sleep(delay)
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator
```

### 3.2 No Circuit Breaker 🟡 Medium

When Yahoo Finance is down or rate-limiting heavily, every poll cycle retries 3 times per token, generating 39+ failing API calls before giving up. A circuit breaker would stop calling Yahoo after N consecutive failures and resume after a cooldown.

### 3.3 No Fallback Data Provider 🟡 Medium

If Yahoo Finance returns 429 or 5xx, there's no fallback. A simple provider abstraction would allow failover:

```python
class DataProvider(ABC):
    @abstractmethod
    def get_quotes_batch(self, tokens): ...
    @abstractmethod
    def get_candles(self, token, days, interval): ...

class YahooProvider(DataProvider): ...
class TwelveDataProvider(DataProvider): ...  # Free tier: 800 req/day

class FallbackProvider(DataProvider):
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def get_quotes_batch(self, tokens):
        try:
            return self.primary.get_quotes_batch(tokens)
        except Exception:
            return self.fallback.get_quotes_batch(tokens)
```

### 3.4 No Structured Logging 🟡 Medium

`utils/logger.py` uses plain text logging. No JSON logging, no correlation IDs, no log rotation size limits (only count-based). Production systems need structured logs for debugging.

---

## 4. Security Audit

### 4.1 No Authentication — Any Endpoint Is Public 🔴 Critical

`main.py:565` — The WebSocket endpoint accepts any `user_id` query parameter and trusts it completely. Every REST endpoint (`/api/tokens/add`, `/api/tokens/remove`, `/api/watchlists`, `/api/portfolio/*`) is publicly accessible with no authentication.

**Any user can read, modify, or delete any other user's watchlists and portfolio data.**

### 4.2 CORS Wildcard with Credentials 🟠 High

`main.py:549-554` — `CORS_ORIGINS` defaults to `"*"` with `allow_credentials=True`. Per the CORS spec, browsers reject `Access-Control-Allow-Origin: *` when credentials are present. This either silently breaks credential-based requests or, if relaxed by a browser, exposes the API to CSRF from any origin.

**Fix:**
```python
cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "https://gt-trading-companion.tgayake3142.workers.dev,http://localhost:3000"
).split(",")
```

### 4.3 No Input Sanitization on `user_id` 🟠 High

`main.py:565` — `user_id` is used as a storage key with no sanitization. In `FileWatchlistStorage` this is harmless (directory traversal mitigated by filename), but `SupabaseWatchlistStorage` injects it into query params without parameterized queries.

### 4.4 Synchronous HTTP Client 🟢 Low

The project uses `requests` (synchronous, via `yfinance`) and `httpx` (listed in requirements but unused). All `yfinance` calls are already wrapped in `run_in_executor`, which is the correct pattern. No migration to `aiohttp` is needed since the executor approach works correctly.

---

## 5. Testing Strategy

### 5.1 Current State 🔴 Critical

The `tests/` directory exists with 7 files, but:
- No `pytest.ini` or `pyproject.toml` for test configuration
- No CI/CD pipeline (`.github/workflows/` does not exist)
- Tests are not run automatically on push
- No test coverage reporting

### 5.2 Missing Test Coverage

| Component | Unit Tests | Integration Tests | Mock Tests |
|-----------|-----------|-------------------|-----------|
| Indicators (RSI, SMA, EMA, Supertrend, Camarilla) | ❌ | ❌ | ❌ |
| Yahoo Provider (batch, cache, retry) | ❌ | ❌ | ❌ |
| Rate Limiter | ❌ | ❌ | ❌ |
| WebSocket broadcast | ❌ | ❌ | ❌ |
| REST API endpoints | ❌ | ❌ | ❌ |
| Storage (file + Supabase) | ❌ | ❌ | ❌ |

### 5.3 Recommended Test Vectors for RSI

The current RSI calculation at `calculator.py:76-89` has a **correctness bug**: it averages gains by `len(gains)` and losses by `len(losses)` separately, instead of dividing by the period length (14). This means if there are 14 gains and 0 losses, the denominator is `sum([])/len([])` which would crash — but the `if gains and losses` guard at line 85 means RSI is simply not calculated in all-gain or all-loss periods.

**Correct RSI formula:**
```python
# Wilder's smoothing method
avg_gain = sum(gains) / 14  # divide by period, not by len(gains)
avg_loss = sum(losses) / 14  # divide by period, not by len(losses)
```

---

## 6. Production Readiness

### 6.1 No Containerization 🔴 Critical

No `Dockerfile` or `docker-compose.yml`. The Render deployment runs bare `uvicorn main:app` with no container isolation.

### 6.2 No CI/CD Pipeline 🔴 Critical

No `.github/workflows/` directory. Code is pushed directly to master with no automated testing, linting, or deployment gates.

### 6.3 Health Endpoint — Partial 🟡 Medium

`/api/health` exists and returns status, uptime, and active tokens. However, it doesn't verify:
- Data freshness (last successful poll timestamp vs current time)
- Yahoo Finance reachability
- Database connectivity

### 6.4 No Prometheus Metrics 🟡 Medium

No `/metrics` endpoint. Missing observability for:
- Request count and latency per endpoint
- WebSocket connection count
- Cache hit ratio
- Yahoo API error rate
- Poll cycle duration

### 6.5 File-Based Storage 🟡 Medium

`watchlist.json` and portfolio data are stored as local JSON files. On Render's free tier, the filesystem is ephemeral — data is lost on every deploy/restart. Supabase integration exists but is optional.

---

## 7. Frontend Improvements

### 7.1 Re-Render Storms 🟠 High

`App.js:59-108` — Over 30 individual `useState` declarations. Every WebSocket message triggers 4+ state updates (`setRowData`, `setLastUpdate`, `setDataLoading`, `setAlertCategories`), each causing a re-render. AG Grid handles this via its own diffing, but the rest of the UI (modals, alerts panel, portfolio view) re-renders unnecessarily.

**Fix:** Group related state into `useReducer`:
```javascript
const [state, dispatch] = useReducer(appReducer, initialState);

// In WebSocket handler:
dispatch({ type: 'WS_UPDATE', payload: { data, timestamp, alertCategories } });
// One dispatch = one re-render instead of four
```

### 7.2 Module-Level WebSocket Variable 🟠 High

`App.js:52-54` — `ws`, `reconnectAttempts`, `reconnectTimeoutId` are module-scoped `let` variables. They survive component re-renders but are invisible to React's dependency tracking. The `useEffect` at line 263 lists `ws` in its dependency array, but since `ws` is not state, the dependency never triggers the effect on reconnect.

**Fix:** Use `useRef`:
```javascript
const wsRef = useRef(null);
const reconnectRef = useRef({ attempts: 0, timeoutId: null });
```

### 7.3 JSON.parse Without Error Handling 🟠 High

`App.js:316` — `ws.onmessage` calls `JSON.parse(event.data)` with no try-catch. A malformed WebSocket message (e.g., partial frame, server bug) will crash the entire message handler and disconnect the client.

### 7.4 AudioContext Leak 🟡 Medium

`App.js:426-443` — A new `AudioContext` is created on every alert sound but never closed. AudioContexts are expensive browser resources. Should create one instance and reuse it.

### 7.5 Symbol Search Not Debounced 🟡 Medium

The search input triggers API calls on every keystroke. Should debounce with a 300ms delay:
```javascript
function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```

### 7.6 Connection Status Indicator — Already Exists ✅

The reconnecting UI with countdown and manual retry button was implemented in the improvementsv2.md work. This is done.

---

## 8. Documentation & Deployment

### 8.1 No CONTRIBUTING.md 🔴 Critical

No contribution guidelines exist. Adding new indicators, data providers, or tests has no documented process.

### 8.2 No `.env.example` 🟡 Medium

No environment variable template for onboarding. The required variables (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CORS_ORIGINS`) are only documented in `render.yaml` and `docs/Cloud Deployment Roadmap.md`.

### 8.3 No Inline Docstrings 🟢 Low

Public functions in `yahoo_provider.py`, `calculator.py`, and `main.py` lack Google/NumPy-style docstrings. The functions have comments but no structured documentation.

---

## Performance Comparison Table

| Metric | Before (sequential) | After (batched) | Theoretical Best (streaming API) |
|--------|--------------------|-----------------|---------------------------------|
| Quote latency (13 tokens) | ~26s | ~6s | <200ms |
| Full poll cycle | ~30s | ~7-8s | <1s |
| Data staleness | 30-40s | 7-8s | <300ms |
| API calls per cycle | 13-39 | 1-2 (batch) | 0 (push) |
| Rate limit risk | High (30+ calls) | Low (1-2 calls) | None |
| Memory per session | Unbounded | Unbounded | Bounded |

---

## Recommended Action Items

| Priority | Item | Severity | Effort | Section |
|----------|------|----------|--------|---------|
| 1 | Add API key authentication to WebSocket + REST | 🔴 Critical | M | 4.1 |
| 2 | Fix CORS wildcard (`*`) with credentials | 🟠 High | S | 4.2 |
| 3 | Fix RSI calculation (wrong averaging) | 🟠 High | S | 5.2 |
| 4 | Add `@retry` decorator to batch methods | 🟠 High | S | 1.3 |
| 5 | Move file I/O to `run_in_executor` | 🟠 High | S | 1.1 |
| 6 | Fix module-level WebSocket variable (useRef) | 🟠 High | S | 7.2 |
| 7 | Add try-catch around `JSON.parse` in WS handler | 🟠 High | S | 7.3 |
| 8 | Bound memory in alert/cache structures (LRU) | 🟠 High | M | 2.3 |
| 9 | Add jitter to retry backoff | 🟡 Medium | S | 3.1 |
| 10 | Create Dockerfile + docker-compose | 🔴 Critical | M | 6.1 |
| 11 | Add GitHub Actions CI pipeline | 🔴 Critical | M | 6.2 |
| 12 | Create CONTRIBUTING.md | 🔴 Critical | S | 8.1 |
| 13 | Add `.env.example` | 🟡 Medium | S | 8.2 |
| 14 | Write indicator unit tests with test vectors | 🔴 Critical | L | 5.2 |
| 15 | Add structured JSON logging | 🟡 Medium | M | 3.4 |
| 16 | Add `/metrics` Prometheus endpoint | 🟡 Medium | M | 6.4 |
| 17 | Improve health check (freshness, DB) | 🟡 Medium | S | 6.3 |
| 18 | Debounce symbol search | 🟡 Medium | S | 7.5 |
| 19 | Consolidate useState into useReducer | 🟠 High | L | 7.1 |
| 20 | Fix AudioContext leak | 🟡 Medium | S | 7.4 |
| 21 | Add circuit breaker for Yahoo API | 🟡 Medium | M | 3.2 |
| 22 | Add fallback data provider abstraction | 🟡 Medium | L | 3.3 |

**Effort key:** S = <2 hours, M = 2-8 hours, L = 1-3 days

---

## Final Verdict

**Not ready for production.** The project is a strong personal/hobby trading dashboard with excellent feature coverage, but it has critical gaps that prevent safe deployment:

1. **No authentication** — anyone can read/modify/delete all data
2. **Incorrect RSI** — indicator values are wrong in all-gain or all-loss periods
3. **No tests, no CI** — code ships untested
4. **No containerization** — deployment is fragile
5. **Memory leaks** — long-running sessions will consume unbounded memory

**What's done well:**
- Feature-rich UI with watchlists, portfolio, charts, heat maps, alerts
- Adaptive polling with batched Yahoo Finance calls
- WebSocket heartbeat with reconnection
- Supabase integration for persistence
- Good documentation (PROJECT-BRIEF.md, deployment roadmap)

**Recommended timeline to production:**
- **Week 1:** Fix critical items (auth, RSI, CORS, batch retry, file I/O)
- **Week 2:** Add Dockerfile, CI pipeline, unit tests for indicators
- **Week 3:** Frontend optimization (useReducer, useRef, debounce), structured logging
- **Week 4:** Prometheus metrics, improved health checks, fallback provider

With focused effort, this could be production-ready in 3-4 weeks.
