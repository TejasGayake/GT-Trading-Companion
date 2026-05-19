import React, { useState, useEffect, useRef, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { createChart } from 'lightweight-charts';
import { Plus, Minus, Download, Upload, Search, Sun, Moon, Bell, AlertTriangle, X, Trash, RefreshCw, TrendingUp, Target, BarChart3, LayoutGrid, LayoutList } from 'lucide-react';
import TokenSearch from './TokenSearch';
import QuickAddGroups from './QuickAddGroups';
import WatchlistCards from './WatchlistCards';

// Performance badge cell renderer
const ChangeCellRenderer = (params) => {
  const v = params.value;
  if (v == null) return <span>-</span>;
  const pct = `${v > 0 ? '+' : ''}${v.toFixed(2)}%`;
  let badgeClass = 'badge ';
  let label = 'Flat';
  if (v > 3) { badgeClass += 'strong-bullish'; label = 'Strong'; }
  else if (v > 1) { badgeClass += 'bullish'; label = 'Up'; }
  else if (v < -3) { badgeClass += 'strong-bearish'; label = 'Strong'; }
  else if (v < -1) { badgeClass += 'bearish'; label = 'Down'; }
  else { badgeClass += 'neutral'; }
  return (
    <span>
      <span>{pct}</span>{' '}
      <span className={badgeClass}>{label}</span>
    </span>
  );
};

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

const MAX_RECONNECT_DELAY = 30000;

function App() {
  // WebSocket refs (persist across renders without triggering re-renders)
  const wsRef = useRef(null);
  const reconnectRef = useRef({ attempts: 0, timeoutId: null });

  // State
  const [theme, setTheme] = useState(() => localStorage.getItem('gt_theme') || 'dark');
  const [activeSheet, setActiveSheet] = useState('live');
  const [rowData, setRowData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertCategories, setAlertCategories] = useState({ camarilla: [], volume_spike: [], volume_sma8: [] });
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // 'connected', 'reconnecting', 'disconnected'
  const [reconnectCountdown, setReconnectCountdown] = useState(0);
  const [dataLoading, setDataLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [showAddToken, setShowAddToken] = useState(false);
  const [showRemoveToken, setShowRemoveToken] = useState(false);
  const [showChart, setShowChart] = useState(false);
  const [chartToken, setChartToken] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [chartTimeframe, setChartTimeframe] = useState('5d'); // '1d', '5d', '1mo'
  const [toasts, setToasts] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [instruments, setInstruments] = useState([]);
  const [watchlists, setWatchlists] = useState({ 'Default': [] });
  const [currentWatchlist, setCurrentWatchlist] = useState('Default');
  const [showNewWatchlist, setShowNewWatchlist] = useState(false);
  const [newWatchlistName, setNewWatchlistName] = useState('');
  const [portfolio, setPortfolio] = useState([]);
  const [portfolioSummary, setPortfolioSummary] = useState({ total_invested: 0, total_current: 0, total_pnl: 0, total_pnl_percent: 0 });
  const [showAddHolding, setShowAddHolding] = useState(false);
  const [newHolding, setNewHolding] = useState({ token: '', symbol: '', quantity: '', buy_price: '' });
  const [trades, setTrades] = useState([]);
  const [viewMode, setViewMode] = useState(() => localStorage.getItem('watchlistViewMode') || 'table');

  // User-created alerts
  const [userAlerts, setUserAlerts] = useState(() => {
    try {
      const saved = localStorage.getItem('user_alerts');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [showCreateAlert, setShowCreateAlert] = useState(false);
  const [newAlert, setNewAlert] = useState({ token: '', symbol: '', condition: 'above', price: '' });

  // Drawing tool state
  const [chartOverlays, setChartOverlays] = useState({ camarilla: true, supertrend: true, vwap: false });
  const [customLines, setCustomLines] = useState(() => {
    try {
      const saved = localStorage.getItem('chart_custom_lines');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [customLinePrice, setCustomLinePrice] = useState('');
  const seriesRef = useRef(null);

  // Symbol search state
  const [symbolSearchText, setSymbolSearchText] = useState('');
  const [symbolResults, setSymbolResults] = useState([]);
  const symbolSearchTimeout = useRef(null);
  const csvFileRef = useRef(null);

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
    { headerName: '%CHANGE', field: 'change_percent', width: 130, cellRenderer: ChangeCellRenderer, cellClass: getPercentClass },
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
    fetchPortfolio();
    fetchTrades();

    return () => {
      if (reconnectRef.current.timeoutId) clearTimeout(reconnectRef.current.timeoutId);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Apply theme
  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-theme' : '';
  }, [theme]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger shortcuts when typing in inputs
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      // Ctrl+A: Add token modal
      if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
        e.preventDefault();
        setShowAddToken(true);
      }
      // Ctrl+F: Focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        document.querySelector('.search-input')?.focus();
      }
      // Ctrl+E: Export CSV
      if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        exportToCSV();
      }
      // Ctrl+D: Toggle theme
      if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        setTheme(t => t === 'dark' ? 'light' : 'dark');
      }
      // F5: Refresh data
      if (e.key === 'F5') {
        e.preventDefault();
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'subscribe', watchlist: currentWatchlist, action: 'refresh' }));
        }
      }
      // Escape: Close modals
      if (e.key === 'Escape') {
        setShowAddToken(false);
        setShowRemoveToken(false);
        setShowChart(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentWatchlist, theme]);

  // Persist custom lines to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('chart_custom_lines', JSON.stringify(customLines));
    } catch {}
  }, [customLines]);

  // Update chart when data changes
  useEffect(() => {
    if (showChart && chartData.length > 0) {
      renderChart();
    }
  }, [chartData, showChart, chartOverlays, customLines]);

  const connectWebSocket = () => {
    const userId = getUserId();
    const wsUrl = `${getWsUrl()}/ws?user_id=${userId}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setConnected(true);
      setConnectionStatus('connected');
      setReconnectCountdown(0);
      reconnectRef.current.attempts = 0;
      addToast('Connected to server', 'success');
    };

    wsRef.current.onclose = () => {
      setConnected(false);
      setConnectionStatus('reconnecting');
      const delay = Math.min(1000 * Math.pow(2, reconnectRef.current.attempts), MAX_RECONNECT_DELAY);
      reconnectRef.current.attempts++;
      addToast('Disconnected from server', 'error');

      // Show countdown
      let remaining = Math.ceil(delay / 1000);
      setReconnectCountdown(remaining);
      const countdownInterval = setInterval(() => {
        remaining--;
        setReconnectCountdown(remaining);
        if (remaining <= 0) clearInterval(countdownInterval);
      }, 1000);

      if (reconnectRef.current.timeoutId) clearTimeout(reconnectRef.current.timeoutId);
      reconnectRef.current.timeoutId = setTimeout(() => {
        clearInterval(countdownInterval);
        connectWebSocket();
      }, delay);
    };

    wsRef.current.onmessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
        return;
      }

      switch (message.type) {
        case 'ping':
          // Respond to server heartbeat
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }));
          }
          break;
        case 'init':
          if (message.watchlists) {
            setWatchlists(message.watchlists);
            const names = Object.keys(message.watchlists);
            if (names.length > 0 && !names.includes(currentWatchlist)) {
              setCurrentWatchlist(names[0]);
            }
          }
          // fall through to update
        case 'update':
          setRowData(message.data);
          setLastUpdate(new Date());
          setDataLoading(false);
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

  // Portfolio functions
  const fetchPortfolio = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/portfolio`);
      const data = await response.json();
      setPortfolio(data.holdings || []);
      setPortfolioSummary(data.summary || {});
    } catch (e) {
      console.error('Failed to load portfolio:', e);
    }
  };

  const fetchTrades = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/portfolio/trades?limit=100`);
      const data = await response.json();
      setTrades(data.trades || []);
    } catch (e) {
      console.error('Failed to load trades:', e);
    }
  };

  const handleAddHolding = async () => {
    if (!newHolding.token || !newHolding.quantity || !newHolding.buy_price) return;
    try {
      await fetch(`${getApiUrl()}/api/portfolio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: newHolding.token,
          symbol: newHolding.symbol || newHolding.token,
          quantity: parseInt(newHolding.quantity),
          buy_price: parseFloat(newHolding.buy_price)
        })
      });
      setShowAddHolding(false);
      setNewHolding({ token: '', symbol: '', quantity: '', buy_price: '' });
      fetchPortfolio();
      addToast('Added to portfolio', 'success');
    } catch (e) {
      const err = parseError(e, 'add holding');
      addToast(err.message, err.type, err.duration);
    }
  };

  const handleRemoveHolding = async (token) => {
    try {
      await fetch(`${getApiUrl()}/api/portfolio/${token}`, { method: 'DELETE' });
      fetchPortfolio();
      addToast('Removed from portfolio', 'success');
    } catch (e) {
      addToast('Failed to remove holding', 'error');
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

  const addToast = (message, type = 'info', duration = 5000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  };

  // Parse error responses into user-friendly messages
  const parseError = (error, context = '') => {
    const msg = error?.message || String(error);
    if (msg.includes('429') || msg.includes('rate limit') || msg.includes('too many requests')) {
      return { message: `Rate limit exceeded - please wait a moment before retrying${context ? ` (${context})` : ''}`, type: 'warning', duration: 8000 };
    }
    if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('ERR_NETWORK')) {
      return { message: `Network error - check your internet connection${context ? ` (${context})` : ''}`, type: 'error', duration: 8000 };
    }
    if (msg.includes('invalid') && msg.includes('symbol')) {
      return { message: `Invalid symbol - use .NS suffix for NSE stocks${context ? ` (${context})` : ''}`, type: 'warning', duration: 8000 };
    }
    return { message: `Error${context ? ` (${context})` : ''}: ${msg}`, type: 'error' };
  };

  // User alert functions
  const requestNotificationPermission = async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission();
    }
  };

  const sendBrowserNotification = (title, body) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body, icon: '/favicon.ico' });
    }
  };

  const createUserAlert = () => {
    if (!newAlert.token || !newAlert.price || isNaN(parseFloat(newAlert.price))) {
      addToast('Please select a stock and enter a valid price', 'warning');
      return;
    }

    const alert = {
      id: Date.now(),
      token: newAlert.token,
      symbol: newAlert.symbol,
      condition: newAlert.condition,
      price: parseFloat(newAlert.price),
      createdAt: new Date().toISOString(),
      triggered: false
    };

    const updated = [...userAlerts, alert];
    setUserAlerts(updated);
    localStorage.setItem('user_alerts', JSON.stringify(updated));
    setShowCreateAlert(false);
    setNewAlert({ token: '', symbol: '', condition: 'above', price: '' });
    addToast(`Alert created: ${alert.symbol} ${alert.condition} ₹${alert.price}`, 'success');
    requestNotificationPermission();
  };

  const deleteUserAlert = (id) => {
    const updated = userAlerts.filter(a => a.id !== id);
    setUserAlerts(updated);
    localStorage.setItem('user_alerts', JSON.stringify(updated));
  };

  const toggleUserAlert = (id) => {
    const updated = userAlerts.map(a => a.id === id ? { ...a, triggered: false } : a);
    setUserAlerts(updated);
    localStorage.setItem('user_alerts', JSON.stringify(updated));
  };

  // Check user alerts against current prices
  useEffect(() => {
    if (rowData.length === 0 || userAlerts.length === 0) return;

    userAlerts.forEach(alert => {
      if (alert.triggered) return;

      const stock = rowData.find(d => d.token === alert.token);
      if (!stock || !stock.ltp) return;

      const ltp = stock.ltp;
      let shouldTrigger = false;

      if (alert.condition === 'above' && ltp >= alert.price) {
        shouldTrigger = true;
      } else if (alert.condition === 'below' && ltp <= alert.price) {
        shouldTrigger = true;
      }

      if (shouldTrigger) {
        const title = `Price Alert: ${alert.symbol}`;
        const body = `${alert.symbol} is now ₹${ltp.toFixed(2)} (${alert.condition} ₹${alert.price})`;
        sendBrowserNotification(title, body);
        addToast(body, 'warning', 10000);

        // Mark as triggered
        setUserAlerts(prev => {
          const updated = prev.map(a => a.id === alert.id ? { ...a, triggered: true } : a);
          localStorage.setItem('user_alerts', JSON.stringify(updated));
          return updated;
        });
      }
    });
  }, [rowData, userAlerts]);

  // Grid filter
  const onFilterTextChange = (e) => {
    setSearchText(e.target.value);
    gridRef.current?.api.setQuickFilter(e.target.value);
  };

  // Row click handler
  const onRowDoubleClick = async (event) => {
    const token = event.data.token;
    setChartToken(token);
    setChartTimeframe('5d'); // Default to 5 days
    await fetchChartData(token, '5d');
    setShowChart(true);
  };

  const fetchChartData = async (token, timeframe) => {
    try {
      const response = await fetch(`${getApiUrl()}/api/candles/${token}?days=${timeframe === '1d' ? 1 : timeframe === '5d' ? 5 : 30}`);
      const data = await response.json();
      setChartData(data.candles || []);
    } catch (e) {
      const err = parseError(e, 'chart data');
      addToast(err.message, err.type, err.duration);
    }
  };

  const changeChartTimeframe = (tf) => {
    setChartTimeframe(tf);
    if (chartToken) {
      fetchChartData(chartToken, tf);
    }
  };

  // Toggle overlay
  const toggleOverlay = (key) => {
    setChartOverlays(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Add custom horizontal line
  const addCustomLine = (price, color = '#2196f3', title = '') => {
    setCustomLines(prev => [...prev, { price, color, title }]);
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
    seriesRef.current = candlestickSeries;

    // Add indicator overlays
    const tokenData = rowData.find(r => r.token === chartToken);
    if (tokenData) {
      if (chartOverlays.camarilla) {
        if (tokenData.Camarilla_H4) {
          candlestickSeries.createPriceLine({
            price: tokenData.Camarilla_H4,
            color: '#f44336',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: 'H4',
          });
        }
        if (tokenData.Camarilla_L4) {
          candlestickSeries.createPriceLine({
            price: tokenData.Camarilla_L4,
            color: '#4caf50',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: 'L4',
          });
        }
      }
      if (chartOverlays.supertrend && tokenData.supertrend) {
        candlestickSeries.createPriceLine({
          price: tokenData.supertrend,
          color: '#ff9800',
          lineWidth: 1,
          lineStyle: 0,
          axisLabelVisible: true,
          title: 'ST',
        });
      }
      if (chartOverlays.vwap && tokenData.vwap) {
        candlestickSeries.createPriceLine({
          price: tokenData.vwap,
          color: '#9c27b0',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'VWAP',
        });
      }
    }

    // Add custom lines
    customLines.forEach(line => {
      candlestickSeries.createPriceLine({
        price: line.price,
        color: line.color,
        lineWidth: 1,
        lineStyle: 0,
        axisLabelVisible: true,
        title: line.title || `₹${line.price}`,
      });
    });

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
      const res = await fetch(`${getApiUrl()}/api/tokens/add?token=${token}&watchlist=${encodeURIComponent(currentWatchlist)}&user_id=${userId}`, { method: 'POST' });
      const data = await res.json();

      if (data.duplicate) {
        addToast(`${symbol} already in ${currentWatchlist}`, 'warning');
        return;
      }

      addToast(`Added ${symbol} to ${currentWatchlist}`, 'success');
      setShowAddToken(false);
      setSymbolSearchText('');
      setSymbolResults([]);

      // Update local watchlist state
      setWatchlists(prev => {
        const wl = prev[currentWatchlist] || [];
        if (!wl.includes(token)) {
          return { ...prev, [currentWatchlist]: [...wl, token] };
        }
        return prev;
      });

      // Trigger refresh via WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'subscribe', watchlist: currentWatchlist, action: 'refresh' }));
      }
    } catch (e) {
      const err = parseError(e, 'add stock');
      addToast(err.message, err.type, err.duration);
    }
  };

  // Upload CSV bulk add
  const handleUploadCSV = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const userId = getUserId();
      const response = await fetch(`${getApiUrl()}/api/tokens/upload?watchlist=${encodeURIComponent(currentWatchlist)}&user_id=${userId}`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        addToast(data.detail || 'Upload failed', 'error');
        return;
      }

      if (data.added > 0) {
        addToast(`Added ${data.added} stocks to ${currentWatchlist}`, 'success');
      }
      if (data.skipped > 0) {
        addToast(`${data.skipped} already in watchlist`, 'info');
      }
      if (data.errors > 0) {
        addToast(`${data.errors} rows had errors`, 'warning');
      }
      if (data.added === 0 && data.skipped === 0 && data.errors === 0) {
        addToast('CSV file is empty', 'warning');
      }

      // Update local watchlist state
      if (data.details?.added) {
        setWatchlists(prev => {
          const wl = prev[currentWatchlist] || [];
          const newTokens = data.details.added.map(a => a.token).filter(t => !wl.includes(t));
          return { ...prev, [currentWatchlist]: [...wl, ...newTokens] };
        });
      }

      // Trigger refresh
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'subscribe', watchlist: currentWatchlist, action: 'refresh' }));
      }
    } catch (e) {
      addToast('Failed to upload CSV', 'error');
    }

    // Reset file input
    if (csvFileRef.current) csvFileRef.current.value = '';
  };

  // Quick add group
  const handleQuickAddGroup = async (token) => {
    const userId = getUserId();
    await fetch(`${getApiUrl()}/api/tokens/add?token=${token}&watchlist=${encodeURIComponent(currentWatchlist)}&user_id=${userId}`, { method: 'POST' });
    setWatchlists(prev => {
      const wl = prev[currentWatchlist] || [];
      if (!wl.includes(token)) {
        return { ...prev, [currentWatchlist]: [...wl, token] };
      }
      return prev;
    });
  };

  // Toggle view mode
  const toggleViewMode = (mode) => {
    setViewMode(mode);
    localStorage.setItem('watchlistViewMode', mode);
  };

  // Remove token
  const handleRemoveToken = async (token) => {
    try {
      const userId = getUserId();
      await fetch(`${getApiUrl()}/api/tokens/${token}?watchlist=${encodeURIComponent(currentWatchlist)}&user_id=${userId}`, { method: 'DELETE' });
      addToast(`Removed ${token} from ${currentWatchlist}`, 'success');

      // Update local watchlist state
      setWatchlists(prev => {
        const wl = prev[currentWatchlist] || [];
        return { ...prev, [currentWatchlist]: wl.filter(t => t !== token) };
      });
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
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', watchlist: currentWatchlist, action: 'refresh' }));
      addToast('Refreshing data...', 'success');
    }
  };

  // Switch watchlist
  const handleSwitchWatchlist = (name) => {
    setCurrentWatchlist(name);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', watchlist: name, action: 'refresh' }));
    }
    addToast(`Switched to ${name}`, 'success');
  };

  // Create new watchlist
  const handleCreateWatchlist = async () => {
    const name = newWatchlistName.trim();
    if (!name) return;
    try {
      await fetch(`${getApiUrl()}/api/watchlists`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, tokens: [] })
      });
      setWatchlists(prev => ({ ...prev, [name]: [] }));
      setCurrentWatchlist(name);
      setNewWatchlistName('');
      setShowNewWatchlist(false);
      addToast(`Created watchlist "${name}"`, 'success');
    } catch (e) {
      addToast('Failed to create watchlist', 'error');
    }
  };

  // Delete watchlist
  const handleDeleteWatchlist = async (name) => {
    if (name === 'Default') return; // Can't delete Default
    try {
      await fetch(`${getApiUrl()}/api/watchlists/${name}`, { method: 'DELETE' });
      setWatchlists(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
      if (currentWatchlist === name) {
        setCurrentWatchlist('Default');
      }
      addToast(`Deleted watchlist "${name}"`, 'success');
    } catch (e) {
      addToast('Failed to delete watchlist', 'error');
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

  // Persist theme to localStorage
  useEffect(() => {
    localStorage.setItem('gt_theme', theme);
  }, [theme]);

  // Manual reconnect
  const manualReconnect = () => {
    if (reconnectRef.current.timeoutId) clearTimeout(reconnectRef.current.timeoutId);
    reconnectRef.current.attempts = 0;
    setConnectionStatus('reconnecting');
    setReconnectCountdown(0);
    connectWebSocket();
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
          <input
            type="file"
            ref={csvFileRef}
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleUploadCSV}
          />
          <button className="toolbar-btn" onClick={() => csvFileRef.current?.click()} title="Upload CSV to bulk-add stocks">
            <Upload size={16} /> Upload CSV
          </button>
          <button className="toolbar-btn" onClick={exportToCSV}>
            <Download size={16} /> Export
          </button>
          <button className="toolbar-btn" onClick={handleClearAlerts}>
            <Trash size={16} /> Clear
          </button>
        </div>

        <div className="toolbar-group">
          <select
            className="watchlist-select"
            value={currentWatchlist}
            onChange={(e) => handleSwitchWatchlist(e.target.value)}
          >
            {Object.keys(watchlists).map(name => (
              <option key={name} value={name}>{name} ({watchlists[name]?.length || 0})</option>
            ))}
          </select>
          <button className="toolbar-btn" onClick={() => setShowNewWatchlist(true)} title="New watchlist">
            <Plus size={16} />
          </button>
          {currentWatchlist !== 'Default' && (
            <button className="toolbar-btn" onClick={() => handleDeleteWatchlist(currentWatchlist)} title="Delete watchlist">
              <Trash size={16} />
            </button>
          )}
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
            className={`toolbar-btn ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => toggleViewMode('table')}
            title="Table view"
          >
            <LayoutList size={16} />
          </button>
          <button
            className={`toolbar-btn ${viewMode === 'cards' ? 'active' : ''}`}
            onClick={() => toggleViewMode('cards')}
            title="Card view"
          >
            <LayoutGrid size={16} />
          </button>
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
        <button
          className={`sheet-tab ${activeSheet === 'heatmap' ? 'active' : ''}`}
          onClick={() => setActiveSheet('heatmap')}
        >
          Heat Map
        </button>
        <button
          className={`sheet-tab ${activeSheet === 'portfolio' ? 'active' : ''}`}
          onClick={() => setActiveSheet('portfolio')}
        >
          Portfolio
        </button>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Live Data Sheet */}
        <div className={`sheet-view ${activeSheet === 'live' ? 'active' : ''}`}>
          {dataLoading ? (
            <div className="ag-theme-alpine-dark grid-container">
              <div className="skeleton-container">
                {Array(8).fill().map((_, i) => (
                  <div key={i} className="skeleton-row">
                    {Array(10).fill().map((_, j) => (
                      <div key={j} className="skeleton-cell" style={{ animationDelay: `${(i * 10 + j) * 0.03}s` }}></div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ) : rowData.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📊</div>
              <h3 className="empty-title">Your watchlist is empty</h3>
              <p className="empty-desc">Add stocks to start tracking real-time prices, indicators, and alerts</p>

              <QuickAddGroups
                onAddGroup={handleQuickAddGroup}
                currentTokens={rowData.map(r => r.token)}
              />

              <div className="empty-search-wrapper">
                <TokenSearch
                  onSelect={handleAddToken}
                  apiUrl={getApiUrl()}
                  existingTokens={rowData.map(r => r.token)}
                />
              </div>

              <p className="empty-hint">Tip: Click the + Add button, search by name, or upload a CSV</p>
            </div>
          ) : viewMode === 'cards' ? (
            <div className="cards-view-container">
              <div className="cards-search-bar">
                <TokenSearch
                  onSelect={handleAddToken}
                  apiUrl={getApiUrl()}
                  existingTokens={rowData.map(r => r.token)}
                />
              </div>
              <WatchlistCards
                watchlist={rowData}
                onRemove={handleRemoveToken}
                onSelect={(stock) => {
                  setChartToken(stock.token);
                  setShowChart(true);
                }}
              />
            </div>
          ) : (
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
          )}
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
          {/* User Alerts Section */}
          <div style={{ marginBottom: '16px', padding: '12px', background: 'var(--card-bg, #1e1e1e)', borderRadius: '8px', border: '1px solid var(--border, #333)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '14px' }}>My Price Alerts</h3>
              <button className="toolbar-btn primary" onClick={() => setShowCreateAlert(true)} style={{ padding: '6px 12px', fontSize: '12px' }}>
                + Create Alert
              </button>
            </div>
            {userAlerts.length === 0 ? (
              <p style={{ color: '#888', margin: 0, fontSize: '13px' }}>No custom alerts. Create one to get notified when a stock crosses a price level.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {userAlerts.map(alert => (
                  <div key={alert.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '8px 12px', background: alert.triggered ? 'rgba(255,152,0,0.1)' : 'transparent',
                    border: '1px solid var(--border, #333)', borderRadius: '6px',
                    opacity: alert.triggered ? 0.7 : 1
                  }}>
                    <div>
                      <span style={{ fontWeight: 'bold' }}>{alert.symbol}</span>
                      <span style={{ color: '#888', marginLeft: '8px' }}>
                        {alert.condition === 'above' ? '≥' : '≤'} ₹{alert.price.toFixed(2)}
                      </span>
                      {alert.triggered && <span style={{ color: '#ffa500', marginLeft: '8px', fontSize: '11px' }}>TRIGGERED</span>}
                    </div>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {alert.triggered && (
                        <button className="toolbar-btn" onClick={() => toggleUserAlert(alert.id)} style={{ padding: '4px 8px', fontSize: '11px' }}>
                          Reset
                        </button>
                      )}
                      <button className="toolbar-btn" onClick={() => deleteUserAlert(alert.id)} style={{ padding: '4px 8px', fontSize: '11px', color: '#f44336' }}>
                        ×
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

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

        {/* Heat Map Sheet */}
        <div className={`sheet-view ${activeSheet === 'heatmap' ? 'active' : ''}`}>
          <div className="heatmap-container">
            <h3 style={{ marginBottom: '16px' }}>Indicator Heat Map</h3>
            <div className="heatmap-legend">
              <span className="legend-item"><span className="legend-color" style={{ background: '#4caf50' }}></span> Oversold / Low</span>
              <span className="legend-item"><span className="legend-color" style={{ background: '#fff' }}></span> Neutral</span>
              <span className="legend-item"><span className="legend-color" style={{ background: '#f44336' }}></span> Overbought / High</span>
            </div>
            <div className="heatmap-grid" style={{ overflowX: 'auto' }}>
              {/* Header row */}
              <div className="heatmap-row heatmap-header">
                <div className="heatmap-cell heatmap-label" title="Stock symbol">Stock</div>
                <div className="heatmap-cell" title="RSI (14): >70 overbought, <30 oversold">RSI</div>
                <div className="heatmap-cell" title="Last Traded Price">LTP</div>
                <div className="heatmap-cell" title="Price change percentage">Change%</div>
                <div className="heatmap-cell" title="Volume / SMA(8) ratio: >2x indicates spike">Vol/SMA8</div>
                <div className="heatmap-cell" title="Supertrend signal: BUY (bullish) or SELL (bearish)">Supertrend</div>
                <div className="heatmap-cell" title="Camarilla H4: Strong resistance level">H4</div>
                <div className="heatmap-cell" title="Camarilla H3: Resistance level">H3</div>
                <div className="heatmap-cell" title="Camarilla L3: Support level">L3</div>
                <div className="heatmap-cell" title="Camarilla L4: Strong support level">L4</div>
              </div>
              {/* Data rows */}
              {rowData.map(item => {
                const rsi = item.rsi14 || 50;
                const change = item.change_percent || 0;
                const volRatio = item.volume_sma8 ? (item.volume / item.volume_sma8) : 1;

                const rsiColor = rsi > 70 ? `rgba(244,67,54,${(rsi - 70) / 30})` :
                                 rsi < 30 ? `rgba(76,175,80,${(30 - rsi) / 30})` :
                                 'transparent';
                const changeColor = change > 0 ? `rgba(76,175,80,${Math.min(Math.abs(change) / 5, 1)})` :
                                    change < 0 ? `rgba(244,67,54,${Math.min(Math.abs(change) / 5, 1)})` :
                                    'transparent';
                const volColor = volRatio > 2 ? `rgba(255,152,0,${Math.min((volRatio - 1) / 4, 1)})` :
                                 'transparent';
                const stColor = item.supertrend_signal === 'BUY' ? 'rgba(76,175,80,0.3)' :
                                item.supertrend_signal === 'SELL' ? 'rgba(244,67,54,0.3)' :
                                'transparent';

                // Camarilla proximity colors (closer to level = stronger color)
                const ltp = item.ltp || 0;
                const camarillaH4 = item.Camarilla_H4 || 0;
                const camarillaH3 = item.Camarilla_H3 || 0;
                const camarillaL3 = item.Camarilla_L3 || 0;
                const camarillaL4 = item.Camarilla_L4 || 0;

                const getProximityColor = (level) => {
                  if (!level || !ltp) return 'transparent';
                  const pct = Math.abs((ltp - level) / ltp) * 100;
                  if (pct < 0.5) return 'rgba(244,67,54,0.6)'; // Very close - strong red
                  if (pct < 1) return 'rgba(244,67,54,0.3)';   // Close - light red
                  return 'transparent';
                };

                return (
                  <div key={item.token} className="heatmap-row">
                    <div className="heatmap-cell heatmap-label">{item.symbol}</div>
                    <div className="heatmap-cell" style={{ background: rsiColor }} title={`RSI: ${rsi.toFixed(1)}`}>{rsi.toFixed(0)}</div>
                    <div className="heatmap-cell" title={`LTP: ₹${ltp?.toFixed(2)}`}>₹{ltp?.toFixed(2)}</div>
                    <div className="heatmap-cell" style={{ background: changeColor }} title={`Change: ${change > 0 ? '+' : ''}${change.toFixed(2)}%`}>{change > 0 ? '+' : ''}{change.toFixed(2)}%</div>
                    <div className="heatmap-cell" style={{ background: volColor }} title={`Vol/SMA8: ${volRatio.toFixed(2)}x`}>{volRatio.toFixed(1)}x</div>
                    <div className="heatmap-cell" style={{ background: stColor }} title={`Supertrend: ${item.supertrend_signal || 'N/A'}`}>{item.supertrend_signal || '-'}</div>
                    <div className="heatmap-cell" style={{ background: getProximityColor(camarillaH4) }} title={`H4 (Strong Resistance): ₹${camarillaH4?.toFixed(2)}`}>{camarillaH4 ? `₹${camarillaH4.toFixed(0)}` : '-'}</div>
                    <div className="heatmap-cell" style={{ background: getProximityColor(camarillaH3) }} title={`H3 (Resistance): ₹${camarillaH3?.toFixed(2)}`}>{camarillaH3 ? `₹${camarillaH3.toFixed(0)}` : '-'}</div>
                    <div className="heatmap-cell" style={{ background: getProximityColor(camarillaL3) }} title={`L3 (Support): ₹${camarillaL3?.toFixed(2)}`}>{camarillaL3 ? `₹${camarillaL3.toFixed(0)}` : '-'}</div>
                    <div className="heatmap-cell" style={{ background: getProximityColor(camarillaL4) }} title={`L4 (Strong Support): ₹${camarillaL4?.toFixed(2)}`}>{camarillaL4 ? `₹${camarillaL4.toFixed(0)}` : '-'}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Portfolio Sheet */}
        <div className={`sheet-view ${activeSheet === 'portfolio' ? 'active' : ''}`}>
          <div className="portfolio-container">
            {/* Summary Cards */}
            <div className="portfolio-summary">
              <div className="summary-card">
                <div className="summary-label">Invested</div>
                <div className="summary-value">₹{portfolioSummary.total_invested?.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Current</div>
                <div className="summary-value">₹{portfolioSummary.total_current?.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">P&L</div>
                <div className={`summary-value ${portfolioSummary.total_pnl >= 0 ? 'profit' : 'loss'}`}>
                  {portfolioSummary.total_pnl >= 0 ? '+' : ''}₹{portfolioSummary.total_pnl?.toLocaleString()}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Returns</div>
                <div className={`summary-value ${portfolioSummary.total_pnl_percent >= 0 ? 'profit' : 'loss'}`}>
                  {portfolioSummary.total_pnl_percent >= 0 ? '+' : ''}{portfolioSummary.total_pnl_percent?.toFixed(2)}%
                </div>
              </div>
            </div>

            {/* Add Holding Button */}
            <div style={{ marginBottom: '12px', display: 'flex', gap: '8px' }}>
              <button className="toolbar-btn primary" onClick={() => setShowAddHolding(true)}>
                <Plus size={16} /> Add Holding
              </button>
              <button className="toolbar-btn" onClick={() => { fetchTrades(); }}>
                <RefreshCw size={16} /> Refresh Trades
              </button>
            </div>

            {/* Holdings Table */}
            <div className="portfolio-table-container">
              <table className="portfolio-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Avg Price</th>
                    <th>LTP</th>
                    <th>Current Value</th>
                    <th>P&L</th>
                    <th>P&L %</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.length === 0 ? (
                    <tr><td colSpan="8" style={{ textAlign: 'center', color: '#888' }}>No holdings yet. Add your first stock!</td></tr>
                  ) : (
                    portfolio.map(h => (
                      <tr key={h.token}>
                        <td className="symbol-cell">{h.symbol}</td>
                        <td>{h.quantity}</td>
                        <td>₹{h.buy_price?.toFixed(2)}</td>
                        <td>₹{h.current_price?.toFixed(2)}</td>
                        <td>₹{h.current_value?.toLocaleString()}</td>
                        <td className={h.pnl >= 0 ? 'profit' : 'loss'}>
                          {h.pnl >= 0 ? '+' : ''}₹{h.pnl?.toLocaleString()}
                        </td>
                        <td className={h.pnl_percent >= 0 ? 'profit' : 'loss'}>
                          {h.pnl_percent >= 0 ? '+' : ''}{h.pnl_percent?.toFixed(2)}%
                        </td>
                        <td>
                          <button className="remove-btn" onClick={() => handleRemoveHolding(h.token)}>Sell</button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Trade History */}
            <h3 style={{ margin: '24px 0 12px', color: 'var(--text-color)' }}>Trade History</h3>
            <div className="portfolio-table-container">
              <table className="portfolio-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Value</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.length === 0 ? (
                    <tr><td colSpan="6" style={{ textAlign: 'center', color: '#888' }}>No trades yet</td></tr>
                  ) : (
                    trades.slice().reverse().map((t, idx) => (
                      <tr key={idx}>
                        <td>
                          <span className={t.type === 'BUY' ? 'profit' : 'loss'} style={{ fontWeight: 600 }}>
                            {t.type}
                          </span>
                        </td>
                        <td>{t.symbol || t.token}</td>
                        <td>{t.quantity}</td>
                        <td>₹{t.price?.toFixed(2)}</td>
                        <td>₹{(t.quantity * t.price)?.toLocaleString()}</td>
                        <td style={{ fontSize: '11px', color: '#888' }}>
                          {t.timestamp ? new Date(t.timestamp).toLocaleString() : '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Navigation (mobile only) */}
      <div className="bottom-nav">
        <button className={`bottom-nav-item ${activeSheet === 'live' ? 'active' : ''}`} onClick={() => setActiveSheet('live')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
          Live
        </button>
        <button className={`bottom-nav-item ${activeSheet === 'alerts' ? 'active' : ''}`} onClick={() => setActiveSheet('alerts')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          Alerts
        </button>
        <button className={`bottom-nav-item ${activeSheet === 'portfolio' ? 'active' : ''}`} onClick={() => setActiveSheet('portfolio')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3h-8l-2 4h12z"/></svg>
          Portfolio
        </button>
        <button className={`bottom-nav-item ${activeSheet === 'heatmap' ? 'active' : ''}`} onClick={() => setActiveSheet('heatmap')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          Heatmap
        </button>
        <button className={`bottom-nav-item ${activeSheet === 'historical' ? 'active' : ''}`} onClick={() => setActiveSheet('historical')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Charts
        </button>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <div className="status-item">
          <span className={`status-dot ${connectionStatus === 'connected' ? '' : connectionStatus === 'reconnecting' ? 'reconnecting' : 'disconnected'}`}></span>
          {connectionStatus === 'connected' && 'Connected'}
          {connectionStatus === 'reconnecting' && (
            <>
              Reconnecting{reconnectCountdown > 0 ? ` in ${reconnectCountdown}s` : '...'}
              <button className="toolbar-btn-sm" onClick={manualReconnect} style={{ marginLeft: 8, padding: '2px 8px', fontSize: '11px' }}>
                Retry Now
              </button>
            </>
          )}
          {connectionStatus === 'disconnected' && 'Disconnected'}
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

      {/* New Watchlist Modal */}
      {showNewWatchlist && (
        <div className="modal-overlay" onClick={() => setShowNewWatchlist(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Create New Watchlist</h3>
            <input
              type="text"
              className="modal-input"
              placeholder="Watchlist name (e.g., NIFTY50, BANKNIFTY)"
              value={newWatchlistName}
              onChange={e => setNewWatchlistName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateWatchlist()}
              autoFocus
            />
            <div className="modal-actions">
              <button className="toolbar-btn primary" onClick={handleCreateWatchlist}>Create</button>
              <button className="toolbar-btn" onClick={() => { setShowNewWatchlist(false); setNewWatchlistName(''); }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Holding Modal */}
      {showAddHolding && (
        <div className="modal-overlay" onClick={() => setShowAddHolding(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Add to Portfolio</h3>
            <div className="modal-form">
              <div className="form-group">
                <label>Token</label>
                <input
                  type="text"
                  className="modal-input"
                  placeholder="e.g., 2885"
                  value={newHolding.token}
                  onChange={e => setNewHolding({ ...newHolding, token: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Symbol</label>
                <input
                  type="text"
                  className="modal-input"
                  placeholder="e.g., RELIANCE"
                  value={newHolding.symbol}
                  onChange={e => setNewHolding({ ...newHolding, symbol: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  className="modal-input"
                  placeholder="e.g., 10"
                  value={newHolding.quantity}
                  onChange={e => setNewHolding({ ...newHolding, quantity: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Buy Price (₹)</label>
                <input
                  type="number"
                  className="modal-input"
                  placeholder="e.g., 2500.50"
                  value={newHolding.buy_price}
                  onChange={e => setNewHolding({ ...newHolding, buy_price: e.target.value })}
                />
              </div>
            </div>
            <div className="modal-actions">
              <button className="toolbar-btn primary" onClick={handleAddHolding}>Add</button>
              <button className="toolbar-btn" onClick={() => setShowAddHolding(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Alert Modal */}
      {showCreateAlert && (
        <div className="modal-overlay" onClick={() => setShowCreateAlert(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Create Price Alert</h3>
            <div className="modal-form">
              <div className="form-group">
                <label>Stock</label>
                <select
                  className="modal-input"
                  value={newAlert.token}
                  onChange={e => {
                    const token = e.target.value;
                    const stock = rowData.find(d => d.token === token);
                    setNewAlert({ ...newAlert, token, symbol: stock?.symbol || '' });
                  }}
                >
                  <option value="">Select a stock...</option>
                  {rowData.map(item => (
                    <option key={item.token} value={item.token}>{item.symbol} (₹{item.ltp?.toFixed(2)})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Condition</label>
                <select
                  className="modal-input"
                  value={newAlert.condition}
                  onChange={e => setNewAlert({ ...newAlert, condition: e.target.value })}
                >
                  <option value="above">Price goes above</option>
                  <option value="below">Price goes below</option>
                </select>
              </div>
              <div className="form-group">
                <label>Target Price (₹)</label>
                <input
                  type="number"
                  className="modal-input"
                  placeholder="e.g., 2500.00"
                  value={newAlert.price}
                  onChange={e => setNewAlert({ ...newAlert, price: e.target.value })}
                />
              </div>
            </div>
            <div className="modal-actions">
              <button className="toolbar-btn primary" onClick={createUserAlert}>Create Alert</button>
              <button className="toolbar-btn" onClick={() => setShowCreateAlert(false)}>Cancel</button>
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
              <div className="chart-tools">
                {/* Timeframe selector */}
                <div className="timeframe-selector" style={{ display: 'flex', gap: '4px', marginRight: '8px' }}>
                  <button
                    className={`chart-tool-btn ${chartTimeframe === '1d' ? 'active' : ''}`}
                    onClick={() => changeChartTimeframe('1d')}
                    title="1 Day"
                  >1D</button>
                  <button
                    className={`chart-tool-btn ${chartTimeframe === '5d' ? 'active' : ''}`}
                    onClick={() => changeChartTimeframe('5d')}
                    title="5 Days"
                  >5D</button>
                  <button
                    className={`chart-tool-btn ${chartTimeframe === '1mo' ? 'active' : ''}`}
                    onClick={() => changeChartTimeframe('1mo')}
                    title="1 Month"
                  >1M</button>
                </div>
                <span style={{ borderLeft: '1px solid #555', margin: '0 4px', height: '20px' }}></span>
                <button
                  className={`chart-tool-btn ${chartOverlays.camarilla ? 'active' : ''}`}
                  onClick={() => toggleOverlay('camarilla')}
                  title="Toggle Camarilla H4/L4"
                >H4/L4</button>
                <button
                  className={`chart-tool-btn ${chartOverlays.supertrend ? 'active' : ''}`}
                  onClick={() => toggleOverlay('supertrend')}
                  title="Toggle Supertrend"
                >ST</button>
                <button
                  className={`chart-tool-btn ${chartOverlays.vwap ? 'active' : ''}`}
                  onClick={() => toggleOverlay('vwap')}
                  title="Toggle VWAP"
                >VWAP</button>
                <span style={{ borderLeft: '1px solid #555', margin: '0 4px', height: '20px' }}></span>
                <input
                  type="number"
                  className="chart-line-input"
                  placeholder="Price..."
                  value={customLinePrice}
                  onChange={e => setCustomLinePrice(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && customLinePrice && !isNaN(parseFloat(customLinePrice))) {
                      addCustomLine(parseFloat(customLinePrice), '#2196f3', '');
                      setCustomLinePrice('');
                    }
                  }}
                  style={{ width: '80px', padding: '4px 6px', fontSize: '12px', background: '#333', color: '#fff', border: '1px solid #555', borderRadius: '4px' }}
                />
                <button
                  className="chart-tool-btn"
                  onClick={() => {
                    if (customLinePrice && !isNaN(parseFloat(customLinePrice))) {
                      addCustomLine(parseFloat(customLinePrice), '#2196f3', '');
                      setCustomLinePrice('');
                    }
                  }}
                  title="Add horizontal line at price"
                >+Line</button>
                {customLines.length > 0 && (
                  <button
                    className="chart-tool-btn"
                    onClick={() => setCustomLines([])}
                    title="Clear all custom lines"
                  >Clear</button>
                )}
              </div>
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
