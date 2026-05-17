Here's a comprehensive prompt you can give to an AI model to implement all the watchlist usability improvements:

```markdown
# GT Trading Companion - Watchlist User Adoption Improvements

## Project Context

You are an expert frontend/React developer tasked with improving the watchlist feature of the **GT Trading Companion** to make it more intuitive and user-friendly for first-time users.

**Repository:** https://github.com/TejasGayake/GT-Trading-Companion

**Current Tech Stack:**
- Frontend: React 18, Tailwind CSS
- Backend: FastAPI, Python 3.9+
- State Management: React Hooks (useState, useEffect)
- HTTP Client: Fetch API

## Problem Statement

New users find the watchlist feature confusing because:
1. Empty state shows no guidance on what to do
2. Users don't know token numbers for stocks they want to add
3. No demo data to understand how the feature works
4. No quick ways to add popular stocks
5. Mobile view is cramped (table view only)

## Implementation Requirements

Implement ALL of the following improvements:

---

## HIGH PRIORITY (Implement First)

### 1. Friendly Empty State with Guidance

**Location:** `web_dashboard/frontend/src/components/WatchlistTable.js`

**Replace the empty state with:**

```jsx
{watchlist.length === 0 ? (
  <div className="empty-watchlist">
    <div className="empty-icon">📋</div>
    <h3>Your watchlist is empty</h3>
    <p>Add stocks to start tracking real-time prices, indicators, and alerts</p>
    
    <div className="quick-start">
      <h4>Quick add popular stocks:</h4>
      <div className="quick-buttons">
        <button onClick={() => addToken('5097')}>+ ETERNAL (5097)</button>
        <button onClick={() => addToken('4503')}>+ MPHASIS (4503)</button>
        <button onClick={() => addToken('11351')}>+ PETRONET (11351)</button>
        <button onClick={() => addToken('21690')}>+ DIXON (21690)</button>
        <button onClick={() => addToken('25049')}>+ PREMIERENE (25049)</button>
      </div>
    </div>
    
    <button className="demo-btn" onClick={loadDemoWatchlist}>
      📋 Load Demo Watchlist (7 stocks)
    </button>
    
    <p className="hint">💡 Tip: Click the + Add button or search by company name above</p>
  </div>
) : (
  // Existing watchlist table
)}
```

**CSS for empty state (add to index.css):**
```css
.empty-watchlist {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: var(--bg-secondary);
  border-radius: 12px;
  margin: 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.7;
}

