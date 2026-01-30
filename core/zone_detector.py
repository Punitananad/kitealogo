import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

class ZoneDetector:
    """
    Detects institutional zones from Fetch Day OHLC data.
    Philosophy: Find the last balanced range before major unbalanced moves.
    """
    
    def __init__(self, atr_multiplier: float = 1.5, zone_candles_min: int = 2, zone_candles_max: int = 6):
        self.atr_multiplier = atr_multiplier
        self.zone_candles_min = zone_candles_min
        self.zone_candles_max = zone_candles_max
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else df['high'].mean() - df['low'].mean()
    
    def find_major_impulse(self, df: pd.DataFrame, atr: float) -> Optional[Dict]:
        """
        Identify the largest directional move of Fetch Day.
        Returns: {direction, start_idx, end_idx, strength}
        """
        df = df.reset_index(drop=True)
        best_impulse = None
        max_move = 0
        
        # Scan for impulse moves
        for i in range(len(df) - 3):
            for j in range(i + 3, min(i + 20, len(df))):
                # Calculate net directional move
                price_start = df.loc[i, 'close']
                price_end = df.loc[j, 'close']
                net_move = abs(price_end - price_start)
                
                # Check if move is significant
                if net_move < self.atr_multiplier * atr:
                    continue
                
                # Check directional dominance (minimal pullback)
                if price_end > price_start:  # Bullish
                    lowest_in_range = df.loc[i:j, 'low'].min()
                    pullback = price_start - lowest_in_range
                    if pullback > net_move * 0.3:  # Too much pullback
                        continue
                    direction = 'BULLISH'
                else:  # Bearish
                    highest_in_range = df.loc[i:j, 'high'].max()
                    pullback = highest_in_range - price_start
                    if pullback > net_move * 0.3:
                        continue
                    direction = 'BEARISH'
                
                # Track best impulse
                if net_move > max_move:
                    max_move = net_move
                    best_impulse = {
                        'direction': direction,
                        'start_idx': i,
                        'end_idx': j,
                        'strength': 'HIGH' if net_move > 2 * atr else 'MEDIUM',
                        'start_time': df.loc[i, 'date'],
                        'end_time': df.loc[j, 'date']
                    }
        
        return best_impulse
    
    def find_origin_zone(self, df: pd.DataFrame, impulse_start_idx: int) -> Optional[Dict]:
        """
        Look backwards from impulse start to find the last balanced range.
        Balanced = overlapping candles, compression, no directional progress.
        """
        if impulse_start_idx < self.zone_candles_min:
            return None
        
        # Look back from impulse start
        for lookback in range(self.zone_candles_min, min(self.zone_candles_max + 1, impulse_start_idx + 1)):
            zone_start = impulse_start_idx - lookback
            zone_end = impulse_start_idx
            
            zone_candles = df.iloc[zone_start:zone_end]
            
            # Check for compression (overlapping ranges)
            zone_low = zone_candles['low'].min()
            zone_high = zone_candles['high'].max()
            zone_range = zone_high - zone_low
            
            # Check if candles overlap significantly
            avg_candle_range = (zone_candles['high'] - zone_candles['low']).mean()
            
            if zone_range < avg_candle_range * 2.5:  # Compressed
                # Check no strong directional bias
                first_close = zone_candles.iloc[0]['close']
                last_close = zone_candles.iloc[-1]['close']
                net_progress = abs(last_close - first_close)
                
                if net_progress < zone_range * 0.5:  # Minimal progress
                    return {
                        'zone_low': zone_low,
                        'zone_high': zone_high,
                        'candle_count': lookback
                    }
        
        return None
    
    def validate_zone(self, df: pd.DataFrame, zone: Dict, impulse: Dict) -> bool:
        """
        Validate that zone was respected and price moved away significantly.
        """
        impulse_end_idx = impulse['end_idx']
        
        # Check price moved away from zone
        if impulse_end_idx >= len(df):
            return False
        
        price_after_impulse = df.iloc[impulse_end_idx]['close']
        zone_mid = (zone['zone_low'] + zone['zone_high']) / 2
        distance = abs(price_after_impulse - zone_mid)
        zone_range = zone['zone_high'] - zone['zone_low']
        
        # Price should be at least 2x zone range away
        if distance < zone_range * 2:
            return False
        
        return True
    
    def extract_zones(self, df: pd.DataFrame, symbol: str, fetch_date: str, timeframe: str) -> List[Dict]:
        """
        Main method: Extract all valid zones from Fetch Day data.
        Returns list of zone dictionaries ready for database storage.
        """
        if len(df) < 20:
            return []
        
        zones = []
        
        # Calculate ATR
        atr = self.calculate_atr(df)
        
        # Find major impulse
        impulse = self.find_major_impulse(df, atr)
        if not impulse:
            return zones
        
        # Find origin zone
        origin_zone = self.find_origin_zone(df, impulse['start_idx'])
        if not origin_zone:
            return zones
        
        # Validate zone
        if not self.validate_zone(df, origin_zone, impulse):
            return zones
        
        # Create zone record
        zone_record = {
            'symbol': symbol,
            'fetch_date': fetch_date,
            'timeframe': timeframe,
            'zone_type': impulse['direction'],
            'zone_low': float(origin_zone['zone_low']),
            'zone_high': float(origin_zone['zone_high']),
            'impulse_strength': impulse['strength'],
            'impulse_start_time': str(impulse['start_time']),
            'impulse_end_time': str(impulse['end_time'])
        }
        
        zones.append(zone_record)
        
        return zones
