from api.kite_client import KiteClient
from database.db_manager import DatabaseManager
from core.date_manager import DateManager
from typing import List, Dict, Optional
import config

class ExecuteDayMonitor:
    """
    Execute Day: Monitor live prices against Fetch Day zones.
    NO zone recalculation. NO indicators. Pure proximity monitoring.
    """
    
    def __init__(self, kite_client: KiteClient, db_manager: DatabaseManager):
        self.kite = kite_client
        self.db = db_manager
        self.near_threshold = config.Config.NEAR_ZONE_PERCENT / 100.0
        self.far_threshold = 1.5  # 1.5% away = Far
    
    def get_monitoring_data(self, execute_day: str, symbols: List[str]) -> Dict:
        """
        Get monitoring data for Execute Day.
        
        CRITICAL LOGIC:
        1. User provides Execute Day
        2. System calculates Fetch Day = Execute Day - 2 trading days
        3. Load/generate zones from Fetch Day (historical only)
        4. Monitor prices on Execute Day
        
        Args:
            execute_day: The date to monitor (YYYY-MM-DD)
            symbols: List of stock symbols to monitor
        
        Returns:
            Dict with: success, data, fetch_day, execute_day, error
        """
        # Step 1: Validate Execute Day and calculate Fetch Day
        is_valid, fetch_day, error = DateManager.validate_execute_day(execute_day)
        
        if not is_valid:
            return {
                'success': False,
                'error': error,
                'data': []
            }
        
        # Step 2: Ensure zones exist for Fetch Day
        # Generate zones on-demand if missing
        zones_generated = False
        for symbol in symbols:
            existing_zones = self.db.get_zones_for_symbol(symbol, fetch_day)
            if not existing_zones:
                # Need to generate zones
                from core.fetch_day import FetchDayProcessor
                processor = FetchDayProcessor(self.kite, self.db)
                
                try:
                    zones = processor.process_fetch_day(symbol, fetch_day)
                    if zones:
                        zones_generated = True
                        print(f"✓ Generated {len(zones)} zones for {symbol} from {fetch_day}")
                    else:
                        print(f"⚠ No zones found for {symbol} on {fetch_day}")
                except Exception as e:
                    print(f"✗ Error generating zones for {symbol}: {e}")
        
        # Step 3: Get prices for Execute Day
        # If Execute Day is today → use LTP
        # If Execute Day is historical → use historical close price
        from datetime import datetime
        execute_dt = datetime.strptime(execute_day, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if execute_dt.date() == today.date():
            # Live monitoring - use LTP
            price_data = self.kite.get_ltp(symbols)
        else:
            # Historical replay - use close price from Execute Day
            price_data = self._get_historical_prices(symbols, execute_day)
        
        # Step 4: Build monitoring data
        monitoring_data = []
        
        for symbol in symbols:
            # Get zones from Fetch Day
            zones = self.db.get_zones_for_symbol(symbol, fetch_day)
            
            # Get price
            ltp = price_data.get(symbol, 0)
            
            if ltp == 0:
                continue
            
            # Calculate proximity to zones
            status, closest_zone, distance_pct, reaction = self._calculate_proximity(ltp, zones)
            
            monitoring_data.append({
                'symbol': symbol,
                'ltp': float(ltp),
                'zones': zones,
                'status': status,
                'closest_zone': closest_zone,
                'distance_percent': float(distance_pct) if distance_pct is not None else None,
                'reaction': reaction,
                'fetch_date': fetch_day,
                'execute_date': execute_day
            })
        
        return {
            'success': True,
            'data': monitoring_data,
            'fetch_day': fetch_day,
            'execute_day': execute_day,
            'error': None
        }
    
    def _get_historical_prices(self, symbols: List[str], date: str) -> Dict[str, float]:
        """
        Get historical closing prices for a specific date.
        Used for historical replay of Execute Days.
        """
        prices = {}
        
        for symbol in symbols:
            try:
                df = self.kite.get_historical_data(
                    symbol=symbol,
                    from_date=date,
                    to_date=date,
                    interval='day'
                )
                
                if not df.empty:
                    prices[symbol] = df.iloc[-1]['close']
            except Exception as e:
                print(f"Error fetching historical price for {symbol}: {e}")
        
        return prices
    
    def _calculate_proximity(self, ltp: float, zones: List[Dict]) -> tuple:
        """
        Calculate price proximity to zones with proper distance calculation.
        
        Returns:
            (status, closest_zone, distance_percent, reaction_state)
            
        Status:
            - INSIDE_BULLISH: Price inside bullish zone
            - INSIDE_BEARISH: Price inside bearish zone
            - NEAR: Price near any zone (within threshold)
            - FAR: Price far from all zones
        
        Reaction State:
            - No Touch Yet: Price hasn't entered zone
            - First Touch: Price just entered zone
            - Holding: Price staying in zone
            - Rejected: Price wicked and moved away
            - Broken: Price closed beyond zone
        """
        if not zones:
            return ('FAR', None, 100.0, 'No Touch Yet')
        
        closest_zone = None
        min_distance_pct = float('inf')
        status = 'FAR'
        reaction = 'No Touch Yet'
        
        for zone in zones:
            zone_low = zone['zone_low']
            zone_high = zone['zone_high']
            zone_mid = (zone_low + zone_high) / 2
            
            # Calculate distance as percentage from zone mid
            distance_from_mid = ((ltp - zone_mid) / zone_mid) * 100
            
            # Check if inside zone
            if zone_low <= ltp <= zone_high:
                if zone['zone_type'] == 'BULLISH':
                    status = 'INSIDE_BULLISH'
                else:
                    status = 'INSIDE_BEARISH'
                
                # Determine reaction state (simplified - can be enhanced with historical data)
                reaction = 'Holding'  # Default for inside zone
                
                return (status, zone, distance_from_mid, reaction)
            
            # Calculate absolute distance percentage
            abs_distance_pct = abs(distance_from_mid)
            
            if abs_distance_pct < abs(min_distance_pct):
                min_distance_pct = distance_from_mid
                closest_zone = zone
                
                # Determine status based on distance
                if abs_distance_pct <= self.near_threshold:
                    status = 'NEAR'
                    reaction = 'First Touch'  # Approaching zone
                elif abs_distance_pct > self.far_threshold:
                    status = 'FAR'
                    reaction = 'No Touch Yet'
                else:
                    status = 'NEAR'
                    reaction = 'No Touch Yet'
        
        return (status, closest_zone, min_distance_pct, reaction)
    
    def get_alerts(self, monitoring_data: List[Dict]) -> List[Dict]:
        """
        Filter monitoring data to only stocks requiring attention.
        Alert ONLY on First Touch or Holding - not on noise.
        """
        alerts = []
        
        for data in monitoring_data:
            # Alert on meaningful states only
            if data['status'] in ['INSIDE_BULLISH', 'INSIDE_BEARISH', 'NEAR']:
                if data['reaction'] in ['First Touch', 'Holding']:
                    alerts.append(data)
        
        return alerts
