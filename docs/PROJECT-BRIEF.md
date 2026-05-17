# GT Trading Companion — Project Brief

> **Purpose:** This document gives a new AI assistant (or human) everything needed to understand, maintain, and extend the GT Trading Companion in one read. Copy-paste this as your first message in a new session.

---

## What Is This?

A **real-time Indian stock market dashboard** that fetches live quotes from Yahoo Finance, calculates technical indicators (RSI, Supertrend, Camarilla pivots, VWAP, SMAs), and displays them in an Excel-style grid with alerts. No API key needed — uses free Yahoo Finance data.

**Core features:**
- Live watchlist with real-time price updates (WebSocket)
- Multiple watchlist groups with create/delete/switch
- Portfolio tracker with P&L, averaging, and trade history
- Interactive charts with overlays (Camarilla H4/L4, Supertrend, VWAP), custom price lines, and timeframe selector (1D/5D/1M)
- Alert system (volume spike, RSI, camarilla breakout) with deduplication (5-min cooldown) + user-created price alerts with browser notifications
- Heat map view with RSI, change%, volume ratio, Supertrend, and Camarilla levels (H4/H3/L3/L4)
- CSV export for data analysis
- Adaptive polling (faster during market hours, slower off-hours)
- WebSocket heartbeat with automatic reconnection and countdown UI
- Dark/light mode with persistent theme preference
- Default watchlist with 15 NSE stocks for new users

**Two interfaces:**
- **React frontend** (AG Grid + lightweight-charts) — deployed on Cloudflare Pages
- **Standalone HTML dashboard** (`web_dashboard/index.html`) — self-contained, no build step, served by the backend

Both share the same backend and should stay feature-synced.

---

## Architecture

```
┌─────────────────────────────────────┐
│  Cloudflare Pages (Frontend)        │
│  gt-trading-companion               │
│  .tgayake3142.workers.dev           │
│  React 18 + AG Grid + lightweight-  │
│  charts                             │
└──────────────┬──────────────────────┘
               │ WebSocket + REST API
               ▼
┌─────────────────────────────────────┐
│  Render (Backend)                   │
│  gt-trading-backend.onrender.com    │
│  FastAPI + uvicorn (Python 3.11)    │
│  Background poll loop (5s interval) │
│  Rate limiter (30 calls/60s)        │
└──────────────┬──────────────────────┘
               │ Watchlist persistence
               ▼
┌─────────────────────────────────────┐
│  Supabase (Database)                │
│  PostgreSQL — watchlists table      │
│  Falls back to local JSON file      │
│  when env vars absent               │
└─────────────────────────────────────┘
```

**Data flow:** Backend polls Yahoo Finance every 5 seconds → calculates indicators → caches in memory → broadcasts to all WebSocket clients → frontend updates grid in real-time.

---

## File Structure

```
GT Trading Companion/
├── yahoo_provider.py          # Core: Yahoo Finance data fetcher with caching + retry
├── yahoo_adapter.py           # Compatibility shim (matches old Angel One interface)
├── yahoo_websocket.py         # Polling-based live stream for Excel path
├── instrument_master.csv      # Angel One token → symbol mapping (207 NSE stocks)
├── symbol_mapping.csv         # Curated token → Yahoo symbol mapping
├── render.yaml                # Render deployment config
├── setup.bat / run.bat        # One-click local setup / quick start
│
├── config/
│   ├── settings.py            # AppConfig dataclass (POLL_INTERVAL, rate limits, etc.)
│   ├── app_config.py          # Older config with Angel One credentials
│   └── credentials.py         # Angel One API credentials (legacy)
│
├── web_dashboard/
│   ├── index.html             # Standalone HTML dashboard (keep in sync with React!)
│   │
│   ├── backend/
│   │   ├── main.py            # FastAPI app — REST + WebSocket + poll loop
│   │   ├── rate_limiter.py    # AsyncRateLimiter (token bucket, 30 calls/60s)
│   │   ├── storage.py         # FileWatchlistStorage + SupabaseWatchlistStorage
│   │   ├── watchlist.json     # Local watchlist persistence
│   │   ├── portfolio.json     # Portfolio holdings + trade history
│   │   └── requirements.txt   # Python deps
│   │
│   └── frontend/
│       ├── src/
│       │   ├── App.js         # Single React component — all UI logic
│       │   └── index.css      # All styles
│       ├── package.json       # React deps
│       └── .env               # DISABLE_ESLINT_PLUGIN=true (for CI)
│
├── indicators/
│   ├── calculator.py          # SMA, EMA, RSI, VWAP, Supertrend, Camarilla
│   └── alerts.py              # Alert system (volume spike, RSI, price jump)
│
├── data/                      # Models (TickData, CandleData), buffers, processor
├── utils/                     # Logger, symbol_loader, helpers, validators
├── excel/                     # xlwings Excel integration (legacy path)
├── angel_api/                 # Legacy Angel One API client (not actively used)
├── supabase/
│   └── schema.sql             # PostgreSQL watchlists table
└── docs/
    └── Cloud Deployment Roadmap.md
```

