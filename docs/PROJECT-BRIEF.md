# GT Trading Companion — Project Brief

> **Purpose:** This document gives a new AI assistant (or human) everything needed to understand, maintain, and extend the GT Trading Companion in one read. Copy-paste this as your first message in a new session.

---

## What Is This?

A **real-time Indian stock market dashboard** that fetches live quotes from Yahoo Finance, calculates technical indicators (RSI, Supertrend, Camarilla pivots, VWAP, SMAs), and displays them in an Excel-style grid with alerts. No API key needed — uses free Yahoo Finance data.

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
| Alert cooldown | `main.py:107` | 300s (5 min) | Per-token per-alert-type |

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
| POST | `/api/tokens/add?token=X` | Add token to default watchlist |
| DELETE | `/api/tokens/{token}` | Remove token from default watchlist |
| GET | `/api/symbols/search?q=X` | Search available symbols |
| GET | `/api/candles/{token}` | Candlestick data for charts |
| POST | `/api/alerts/clear` | Clear all alerts |
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

**Push to `master` → both services auto-deploy:**
1. **Cloudflare Pages** detects push → runs `npm run build` → deploys frontend
2. **Render** detects push → runs `pip install -r requirements.txt` → starts `uvicorn main:app`

**Important:** Changing `render.yaml` env vars does NOT update existing Render services. Must update manually on Render dashboard (Render → service → Environment → Save).

**Frontend env vars on Cloudflare Pages** (set BEFORE build):
- `REACT_APP_API_URL` = `https://gt-trading-backend.onrender.com`
- `REACT_APP_WS_URL` = `wss://gt-trading-backend.onrender.com`

**Backend env vars on Render:**
- `CORS_ORIGINS` = `https://gt-trading-companion.tgayake3142.workers.dev,http://localhost:3000`
- `SUPABASE_URL` = (from Supabase dashboard)
- `SUPABASE_SERVICE_ROLE_KEY` = `sb_secret_...` key (NOT legacy anon/service_role)

**UptimeRobot** pings `/api/health` every 5 min to prevent Render free tier cold starts.

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

---

## Commit History

```
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
