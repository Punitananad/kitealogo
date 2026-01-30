import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema"""
        with open('database/schema.sql', 'r') as f:
            schema = f.read()
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript(schema)
        conn.commit()
        conn.close()
    
    def save_zone(self, zone_data: Dict) -> bool:
        """Save a zone from Fetch Day (immutable)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO zones 
                (symbol, fetch_date, timeframe, zone_type, zone_low, zone_high, 
                 impulse_strength, impulse_start_time, impulse_end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                zone_data['symbol'],
                zone_data['fetch_date'],
                zone_data['timeframe'],
                zone_data['zone_type'],
                zone_data['zone_low'],
                zone_data['zone_high'],
                zone_data.get('impulse_strength', 'MEDIUM'),
                zone_data.get('impulse_start_time', None),
                zone_data.get('impulse_end_time', None)
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error saving zone: {e}")
            return False
        finally:
            conn.close()
    
    def get_zones_for_symbol(self, symbol: str, fetch_date: str) -> List[Dict]:
        """Retrieve zones for a symbol from specific Fetch Day"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM zones 
            WHERE symbol = ? AND fetch_date = ?
            ORDER BY zone_type, zone_low
        ''', (symbol, fetch_date))
        
        zones = []
        for row in cursor.fetchall():
            zone = dict(row)
            # Convert to native Python types for JSON serialization
            zone['id'] = int(zone['id']) if zone['id'] else None
            zone['zone_low'] = float(zone['zone_low'])
            zone['zone_high'] = float(zone['zone_high'])
            zones.append(zone)
        
        conn.close()
        return zones
    
    def add_decode_list(self, decode_date: str, symbols: List[str], fetch_date: str):
        """Add stocks to Decode Day list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for symbol in symbols:
            cursor.execute('''
                INSERT OR IGNORE INTO decode_lists (decode_date, symbol, fetch_date)
                VALUES (?, ?, ?)
            ''', (decode_date, symbol, fetch_date))
        
        conn.commit()
        conn.close()
    
    def update_zone(self, symbol: str, fetch_date: str, zone_data: Dict) -> bool:
        """Update or replace a zone for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete existing zones
            cursor.execute('''
                DELETE FROM zones WHERE symbol = ? AND fetch_date = ?
            ''', (symbol, fetch_date))
            
            # Insert new zone
            cursor.execute('''
                INSERT INTO zones 
                (symbol, fetch_date, timeframe, zone_type, zone_low, zone_high, 
                 impulse_strength, impulse_start_time, impulse_end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                zone_data['symbol'],
                zone_data['fetch_date'],
                zone_data['timeframe'],
                zone_data['zone_type'],
                zone_data['zone_low'],
                zone_data['zone_high'],
                zone_data.get('impulse_strength', 'MANUAL'),
                zone_data.get('impulse_start_time', None),
                zone_data.get('impulse_end_time', None)
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating zone: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
        """Get stocks for Execute Day monitoring"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, fetch_date FROM decode_lists
            WHERE decode_date = ?
        ''', (decode_date,))
        
        stocks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return stocks