---

## Key Configuration Values

| Setting | Location | Value | Purpose |
|---------|----------|-------|---------|
| `POLL_INTERVAL` | `config/settings.py` | 5.0s | Seconds between data polls |
| `QUOTE_CACHE_DURATION` | `yahoo_provider.py` | 10s | Quote cache TTL |
| `CACHE_DURATION` | `yahoo_provider.py` | 120s | Candle cache TTL |
| `PREV_DAY_CACHE_DURATION` | `yahoo_provider.py` | 3600s | Previous day cache TTL |
| `RATE_LIMIT_CALLS` | `config/settings.py` | 30 | Max calls per period |
| `RATE_LIMIT_PERIOD` | `config/settings.py` | 60s | Rate limit window |
| `MAX_WATCHLIST_TOKENS` | `config/settings.py` | 200 | Hard cap on tokens |
| Alert cooldown | `main.py` | 300s (5 min) | Per-token per-alert-type dedup |
| Market hours | `main.py` | 9:15-15:30 IST | Adaptive polling: 5s market, 30s off-hours |
| Portfolio storage | `main.py` | `portfolio.json` | Holdings + trade history persistence |

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET/HEAD | `/api/health` | Health check (UptimeRobot monitors this) |
| GET | `/api/data` | Current token data cache |
| GET | `/api/alerts/categories` | Categorized alerts (volume_spike, camarilla, volume_sma8) |
| GET | `/api/watchlist` | All watchlists |
| GET | `/api/watchlist/{user_id}` | User-specific watchlist |
| POST | `/api/watchlist/{user_id}` | Save user watchlist |
| DELETE | `/api/watchlists/{name}` | Delete a watchlist group |
| POST | `/api/tokens/add?token=X&watchlist=Y` | Add token to watchlist |
| DELETE | `/api/tokens/{token}?watchlist=Y` | Remove token from watchlist |
| GET | `/api/symbols/search?q=X` | Search available symbols |
| GET | `/api/candles/{token}?days=5` | Candlestick data for charts (days: 1, 5, 30) |
| POST | `/api/alerts/clear` | Clear all alerts |
| GET | `/api/portfolio` | Get portfolio holdings with live P&L |
| POST | `/api/portfolio` | Add/update holding (quantity averaging) |
| DELETE | `/api/portfolio/{token}?quantity=N` | Remove holding (partial or full) |
| GET | `/api/portfolio/trades?limit=50` | Trade history log |
| WS | `/ws?user_id=X` | WebSocket for real-time updates |

---

## Live URLs

| Service | URL |
|---------|-----|
| **Frontend** | `https://gt-trading-companion.tgayake3142.workers.dev/` |
| **Backend** | `https://gt-trading-backend.onrender.com` |
| **Health check** | `https://gt-trading-backend.onrender.com/api/health` |
| **Standalone HTML** | `https://gt-trading-backend.onrender.com/` (root) |
| **GitHub** | `https://github.com/TejasGayake/GT-Trading-Companion` |

---

## How to Run Locally

```bash
# Quick start (Windows)
setup.bat          # First time — installs deps + starts both
run.bat            # After setup — just starts servers

# Manual
python web_dashboard/backend/main.py    # Backend on :8000
cd web_dashboard/frontend && npm start  # Frontend on :3000
```

