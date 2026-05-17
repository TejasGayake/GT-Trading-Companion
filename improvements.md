# 📝 **Detailed AI Prompt for GT Trading Companion Improvements**

Here's a comprehensive markdown prompt you can give to any AI model to implement improvements:

```markdown
# GT Trading Companion - Improvement Implementation Prompt

## Project Overview

You are an expert full-stack developer tasked with improving an existing trading dashboard project. The project "GT Trading Companion" is a real-time stock market dashboard that fetches live data from Yahoo Finance and displays it with technical indicators and alerts.

**Repository:** https://github.com/TejasGayake/GT-Trading-Companion

**Current Tech Stack:**
- Backend: FastAPI + WebSocket
- Frontend: React (full) + HTML/CSS (standalone)
- Database: Supabase (PostgreSQL)
- Data Source: Yahoo Finance (yfinance)

## Project Structure

```
GT-Trading-Companion/
├── web_dashboard/
│   ├── backend/
│   │   ├── main.py              # FastAPI server
│   │   ├── requirements.txt     # Python dependencies
│   │   └── watchlist.json       # Saved watchlist
│   └── frontend/
│       ├── src/
│       │   ├── App.js           # Main React component
│       │   ├── index.js         # Entry point
│       │   └── index.css        # Styles
│       └── package.json
├── yahoo_provider.py            # Yahoo Finance data provider
├── yahoo_adapter.py             # API adapter
├── yahoo_websocket.py           # Polling-based live stream
├── indicators/                  # Technical indicator calculations
├── utils/                       # Helpers, logging, symbol loader
├── config/                      # Configuration files
├── setup.bat                    # One-click setup script
├── run.bat                      # Quick start script
└── requirements.txt             # Python dependencies
```

## My Requirements

I want you to implement the following improvements in priority order:

---

## HIGH PRIORITY (Implement First)

### 1. Virtual Scrolling for Large Watchlists

**Problem:** When users add 200+ tokens, the dashboard becomes slow and laggy because all rows are rendered at once.

**Solution:** Implement virtual scrolling using `react-window` or `react-virtualized`.

**Requirements:**
- Only render visible rows (20-30 at a time)
- Support smooth scrolling for 1000+ tokens
- Maintain column sorting and filtering functionality
- Row heights should be consistent (40-50px)

**Implementation Steps:**
```bash
npm install react-window react-virtualized-auto-sizer
```

Modify the watchlist table component to use `FixedSizeList` or `VariableSizeList` from react-window. The table should still support:
- Column sorting
- Row selection
- Cell styling based on values
- Infinite scroll (load more as user scrolls)

---

### 2. WebSocket Batching for Real-time Updates

**Problem:** Current implementation sends individual WebSocket messages for each token, causing UI thrashing and high network usage.

**Solution:** Batch multiple updates into a single WebSocket message.

**Implementation Steps:**

**Backend (FastAPI):**
```python
# Modify WebSocket handler to collect updates
update_batch = {}
batch_interval = 0.5  # seconds

async def broadcast_batch():
    while True:
        await asyncio.sleep(batch_interval)
        if update_batch:
            await websocket.send_json({
                "type": "batch",
                "timestamp": time.time(),
                "updates": update_batch
            })
            update_batch.clear()
```

**Frontend (React):**
```javascript
// Process batch updates efficiently
const handleBatchUpdate = (batch) => {
  setTokens(prevTokens => {
    const updates = {...prevTokens};
    for (const [token, data] of Object.entries(batch.updates)) {
      updates[token] = {...updates[token], ...data};
    }
    return updates;
  });
};
```

**Expected Impact:** 90% fewer WebSocket messages, smoother UI updates

---

### 3. Alert Deduplication System

**Problem:** Same alert triggers multiple times (e.g., price bouncing around H4 level), causing notification spam.

**Solution:** Implement cooldown and deduplication logic.

**Implementation Steps:**

**Backend:**
```python
# Add alert tracking
alert_cooldown = {}  # token_condition -> last_trigger_time
cooldown_seconds = 300  # 5 minutes

