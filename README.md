# Trading Decision Support System

A Flask-based trading dashboard that extracts institutional price zones from completed Fetch Days and alerts in real-time on Execute Day when price revisits those zones.

## Philosophy

**Fetch Day = Intent**  
**Decode Day = Selection**  
**Execute Day = Reaction**

Zones represent where institutions care. Price comes to you — you don't chase.

## Core Concepts

### Fetch Day (Historical)
- Completed trading day used ONLY for zone detection
- Zones are extracted once and stored immutably
- NO recalculation ever

### Decode Day (Selection)
- Provide stock list with reference to Fetch Day
- NO zone creation, NO indicators
- Pure selection phase

### Execute Day (Live Monitoring)
- Monitor live prices against Fetch Day zones
- Alert when price approaches or enters zones
- NO strategy logic, NO auto-trading

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Kite API:
```bash
cp .env.example .env
# Edit .env with your Kite credentials
```

3. Initialize database:
```bash
python -c "from database.db_manager import DatabaseManager; DatabaseManager('trading_zones.db')"
```

## Usage

### 1. Process Fetch Day (Extract Zones)

```python
from api.kite_client import KiteClient
from database.db_manager import DatabaseManager
from core.fetch_day import FetchDayProcessor
import config

# Initialize
kite = KiteClient(config.Config.KITE_API_KEY, config.Config.KITE_ACCESS_TOKEN)
db = DatabaseManager(config.Config.DATABASE_PATH)
processor = FetchDayProcessor(kite, db)

# Process Fetch Day for stocks
symbols = ['HINDZINC', 'TATASTEEL', 'RELIANCE']
fetch_date = '2026-01-28'  # Completed trading day

results = processor.process_multiple_stocks(symbols, fetch_date)
```

### 2. Add Decode List

```python
# Add stocks to Decode Day list
decode_date = '2026-01-29'
db.add_decode_list(decode_date, symbols, fetch_date)
```

### 3. Run Execute Day Monitor

```bash
python app.py
```

Open browser: `http://localhost:5000`

The dashboard will:
- Show all stocks from Decode Day list
- Display live prices (LTP)
- Highlight stocks near/inside zones:
  - 🟢 Green = Inside bullish zone
  - 🔴 Red = Inside bearish zone
  - 🟡 Yellow = Near zone
  - ⚪ White = Away from zones

## API Endpoints

### POST /api/process-fetch-day
Process Fetch Day and extract zones.

```json
{
  "symbols": ["HINDZINC", "TATASTEEL"],
  "fetch_date": "2026-01-28"
}
```

### POST /api/add-decode-list
Add stocks to Decode Day list.

```json
{
  "decode_date": "2026-01-29",
  "symbols": ["HINDZINC", "TATASTEEL"],
  "fetch_date": "2026-01-28"
}
```

### GET /api/execute-day-monitor
Get live monitoring data.

Query params: `decode_date` (optional, defaults to today)

### GET /api/alerts
Get only stocks requiring attention (near/inside zones).

## Configuration

Edit `config.py`:

```python
TIMEFRAME = '15minute'  # 5minute, 10minute, 15minute
ATR_MULTIPLIER = 1.5    # Impulse detection threshold
ZONE_CANDLES_MIN = 2    # Min candles in zone
ZONE_CANDLES_MAX = 6    # Max candles in zone
NEAR_ZONE_PERCENT = 0.5 # Proximity threshold (%)
```

## What This System Does NOT Do

❌ No RSI / MACD / EMA  
❌ No zone recalculation on Execute Day  
❌ No candle prediction  
❌ No ML / LSTM  
❌ No trade execution  
❌ No auto-trading

This is a **decision-elbow**, not a robot.

## Zone Detection Logic

1. **Calculate ATR** for volatility context
2. **Find Major Impulse**: Largest directional move of Fetch Day
3. **Identify Origin Zone**: Last balanced range before impulse
4. **Validate Zone**: Ensure price moved away significantly
5. **Store Immutably**: Save to database, never recalculate

## Database Schema

### zones
- Immutable Fetch Day zones
- Fields: symbol, fetch_date, zone_type, zone_low, zone_high, impulse_strength

### decode_lists
- Decode Day stock selections
- Fields: decode_date, symbol, fetch_date

## Next Steps (Future)

- WebSocket integration for real-time updates
- Chart visualization (TradingView integration)
- Order placement interface (manual confirmation)
- Multi-timeframe zone analysis
- Zone strength scoring

## License

MIT
