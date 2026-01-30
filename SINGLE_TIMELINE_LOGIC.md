# Single Timeline Engine - How It Works

## Core Principle
**ONE EXECUTE DAY = ONE TIMELINE**

The entire system behaves as if the selected Execute Day is "today". No mixing of dates, no confusion.

## Visual Display

### Header (Always Visible)
```
Mode: LIVE or REPLAY
Execute Day: 2026-01-29
Fetch Day: 2026-01-27
Alerts: 3
```

### Banner
```
📅 Single Timeline: Execute Day = 2026-01-29 | Fetch Day = 2026-01-27
```

## Date Logic

### When You Select Execute Day = 2026-01-29
1. System sets: `ACTIVE_EXECUTE_DAY = 2026-01-29`
2. System calculates: `ACTIVE_FETCH_DAY = 2026-01-27` (2 trading days back)
3. System determines mode:
   - If Execute Day = Today → **LIVE MODE** (green)
   - If Execute Day ≠ Today → **REPLAY MODE** (orange)

### Example 1: LIVE MODE
```
Today = 2026-01-29
You select Execute Day = 2026-01-29
→ Mode: LIVE
→ Fetch Day: 2026-01-27
→ Zones loaded from Jan 27
→ Prices are live LTP
```

### Example 2: REPLAY MODE
```
Today = 2026-01-29
You select Execute Day = 2026-01-21
→ Mode: REPLAY
→ Fetch Day: 2026-01-19
→ Zones loaded from Jan 19
→ Prices are historical close from Jan 21
```

## What Happens When You Add Stocks

### Step 1: Enter Stocks
```
Input: HINDZINC, TATASTEEL, RELIANCE
```

### Step 2: System Processes
1. Uses `ACTIVE_EXECUTE_DAY` (from date picker)
2. Calculates `ACTIVE_FETCH_DAY` automatically
3. Fetches historical OHLC from Fetch Day
4. Extracts zones (if not already in database)
5. Saves zones permanently

### Step 3: System Monitors
1. Gets price for Execute Day:
   - LIVE MODE → Current LTP
   - REPLAY MODE → Historical close
2. Compares price to zones
3. Calculates distance and reaction
4. Updates table

## Table Display

| Symbol | LTP | Zone Type | Zone Range | Distance | Reaction | Status |
|--------|-----|-----------|------------|----------|----------|--------|
| HINDZINC | ₹715.20 | BULLISH | 708–712 | +0.4% | Holding | 🟢 |

**All rows use the SAME Execute Day and Fetch Day** - no mixing!

## Timeline Changes

When you change the Execute Day picker:
1. System clears current stocks
2. Recalculates Fetch Day
3. Updates mode (LIVE/REPLAY)
4. Waits for you to add stocks again

This ensures **no date confusion** - one timeline at a time.

## Key Rules

✅ **DO:**
- Show only ACTIVE_EXECUTE_DAY and ACTIVE_FETCH_DAY
- Use same dates for all rows
- Calculate Fetch Day automatically
- Support both LIVE and REPLAY modes

❌ **DON'T:**
- Show system date/time
- Mix different execute days per row
- Allow manual Fetch Day input
- Access future data

## Verification

To verify which dates are being used:
1. Look at header: Shows Execute Day and Fetch Day
2. Look at banner: Confirms single timeline
3. Look at mode: LIVE (today) or REPLAY (historical)

**Example:**
```
Mode: REPLAY
Execute Day: 2026-01-28
Fetch Day: 2026-01-26

This means:
- All zones are from Jan 26
- All prices are from Jan 28
- System is in historical replay mode
```