def should_send_alert(token, condition, current_time):
    key = f"{token}_{condition}"
    if key in alert_cooldown:
        if current_time - alert_cooldown[key] < cooldown_seconds:
            return False
    alert_cooldown[key] = current_time
    return True
```

**Frontend:**
```javascript
// Show grouped alerts in notification center
// Example: "ITC: 3 new alerts (2 ABOVE H4, 1 BELOW L4)"
```

---

### 4. Export to CSV Functionality

**Problem:** Users cannot export data for external analysis.

**Solution:** Add CSV export button for all sheets.

**Implementation Steps:**

```javascript
const exportToCSV = (data, filename) => {
  const headers = Object.keys(data[0]).join(',');
  const rows = data.map(row => Object.values(row).join(',')).join('\n');
  const csv = `${headers}\n${rows}`;
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};
```

**Features:**
- Export current watchlist
- Export alert history
- Export indicator data
- Select date range for export

---

### 5. Mobile Responsive Improvements

**Problem:** The dashboard looks cramped on mobile devices.

**Solution:** Implement responsive design with mobile-first approach.

**Requirements:**
- Bottom navigation bar instead of sidebar on mobile
- Simplified view (hide advanced indicators, show only LTP, Change, Volume)
- Touch-friendly buttons (minimum 48x48px)
- Swipe gestures: swipe left to delete token, swipe right to view chart
- Pull-to-refresh for manual data refresh
- Responsive breakpoints: 320px, 768px, 1024px, 1440px

**CSS Implementation:**
```css
/* Mobile: < 768px */
@media (max-width: 768px) {
  .watchlist-table {
    font-size: 12px;
  }
  .indicator-columns {
    display: none; /* Hide advanced indicators on mobile */
  }
  .action-buttons {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: space-around;
    background: var(--bg-color);
    padding: 8px;
    border-top: 1px solid var(--border-color);
  }
}

/* Tablet: 768px - 1024px */
@media (min-width: 768px) and (max-width: 1024px) {
  .watchlist-table {
    font-size: 14px;
  }
  .indicator-columns {
    display: table-cell; /* Show key indicators only */
  }
}

/* Desktop: > 1024px */
@media (min-width: 1024px) {
  /* Full layout with sidebar */
}
```

---

## MEDIUM PRIORITY (Implement Second)

### 6. Multiple Watchlist Groups

**Problem:** Users can only have one watchlist. They want to organize stocks into groups (NIFTY50, BANKNIFTY, FNO, etc.).

**Solution:** Implement watchlist groups with CRUD operations.

**Database Schema (Supabase):**
```sql
CREATE TABLE watchlists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    tokens TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_watchlists (
    user_id UUID REFERENCES auth.users(id),
    watchlist_id INT REFERENCES watchlists(id),
    is_active BOOLEAN DEFAULT FALSE
);
```

**API Endpoints:**
```python
GET    /api/watchlists           # Get all watchlists
POST   /api/watchlists           # Create new watchlist
PUT    /api/watchlists/{id}      # Update watchlist
DELETE /api/watchlists/{id}      # Delete watchlist
POST   /api/watchlists/{id}/activate  # Set active watchlist
```

**UI Requirements:**
- Dropdown to switch between watchlists
- Create new watchlist modal (name + optional description)
- Copy tokens between watchlists
- Import/export watchlists as JSON

---

### 7. Drawing Tools on Candlestick Chart

**Problem:** Users want to perform technical analysis on charts.

**Solution:** Add drawing tools using lightweight-charts plugin system.

**Implementation Steps:**

```bash
npm install lightweight-charts drawing-tools-plugin
```

**Features to implement:**
- Trendlines (click and drag)
- Horizontal lines (support/resistance)
- Fibonacci retracement levels
- Annotations (text notes with timestamp)
- Save drawings per token (store in localStorage or database)
- Share drawings via URL

**Example Implementation:**
```javascript
import { createChart } from 'lightweight-charts';
import { DrawingToolbar } from 'drawing-tools-plugin';