Frontend proxies to backend via `"proxy": "http://localhost:8000"` in package.json.

---

## How Deployment Works

### The Auto-Deploy Pipeline

Both services are connected to the GitHub repo and **auto-deploy on every push to `master`**. No manual deploy step needed.

```
git push origin master
        │
        ├──→ Cloudflare Pages detects push
        │    1. Clones repo
        │    2. Sets env vars (REACT_APP_API_URL, REACT_APP_WS_URL)
        │    3. Runs: cd web_dashboard/frontend && npm run build
        │    4. Deploys build/ output to CDN
        │    5. Live at https://gt-trading-companion.tgayake3142.workers.dev/
        │    ⏱ Takes 3-5 minutes
        │
        └──→ Render detects push
             1. Clones repo
             2. Runs: pip install -r web_dashboard/backend/requirements.txt
             3. Runs: cd web_dashboard/backend && uvicorn main:app --host 0.0.0.0 --port $PORT
             4. Live at https://gt-trading-backend.onrender.com
             ⏱ Takes 3-5 minutes (longer if cold start)
```

### How to Deploy After Making Changes

```bash
# 1. Make your code changes
# 2. Stage, commit, push — that's it
git add <changed-files>
git commit -m "Your commit message"
git push
# 3. Both services auto-deploy within 3-5 min
```

### How to Check Deploy Status

| Service | Where to check |
|---------|---------------|
| **Cloudflare Pages** | https://dash.cloudflare.com → Pages → gt-trading-companion → Deployments |
| **Render** | https://dashboard.render.com → gt-trading-backend → Logs |
| **Backend health** | `curl https://gt-trading-backend.onrender.com/api/health` |
| **Frontend live** | Open https://gt-trading-companion.tgayake3142.workers.dev/ |

### Deploy Triggers

- **Cloudflare Pages:** Any push to `master` that changes files under `web_dashboard/frontend/`. If only backend files changed, Pages still triggers but the build output is identical.
- **Render:** Any push to `master`. Both backend-only and frontend-only changes trigger a full redeploy.

### Important Notes

- **`render.yaml` env vars don't update existing services.** Changing env vars in `render.yaml` only affects NEW service setups. For existing Render services, update manually: Render dashboard → service → Environment → edit → Save (triggers redeploy).
- **Cloudflare Pages env vars must be set BEFORE build.** `REACT_APP_*` vars get baked into the JS bundle at build time. Setting them after deploy has no effect — you must redeploy.
- **Both deploys are independent.** A frontend-only change still triggers a backend redeploy on Render (and vice versa). This is fine — both are idempotent.
- **Render free tier has cold starts.** If no requests come in for ~15 min, the service spins down. UptimeRobot pings `/api/health` every 5 min to prevent this.

### Frontend Environment Variables (Cloudflare Pages)

Set at: Cloudflare Dashboard → Pages → gt-trading-companion → Settings → Environment variables

| Key | Value |
|-----|-------|
| `REACT_APP_API_URL` | `https://gt-trading-backend.onrender.com` |
| `REACT_APP_WS_URL` | `wss://gt-trading-backend.onrender.com` |
| `DISABLE_ESLINT_PLUGIN` | `true` |

### Backend Environment Variables (Render)

Set at: Render Dashboard → gt-trading-backend → Environment

| Key | Value |
|-----|-------|
| `CORS_ORIGINS` | `https://gt-trading-companion.tgayake3142.workers.dev,http://localhost:3000` |
| `SUPABASE_URL` | (from Supabase dashboard → Settings → API) |
| `SUPABASE_SERVICE_ROLE_KEY` | `sb_secret_...` (NOT legacy anon/service_role) |

### UptimeRobot (Keep Render Awake)

- URL: https://uptimerobot.com
- Monitor type: HTTP(s)
- URL to monitor: `https://gt-trading-backend.onrender.com/api/health`
- Interval: every 5 minutes
- This prevents Render free tier from spinning down due to inactivity

---

## Recent Issues Fixed (2026-05-16)

