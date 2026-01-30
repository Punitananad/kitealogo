from api.kite_client import KiteClient
from core.zone_detector import ZoneDetector
from database.db_manager import DatabaseManager
from typing import List
import config

class FetchDayProcessor:
    """
    Processes Fetch Day: extracts zones and stores them immutably.
    This runs ONCE per stock per Fetch Day.
    """
    
    def __init__(self, kite_client: KiteClient, db_manager: DatabaseManager):
        self.kite = kite_client
        self.db = db_manager
        self.detector = ZoneDetector(
            atr_multiplier=config.Config.ATR_MULTIPLIER,
            zone_candles_min=config.Config.ZONE_CANDLES_MIN,
            zone_candles_max=config.Config.ZONE_CANDLES_MAX
        )
    
    def process_fetch_day(self, symbol: str, fetch_date: str, timeframe: str = None) -> List[dict]:
        """
        Process a single stock's Fetch Day.
        
        Args:
            symbol: Stock symbol
            fetch_date: Date in YYYY-MM-DD format (completed trading day)
            timeframe: Optional override for timeframe
        
        Returns:
            List of extracted zones
        """
        if timeframe is None:
            timeframe = config.Config.TIMEFRAME
        
        print(f"📊 Processing Fetch Day for {symbol} on {fetch_date}...")
        
        # Fetch historical data for the entire Fetch Day
        df = self.kite.get_historical_data(
            symbol=symbol,
            from_date=fetch_date,
            to_date=fetch_date,
            interval=timeframe
        )
        
        if df.empty:
            print(f"⚠ No data available for {symbol} on {fetch_date}")
            return []
        
        print(f"✓ Loaded {len(df)} candles for {symbol}")
        
        # Extract zones using zone detector
        zones = self.detector.extract_zones(df, symbol, fetch_date, timeframe)
        
        if not zones:
            print(f"⚠ No valid zones detected for {symbol}")
            return []
        
        # Save zones to database (immutable)
        for zone in zones:
            success = self.db.save_zone(zone)
            if success:
                print(f"✓ Saved {zone['zone_type']} zone: {zone['zone_low']:.2f} - {zone['zone_high']:.2f}")
            else:
                print(f"⚠ Zone already exists or failed to save")
        
        return zones
    
    def process_multiple_stocks(self, symbols: List[str], fetch_date: str) -> dict:
        """
        Process multiple stocks for the same Fetch Day.
        Returns summary of zones found per stock.
        """
        results = {}
        
        for symbol in symbols:
            zones = self.process_fetch_day(symbol, fetch_date)
            results[symbol] = {
                'zones_found': len(zones),
                'zones': zones
            }
        
        return results