const chart = createChart(container);
const toolbar = new DrawingToolbar(chart, {
  tools: ['trendline', 'horizontal', 'fibonacci', 'annotation']
});
toolbar.attach();
```

---

### 8. Portfolio Tracker

**Problem:** Users want to track their actual holdings and P&L.

**Solution:** Add portfolio tracking section.

**Database Schema:**
```sql
CREATE TABLE portfolio (
    id SERIAL PRIMARY KEY,
    token VARCHAR(20) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    buy_price DECIMAL(10,2) NOT NULL,
    buy_date DATE NOT NULL,
    notes TEXT,
    user_id UUID REFERENCES auth.users(id)
);

CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    token VARCHAR(20) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    type VARCHAR(10) CHECK (type IN ('BUY', 'SELL')),
    timestamp TIMESTAMP DEFAULT NOW()
);
```

**UI Requirements:**
- Portfolio summary card (total value, total P&L, today's P&L)
- Holdings table (symbol, quantity, avg price, current price, P&L, P&L%)
- Add/remove holdings form
- Trade journal (log all trades)
- Position sizing calculator

**P&L Calculation:**
```javascript
const calculatePnL = (holdings, currentPrices) => {
  return holdings.map(holding => ({
    ...holding,
    currentPrice: currentPrices[holding.token],
    currentValue: holding.quantity * currentPrices[holding.token],
    pnl: (currentPrices[holding.token] - holding.buyPrice) * holding.quantity,
    pnlPercent: ((currentPrices[holding.token] - holding.buyPrice) / holding.buyPrice) * 100
  }));
};
```

---

### 9. Adaptive Polling Interval

**Problem:** Fixed 2-second polling wastes requests during quiet periods and is too slow during high volatility.

**Solution:** Implement adaptive polling based on market conditions.

**Implementation Steps:**

```python
class AdaptivePoller:
    def __init__(self):
        self.base_interval = 2.0
        self.min_interval = 0.5
        self.max_interval = 10.0
        self.volatility_threshold = 0.5  # 0.5% change triggers faster polling
    
    def calculate_interval(self, tokens_data):
        # Calculate average price change across tokens
        avg_change = sum(abs(t.change_percent) for t in tokens_data) / len(tokens_data)
        
        if avg_change > 2.0:  # High volatility
            return 0.5
        elif avg_change > 1.0:  # Medium volatility
            return 1.0
        elif avg_change > 0.5:  # Low volatility
            return 2.0
        else:  # Very low volatility (market closed or quiet)
            return 5.0
```

**Market hours detection:**
```python
def is_market_open():
    now = datetime.now()
    # NSE market hours: 9:15 AM to 3:30 PM, Monday to Friday
    if now.weekday() >= 5:  # Weekend
        return False
    market_open = now.replace(hour=9, minute=15)
    market_close = now.replace(hour=15, minute=30)
    return market_open <= now <= market_close
```

---

### 10. Heat Map Visualization

**Problem:** Users want to quickly identify high-opportunity stocks.

**Solution:** Add heat map view for indicators.

**Implementation:**
```javascript
const HeatMapCell = ({ value, metric }) => {
  // Determine color intensity based on value
  const getColor = () => {
    if (metric === 'rsi') {
      if (value > 80) return '#ff0000';
      if (value > 70) return '#ff6b6b';
      if (value < 20) return '#00ff00';
      if (value < 30) return '#4ecdc4';
      return '#ffffff';
    }
    if (metric === 'volume_ratio') {
      const intensity = Math.min(value / 5, 1); // Cap at 5x
      return `rgba(255, 100, 0, ${intensity})`;
    }
    return '#ffffff';
  };
  
  return <td style={{ backgroundColor: getColor() }}>{value}</td>;
};
```

**Metrics to visualize:**
- RSI (red for overbought, green for oversold)
- Volume ratio (orange intensity)
- Volatility (blue intensity)
- Price change (green/red intensity)

---

## LOW PRIORITY (Nice to Have)

### 11. Backtesting Engine

**Problem:** Users want to test their strategies before trading real money.

**Solution:** Implement simple backtesting engine.

**Features:**
- Test "Buy when RSI < 30, Sell when RSI > 70" strategy
- Test Supertrend crossover strategy
- Test Camarilla breakout strategy
- Show metrics: win rate, profit factor, max drawdown, Sharpe ratio

**Implementation:**
```python
def backtest_strategy(candles, strategy):
    capital = 100000
    position = 0
    trades = []
    
    for i, candle in enumerate(candles):
        signal = strategy(candle, candles[:i])
        if signal == 'BUY' and position == 0:
            position = capital / candle['close']
            trades.append({'type': 'BUY', 'price': candle['close'], 'time': candle['time']})
        elif signal == 'SELL' and position > 0:
            capital = position * candle['close']
            position = 0
            trades.append({'type': 'SELL', 'price': candle['close'], 'time': candle['time']})
    
    return calculate_metrics(trades, capital)