### 1. Yahoo Finance Rate Limiting (commit 7a46c1c)
**Problem:** "Too Many Requests" errors — app was making ~180 API calls/min, Yahoo allows ~33/min.

**Fix:**
- Added `_retry_on_rate_limit` decorator with exponential backoff (2s/4s/8s) in `yahoo_provider.py`
- All 3 call types (quote, candles, prev_day) now go through rate limiter
- Quote cache: 2s → 10s, Candle cache: 60s → 120s, Poll interval: 2s → 5s
- Poll loop skips candle/prev_day fetch when cache is still fresh

### 2. CORS Mismatch (commit 7a46c1c)
**Problem:** Frontend at `workers.dev` couldn't reach backend — CORS_ORIGINS had `pages.dev`.

**Fix:** Updated `render.yaml` CORS_ORIGINS to `workers.dev` URL. User must also update on Render dashboard manually.

### 3. ReferenceError in Frontend (commit ccddf05)
**Problem:** `Cannot access 'he' before initialization` — format helpers defined after useMemo.

**Fix:** Moved format helper functions before useMemo.

### 4. Health Endpoint 405 (commit b09d499)
**Problem:** UptimeRobot got 405 Method Not Allowed on HEAD requests.

**Fix:** Changed `@app.get` to `@app.api_route(methods=["GET", "HEAD"])`.

### 5. Cloudflare Infinite Loop (commit 80e2cd8)
**Problem:** `_redirects` file caused error 10021 infinite redirect.

**Fix:** Removed `_redirects` — Cloudflare Pages handles SPA routing automatically.

### 6. ReferenceError: drawing tool state (commit 0fd4a77)
**Problem:** `Cannot access 'lt' before initialization` — `chartOverlays` and `customLines` states declared at line 348 but referenced in useEffect at line 174 (temporal dead zone).

**Fix:** Moved drawing tool state declarations before the useEffect that uses them.

---

## improvementsv2.md Features Implemented (2026-05-17)

### 1. Default Stocks for New Users
**Problem:** New users saw empty watchlist with no stocks.

**Fix:** Backend now seeds 15 default NSE stocks (RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK, LT, AXISBANK, MARUTI, SUNPHARMA, WIPRO) when watchlist is empty on first load.

### 2. WebSocket Heartbeat + Reconnect UI
**Problem:** Users saw "Disconnected" with no indication of reconnection attempts.

**Fix:**
- Backend sends `{"type": "ping"}` every 15 seconds to all WebSocket clients
- Frontend responds with `{"type": "pong"}` to acknowledge connection
- On miss, frontend shows "Reconnecting in Xs" with countdown timer
- Manual "Retry Now" button allows immediate reconnection attempt
- Exponential backoff (1s, 2s, 4s, 8s...) prevents server hammering

### 3. Error Messaging with Specific Types
**Problem:** Generic "Failed to add token" errors with no guidance.

**Fix:** `parseError()` function detects specific error types:
- Rate limit (429) → "Rate limit exceeded - please wait a moment before retrying"
- Network error → "Network error - check your internet connection"
- Invalid symbol → "Invalid symbol - use .NS suffix for NSE stocks"
- Toast duration extended to 8s for warnings/errors

### 4. Camarilla in Heat Map + Tooltips
**Problem:** Heat map showed RSI, change%, vol ratio, supertrend but missing Camarilla levels.

**Fix:**
- Added H4, H3, L3, L4 columns to heat map
- Proximity-based coloring: cells turn red when LTP is within 0.5% of level
- Tooltips on all indicators explaining what each value means
- Heat map now scrollable horizontally for all columns

### 5. Chart Timeframe Selector
**Problem:** Charts always showed 5-day data with no way to change timeframe.

**Fix:** Added 1D/5D/1M buttons in chart modal header. Selecting a timeframe re-fetches candle data with appropriate `days` parameter (1, 5, or 30).

### 6. User-Created Alerts with Browser Notifications
**Problem:** Only system-generated alerts (volume spike, RSI, camarilla). No way to set custom price alerts.

