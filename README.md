# GT Trading Companion

Trading dashboard with real-time market data, technical indicators, and alerts. Uses Yahoo Finance for live NSE stock data — no API keys required.

## One-Click Setup (For New Users)

### Prerequisites
- **Python 3.9+** — [Download here](https://python.org/downloads/) (check "Add to PATH" during install)
- **Node.js 16+** — [Download here](https://nodejs.org/)

### Steps
1. **Clone the repo:**
   ```bash
   git clone https://github.com/TejasGayake/GT-Trading-Companion.git
   cd GT-Trading-Companion
   ```

2. **Double-click `setup.bat`** — that's it!

   This will automatically:
   - Install all Python dependencies
   - Install frontend npm packages
   - Create config files
   - Start the backend + frontend servers
   - Open the dashboard in your browser

3. **For future launches**, just double-click `run.bat` (skips dependency install).

---

## What You Get

| Feature | Description |
|---------|-------------|
| Live Data | Real-time stock prices updated every 2 seconds |
| Technical Indicators | SMA, EMA, RSI, VWAP, Supertrend, Camarilla pivots |
| Alerts | Price crosses, RSI levels, volume spikes with notifications |
| Watchlist | Add/remove stocks, persists across sessions |
| Dark/Light Mode | Toggle between themes |
| Charts | Candlestick charts on double-click |

---

## Manual Setup (If You Prefer)

### Option A: Standalone HTML Dashboard (Simplest)
No Node.js needed — just Python:
```bash
cd web_dashboard/backend
pip install -r requirements.txt
python main.py
```
Open **http://localhost:8000** in your browser.

### Option B: React Frontend + Backend (Full Features)
```bash
# Terminal 1 — Backend
cd web_dashboard/backend
pip install -r requirements.txt
python main.py

# Terminal 2 — Frontend
cd web_dashboard/frontend
npm install
npm start
```
Open **http://localhost:3000** in your browser.

---

## Project Structure

```
GT Trading Companion/
├── setup.bat                    # One-click setup & launch (first time)
├── run.bat                      # Quick start (after setup)
├── requirements.txt             # Python dependencies
├── yahoo_provider.py            # Yahoo Finance data provider
├── yahoo_adapter.py             # Angel One compatible adapter
├── yahoo_websocket.py           # Polling-based live stream
│
├── web_dashboard/
│   ├── index.html               # Standalone dashboard (no build needed)
│   ├── backend/
│   │   ├── main.py              # FastAPI server (port 8000)
│   │   ├── requirements.txt     # Backend Python deps
│   │   └── watchlist.json       # Saved watchlist
│   └── frontend/
│       ├── package.json         # React dependencies
│       └── src/
│           ├── App.js           # Main React component
│           ├── index.js         # Entry point
│           └── index.css        # Styles
│
├── config/
│   ├── settings.py              # App configuration
│   └── credentials.example.py   # Angel One credentials template (optional)
│
├── indicators/                  # Technical indicator calculations
├── data/                        # Data models & processing
├── utils/                       # Helpers, logging, symbol loader
├── angel_api/                   # Legacy Angel One API (not used)
├── excel/                       # Excel integration (optional)
└── tests/                       # Unit tests
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard (standalone HTML) |
| WS | `/ws` | WebSocket for real-time data |
| GET | `/api/data` | All token data |
| GET | `/api/data/{token}` | Single token data |
| GET | `/api/candles/{token}` | Historical candles |
| GET | `/api/alerts` | Active alerts |
| POST | `/api/tokens/add` | Add token to watchlist |
| DELETE | `/api/tokens/{token}` | Remove token |
| GET | `/api/instruments` | Available instruments |
| GET | `/api/symbols/search?q=` | Search symbols |
| GET | `/api/health` | Health check |

---

## Troubleshooting

**Python not found:**
Install Python from python.org and check "Add to PATH". Restart your terminal.

**Node.js not found:**
Install Node.js from nodejs.org. Restart your terminal.

**Port 8000 or 3000 already in use:**
The setup scripts automatically kill existing processes. If issues persist, manually stop other services on those ports.

**No data showing:**
Add stocks to your watchlist using the "Add Token" button in the dashboard. The system starts with an empty watchlist.

---

## License

For personal use only. Not financial advice.
