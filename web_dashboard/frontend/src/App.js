import React, { useState, useEffect, useRef, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { createChart } from 'lightweight-charts';
import { Plus, Minus, Download, Search, Sun, Moon, Bell, AlertTriangle, X, Trash, RefreshCw, TrendingUp, Target, BarChart3 } from 'lucide-react';

// Cloud-ready configuration
const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) return process.env.REACT_APP_API_URL;
  return `http://${window.location.hostname}:8000`;
};

const getWsUrl = () => {
  if (process.env.REACT_APP_WS_URL) return process.env.REACT_APP_WS_URL;
  return `ws://${window.location.hostname}:8000`;
};

const getUserId = () => {
  let uid = localStorage.getItem('gt_user_id');
  if (!uid) {
    uid = crypto.randomUUID();
    localStorage.setItem('gt_user_id', uid);
  }
  return uid;
};

// WebSocket connection
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_DELAY = 30000;

function App() {
  // State
  const [theme, setTheme] = useState('dark');
  const [activeSheet, setActiveSheet] = useState('live');
  const [rowData, setRowData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertCategories, setAlertCategories] = useState({ camarilla: [], volume_spike: [], volume_sma8: [] });
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [showAddToken, setShowAddToken] = useState(false);
  const [showRemoveToken, setShowRemoveToken] = useState(false);
  const [showChart, setShowChart] = useState(false);
  const [chartToken, setChartToken] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [instruments, setInstruments] = useState([]);

  // Symbol search state
  const [symbolSearchText, setSymbolSearchText] = useState('');
  const [symbolResults, setSymbolResults] = useState([]);
  const symbolSearchTimeout = useRef(null);

  // Remove token search state
  const [removeSearchText, setRemoveSearchText] = useState('');

  const gridRef = useRef();
  const chartContainerRef = useRef();
  const chartRef = useRef(null);

  // Format helpers
  const formatPrice = (value) => value ? `₹${value.toFixed(2)}` : '-';
  const formatChange = (value) => value ? (value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2)) : '-';
  const formatPercent = (value) => value ? (value > 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`) : '-';
  const formatVolume = (value) => value ? value.toLocaleString() : '-';
  const formatRSI = (value) => value ? value.toFixed(1) : '-';
  const formatAlert = (value) => value || '';
  const formatStatus = (value) => value ? 'ERROR' : 'OK';

  const getPriceClass = (params) => {
    if (params.value > 0) return 'cell-positive';
    if (params.value < 0) return 'cell-negative';
    return '';
  };

  const getPercentClass = (params) => {
    if (params.value > 0) return 'cell-positive';
    if (params.value < 0) return 'cell-negative';
    return '';
  };

  const getRSIClass = (params) => {
    if (params.value > 70) return 'cell-rsi-high';
    if (params.value < 30) return 'cell-rsi-low';
    return '';
  };

  const getAlertClass = (params) => {
    return params.value ? 'cell-alert' : '';
  };

  const getStatusClass = (params) => {
    return params.value ? 'cell-status-error' : 'cell-status-ok';
  };

  // Column definitions - matching HTML version exactly
  const columnDefs = useMemo(() => [
    { headerName: 'TOKEN', field: 'token', width: 80, pinned: 'left' },
    { headerName: 'SYMBOL', field: 'symbol', width: 120, pinned: 'left' },
    { headerName: 'LTP', field: 'ltp', width: 90, cellRenderer: p => formatPrice(p.value), cellClass: getPriceClass },
    { headerName: 'OPEN', field: 'open', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'HIGH', field: 'high', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'LOW', field: 'low', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'PREV CLOSE', field: 'prev_close', width: 100, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'CHANGE', field: 'change', width: 100, cellRenderer: p => formatChange(p.value), cellClass: getPriceClass },
    { headerName: '%CHANGE', field: 'change_percent', width: 90, cellRenderer: p => formatPercent(p.value), cellClass: getPercentClass },
    { headerName: 'VOLUME', field: 'volume', width: 120, cellRenderer: p => formatVolume(p.value) },
    { headerName: 'AVG VOL', field: 'avg_volume', width: 100, cellRenderer: p => formatVolume(p.value) },
    { headerName: 'SMA8', field: 'sma8', width: 80, cellRenderer: p => formatVolume(p.value) },
    { headerName: 'VWAP', field: 'vwap', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'SMA21', field: 'sma21', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'SMA40', field: 'sma40', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'SMA200', field: 'sma200', width: 100, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'EMA10', field: 'ema10', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'RSI14', field: 'rsi14', width: 80, cellRenderer: p => formatRSI(p.value), cellClass: getRSIClass },
    { headerName: 'SUPERTREND', field: 'supertrend', width: 110, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'S. DIR', field: 'supertrend_direction', width: 70 },
    { headerName: 'C.H4', field: 'Camarilla_H4', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'C.H3', field: 'Camarilla_H3', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'C.L3', field: 'Camarilla_L3', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'C.L4', field: 'Camarilla_L4', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'SUPPORT', field: 'support', width: 100, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'RESISTANCE', field: 'resistance', width: 110, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'VOLATILITY', field: 'volatility', width: 100, cellRenderer: p => p.value ? p.value.toFixed(2) + '%' : '-' },
    { headerName: 'PD HIGH', field: 'prev_day_high', width: 100, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'PD LOW', field: 'prev_day_low', width: 90, cellRenderer: p => formatPrice(p.value) },
    { headerName: 'ALERT', field: 'alert', width: 120, cellRenderer: p => formatAlert(p.value), cellClass: getAlertClass },
    { headerName: 'STATUS', field: 'last_error', width: 90, cellRenderer: p => formatStatus(p.value), cellClass: getStatusClass },
  ], []);

  const defaultColDef = useMemo(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    suppressMenu: false,
  }), []);

  // Connect to WebSocket
  useEffect(() => {
    connectWebSocket();
    fetchInstruments();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  // Apply theme
  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-theme' : '';
  }, [theme]);

  // Update chart when data changes
  useEffect(() => {
    if (showChart && chartData.length > 0) {
      renderChart();
    }
  }, [chartData, showChart]);

  const connectWebSocket = () => {
    const userId = getUserId();
    const wsUrl = `${getWsUrl()}/ws?user_id=${userId}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempts = 0;
      addToast('Connected to server', 'success');
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY);
      reconnectAttempts++;
      addToast('Disconnected from server', 'error');
      setTimeout(connectWebSocket, delay);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'init':
        case 'update':
          setRowData(message.data);
          setLastUpdate(new Date());
          if (message.alert_categories) {
            setAlertCategories(message.alert_categories);
          }
          break;
        case 'alert':
          handleNewAlert(message.data);
          break;
        case 'subscribed':
          console.log('Subscribed:', message.watchlist);
          break;
        default:
          break;
      }
    };
  };

  const fetchInstruments = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/instruments`);
      const data = await response.json();
      setInstruments(data.instruments || []);
    } catch (e) {
      console.error('Failed to load instruments:', e);
    }
  };

  const handleNewAlert = (alert) => {
    setAlerts(prev => [alert, ...prev].slice(0, 50));
    if (soundEnabled) {
      playAlertSound(alert.condition);
    }
  };

  const playAlertSound = (condition) => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      oscillator.frequency.value = condition === 'ABOVE H4' ? 800 : 400;
      oscillator.type = 'sine';
      gainNode.gain.value = 0.1;

      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.3);
    } catch (e) {
      console.log('Audio not available');
    }
  };

  const addToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  // Grid filter
  const onFilterTextChange = (e) => {
    setSearchText(e.target.value);
    gridRef.current?.api.setQuickFilter(e.target.value);
  };

  // Row click handler
  const onRowDoubleClick = async (event) => {
    const token = event.data.token;
    setChartToken(token);

    try {
      const response = await fetch(`${getApiUrl()}/api/candles/${token}`);
      const data = await response.json();
      setChartData(data.candles || []);
      setShowChart(true);
    } catch (e) {
      addToast('Failed to load chart data', 'error');
    }
  };

  // Render chart
  const renderChart = () => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { type: 'solid', color: theme === 'light' ? '#fff' : '#1a1a1a' },
        textColor: theme === 'light' ? '#333' : '#ddd',
      },
      grid: {
        vertLines: { color: theme === 'light' ? '#eee' : '#333' },
        horzLines: { color: theme === 'light' ? '#eee' : '#333' },
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#4caf50',
      downColor: '#f44336',
      borderUpColor: '#4caf50',
      borderDownColor: '#f44336',
      wickUpColor: '#4caf50',
      wickDownColor: '#f44336',
    });

    candlestickSeries.setData(chartData);
    chart.timeScale().fitContent();
    chartRef.current = chart;
  };

  // Export to CSV
  const exportToCSV = () => {
    const gridApi = gridRef.current?.api;
    if (gridApi) {
      gridApi.exportDataAsCsv({
        fileName: `trading_data_${new Date().toISOString().split('T')[0]}.csv`
      });
      addToast('Exported to CSV', 'success');
    }
  };

  // Symbol search for Add Token
  const handleSymbolSearch = (query) => {
    setSymbolSearchText(query);
    clearTimeout(symbolSearchTimeout.current);
    symbolSearchTimeout.current = setTimeout(async () => {
      try {
        const response = await fetch(`${getApiUrl()}/api/symbols/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        const addedTokens = rowData.map(r => r.token);
        const available = (data.symbols || []).filter(s => !addedTokens.includes(s.token));
        setSymbolResults(available);
      } catch (e) {
        console.error('Search error:', e);
      }
    }, 300);
  };

  // Add token by symbol
  const handleAddToken = async (token, symbol) => {
    try {
      const userId = getUserId();
      await fetch(`${getApiUrl()}/api/tokens/add?token=${token}&user_id=${userId}`, { method: 'POST' });
      addToast(`Added ${symbol}`, 'success');
      setShowAddToken(false);
      setSymbolSearchText('');
      setSymbolResults([]);

      // Trigger refresh via WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'subscribe', watchlist: 'Default', action: 'refresh' }));
      }
    } catch (e) {
      addToast('Failed to add token', 'error');
    }
  };

  // Remove token
  const handleRemoveToken = async (token) => {
    try {
      const userId = getUserId();
      await fetch(`${getApiUrl()}/api/tokens/${token}?user_id=${userId}`, { method: 'DELETE' });
      addToast(`Removed token ${token}`, 'success');
    } catch (e) {
      addToast('Failed to remove token', 'error');
    }
  };

  // Clear alerts
  const handleClearAlerts = async () => {
    try {
      await fetch(`${getApiUrl()}/api/alerts/clear`, { method: 'POST' });
      setAlerts([]);
      addToast('Alerts cleared', 'success');
    } catch (e) {
      addToast('Failed to clear alerts', 'error');
    }
  };

  // Refresh data
  const handleRefresh = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'subscribe', watchlist: 'Default', action: 'refresh' }));
      addToast('Refreshing data...', 'success');
    }
  };

  // Close chart
  const closeChart = () => {
    setShowChart(false);
    setChartToken(null);
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
  };

  // Toggle theme
  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  // Select stock from alerts
  const selectStock = (token) => {
    setActiveSheet('live');
    setSearchText(token);
    gridRef.current?.api.setQuickFilter(token);
  };

  // Filtered remove token list
  const filteredRemoveTokens = useMemo(() => {
    if (!removeSearchText) return rowData;
    const lower = removeSearchText.toLowerCase();
    return rowData.filter(r =>
      r.symbol?.toLowerCase().includes(lower) ||
      r.token?.toLowerCase().includes(lower)
    );
  }, [rowData, removeSearchText]);

  // Total alert count
  const totalAlertCount = (alertCategories.camarilla?.length || 0) +
                          (alertCategories.volume_spike?.length || 0) +
                          (alertCategories.volume_sma8?.length || 0);

  return (
    <div className="app-container">
      {/* Toolbar */}
      <div className="toolbar">
        <div className="toolbar-group">
          <button className="toolbar-btn primary" onClick={() => setShowAddToken(true)}>
            <Plus size={16} /> Add
          </button>
          <button className="toolbar-btn" onClick={() => setShowRemoveToken(true)}>
            <Minus size={16} /> Remove
          </button>
          <button className="toolbar-btn" onClick={exportToCSV}>
            <Download size={16} /> Export
          </button>
          <button className="toolbar-btn" onClick={handleClearAlerts}>
            <Trash size={16} /> Clear
          </button>
        </div>

        <div className="toolbar-group">
          <Search size={16} />
          <input
            type="text"
            className="search-input"
            placeholder="Search symbol or token..."
            value={searchText}
            onChange={onFilterTextChange}
          />
        </div>

        <div className="toolbar-group" style={{ marginLeft: 'auto' }}>
          <button
            className="toolbar-btn"
            onClick={toggleTheme}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button className="toolbar-btn" onClick={handleRefresh}>
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Sheet Tabs */}
      <div className="sheet-tabs">
        <button
          className={`sheet-tab ${activeSheet === 'live' ? 'active' : ''}`}
          onClick={() => setActiveSheet('live')}
        >
          Live Data
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'instruments' ? 'active' : ''}`}
          onClick={() => setActiveSheet('instruments')}
        >
          Instruments
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveSheet('alerts')}
        >
          Alerts ({totalAlertCount})
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'historical' ? 'active' : ''}`}
          onClick={() => setActiveSheet('historical')}
        >
          Historical
        </button>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Live Data Sheet */}
        <div className={`sheet-view ${activeSheet === 'live' ? 'active' : ''}`}>
          <div className="ag-theme-alpine-dark grid-container">
            <AgGridReact
              ref={gridRef}
              rowData={rowData}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              onRowDoubleClicked={onRowDoubleClick}
              rowHeight={32}
              headerHeight={32}
              animateRows={true}
              getRowId={(params) => params.data.token}
              suppressCellFocus={true}
            />
          </div>
        </div>

        {/* Instruments Sheet */}
        <div className={`sheet-view ${activeSheet === 'instruments' ? 'active' : ''}`}>
          <div className="alerts-panel">
            <h3>Available Instruments</h3>
            <p style={{ color: '#888', marginBottom: '16px' }}>
              Total: {rowData.length} tokens
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {rowData.slice(0, 100).map((item) => (
                <div
                  key={item.token}
                  style={{
                    padding: '6px 12px',
                    background: 'var(--border-color)',
                    borderRadius: '4px',
                    fontSize: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    minWidth: '140px'
                  }}
                >
                  <span>{item.symbol} <span style={{ color: '#888' }}>{item.token}</span></span>
                  <button
                    onClick={() => handleRemoveToken(item.token)}
                    style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: '14px', padding: '2px 6px' }}
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Alerts Sheet - 3 Columns */}
        <div className={`sheet-view ${activeSheet === 'alerts' ? 'active' : ''}`}>
          <div className="alerts-columns">
            {/* Volume Spike Column */}
            <div className="alert-column">
              <div className="alert-column-header">
                <TrendingUp size={16} />
                Volume Spike
                <span className="alert-count">({alertCategories.volume_spike?.length || 0})</span>
              </div>
              <div className="alert-column-content">
                {(!alertCategories.volume_spike || alertCategories.volume_spike.length === 0) ? (
                  <p style={{ color: '#888' }}>No volume spike alerts</p>
                ) : (
                  alertCategories.volume_spike.map((s, idx) => (
                    <div key={idx} className="alert-stock-item volume-spike" onClick={() => selectStock(s.token)}>
                      <div>
                        <div className="symbol">{s.symbol}</div>
                        <div style={{ fontSize: '11px', color: '#888' }}>Vol: {s.volume?.toLocaleString()}</div>
                      </div>
                      <div>
                        <span className="ltp">₹{s.ltp?.toFixed(2)}</span>
                        <span className="condition" style={{ marginLeft: '8px' }}>SPIKE</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Camarilla Column */}
            <div className="alert-column">
              <div className="alert-column-header">
                <Target size={16} />
                Camarilla
                <span className="alert-count">({alertCategories.camarilla?.length || 0})</span>
              </div>
              <div className="alert-column-content">
                {(!alertCategories.camarilla || alertCategories.camarilla.length === 0) ? (
                  <p style={{ color: '#888' }}>No camarilla alerts</p>
                ) : (
                  alertCategories.camarilla.map((s, idx) => (
                    <div key={idx} className={`alert-stock-item ${s.condition === 'ABOVE H4' ? 'camarilla-above' : 'camarilla-below'}`} onClick={() => selectStock(s.token)}>
                      <div>
                        <div className="symbol">{s.symbol}</div>
                        <div style={{ fontSize: '11px', color: '#888' }}>H4: ₹{s.Camarilla_H4?.toFixed(2)} | L4: ₹{s.Camarilla_L4?.toFixed(2)}</div>
                      </div>
                      <div>
                        <span className="ltp">₹{s.ltp?.toFixed(2)}</span>
                        <span className="condition" style={{ marginLeft: '8px' }}>{s.condition}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Volume SMA8 Column */}
            <div className="alert-column">
              <div className="alert-column-header">
                <BarChart3 size={16} />
                Volume &gt; 3x SMA8
                <span className="alert-count">({alertCategories.volume_sma8?.length || 0})</span>
              </div>
              <div className="alert-column-content">
                {(!alertCategories.volume_sma8 || alertCategories.volume_sma8.length === 0) ? (
                  <p style={{ color: '#888' }}>No volume SMA8 alerts</p>
                ) : (
                  alertCategories.volume_sma8.map((s, idx) => (
                    <div key={idx} className="alert-stock-item" onClick={() => selectStock(s.token)}>
                      <div>
                        <div className="symbol">{s.symbol}</div>
                        <div style={{ fontSize: '11px', color: '#888' }}>Vol SMA8: {s.volume_sma8?.toLocaleString()}</div>
                      </div>
                      <div>
                        <span className="ltp">₹{s.ltp?.toFixed(2)}</span>
                        <span className="condition" style={{ marginLeft: '8px' }}>3x</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Historical Sheet */}
        <div className={`sheet-view ${activeSheet === 'historical' ? 'active' : ''}`}>
          <div className="alerts-panel">
            <h3>Historical Data</h3>
            <p style={{ color: '#888' }}>
              Double-click any row in Live Data to view charts
            </p>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <div className="status-item">
          <span className={`status-dot ${connected ? '' : 'disconnected'}`}></span>
          {connected ? 'Connected' : 'Disconnected'}
        </div>
        <div className="status-item">
          Last Update: {lastUpdate ? lastUpdate.toLocaleTimeString() : '-'}
        </div>
        <div className="status-item">
          Active Alerts: {totalAlertCount}
        </div>
        <div className="status-item">
          Rows: {rowData.length}
        </div>
      </div>

      {/* Add Token Modal with Symbol Search */}
      {showAddToken && (
        <div className="modal-overlay" onClick={() => { setShowAddToken(false); setSymbolSearchText(''); setSymbolResults([]); }}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ minWidth: '500px' }}>
            <h3 className="modal-title">Add Stock to Watchlist</h3>
            <input
              type="text"
              className="modal-input"
              placeholder="Search by symbol name (e.g., RELIANCE, TCS)..."
              value={symbolSearchText}
              onChange={e => handleSymbolSearch(e.target.value)}
              autoFocus
            />
            <div className="symbol-results">
              {symbolResults.length === 0 && symbolSearchText ? (
                <p style={{ color: '#888', padding: '12px' }}>No symbols found</p>
              ) : (
                symbolResults.map((s) => (
                  <div
                    key={s.token}
                    className="symbol-result-item"
                    onClick={() => handleAddToken(s.token, s.symbol)}
                  >
                    <span style={{ fontWeight: 600 }}>{s.symbol}</span>
                    <span style={{ color: '#888', fontSize: '12px' }}>Token: {s.token}</span>
                  </div>
                ))
              )}
            </div>
            <div className="modal-actions">
              <button className="toolbar-btn" onClick={() => { setShowAddToken(false); setSymbolSearchText(''); setSymbolResults([]); }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Remove Token Modal */}
      {showRemoveToken && (
        <div className="modal-overlay" onClick={() => { setShowRemoveToken(false); setRemoveSearchText(''); }}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Remove Token</h3>
            <input
              type="text"
              className="modal-input"
              placeholder="Search by symbol..."
              value={removeSearchText}
              onChange={e => setRemoveSearchText(e.target.value)}
              autoFocus
            />
            <div className="remove-token-list">
              {filteredRemoveTokens.length === 0 ? (
                <p style={{ color: '#888' }}>No tokens found</p>
              ) : (
                filteredRemoveTokens.map((r) => (
                  <div key={r.token} className="remove-token-item">
                    <span>{r.symbol} ({r.token})</span>
                    <button className="remove-btn" onClick={() => handleRemoveToken(r.token)}>Remove</button>
                  </div>
                ))
              )}
            </div>
            <div className="modal-actions">
              <button className="toolbar-btn" onClick={() => { setShowRemoveToken(false); setRemoveSearchText(''); }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chart Modal */}
      {showChart && (
        <div className="chart-modal">
          <div className="chart-content">
            <div className="chart-header">
              <h3>{chartToken} - Candlestick Chart</h3>
              <button className="chart-close" onClick={closeChart}>
                <X size={24} />
              </button>
            </div>
            <div ref={chartContainerRef}></div>
          </div>
        </div>
      )}

      {/* Toast Container */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
