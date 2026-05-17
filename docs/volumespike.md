# Volume Spike Detection — Formula & Approach

> How the GT Trading Companion detects abnormal volume activity in real-time.

---

## Overview

The system uses **two independent volume alert types**:

| Alert | What it detects | Lookback | Threshold |
|-------|----------------|----------|-----------|
| **Volume Spike** | Current volume vs 20-period average | 20 candles (5m) | 2.5x |
| **Volume SMA8** | Current volume vs 8-period SMA | 8 candles (5m) | 1.5x |

Both run on every poll cycle (5s during market hours) for every token in the watchlist.

---

## 1. Volume Spike (Primary)

### Formula

```
avg_volume = SMA(volume, 20)    // 20-period simple moving average of volume
volume_ratio = current_volume / avg_volume

TRIGGER IF: volume_ratio > 2.5
```

### Implementation (indicators/calculator.py:98-101)

```python
# Average volume (20-period SMA)
if len(volumes) >= 20:
    result["avg_volume"] = int(sum(volumes[-20:]) / 20)
else:
    result["avg_volume"] = 0  # Skip alerts when insufficient data
```

### Alert Check (web_dashboard/backend/main.py:210-214)

```python
avg_vol = row.get("avg_volume", 0)
volume_spike_threshold = config.ALERT_THRESHOLDS.get('volume_spike', 2.5)
if avg_vol > 0 and vol > avg_vol * volume_spike_threshold:
    categories["volume_spike"] = True
```

### Key Details
- **Data source:** 5-minute candles from Yahoo Finance
- **Lookback:** Last 20 candles (~100 minutes of trading)
- **Threshold:** Configurable via `config.ALERT_THRESHOLDS['volume_spike']` (default: 2.5)
- **Guard:** Alert is skipped if `avg_volume == 0` (insufficient data, < 20 candles)
- **Severity:** HIGH if ratio > 5x, MEDIUM otherwise (alerts.py:50)

---

## 2. Volume SMA8 (Secondary)

### Formula

```
volume_sma8 = SMA(volume, 8)    // 8-period simple moving average of volume

TRIGGER IF: current_volume > volume_sma8 * 1.5
```

### Implementation (indicators/calculator.py:58-59)

```python
if len(volumes) >= 8:
    result["volume_sma8"] = int(sum(volumes[-8:]) / 8)
```

### Alert Check (web_dashboard/backend/main.py:217-219)

```python
vol_sma8 = row.get("volume_sma8", 0)
if vol_sma8 > 0 and vol > vol_sma8 * 1.5:
    categories["volume_sma8"] = True
```

### Key Details
- **Lookback:** Last 8 candles (~40 minutes of trading)
- **Threshold:** 1.5x the 8-period SMA
- **Purpose:** Catches shorter-term volume surges that the 20-period average might miss

---

## Alert Deduplication

Both alert types use a **cooldown system** to prevent spam:

```
Cooldown: 300 seconds (5 minutes) per token per alert type
Key format: "TOKEN:ALERT_TYPE" (e.g., "RELIANCE.NS:volume_spike")
```

### Implementation (web_dashboard/backend/main.py:126-127)

```python
self.alert_cooldown: Dict[str, float] = {}  # "token:alert_type" -> last_trigger_time
self.alert_cooldown_seconds: int = 300
```

Once an alert fires for a token, the same alert type won't fire again for that token within 5 minutes — even if volume continues to spike.

---

## Data Flow

```
Yahoo Finance (5m candles)
        │
        ▼
  poll_data() ──── every 5s during market hours
        │
        ▼
  calculate_all_indicators()
        │
        ├── avg_volume  = SMA(volumes[-20:])
        └── volume_sma8 = SMA(volumes[-8:])
        │
        ▼
  get_alert_categories()
        │
        ├── vol > avg_volume * 2.5  →  volume_spike = True
        └── vol > volume_sma8 * 1.5 →  volume_sma8 = True
        │
        ▼
  WebSocket broadcast → Frontend alert panel
```

---

## Configuration

All thresholds are in `config/settings.py`:

```python
ALERT_THRESHOLDS = {
    'volume_spike': 2.5,      # 2.5x average volume
    'price_jump': 3.0,        # 3% price jump
    'rsi_oversold': 30,
    'rsi_overbought': 70,
}
```

To change the volume spike sensitivity, modify `volume_spike`:
- **2.0** = more sensitive (more alerts)
- **3.0** = less sensitive (fewer alerts)
- **2.5** = default (balanced)

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| < 20 candles available | `avg_volume = 0`, volume spike alert skipped |
| `avg_volume = 0` | Alert skipped (guard clause) |
| Volume exactly at threshold | Not triggered (strict `>` comparison) |
| Token on cooldown | Alert suppressed for 5 min, logged at INFO level |
| Market closed | Adaptive polling slows to 30s, alerts still check on cached data |

---

## Testing

Unit tests in `tests/test_dashboard.py`:

- `test_volume_spike` — volume 3x avg triggers alert
- `test_volume_spike_no_avg` — no alert when avg_volume = 0
- `test_volume_spike_threshold` — volume below threshold doesn't trigger
- `test_alert_cooldown` — same alert suppressed within 5 min window
