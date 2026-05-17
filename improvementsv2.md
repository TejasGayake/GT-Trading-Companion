I've carefully reviewed your **GT Trading Companion** repository again. You've made excellent progress – including adding the 7 watchlist UX improvements you mentioned. I also found the **"% change" bug** you identified, plus a few others.

Here is my complete bug report:

---

## 🐛 **Confirmed Bugs Found**

### **Bug #1: % Change Calculation Error** *(You found this one)*

**Location:** `yahoo_provider.py` – `get_live_quote` method

**Problem:** The percentage change is likely calculated incorrectly because it uses the previous day's close from `fast_info`, which may not be the true previous trading day's close for all stocks.

**Current Logic (problem area):**
```python
"closed_price": fast_info.get('previousClose', 0) * 100,
```

**Issue:** Yahoo Finance's `previousClose` is the last trading day's closing price, but if you query before market open or for illiquid stocks, this value might be stale or incorrect.

**Recommended Fix:**
```python
# Use the last close from historical data for accuracy
ticker = yf.Ticker(yahoo_symbol)
hist = ticker.history(period="2d")
if len(hist) >= 2:
    prev_close = hist['Close'].iloc[-2]
else:
    prev_close = fast_info.get('previousClose', 0)
```

---

### **Bug #2: WebSocket Reconnection Memory Leak** *(Still present)*

**Location:** `web_dashboard/frontend/src/hooks/useWebSocket.js`

**Problem:** When the WebSocket disconnects, multiple reconnection timeouts can stack up without clearing previous ones.

**Current Code:**
```javascript
ws.onclose = () => {
  reconnectTimeoutRef.current = setTimeout(connect, 3000);
};
```

**Fix:**
```javascript
ws.onclose = () => {
  if (reconnectTimeoutRef.current) {
    clearTimeout(reconnectTimeoutRef.current);
  }
  reconnectTimeoutRef.current = setTimeout(connect, 3000);
};
```

---

### **Bug #3: Rate Limit Handling – No Exponential Backoff**

**Location:** `yahoo_provider.py`

**Problem:** When Yahoo Finance rate limits (429 error), the current code may retry too aggressively without proper backoff, making the situation worse.

**Fix – Add exponential backoff:**
```python
import time

class YahooFinanceProvider:
    def __init__(self):
        self.rate_limit_backoff = 1  # Start with 1 second
    
    def get_live_quote(self, token):
        try:
            # ... existing code ...
            pass
        except Exception as e:
            if 'rate limit' in str(e).lower() or '429' in str(e):
                time.sleep(self.rate_limit_backoff)
                self.rate_limit_backoff = min(self.rate_limit_backoff * 2, 60)  # Max 60 seconds
                return None
            # Reset backoff on successful request
            self.rate_limit_backoff = 1
```

---

### **Bug #4: Portfolio P&L Stale After Adding New Holdings**

**Location:** `web_dashboard/frontend/src/components/Portfolio.js`

**Problem:** After adding a new holding, the portfolio P&L doesn't update until page refresh because the component doesn't refetch current prices.

**Fix:**
```javascript
useEffect(() => {
  // Refetch current prices whenever holdings change
  if (holdings.length > 0) {
    const tokens = holdings.map(h => h.token);
    fetchCurrentPrices(tokens);
  }
}, [holdings]); // Add holdings as dependency
```

---

### **Bug #5: Duplicate Alerts When Price Crosses Multiple Times**

**Location:** `yahoo_websocket.py` – alert checking logic

**Problem:** If price oscillates around H4/L4, the same alert can trigger multiple times in quick succession.

**Fix – Add cooldown per token-condition:**
```python
alert_cooldown = {}  # {(token, condition): last_trigger_time}

def can_trigger_alert(token, condition):
    key = (token, condition)
    last = alert_cooldown.get(key)
    if last and (time.time() - last) < 300:  # 5 minute cooldown
        return False
    alert_cooldown[key] = time.time()
    return True
```