.empty-watchlist h3 {
  font-size: 24px;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.empty-watchlist p {
  color: var(--text-secondary);
  margin-bottom: 30px;
}

.quick-start {
  background: var(--bg-tertiary);
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  width: 100%;
  max-width: 500px;
}

.quick-start h4 {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.quick-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

.quick-buttons button {
  padding: 8px 16px;
  background: var(--button-bg);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.quick-buttons button:hover {
  background: var(--button-hover-bg);
  transform: scale(1.02);
}

.demo-btn {
  padding: 10px 24px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 20px;
}

.demo-btn:hover {
  background: #45a049;
}

.hint {
  font-size: 12px;
  color: var(--text-secondary);
}
```

---

### 2. Demo Watchlist Functionality

**Location:** `web_dashboard/frontend/src/App.js`

**Add the loadDemoWatchlist function:**

```javascript
const DEMO_WATCHLIST = ['5097', '4503', '11351', '21690', '25049', '1594', '7229'];

const loadDemoWatchlist = async () => {
  setLoading(true);
  let successCount = 0;
  let failCount = 0;
  
  for (const token of DEMO_WATCHLIST) {
    try {
      const response = await fetch('/api/tokens/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      const data = await response.json();
      if (data.success) {
        successCount++;
      } else {
        failCount++;
      }
    } catch (error) {
      failCount++;
    }
  }
  
  // Refresh watchlist
  await fetchWatchlist();
  
  // Show feedback
  if (successCount > 0) {
    showToast(`✅ Added ${successCount} stocks to watchlist`, 'success');
  }
  if (failCount > 0) {
    showToast(`⚠️ ${failCount} stocks already in watchlist`, 'info');
  }
  
  setLoading(false);
};
```

---

### 3. Smart Token Search with Autocomplete

**Create new file:** `web_dashboard/frontend/src/components/TokenSearch.js`

```javascript
import React, { useState, useEffect, useRef } from 'react';

const TokenSearch = ({ onSelect, placeholder = "Search by company name or token..." }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef(null);
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (searchTerm.length >= 2) {
        searchStocks();
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);
    
    return () => clearTimeout(delayDebounce);
  }, [searchTerm]);
  
  const searchStocks = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/symbols/search?q=${searchTerm}`);
      const data = await response.json();
      setSuggestions(data.slice(0, 8));
      setShowSuggestions(true);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSelect = (stock) => {
    setSearchTerm('');
    setSuggestions([]);
    setShowSuggestions(false);
    onSelect(stock.token);
  };
  
  return (
    <div className="token-search" ref={searchRef}>
      <div className="search-input-wrapper">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          className="search-input"
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onFocus={() => searchTerm.length >= 2 && setShowSuggestions(true)}
        />
        {isLoading && <span className="loading-icon">⏳</span>}
      </div>
      
      {showSuggestions && suggestions.length > 0 && (
        <div className="suggestions-dropdown">
          {suggestions.map(stock => (
            <div
              key={stock.token}
              className="suggestion-item"
              onClick={() => handleSelect(stock)}
            >
              <div className="suggestion-symbol">{stock.symbol}</div>
              <div className="suggestion-name">{stock.name}</div>
              <div className="suggestion-token">{stock.token}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TokenSearch;
```

**CSS for search (add to index.css):**

```css
.token-search {
  position: relative;
  width: 100%;
  max-width: 400px;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.search-input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #4caf50;
}

.loading-icon {
  position: absolute;
  right: 12px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-top: 4px;
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.suggestion-item:hover {
  background: var(--hover-bg);
}

.suggestion-symbol {
  font-weight: bold;
  color: var(--text-primary);
}

.suggestion-name {
  flex: 1;
  margin-left: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.suggestion-token {
  color: var(--text-secondary);
  font-size: 12px;
  font-family: monospace;
}
```

---

### 4. Quick Add Groups (Popular Stock Lists)

**Location:** `web_dashboard/frontend/src/components/QuickAddGroups.js`

```javascript
import React from 'react';

const POPULAR_LISTS = {
  'NIFTY 50': ['2885', '3045', '1594', '11536', '1660', '1394', '4963', '2475', '3499', '10738'],
  'BANK NIFTY': ['1394', '4963', '17818', '2475', '317', '1901'],
  'High Volume': ['5097', '4503', '11351', '21690', '25049', '1594', '7229'],
};

const QuickAddGroups = ({ onAddGroup, currentWatchlist }) => {
  const [selectedGroup, setSelectedGroup] = useState(null);
  
  const handleAddGroup = async (groupName, tokens) => {
    const newTokens = tokens.filter(t => !currentWatchlist.includes(t));
    if (newTokens.length === 0) {
      alert('All stocks already in watchlist');
      return;
    }
    
    setSelectedGroup(groupName);
    for (const token of newTokens) {
      await onAddGroup(token);
    }
    setSelectedGroup(null);
  };
  
  return (
    <div className="quick-add-groups">
      <span className="groups-label">Quick add:</span>
      {Object.entries(POPULAR_LISTS).map(([name, tokens]) => (
        <button
          key={name}
          className="group-btn"
          onClick={() => handleAddGroup(name, tokens)}
          disabled={selectedGroup === name}
        >
          {selectedGroup === name ? 'Adding...' : `+ ${name}`}
        </button>
      ))}
    </div>
  );
};

export default QuickAddGroups;
```

---

### 5. Mobile Card View

**Create new file:** `web_dashboard/frontend/src/components/WatchlistCards.js`

```javascript
import React from 'react';

const WatchlistCards = ({ watchlist, onRemove, onSelect }) => {
  const formatVolume = (volume) => {
    if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
    if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
    return volume.toLocaleString();
  };
  
  return (
    <div className="watchlist-cards">
      {watchlist.map(stock => (
        <div 
          key={stock.token} 
          className="stock-card"
          onClick={() => onSelect(stock)}
        >
          <div className="card-header">
            <div className="stock-info">
              <span className="symbol">{stock.symbol}</span>
              <span className="token">{stock.token}</span>
            </div>
            <button 
              className="remove-btn"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`Remove ${stock.symbol}?`)) onRemove(stock.token);
              }}
            >
              ✕
            </button>
          </div>
          
          <div className="card-price">
            <span className="ltp">₹{stock.ltp.toFixed(2)}</span>
            <span className={`change ${stock.change >= 0 ? 'positive' : 'negative'}`}>
              {stock.change >= 0 ? '▲' : '▼'} {Math.abs(stock.changePercent).toFixed(2)}%
            </span>
          </div>
          
          <div className="card-details">
            <div className="detail">
              <span className="label">Volume</span>
              <span className="value">{formatVolume(stock.volume)}</span>
            </div>
            <div className="detail">
              <span className="label">RSI</span>
              <span className={`value ${stock.rsi > 70 ? 'overbought' : stock.rsi < 30 ? 'oversold' : ''}`}>
                {stock.rsi.toFixed(1)}
              </span>
            </div>
            {stock.alert && (
              <div className="detail alert">
                <span className="label">⚠️ Alert</span>
                <span className="value">{stock.alert}</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default WatchlistCards;
```

**CSS for cards (add to index.css):**

```css
.watchlist-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
}

.stock-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-color);
}

.stock-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stock-info .symbol {
  font-weight: bold;
  font-size: 16px;
  margin-right: 8px;
}

.stock-info .token {
  color: var(--text-secondary);
  font-size: 12px;
}

.remove-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
}

.remove-btn:hover {
  color: #ff4444;
}

.card-price {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.ltp {
  font-size: 24px;
  font-weight: bold;
}

.change {
  font-size: 14px;
  font-weight: 500;
}

.change.positive {
  color: #4caf50;
}

.change.negative {
  color: #f44336;
}

.card-details {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail .label {
  font-size: 11px;
  color: var(--text-secondary);
}

.detail .value {
  font-size: 14px;
  font-weight: 500;
}

.detail .value.overbought {
  color: #ff6b6b;
}

.detail .value.oversold {
  color: #4ecdc4;
}

.detail.alert {
  flex: 1;
  text-align: right;
}
```

---

### 6. View Toggle (Table/Card View)

**Add to `web_dashboard/frontend/src/components/WatchlistHeader.js`:**

```javascript
const [viewMode, setViewMode] = useState(() => {
  return localStorage.getItem('watchlistViewMode') || 'table';
});

const toggleViewMode = (mode) => {
  setViewMode(mode);
  localStorage.setItem('watchlistViewMode', mode);
};

// In JSX
<div className="view-toggle">
  <button 
    className={viewMode === 'table' ? 'active' : ''}
    onClick={() => toggleViewMode('table')}
  >
    📊 Table View
  </button>
  <button 
    className={viewMode === 'cards' ? 'active' : ''}
    onClick={() => toggleViewMode('cards')}
  >
    🃏 Card View
  </button>
</div>

// Conditional rendering
{viewMode === 'table' ? (
  <WatchlistTable ... />
) : (
  <WatchlistCards ... />
)}
```

---

### 7. Performance Badges

**Add to `WatchlistTable.js` cells:**

```javascript
const getPerformanceBadge = (changePercent) => {
  if (changePercent > 3) return <span className="badge strong-bullish">🚀 Strong</span>;
  if (changePercent > 1) return <span className="badge bullish">📈 Up</span>;
  if (changePercent < -3) return <span className="badge strong-bearish">📉 Strong</span>;
  if (changePercent < -1) return <span className="badge bearish">🔻 Down</span>;
  return <span className="badge neutral">➡️ Flat</span>;
};

// Use in the Change column
{getPerformanceBadge(stock.changePercent)}
```

**CSS for badges:**

```css
.badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  display: inline-block;
}

.badge.strong-bullish {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.badge.bullish {
  background: rgba(76, 175, 80, 0.1);
  color: #8bc34a;
}

.badge.strong-bearish {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.badge.bearish {
  background: rgba(244, 67, 54, 0.1);
  color: #ff8a80;
}

.badge.neutral {
  background: rgba(158, 158, 158, 0.2);
  color: #9e9e9e;
}
```

---

## Implementation Instructions

### Files to Create:
1. `web_dashboard/frontend/src/components/TokenSearch.js`
2. `web_dashboard/frontend/src/components/QuickAddGroups.js`
3. `web_dashboard/frontend/src/components/WatchlistCards.js`

### Files to Modify:
1. `web_dashboard/frontend/src/components/WatchlistTable.js` - Add empty state, performance badges
2. `web_dashboard/frontend/src/App.js` - Add demo watchlist, loadDemoWatchlist function
3. `web_dashboard/frontend/src/index.css` - Add all new CSS styles

### Backend Enhancement (Optional but Recommended):

**Add symbol search endpoint in `web_dashboard/backend/main.py`:**

```python
@app.get("/api/symbols/search")
async def search_symbols(q: str):
    """Search for symbols by name or token"""
    if not q or len(q) < 2:
        return []
    
    q = q.lower()
    results = []
    
    for token, symbol in symbol_mapping.items():
        if q in symbol.lower() or q in token:
            results.append({
                "token": token,
                "symbol": symbol,
                "name": symbol.replace('.NS', '').replace('-EQ', ''),
                "exchange": "NSE"
            })
            if len(results) >= 10:
                break
    
    return results
```

---

## Testing Checklist

After implementation, verify:

- [ ] Empty watchlist shows friendly guidance with quick-add buttons
- [ ] Demo watchlist loads 7 popular stocks successfully
- [ ] Search works with company names (e.g., "infosys")
- [ ] Search works with token numbers (e.g., "1594")
- [ ] Quick-add groups add multiple stocks at once
- [ ] Mobile card view works on small screens
- [ ] View toggle persists user preference
- [ ] Performance badges show correct colors
- [ ] All styles work in both light and dark mode

## Success Criteria

The watchlist feature will be considered improved when:

1. ✅ New users can add their first stock within 10 seconds
2. ✅ Zero confusion about what to do (empty state guides clearly)
3. ✅ Users can find stocks by company name without knowing token numbers
4. ✅ Mobile users have comfortable touch-friendly interface
5. ✅ Demo watchlist provides instant value without manual entry

---

**Focus on HIGH PRIORITY items first. Complete ALL implementations before considering the task done.**

This will transform the watchlist from "functional but confusing" to "intuitive and delightful" for new users!
```

---

This prompt is ready to give to any AI model. It contains:
- ✅ 7 complete features with full code
- ✅ CSS styling for all components
- ✅ Implementation instructions
- ✅ Testing checklist
- ✅ Success criteria

