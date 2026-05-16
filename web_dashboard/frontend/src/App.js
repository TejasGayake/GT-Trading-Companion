import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { createChart } from 'lightweight-charts';
import { Plus, Trash2, Download, Search, Sun, Moon, Bell, AlertTriangle, X, RefreshCw, Menu, Save } from 'lucide-react';

// WebSocket connection
let ws = null;

function App() {
  // State
  const [theme, setTheme] = useState('dark');
  const [activeSheet, setActiveSheet] = useState('live');
  const [rowData, setRowData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [showAddToken, setShowAddToken] = useState(false);
  const [newToken, setNewToken] = useState('');
  const [showChart, setShowChart] = useState(false);
  const [chartToken, setChartToken] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [instruments, setInstruments] = useState([]);

  const gridRef = useRef();
  const chartContainerRef = useRef();
  const chartRef = useRef(null);

  // Column definitions - matching Excel exactly
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

    // Load instruments
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
    const wsUrl = `ws://${window.location.hostname}:8000/ws`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      addToast('Connected to server', 'success');
    };

    ws.onclose = () => {
      setConnected(false);
      addToast('Disconnected from server', 'error');
      // Reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'init':
        case 'update':
          setRowData(message.data);
          setLastUpdate(new Date());
          break;
        case 'alert':
          handleNewAlert(message.data);
          break;
        case 'subscribed':
          console.log('Subscribed:', message.watchlist);
          break;
      }
    };
  };

  const fetchInstruments = async () => {
    try {
      const response = await fetch('/api/instruments');
      const data = await response.json();
      setInstruments(data.instruments || []);
    } catch (e) {
      console.error('Failed to load instruments:', e);
    }
  };

  const handleNewAlert = (alert) => {
    setAlerts(prev => [alert, ...prev].slice(0, 50));
    // addToast(`${alert.symbol}: ${alert.condition}`, 'warning'); // popup disabled

    // Play sound if enabled
    if (soundEnabled) {
      playAlertSound(alert.condition);
    }
  };

  const playAlertSound = (condition) => {
    // Simple beep using Web Audio API
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

  // Format helpers
  const formatPrice = (value) => value ? `₹${value.toFixed(2)}` : '-';
  const formatChange = (value) => value ? (value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2)) : '-';
  const formatPercent = (value) => value ? (value > 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`) : '-';
  const formatVolume = (value) => value ? value.toLocaleString() : '-';
  const formatRSI = (value) => value ? value.toFixed(1) : '-';
  const formatAlert = (value) => value || '';

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

  // Grid filter
  const onFilterTextChange = (e) => {
    setSearchText(e.target.value);
    gridRef.current?.api.setQuickFilter(e.target.value);
  };

  // Row click handler
  const onRowDoubleClick = async (event) => {
    const token = event.data.token;
    setChartToken(token);

    // Fetch candle data
    try {
      const response = await fetch(`/api/candles/${token}`);
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

    // Clear existing chart
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

  // Add token
  const handleAddToken = async () => {
    if (!newToken) return;

    try {
      await fetch(`/api/tokens/add?token=${newToken}`, { method: 'POST' });
      addToast(`Added token ${newToken}`, 'success');
      setNewToken('');
      setShowAddToken(false);
    } catch (e) {
      addToast('Failed to add token', 'error');
    }
  };

  // Remove token
  const handleRemoveToken = async (token) => {
    try {
      await fetch(`/api/tokens/${token}`, { method: 'DELETE' });
      addToast(`Removed token ${token}`, 'success');
    } catch (e) {
      addToast('Failed to remove token', 'error');
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

  // Quick filter from search
  const filteredData = useMemo(() => {
    if (!searchText) return rowData;
    const lower = searchText.toLowerCase();
    return rowData.filter(r =>
      r.symbol?.toLowerCase().includes(lower) ||
      r.token?.toLowerCase().includes(lower)
    );
  }, [rowData, searchText]);

  return (
    <div className="app-container">
      {/* Toolbar */}
      <div className="toolbar">
        <div className="toolbar-group">
          <button className="toolbar-btn primary" onClick={() => setShowAddToken(true)}>
            <Plus size={16} /> Add Token
          </button>
          <button className="toolbar-btn" onClick={exportToCSV}>
            <Download size={16} /> Export
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
            onClick={() => setSoundEnabled(!soundEnabled)}
            title="Toggle sound"
          >
            {soundEnabled ? <Bell size={16} /> : <AlertTriangle size={16} />}
          </button>
          <button
            className="toolbar-btn"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>

      {/* Sheet Tabs */}
      <div className="sheet-tabs">
        <button
          className={`sheet-tab ${activeSheet === 'live' ? 'active' : ''}`}
          onClick={() => setActiveSheet('live')}
        >
          📊 Live Data
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'instruments' ? 'active' : ''}`}
          onClick={() => setActiveSheet('instruments')}
        >
          📋 Instruments
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveSheet('alerts')}
        >
          🔔 Alerts ({alerts.length})
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'historical' ? 'active' : ''}`}
          onClick={() => setActiveSheet('historical')}
        >
          📈 Historical
        </button>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Live Data Sheet */}
        <div className={`sheet-view ${activeSheet === 'live' ? 'active' : ''}`}>
          <div className="ag-theme-alpine-dark grid-container">
            <AgGridReact
              ref={gridRef}
              rowData={filteredData}
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
              Total: {instruments.length} tokens
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {instruments.slice(0, 100).map((inst) => (
                <div
                  key={inst.token}
                  style={{
                    padding: '6px 12px',
                    background: 'var(--border-color)',
                    borderRadius: '4px',
                    fontSize: '12px'
                  }}
                >
                  {inst.symbol} ({inst.token})
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Alerts Sheet */}
        <div className={`sheet-view ${activeSheet === 'alerts' ? 'active' : ''}`}>
          <div className="alerts-panel">
            {alerts.length === 0 ? (
              <p style={{ color: '#888' }}>No alerts yet</p>
            ) : (
              alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className={`alert-card ${alert.condition.toLowerCase().replace(' ', '-')}`}
                >
                  <strong>{alert.symbol}</strong>
                  <span>{alert.condition}</span>
                  <span>₹{alert.ltp?.toFixed(2)}</span>
                  <span style={{ color: '#888', fontSize: '12px' }}>
                    {new Date(alert.triggered_at).toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
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
          Last Update: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
        </div>
        <div className="status-item">
          Active Alerts: {alerts.filter(a => a.status === 'active').length}
        </div>
        <div className="status-item">
          Rows: {rowData.length}
        </div>
      </div>

      {/* Add Token Modal */}
      {showAddToken && (
        <div className="modal-overlay" onClick={() => setShowAddToken(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Add Token</h3>
            <input
              type="text"
              className="modal-input"
              placeholder="Enter token number (e.g., 3045)"
              value={newToken}
              onChange={e => setNewToken(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && handleAddToken()}
            />
            <div className="modal-actions">
              <button className="toolbar-btn" onClick={() => setShowAddToken(false)}>
                Cancel
              </button>
              <button className="toolbar-btn primary" onClick={handleAddToken}>
                Add
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
              <h3>📈 {chartToken} - Candlestick Chart</h3>
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