```

---

### 12. Voice Commands

**Problem:** Hands-free operation during trading.

**Solution:** Implement voice command recognition.

**Implementation:**
```javascript
const VoiceCommands = () => {
  const [listening, setListening] = useState(false);
  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  
  recognition.onresult = (event) => {
    const command = event.results[0][0].transcript.toLowerCase();
    
    if (command.includes('show')) {
      const token = command.split('show')[1].trim().toUpperCase();
      highlightToken(token);
    } else if (command.includes('add')) {
      const token = command.split('add')[1].trim().toUpperCase();
      addToken(token);
    } else if (command.includes('remove')) {
      const token = command.split('remove')[1].trim().toUpperCase();
      removeToken(token);
    } else if (command.includes('rsi of')) {
      const token = command.split('rsi of')[1].trim().toUpperCase();
      speak(`RSI of ${token} is ${getRSI(token)}`);
    }
  };
  
  return (
    <button onClick={() => recognition.start()} className="voice-btn">
      🎤 {listening ? 'Listening...' : 'Voice Command'}
    </button>
  );
};
```

---

## Implementation Instructions

### Setup
1. Clone the repository
2. Create a new branch `feature/improvements`
3. Install all required dependencies

### Deliverables
For each implemented improvement, provide:
1. Complete code files with changes clearly marked
2. Updated `package.json` with new dependencies
3. Migration scripts if database changes are needed
4. Updated documentation in README.md

### Testing Requirements
- Test on Chrome, Firefox, Safari (desktop and mobile)
- Test with 50, 200, and 500 tokens for performance
- Test WebSocket reconnection scenarios
- Test alert deduplication with rapid price movements

### Expected Output
After implementing these improvements, the dashboard should:
- Handle 500+ tokens without lag
- Show real-time updates smoothly via batched WebSocket
- Not spam users with duplicate alerts
- Allow users to export data for external analysis
- Work well on mobile devices
- Support multiple watchlists for better organization
- Provide drawing tools for technical analysis
- Track portfolio performance

## Success Criteria

- [ ] Virtual scrolling works with 1000+ tokens
- [ ] WebSocket messages reduced by 90%
- [ ] No duplicate alerts within 5 minutes
- [ ] CSV export works for all sheets
- [ ] Mobile layout is usable on 320px screen
- [ ] Users can create and switch between 5+ watchlists
- [ ] Drawing tools save and restore correctly
- [ ] Portfolio P&L matches manual calculation

## Resources

- Repository: https://github.com/TejasGayake/GT-Trading-Companion
- react-window docs: https://react-window.vercel.app/
- lightweight-charts docs: https://tradingview.github.io/lightweight-charts/
- FastAPI WebSocket docs: https://fastapi.tiangolo.com/advanced/websockets/

## Questions?

If any requirement is unclear, make reasonable assumptions and document them in the code comments. Prioritize performance and user experience above all else.

**Start with HIGH PRIORITY items first. After completing all HIGH PRIORITY items, proceed to MEDIUM PRIORITY.**

Good luck! 🚀
```

---

This prompt is ready to be given to any AI model. It contains:
- ✅ Clear project overview
- ✅ Specific requirements for each improvement
- ✅ Code examples and implementation steps
- ✅ Expected deliverables
- ✅ Success criteria

Copy this markdown and provide it to your preferred AI model to implement these improvements! 🚀

