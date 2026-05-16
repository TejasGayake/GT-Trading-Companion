# Excel-Style Web Dashboard

A complete replacement for your Excel trading system with an Excel-like interface.

---

## 🚀 To Restart the Dashboard

Run these commands:

```powershell
# Terminal 1
cd G:\mnt\full\Project2\web_dashboard\backend
python main.py
```

Then open **http://localhost:8000** in your browser.

---

## 🚀 ONE CLICK START (For Non-Tech Users)

**Simply double-click this file:**
```
setup_and_run.bat
```

This will:
1. ✅ Check if Python and Node.js are installed
2. ✅ Install required dependencies (first time only)
3. ✅ Start the backend server
4. ✅ Start the frontend
5. ✅ Open dashboard in your browser automatically!

**That's it!** No commands to type, no terminal to worry about.

---

## Quick Start (Manual Way)

### Simplest Option - No Build Required!

```powershell
# 1. Start the backend
cd G:\mnt\full\Project2\web_dashboard\backend
python main.py

# 2. Open your browser to:
http://localhost:8000
```

That's it! The backend now serves the dashboard directly at port 8000.

### Option 2: React Frontend (Full Features)

```bash
# 1. Start backend
cd web_dashboard/backend
pip install -r requirements.txt
python main.py

# 2. Build and run frontend
cd web_dashboard/frontend
npm install
npm start
```

Then open http://localhost:3000

## Features

### Live Data Sheet (29 columns)
- ✅ TOKEN, SYMBOL, LTP, OPEN, HIGH, LOW, PREV CLOSE
- ✅ CHANGE, %CHANGE with green/red color coding
- ✅ VOLUME, AVG VOL
- ✅ VWAP, SMA21, SMA40, SMA200, EMA10
- ✅ RSI14 with orange (>70) / blue (<30) highlighting
- ✅ SUPERTREND, Supertrend Direction
- ✅ Camarilla H4, H3, L3, L4
- ✅ SUPPORT, RESISTANCE
- ✅ VOLATILITY, PD HIGH, PD LOW
- ✅ ALERT column with visual highlighting

### Color Coding (Exactly like Excel)
- **LTP / Change**: Green for positive, Red for negative
- **RSI14**: Orange background for >70, Blue background for <30
- **Alert rows**: Highlighted background with pulse animation

### Tabs
- 📊 Live Data - Main grid with all indicators
- 📋 Instruments - Available tokens
- 🔔 Alerts - Alert history with notifications
- 📈 Historical - Data analysis

### Toolbar
- Add Token - Add new token to watchlist
- Export - Export to CSV
- Clear Alerts - Reset alert history
- Search - Filter by symbol/token
- Theme Toggle - Dark/Light mode

### Real-time Features
- WebSocket updates every 2 seconds
- Toast notifications for new alerts
- Sound alerts (configurable)
- Auto-reconnect on disconnect

### Grid Features (AG Grid)
- Column sorting (click headers)
- Column filtering (click filter icon)
- Column resizing (drag borders)
- Quick search (top right)
- Double-click row → Opens candlestick chart
- Export to CSV

## File Structure

```
web_dashboard/
├── index.html           # Standalone dashboard (open in browser)
├── backend/
│   ├── main.py         # FastAPI backend with WebSocket
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.js      # React component
    │   ├── index.js
    │   └── index.css
    └── package.json
```

## Running

```powershell
# Terminal 1 - Start backend
cd G:\mnt\full\Project2\web_dashboard\backend
python main.py

# Open browser to:
http://localhost:8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | /ws | WebSocket for real-time data |
| GET | /api/data | All token data |
| GET | /api/data/{token} | Single token |
| GET | /api/candles/{token} | Historical candles |
| GET | /api/alerts | Active alerts |
| GET | /api/alerts/history | Alert history |
| POST | /api/tokens/add | Add token |
| DELETE | /api/tokens/{token} | Remove token |
| POST | /api/alerts/clear | Clear alerts |

## Column Order (matching your Excel)

1. TOKEN
2. SYMBOL
3. LTP
4. OPEN
5. HIGH
6. LOW
7. PREV CLOSE
8. CHANGE
9. %CHANGE
10. VOLUME
11. AVG VOL
12. VWAP
13. SMA21
14. SMA40
15. SMA200
16. EMA10
17. RSI14
18. SUPERTREND
19. S. DIR
20. C.H4
21. C.H3
22. C.L3
23. C.L4
24. SUPPORT
25. RESISTANCE
26. VOLATILITY
27. PD HIGH
28. PD LOW
29. ALERT