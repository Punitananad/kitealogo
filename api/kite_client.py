from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Optional
import numpy as np

class KiteClient:
    """
    Wrapper for Zerodha Kite API.
    Handles historical data (Fetch Day) and live prices (Execute Day).
    """
    
    def __init__(self, api_key: str, access_token: str):
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        self.instruments_cache = {}
        self._load_instruments()
    
    def _load_instruments(self):
        """Load and cache instrument tokens"""
        try:
            instruments = self.kite.instruments("NSE")
            for inst in instruments:
                self.instruments_cache[inst['tradingsymbol']] = inst['instrument_token']
            print(f"✓ Loaded {len(self.instruments_cache)} NSE instruments")
        except Exception as e:
            print(f"Warning: Could not load instruments: {e}")
            print("Using mock data mode for testing")
    
    def get_historical_data(self, symbol: str, from_date: str, to_date: str, interval: str) -> pd.DataFrame:
        """
        Fetch historical OHLC data for Fetch Day.
        
        Args:
            symbol: Trading symbol (e.g., 'HINDZINC')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: '5minute', '10minute', '15minute', 'day'
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            instrument_token = self._get_instrument_token(symbol)
            
            if instrument_token == 0:
                print(f"Warning: No instrument token for {symbol}, using mock data")
                return self._generate_mock_data(symbol, from_date, to_date, interval)
            
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
            
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_dt,
                to_date=to_dt,
                interval=interval
            )
            
            df = pd.DataFrame(data)
            return df
        
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            print(f"Falling back to mock data for testing")
            return self._generate_mock_data(symbol, from_date, to_date, interval)
    
    def _generate_mock_data(self, symbol: str, from_date: str, to_date: str, interval: str) -> pd.DataFrame:
        """Generate realistic mock OHLC data for testing"""
        # Base prices for common stocks
        base_prices = {
            'HINDZINC': 715,
            'TATASTEEL': 202,
            'RELIANCE': 1391,
            'INFY': 1659,
            'TCS': 3144,
            'HDFCBANK': 935,
            'MRF': 130915
        }
        
        base_price = base_prices.get(symbol, 1000)
        
        # Generate intraday data
        if interval in ['5minute', '10minute', '15minute']:
            num_candles = 75  # Full trading day
        else:
            num_candles = 1
        
        data = []
        current_price = base_price
        
        for i in range(num_candles):
            # Simulate price movement
            change = np.random.randn() * (base_price * 0.01)
            current_price += change
            
            high = current_price + abs(np.random.randn() * base_price * 0.005)
            low = current_price - abs(np.random.randn() * base_price * 0.005)
            open_price = current_price + np.random.randn() * base_price * 0.003
            close_price = current_price + np.random.randn() * base_price * 0.003
            
            data.append({
                'date': datetime.strptime(from_date, '%Y-%m-%d') + timedelta(minutes=i*15),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': int(np.random.randint(10000, 100000))
            })
        
        return pd.DataFrame(data)
    
    def get_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get Last Traded Price for multiple symbols (Execute Day).
        
        Args:
            symbols: List of trading symbols
        
        Returns:
            Dict mapping symbol to LTP
        """
        try:
            # Convert symbols to exchange:symbol format
            instruments = [f"NSE:{symbol}" for symbol in symbols]
            
            quotes = self.kite.ltp(instruments)
            
            ltp_data = {}
            for instrument, data in quotes.items():
                symbol = instrument.split(':')[1]
                ltp_data[symbol] = data['last_price']
            
            return ltp_data
        
        except Exception as e:
            print(f"Error fetching LTP: {e}")
            print("Using mock LTP data")
            return self._generate_mock_ltp(symbols)
    
    def _generate_mock_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """Generate mock LTP for testing"""
        base_prices = {
            'HINDZINC': 715.20,
            'TATASTEEL': 202.32,
            'RELIANCE': 1391.00,
            'INFY': 1659.50,
            'TCS': 3144.40,
            'HDFCBANK': 935.50,
            'MRF': 130915.00
        }
        
        ltp_data = {}
        for symbol in symbols:
            base = base_prices.get(symbol, 1000)
            # Add small random variation
            ltp_data[symbol] = round(base + np.random.randn() * base * 0.01, 2)
        
        return ltp_data
    
    def _get_instrument_token(self, symbol: str) -> int:
        """
        Map symbol to instrument token.
        """
        return self.instruments_cache.get(symbol, 0)
    
    def get_quote(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get detailed quote including OHLC for Execute Day monitoring.
        """
        try:
            instruments = [f"NSE:{symbol}" for symbol in symbols]
            quotes = self.kite.quote(instruments)
            
            quote_data = {}
            for instrument, data in quotes.items():
                symbol = instrument.split(':')[1]
                quote_data[symbol] = {
                    'ltp': data['last_price'],
                    'open': data['ohlc']['open'],
                    'high': data['ohlc']['high'],
                    'low': data['ohlc']['low'],
                    'close': data['ohlc']['close'],
                    'volume': data['volume']
                }
            
            return quote_data
        
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return {}