**Fix:**
- "Create Alert" button in Alerts tab opens modal
- Select stock from dropdown (shows current LTP)
- Choose condition: "Price goes above" or "Price goes below"
- Enter target price
- Alerts stored in `localStorage('user_alerts')`
- Checked against live prices every update cycle
- Browser Notification API integration (permission requested on first alert)
- Triggered alerts show "TRIGGERED" badge with reset option

### 7. Dark/Light Mode Persistence
**Problem:** Theme reset to dark on every page refresh.

**Fix:** Theme saved to `localStorage('gt_theme')` on toggle, restored on component mount. Uses `useState(() => localStorage.getItem('gt_theme') || 'dark')` for lazy initialization.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Data source | yfinance (Yahoo Finance, no API key) |
| Frontend | React 18, AG Grid, lightweight-charts, Lucide icons |
| Database | Supabase (PostgreSQL) — optional, falls back to local JSON |
| Hosting | Render (backend), Cloudflare Pages (frontend) |
| Monitoring | UptimeRobot (keeps Render awake) |
| Legacy | Angel One SmartAPI, xlwings Excel integration |

---

## Gotchas & Lessons Learned

1. **CORS origin must be the CLIENT URL, not the server URL.** `localhost:3000` for local dev, `workers.dev` for production. Never `localhost:8000`.
2. **`render.yaml` env vars don't update existing services.** Always update on Render dashboard manually.
3. **Cloudflare Pages: set `REACT_APP_*` env vars BEFORE build.** They get baked into the JS bundle at build time.
4. **Don't add `_redirects` for React SPAs on Cloudflare Pages.** It causes infinite loops. Pages handles it automatically.
5. **Use `DISABLE_ESLINT_PLUGIN=true` in `.env` for CI builds.** CRA's ESLint plugin fails in CI.
6. **UptimeRobot needs HEAD support.** Use `@app.api_route(methods=["GET", "HEAD"])` not `@app.get`.
7. **Supabase: use `sb_secret_` key for backend**, not legacy `anon`/`service_role`.
8. **Frontend is at `workers.dev`, not `pages.dev`.** Cloudflare Workers domain.
9. **Each watchlist token ≈ 12 API calls/min** with current caching. 200 tokens = ~2400 calls/min (will hit Yahoo limits).
10. **User prefers standalone HTML over React.** Keep both interfaces feature-synced.
11. **React `useState` declarations must come before `useEffect` that references them.** `const` variables are in temporal dead zone until their line — referencing them in an earlier useEffect causes `ReferenceError: Cannot access 'X' before initialization`.

---

## Commit History

```
[Latest] improvementsv2.md items: default stocks, WebSocket heartbeat, user alerts, theme persistence, Camarilla heat map, chart timeframes, error messaging
367158b Fix STATUS column showing ERROR for all rows
76d0949 Fix React error #31: use React component for badge cellRenderer
5087574 Remove demo watchlist feature
b7c279d Fix performance badge rendering: use DOM elements instead of HTML string
1ef8461 Fix 4 remaining bugs from improvementsv2.md
0fd4a77 Fix: move drawing tool state declarations before useEffect reference
7d97451 Complete partial features: watchlists, portfolio, drawing tools
3a46277 Expand deployment pipeline docs with auto-deploy workflow
d45533f Add comprehensive project brief for onboarding new sessions
7a46c1c Fix Yahoo rate limiting, CORS for workers.dev, and add alert icons
ccddf05 Fix: move format helpers before useMemo to fix ReferenceError
494a935 Add instrument master CSV for symbol mapping
b09d499 Support HEAD requests on health endpoint for UptimeRobot
80e2cd8 Remove _redirects causing infinite loop on Cloudflare Pages
7dd5648 Disable ESLint plugin for CI build
907eb29 Fix ESLint errors for CI build
1da77cb Add cloud deployment roadmap
de8dd91 Add cloud deployment support
00cdd98 Add one-click setup for new users
e9f4d17 Initial commit
```

---

## Improvements Roadmap (as of 2026-05-17)

