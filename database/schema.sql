-- Zones table: immutable Fetch Day zones
CREATE TABLE IF NOT EXISTS zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    fetch_date TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    zone_type TEXT NOT NULL,
    zone_low REAL NOT NULL,
    zone_high REAL NOT NULL,
    impulse_strength TEXT,
    impulse_start_time TEXT,
    impulse_end_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, fetch_date, timeframe, zone_low, zone_high)
);

-- Decode day stock lists
CREATE TABLE IF NOT EXISTS decode_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decode_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    fetch_date TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(decode_date, symbol)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_zones_symbol_date ON zones(symbol, fetch_date);
CREATE INDEX IF NOT EXISTS idx_decode_date ON decode_lists(decode_date);

-- Watchlists: Save stock lists with zones for quick loading
CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    execute_day TEXT NOT NULL,
    fetch_day TEXT NOT NULL,
    symbols TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watchlist_name ON watchlists(name);
