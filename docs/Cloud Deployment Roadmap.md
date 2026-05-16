# GT Trading Companion - Cloud Deployment Roadmap

## Overview

Deploy the GT Trading Companion to free cloud services for 24/7 access.

| Service | Purpose | Cost |
|---------|---------|------|
| Supabase | Database (watchlists) | Free (500MB) |
| Render | Backend API + WebSocket | Free (512MB RAM) |
| Cloudflare Pages | Frontend (React) | Free (unlimited) |
| UptimeRobot | Keep backend awake | Free (50 monitors) |

**Total cost: $0/month**

---

## Phase 1: Supabase (Database) — 5 min

### 1.1 Create Account
- Go to `https://supabase.com`
- Click "Start your project" → Sign in with GitHub

### 1.2 Create Project
- Click "New Project"
- Organization: Create one (e.g., "Tejas Projects")
- Project name: `gt-trading`
- Database password: Generate a strong one (save it)
- Region: `Southeast Asia (Mumbai)`
- Click "Create new project"
- Wait ~2 minutes for provisioning

### 1.3 Run Database Migration
- Left sidebar → "SQL Editor" → "New query"
- Paste and click "Run":

```sql
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    tokens JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
```

### 1.4 Get API Credentials
- Left sidebar → gear icon (Settings) → "API"
- Copy these (need them later):
  - **Project URL**: `https://xxxxxxxx.supabase.co`
  - **Service Role Key**: starts with `eyJ...` (under `service_role`, NOT `anon`)

---

## Phase 2: Render (Backend) — 10 min

### 2.1 Create Account
- Go to `https://render.com`
- Click "Get Started for Free" → Sign in with GitHub
- Authorize Render to access repos

### 2.2 Create Web Service
- Dashboard → "New +" → "Web Service"
- Connect repository: `TejasGayake/GT-Trading-Companion`
- Click "Connect"

### 2.3 Configure Service

| Field | Value |
|-------|-------|
| Name | `gt-trading-backend` |
| Region | `Singapore` |
| Branch | `master` |
| Runtime | `Python 3` |
| Build Command | `pip install -r web_dashboard/backend/requirements.txt` |
| Start Command | `cd web_dashboard/backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Plan | `Free` |

### 2.4 Set Environment Variables

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | `https://xxxxxxxx.supabase.co` (from 1.4) |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` (from 1.4) |
| `CORS_ORIGINS` | `*` (update after Cloudflare deploy) |

### 2.5 Deploy
- Click "Create Web Service"
- Wait 3-5 minutes
- Watch logs for: `Starting Trading Dashboard API...`
- Copy backend URL: `https://gt-trading-backend.onrender.com`
- Test: open `https://gt-trading-backend.onrender.com/api/health`

---

## Phase 3: Cloudflare Pages (Frontend) — 10 min

### 3.1 Create Account
- Go to `https://pages.cloudflare.com`
- Sign up → Sign in with GitHub

### 3.2 Create Pages Project
- "Create a project" → "Connect to Git"
- Choose: `TejasGayake/GT-Trading-Companion`
- Click "Begin setup"

### 3.3 Configure Build

| Field | Value |
|-------|-------|
| Project name | `gt-trading-companion` |
| Production branch | `master` |
| Framework preset | `None` |
| Build command | `cd web_dashboard/frontend && npm run build` |
| Build output directory | `web_dashboard/frontend/build` |

### 3.4 Set Environment Variables

| Key | Value |
|-----|-------|
| `REACT_APP_API_URL` | `https://gt-trading-backend.onrender.com` |
| `REACT_APP_WS_URL` | `wss://gt-trading-backend.onrender.com` |

- Click "Save and Deploy"
- Wait 3-5 minutes
- Frontend URL: `https://gt-trading-companion.pages.dev`

### 3.5 Update Render CORS
- Render dashboard → your service → "Environment"
- Update `CORS_ORIGINS`:
  ```
  https://gt-trading-companion.pages.dev,http://localhost:3000
  ```
- Save (auto-redeploys)

---

## Phase 4: UptimeRobot (Keep Alive) — 3 min

### 4.1 Create Account
- Go to `https://uptimerobot.com`
- Sign up free (no credit card)

### 4.2 Add Monitor

| Field | Value |
|-------|-------|
| Monitor Type | `HTTP(s)` |
| Friendly Name | `GT Trading Backend` |
| URL | `https://gt-trading-backend.onrender.com/api/health` |
| Monitoring Interval | `5 minutes` |

---

## Phase 5: Verify — 5 min

### 5.1 Test Live Dashboard
- Open `https://gt-trading-companion.pages.dev`
- Click "Add Token" → enter `2885` (Reliance)
- Wait 5-10 seconds for data

### 5.2 Test Multi-User
- Open in different browser/incognito
- Add different token (e.g., `1594` for Infosys)
- Both browsers should see both stocks

### 5.3 Test Persistence
- Refresh page
- Watchlist should restore from Supabase

### 5.4 Check Health
- Open `https://gt-trading-backend.onrender.com/api/health`
- Expected:
```json
{
  "status": "healthy",
  "active_tokens": 2,
  "connected_clients": 1,
  "users_online": 2,
  "uptime": 123.45,
  "poll_running": true
}
```

---

## Troubleshooting

### "Disconnected" on frontend
- Check Render logs — backend may have failed
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`

### No data showing
- Check backend: `https://gt-trading-backend.onrender.com/api/health`
- Add tokens via "Add Token" — watchlist starts empty

### CORS errors
- `CORS_ORIGINS` in Render must include Cloudflare Pages URL

### Render cold start (30-60s delay)
- UptimeRobot should prevent this
- First load after cold start takes longer — normal

### Build fails on Cloudflare
- Check build logs for missing dependencies
- Build command must be: `cd web_dashboard/frontend && npm run build`

---

## URLs to Save

| Service | URL |
|---------|-----|
| GitHub Repo | `https://github.com/TejasGayake/GT-Trading-Companion` |
| Supabase Dashboard | `https://supabase.com/dashboard` |
| Render Dashboard | `https://dashboard.render.com` |
| Cloudflare Dashboard | `https://dash.cloudflare.com` |
| UptimeRobot Dashboard | `https://uptimerobot.com/dashboard` |
| **Live Dashboard** | `https://gt-trading-companion.pages.dev` |
| **Backend API** | `https://gt-trading-backend.onrender.com` |
| **API Health** | `https://gt-trading-backend.onrender.com/api/health` |
