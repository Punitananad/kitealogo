import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Kite API credentials
    KITE_API_KEY = os.getenv('KITE_API_KEY', '')
    KITE_API_SECRET = os.getenv('KITE_API_SECRET', '')
    KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN', '')
    KITE_REDIRECT_URL = os.getenv('KITE_REDIRECT_URL', 'http://localhost:8080/callback')
    
    # Database
    DATABASE_PATH = 'trading_zones.db'
    
    # Zone detection parameters
    TIMEFRAME = '15minute'  # 5minute, 10minute, 15minute
    ATR_MULTIPLIER = 1.5  # Minimum impulse move threshold
    ZONE_CANDLES_MIN = 2
    ZONE_CANDLES_MAX = 6
    
    # Execute day proximity
    NEAR_ZONE_PERCENT = 0.5  # 0.5% proximity threshold
    
    # UI refresh rate
    REFRESH_INTERVAL_MS = 3000  # 3 seconds
