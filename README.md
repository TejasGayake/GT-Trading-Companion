# Live Feed Trading System v12

High-performance stock market live feed with real-time data streaming, technical indicators, Excel integration, and web dashboards.

## Quick Start

### Option 1: Excel Dashboard (Original)
```bash
python run.py
```

### Option 2: Streamlit Web Dashboard (New!)
```bash
streamlit run complete_dashboard.py
```

### Option 3: Both Systems
```bash
run_both.bat
```

### Option 4: Backend API + WebSocket
```bash
# Terminal 1: Start API backend
cd backend
python main.py

# Terminal 2: Start Streamlit
streamlit run complete_dashboard.py
```

Then open:
- Web Dashboard: http://localhost:8501
- API Docs: http://localhost:8000/docs

## Features Comparison

| Feature | Excel Dashboard | Streamlit Dashboard | FastAPI Backend |
|---------|-----------------|---------------------|-----------------|
| Real-time updates | 0.5s batch | 10s auto-refresh | WebSocket <100ms |
| Mobile access | ❌ | ✅ | ✅ |
| Charts | Basic | Interactive | Via frontend |
| Alerts | Excel cells | Popups + sound | WebSocket + push |
| Multi-user | ❌ | Limited | ✅ |
| Historical data | ❌ | ❌ | ✅ (database) |

## Project Structure

```
├── run.py                    # Main Excel app entry point
├── run_both.bat             # Run both Excel + web dashboard
├── complete_dashboard.py    # Full-featured Streamlit dashboard
├── alerts_dashboard.py       # Lightweight alerts dashboard
├── alerts_queue.py          # Shared alert queue
│
├── yahoo_provider.py        # Yahoo Finance data provider
├── yahoo_websocket.py      # Polling-based live stream
├── yahoo_adapter.py        # Angel One API compatible adapter
│
├── backend/
│   ├── main.py              # FastAPI backend with WebSocket
│   └── requirements.txt    # Backend dependencies
│
├── angel_api/               # (Legacy - no longer needed)
├── excel/                   # Excel management
├── indicators/              # Technical indicators & alerts
├── data/                   # Data models & processing
├── backup/                 # Token backup system
├── utils/                  # Utilities
├── config/                 # Configuration
│
├── symbol_mapping.csv       # Token to symbol mappings
├── requirements.txt         # Python dependencies
└── tests/                   # Test files
```

## Technical Indicators Supported

| Indicator | Period | Description |
|-----------|--------|-------------|
| SMA21 | 21 | Simple Moving Average |
| SMA40 | 40 | Simple Moving Average |
| SMA200 | 200 | Simple Moving Average |
| EMA10 | 10 | Exponential Moving Average |
| RSI14 | 14 | Relative Strength Index |
| VWAP | 26 | Volume Weighted Average Price |
| Supertrend | ATR 13 | Trend following |
| Camarilla H4/L4 | 20-day | Pivot levels |
| Support | 20-day | Support price |
| Resistance | 20-day | Resistance price |
| Volume Avg | 20 | Average volume |
| Volume Ratio | - | Current/Avg volume |

## Alert Conditions

| Condition | Icon | Description |
|-----------|------|-------------|
| ABOVE H4 | 📈 | Price > Camarilla H4 |
| BELOW L4 | 📉 | Price < Camarilla L4 |
| OVERBOUGHT | 🔴 | RSI > 70 |
| OVERSOLD | 🟢 | RSI < 30 |
| VOLUME SPIKE | 📊 | Volume > 2.5x avg |

## Running Different Components

### 1. Excel Dashboard Only
```bash
python run.py
```
- Opens Live_Feed_Data.xlsx
- Updates every 0.5 seconds
- Alerts in Excel sheet

### 2. Streamlit Dashboard Only
```bash
streamlit run complete_dashboard.py
```
- Opens http://localhost:8501
- Auto-refreshes every 10 seconds
- Charts, alerts, watchlists

### 3. Alerts Dashboard Only (Lightweight)
```bash
streamlit run alerts_dashboard.py
```
- Focuses on alerts only
- Good for separate monitor

### 4. Backend API + Dashboard
```bash
# Terminal 1
cd backend
pip install -r requirements.txt
python main.py

# Terminal 2
streamlit run complete_dashboard.py
```
- Real-time WebSocket updates
- REST API at http://localhost:8000
- Swagger docs at http://localhost:8000/docs

## API Endpoints (Backend)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/tokens | Get tokens in watchlist |
| POST | /api/tokens | Add token |
| DELETE | /api/tokens/{token} | Remove token |
| GET | /api/indicators/{token} | Get indicators |
| GET | /api/candles/{token} | Get historical candles |
| GET | /api/alerts | Get active alerts |
| GET | /api/alerts/history | Get alert history |
| GET | /api/watchlists | Get all watchlists |
| GET | /ws/live | WebSocket for live data |

## Configuration

### Settings
Edit `config/settings.py`:
- Excel file path
- Update intervals
- Alert thresholds
- Log levels

### Symbol Mapping
Edit `symbol_mapping.csv` - format: `TOKEN,SYMBOL`

### Switching Data Source
In `sw_excelv12.py`:
```python
USE_YAHOO_FINANCE = True   # Default - no API key needed
USE_YAHOO_FINANCE = False  # Use Angel One (requires credentials)
```

## Troubleshooting

### Excel Connection Error
- Ensure Excel is installed (Windows required)
- Run as Administrator

### Yahoo Finance Data Not Loading
- Check internet connection
- Some tokens may not be available

### Streamlit Port Already in Use
```bash
# Kill existing
taskkill /F /IM streamlit.exe
# Or use different port
streamlit run complete_dashboard.py --server.port 8502
```

### WebSocket Connection Issues
- Ensure backend is running: `python backend/main.py`
- Check firewall settings

## Dependencies

```
xlwings>=0.27.0     # Excel integration
pandas>=1.3.0       # Data processing
numpy>=1.21.0       # Calculations
yfinance>=0.2.28    # Yahoo Finance data
streamlit>=1.28.0   # Web dashboard
fastapi>=0.100.0    # API backend
uvicorn>=0.23.0     # ASGI server
websockets>=11.0    # WebSocket support
```

## Performance Notes

- Yahoo Finance: ~2000 requests/hour limit
- Polling interval: 2 seconds
- Indicator cache: 5 minutes
- Excel updates: every 0.5 seconds
- WebSocket latency: <100ms (with backend)

## For Developers

### Backend API Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend Development
```bash
# Start backend first
cd backend
python main.py

# Then start Streamlit in another terminal
streamlit run complete_dashboard.py
```

### Adding New Indicators
Edit `indicators/calculator.py` to add new technical indicators.

## License

For personal use only. Not financial advice.