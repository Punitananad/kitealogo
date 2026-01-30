"""
Date Manager: Handles the 3-day cycle logic.
CRITICAL: Execute Day → Fetch Day (auto-calculated, historical only)
"""

from datetime import datetime, timedelta
from typing import Optional, List

class DateManager:
    """
    Manages date logic for the trading system.
    
    CORE PRINCIPLE:
    - User provides Execute Day (E)
    - System calculates Fetch Day (F) = E - 2 trading days
    - NO future data access, ever
    """
    
    # NSE holidays 2026 (update annually)
    NSE_HOLIDAYS_2026 = [
        '2026-01-26',  # Republic Day
        '2026-03-03',  # Holi
        '2026-03-30',  # Ram Navami
        '2026-04-02',  # Mahavir Jayanti
        '2026-04-03',  # Good Friday
        '2026-04-14',  # Ambedkar Jayanti
        '2026-05-01',  # Maharashtra Day
        '2026-08-15',  # Independence Day
        '2026-08-19',  # Muharram
        '2026-10-02',  # Gandhi Jayanti
        '2026-10-20',  # Dussehra
        '2026-11-04',  # Diwali
        '2026-11-05',  # Diwali
        '2026-11-25',  # Gurunanak Jayanti
        '2026-12-25',  # Christmas
    ]
    
    @staticmethod
    def is_trading_day(date: datetime) -> bool:
        """
        Check if a date is a trading day.
        Returns False for weekends and NSE holidays.
        """
        # Check weekend
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check NSE holidays
        date_str = date.strftime('%Y-%m-%d')
        if date_str in DateManager.NSE_HOLIDAYS_2026:
            return False
        
        return True
    
    @staticmethod
    def get_previous_trading_day(date: datetime) -> datetime:
        """
        Get the previous trading day from given date.
        Skips weekends and holidays.
        """
        current = date - timedelta(days=1)
        
        # Keep going back until we find a trading day
        max_lookback = 10  # Safety limit
        for _ in range(max_lookback):
            if DateManager.is_trading_day(current):
                return current
            current = current - timedelta(days=1)
        
        # Fallback: return 1 day back (shouldn't happen)
        return date - timedelta(days=1)
    
    @staticmethod
    def calculate_fetch_day(execute_day: str) -> str:
        """
        Calculate Fetch Day from Execute Day.
        
        RULE: Fetch Day = Execute Day - 2 trading days
        
        Args:
            execute_day: Date string in 'YYYY-MM-DD' format
        
        Returns:
            Fetch Day as 'YYYY-MM-DD' string
        
        Example:
            Execute Day = 2026-01-30 (Friday)
            → Go back 1 trading day → 2026-01-29 (Thursday)
            → Go back 2 trading days → 2026-01-28 (Wednesday)
            Fetch Day = 2026-01-28
        """
        execute_dt = datetime.strptime(execute_day, '%Y-%m-%d')
        
        # Go back 2 trading days
        current = execute_dt
        trading_days_back = 0
        
        while trading_days_back < 2:
            current = DateManager.get_previous_trading_day(current)
            trading_days_back += 1
        
        return current.strftime('%Y-%m-%d')
    
    @staticmethod
    def get_trading_days_between(start_date: str, end_date: str) -> List[str]:
        """
        Get all trading days between two dates (inclusive).
        Useful for historical replay.
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        trading_days = []
        current = start_dt
        
        while current <= end_dt:
            if DateManager.is_trading_day(current):
                trading_days.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return trading_days
    
    @staticmethod
    def validate_execute_day(execute_day: str) -> tuple:
        """
        Validate Execute Day and calculate Fetch Day.
        
        Returns:
            (is_valid, fetch_day, error_message)
        """
        try:
            execute_dt = datetime.strptime(execute_day, '%Y-%m-%d')
            
            # Calculate Fetch Day
            fetch_day = DateManager.calculate_fetch_day(execute_day)
            
            # Fetch Day must be in the past (historical data only)
            fetch_dt = datetime.strptime(fetch_day, '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if fetch_dt > today:
                return (False, None, f"Fetch Day ({fetch_day}) is in the future. No historical data available.")
            
            return (True, fetch_day, None)
            
        except ValueError as e:
            return (False, None, f"Invalid date format: {str(e)}")