**Completed (14/14 from improvements + extras):**
- Adaptive polling (market hours detection, volatility-based intervals)
- Alert deduplication (5-min cooldown per token per alert type)
- CSV export (AG Grid built-in export)
- Multiple watchlist groups (create/delete/switch)
- Portfolio tracker (holdings with P&L, averaging, trade history)
- Drawing tools (Camarilla/Supertrend/VWAP toggles + custom price lines)
- Heat map view (RSI, change%, volume ratio, supertrend)
- Virtual scrolling (AG Grid built-in row virtualization)
- WebSocket delta updates (only broadcast changed tokens)
- Mobile responsive (media queries + bottom nav with all tabs)
- Loading skeleton (shimmer animation while data loads)
- Keyboard shortcuts (Ctrl+A/F/E/D, F5, Escape)
- CSV bulk upload (upload CSV to add multiple stocks at once)
- Performance monitoring (/api/metrics endpoint)

**improvementsv2.md Items Completed (2026-05-17):**

| # | Feature | Priority | Status | Implementation |
|---|---------|----------|--------|----------------|
| 1 | Default stocks for new users | P0 | ✅ Done | Backend seeds 15 NSE stocks when watchlist is empty |
| 2 | Error messaging with specific types | P1 | ✅ Done | `parseError()` detects rate limit, network, invalid symbol errors |
| 3 | WebSocket heartbeat + reconnect UI | P0 | ✅ Done | Server sends ping every 15s, client shows "Reconnecting in Xs" with countdown |
| 4 | Persist dark/light mode | P2 | ✅ Done | Theme saved to `localStorage('gt_theme')`, restored on load |
| 5 | User-created alerts | P2 | ✅ Done | "Create Alert" modal with price above/below conditions, browser notifications |
| 6 | Camarilla in heat map + tooltips | P1 | ✅ Done | H4/H3/L3/L4 columns with proximity coloring, tooltips on all indicators |
| 7 | Chart timeframe selector | P2 | ✅ Done | 1D/5D/1M buttons in chart modal, fetches appropriate data |

**Key implementation details:**
- **WebSocket heartbeat**: Backend sends `{"type": "ping", "ts": ...}` every 15 seconds, client responds with `{"type": "pong"}`. On miss, frontend shows reconnect countdown with exponential backoff.
- **User alerts**: Stored in `localStorage('user_alerts')`. Checked against live prices in `useEffect`. Uses browser Notification API (permission requested on first alert creation).
- **Camarilla heat map**: Shows H4, H3, L3, L4 columns. Cells turn red when LTP is within 0.5% of level (proximity-based coloring).
- **Default stocks**: Seeded tokens: RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK, LT, AXISBANK, MARUTI, SUNPHARMA, WIPRO.

**Remaining (from original 12):**
- Backtesting
- Voice commands

See `improvements.md` and `improvementsv2.md` for full detailed specs.

---

## User Preferences

- **No co-author lines** in commit messages — only user as author
- **Prefers one-click scripts** over manual terminal commands
- **Prefers standalone HTML dashboard** over React — keep both in sync
- **Execute directly** instead of giving instructions (just do `git push`, don't say "you should push")
- **Be explicit about UI steps** — button labels, scroll locations in cloud dashboards
- **Uses Obsidian** for documentation — prefers `.md` files in `docs/`
- **GitHub username:** TejasGayake

---

## Where to Continue

**If resuming work, check:**
1. `git log --oneline -5` for latest commits
2. `git status` for uncommitted changes
3. `https://gt-trading-backend.onrender.com/api/health` for deployment health
4. `https://gt-trading-companion.tgayake3142.workers.dev/` for frontend

**Common tasks:**
- Add a new indicator → `indicators/calculator.py` + add column in `App.js` and `index.html`
- Add a new alert type → `indicators/alerts.py` + add column in `main.py` alert_categories + add UI in `App.js` and `index.html`
- Change poll/cache timing → `config/settings.py` (POLL_INTERVAL) + `yahoo_provider.py` (cache durations)
- Fix frontend → edit `web_dashboard/frontend/src/App.js` + `index.css` → `git push` → auto-deploys
- Fix backend → edit `web_dashboard/backend/main.py` → `git push` → auto-deploys
- Update env vars → Render dashboard manually (render.yaml changes don't affect existing services)