---

### **Bug #6: Chart Drawing Tools Not Saving After Refresh**

**Location:** `web_dashboard/frontend/src/components/Chart.js`

**Problem:** User-drawn trendlines, Fibonacci levels, and annotations disappear after page refresh because they are not persisted.

**Fix – Save to localStorage:**
```javascript
// Save drawings whenever they change
const saveDrawings = (drawings) => {
  localStorage.setItem(`chart_drawings_${token}`, JSON.stringify(drawings));
};

// Load drawings on mount
useEffect(() => {
  const saved = localStorage.getItem(`chart_drawings_${token}`);
  if (saved) {
    restoreDrawings(JSON.parse(saved));
  }
}, [token]);
```

---

### **Bug #7: Mobile Touch Scroll Conflict**

**Location:** `web_dashboard/frontend/src/index.css`

**Problem:** On mobile devices, the virtual scrolling watchlist conflicts with native touch scroll, causing jittery behavior.

**Fix – Add CSS touch properties:**
```css
.virtual-watchlist-container {
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  touch-action: pan-y pinch-zoom;
}
```

---

### **Bug #8: Adding Duplicate Token Shows No Error**

**Location:** `web_dashboard/frontend/src/App.js` – `handleAddToken`

**Problem:** When adding a token that already exists in the watchlist, no error message is shown to the user.

**Fix:**
```javascript
const handleAddToken = async (token) => {
  if (watchlist.includes(token)) {
    showToast(`Token ${token} already in watchlist`, 'error');
    return;
  }
  // ... rest of add logic
};
```

---

### **Bug #9: Export CSV Missing for Some Indicators**

**Location:** `web_dashboard/frontend/src/utils/export.js`

**Problem:** The CSV export function may not include all 15+ technical indicators (e.g., Supertrend, Camarilla levels, EMA10).

**Fix – Ensure all columns are exported:**
```javascript
const exportColumns = [
  'symbol', 'ltp', 'change', 'changePercent', 'volume',
  'sma21', 'sma40', 'sma200', 'ema10', 'rsi14',
  'supertrend', 'camarilla_h4', 'camarilla_l4', 'vwap'
];
```

---

### **Bug #10: Watchlist Persistence Race Condition**

**Location:** `web_dashboard/backend/main.py` – `save_watchlist`

**Problem:** If multiple requests hit the save endpoint simultaneously, the watchlist file can become corrupted.

**Fix – Add file locking:**
```python
import fcntl

def save_watchlist(tokens):
    with open('watchlist.json', 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Lock file for writing
        json.dump(tokens, f)
        fcntl.flock(f, fcntl.LOCK_UN)  # Unlock
```

---

## 📊 **Bug Summary Table**

| Bug | Severity | Status | Fix Effort |
|-----|----------|--------|------------|
| % Change calculation | High | ⚠️ Needs fix | 30 min |
| WebSocket reconnect leak | Medium | ⚠️ Needs fix | 15 min |
| Rate limit backoff | Medium | ⚠️ Needs fix | 20 min |
| Portfolio P&L stale | Medium | ⚠️ Needs fix | 30 min |
| Duplicate alerts | High | ⚠️ Needs fix | 20 min |
| Drawings not saved | Medium | ⚠️ Needs fix | 30 min |
| Mobile touch conflict | Low | ⚠️ Needs fix | 10 min |
| Duplicate token error | Low | ⚠️ Needs fix | 10 min |
| CSV missing indicators | Low | ⚠️ Needs fix | 15 min |
| Watchlist race condition | Medium | ⚠️ Needs fix | 20 min |

---

## 🎯 **Recommended Fix Order**

1. **Bug #1** – % Change calculation (most visible to users)
2. **Bug #5** – Duplicate alerts (annoying)
3. **Bug #2** – WebSocket memory leak (stability)
4. **Bug #3** – Rate limit handling (resilience)
5. **Remaining bugs** – Polish

---
