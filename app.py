from flask import Flask, render_template, request, jsonify, redirect, session
from api.kite_client import KiteClient
from database.db_manager import DatabaseManager
from core.fetch_day import FetchDayProcessor
from core.execute_day import ExecuteDayMonitor
from kiteconnect import KiteConnect
import config
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize components
db_manager = DatabaseManager(config.Config.DATABASE_PATH)

# Initialize Kite client
kite_client = None
try:
    if config.Config.KITE_API_KEY and config.Config.KITE_ACCESS_TOKEN:
        kite_client = KiteClient(
            api_key=config.Config.KITE_API_KEY,
            access_token=config.Config.KITE_ACCESS_TOKEN
        )
        print("✅ Kite client initialized successfully")
    else:
        print("⚠️ Kite API credentials not found in .env")
except Exception as e:
    print(f"⚠️ Could not initialize Kite client: {e}")
    print("System will use mock data for testing")

@app.route('/')
def index():
    """Main dashboard"""
    # Check if authenticated
    if not config.Config.KITE_ACCESS_TOKEN:
        return render_template('auth_required.html', 
                             api_key=config.Config.KITE_API_KEY)
    return render_template('dashboard.html')

@app.route('/setup')
def setup():
    """Setup page for adding stocks"""
    return render_template('setup.html')

@app.route('/login')
def login():
    """Redirect to Kite login"""
    kite = KiteConnect(api_key=config.Config.KITE_API_KEY)
    login_url = kite.login_url()
    return redirect(login_url)

@app.route('/callback')
def callback():
    """Handle Kite OAuth callback"""
    request_token = request.args.get('request_token')
    
    if not request_token:
        return "Error: No request token received", 400
    
    try:
        kite = KiteConnect(api_key=config.Config.KITE_API_KEY)
        data = kite.generate_session(
            request_token=request_token,
            api_secret=config.Config.KITE_API_SECRET
        )
        
        access_token = data['access_token']
        
        # Save to .env file
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('KITE_ACCESS_TOKEN='):
                    f.write(f'KITE_ACCESS_TOKEN={access_token}\n')
                else:
                    f.write(line)
        
        # Update config
        config.Config.KITE_ACCESS_TOKEN = access_token
        
        # Initialize Kite client
        global kite_client
        kite_client = KiteClient(
            api_key=config.Config.KITE_API_KEY,
            access_token=access_token
        )
        
        return redirect('/')
        
    except Exception as e:
        return f"Authentication failed: {str(e)}", 400

@app.route('/api/process-fetch-day', methods=['POST'])
def process_fetch_day():
    """
    Process Fetch Day for given stocks.
    Body: {symbols: [], fetch_date: 'YYYY-MM-DD'}
    """
    if not kite_client:
        return jsonify({'error': 'Kite API not configured'}), 400
    
    data = request.json
    symbols = data.get('symbols', [])
    fetch_date = data.get('fetch_date')
    
    if not symbols or not fetch_date:
        return jsonify({'error': 'Missing symbols or fetch_date'}), 400
    
    processor = FetchDayProcessor(kite_client, db_manager)
    results = processor.process_multiple_stocks(symbols, fetch_date)
    
    return jsonify({
        'success': True,
        'results': results
    })

@app.route('/api/add-decode-list', methods=['POST'])
def add_decode_list():
    """
    Add stocks to Decode Day list.
    Body: {decode_date: 'YYYY-MM-DD', symbols: [], fetch_date: 'YYYY-MM-DD'}
    """
    data = request.json
    decode_date = data.get('decode_date')
    symbols = data.get('symbols', [])
    fetch_date = data.get('fetch_date')
    
    if not decode_date or not symbols or not fetch_date:
        return jsonify({'error': 'Missing required fields'}), 400
    
    db_manager.add_decode_list(decode_date, symbols, fetch_date)
    
    return jsonify({
        'success': True,
        'message': f'Added {len(symbols)} stocks to decode list'
    })

@app.route('/api/execute-day-monitor', methods=['GET'])
def execute_day_monitor():
    """
    Get Execute Day monitoring data.
    
    CRITICAL: Execute Day drives everything.
    System auto-calculates Fetch Day = Execute Day - 2 trading days.
    
    Query params:
        - execute_day: Date to monitor (defaults to today)
        - symbols: Comma-separated symbols (optional, uses decode list if not provided)
    """
    if not kite_client:
        return jsonify({'error': 'Kite API not configured'}), 400
    
    execute_day = request.args.get('execute_day', datetime.now().strftime('%Y-%m-%d'))
    symbols_param = request.args.get('symbols', '')
    
    # Get symbols from parameter or decode list
    if symbols_param:
        symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    else:
        # Fallback: get from decode list (legacy support)
        decode_list = db_manager.get_decode_list(execute_day)
        symbols = [item['symbol'] for item in decode_list]
    
    if not symbols:
        return jsonify({
            'success': False,
            'error': 'No symbols to monitor. Add stocks using the search box.',
            'data': []
        })
    
    monitor = ExecuteDayMonitor(kite_client, db_manager)
    result = monitor.get_monitoring_data(execute_day, symbols)
    
    if not result['success']:
        return jsonify(result), 400
    
    return jsonify({
        'success': True,
        'data': result['data'],
        'fetch_day': result['fetch_day'],
        'execute_day': result['execute_day'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get only stocks requiring attention"""
    if not kite_client:
        return jsonify({'error': 'Kite API not configured'}), 400
    
    decode_date = request.args.get('decode_date', datetime.now().strftime('%Y-%m-%d'))
    
    monitor = ExecuteDayMonitor(kite_client, db_manager)
    monitoring_data = monitor.get_monitoring_data(decode_date)
    alerts = monitor.get_alerts(monitoring_data)
    
    return jsonify({
        'success': True,
        'alerts': alerts,
        'count': len(alerts)
    })

@app.route('/api/test-fetch-day', methods=['GET'])
def test_fetch_day():
    """
    Test endpoint to check if Fetch Day data is available.
    Usage: /api/test-fetch-day?symbol=RELIANCE&fetch_date=2026-01-12
    """
    if not kite_client:
        return jsonify({'error': 'Kite API not configured'}), 400
    
    symbol = request.args.get('symbol', 'RELIANCE')
    fetch_date = request.args.get('fetch_date', '2026-01-27')
    
    try:
        # Try to fetch data
        df = kite_client.get_historical_data(
            symbol=symbol,
            from_date=fetch_date,
            to_date=fetch_date,
            interval='15minute'
        )
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'fetch_date': fetch_date,
            'candles_found': len(df),
            'data_available': not df.empty,
            'sample': df.head(3).to_dict('records') if not df.empty else []
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calculate-fetch-day', methods=['GET'])
def calculate_fetch_day():
    """
    Helper endpoint to show which Fetch Day will be used for a given Execute Day.
    This helps users understand the date logic.
    """
    from core.date_manager import DateManager
    
    execute_day = request.args.get('execute_day', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        is_valid, fetch_day, error = DateManager.validate_execute_day(execute_day)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        return jsonify({
            'success': True,
            'execute_day': execute_day,
            'fetch_day': fetch_day,
            'explanation': f'Zones will be loaded from {fetch_day} (2 trading days before {execute_day})'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/smart-monitor', methods=['POST'])
def smart_monitor():
    """
    Smart endpoint: Just provide symbols and optional Execute Day.
    System automatically:
    1. Calculates Fetch Day = Execute Day - 2 trading days
    2. Generates zones from Fetch Day (if not exists)
    3. Adds to monitoring list
    
    NO manual Fetch Day input. NO future data access.
    """
    # Initialize kite_client if not already done
    global kite_client
    if not kite_client:
        try:
            kite_client = KiteClient(
                api_key=config.Config.KITE_API_KEY,
                access_token=config.Config.KITE_ACCESS_TOKEN
            )
            print("✅ Kite client initialized")
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to initialize Kite API: {str(e)}'
            }), 400
    
    from core.date_manager import DateManager
    
    data = request.json
    symbols = data.get('symbols', [])
    execute_day = data.get('execute_day', datetime.now().strftime('%Y-%m-%d'))
    
    if not symbols:
        return jsonify({'error': 'No symbols provided'}), 400
    
    try:
        # Step 1: Calculate Fetch Day from Execute Day
        is_valid, fetch_day, error = DateManager.validate_execute_day(execute_day)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        # Step 2: Process Fetch Day (extract zones if not exists)
        processor = FetchDayProcessor(kite_client, db_manager)
        
        # Check if zones already exist and generate if needed
        zones_generated = False
        for symbol in symbols:
            existing_zones = db_manager.get_zones_for_symbol(symbol, fetch_day)
            if not existing_zones:
                print(f"🔄 Generating zones for {symbol} from Fetch Day {fetch_day}")
                zones = processor.process_fetch_day(symbol, fetch_day)
                if zones:
                    zones_generated = True
                    print(f"✅ Generated {len(zones)} zones for {symbol}")
                else:
                    print(f"⚠️ No zones detected for {symbol} on {fetch_day}")
            else:
                print(f"✓ Using existing {len(existing_zones)} zones for {symbol}")
        
        # Step 3: Add to decode list (for legacy support)
        db_manager.add_decode_list(execute_day, symbols, fetch_day)
        
        return jsonify({
            'success': True,
            'message': f'Monitoring {len(symbols)} stocks on Execute Day',
            'fetch_day': fetch_day,
            'execute_day': execute_day,
            'symbols': symbols,
            'zones_generated': zones_generated
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get-zones', methods=['GET'])
def get_zones():
    """Get zones for a specific symbol and fetch day"""
    symbol = request.args.get('symbol')
    fetch_day = request.args.get('fetch_day')
    
    if not symbol or not fetch_day:
        return jsonify({'error': 'Missing symbol or fetch_day'}), 400
    
    zones = db_manager.get_zones_for_symbol(symbol, fetch_day)
    
    return jsonify({
        'success': True,
        'zones': zones
    })

@app.route('/api/update-zone', methods=['POST'])
def update_zone():
    """Update or create a zone manually"""
    data = request.json
    symbol = data.get('symbol')
    fetch_day = data.get('fetch_day')
    zone_type = data.get('zone_type')
    zone_low = data.get('zone_low')
    zone_high = data.get('zone_high')
    
    if not all([symbol, fetch_day, zone_type, zone_low, zone_high]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Use the database manager to update zone
        zone_data = {
            'symbol': symbol,
            'fetch_date': fetch_day,
            'timeframe': config.Config.TIMEFRAME,
            'zone_type': zone_type,
            'zone_low': float(zone_low),
            'zone_high': float(zone_high),
            'impulse_strength': 'MANUAL'
        }
        
        # Save new zone using update method
        success = db_manager.update_zone(symbol, fetch_day, zone_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Zone updated for {symbol}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save zone'
            }), 500
            
    except Exception as e:
        print(f"Error updating zone: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save-watchlist', methods=['POST'])
def save_watchlist():
    """Save current stock list as a watchlist"""
    data = request.json
    name = data.get('name')
    description = data.get('description', '')
    execute_day = data.get('execute_day')
    fetch_day = data.get('fetch_day')
    symbols = data.get('symbols', [])
    
    if not name or not execute_day or not fetch_day or not symbols:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        import sqlite3
        conn = sqlite3.connect(config.Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Delete if exists
        cursor.execute('DELETE FROM watchlists WHERE name = ?', (name,))
        
        # Insert new watchlist
        cursor.execute('''
            INSERT INTO watchlists (name, description, execute_day, fetch_day, symbols)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, execute_day, fetch_day, ','.join(symbols)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Watchlist "{name}" saved'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-watchlists', methods=['GET'])
def get_watchlists():
    """Get all saved watchlists"""
    try:
        import sqlite3
        conn = sqlite3.connect(config.Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM watchlists ORDER BY updated_at DESC')
        watchlists = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'watchlists': watchlists
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/load-watchlist', methods=['GET'])
def load_watchlist():
    """Load a watchlist by name"""
    name = request.args.get('name')
    
    if not name:
        return jsonify({'error': 'Missing watchlist name'}), 400
    
    try:
        import sqlite3
        conn = sqlite3.connect(config.Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM watchlists WHERE name = ?', (name,))
        watchlist = cursor.fetchone()
        
        conn.close()
        
        if not watchlist:
            return jsonify({'error': 'Watchlist not found'}), 404
        
        watchlist = dict(watchlist)
        symbols = watchlist['symbols'].split(',')
        
        return jsonify({
            'success': True,
            'name': watchlist['name'],
            'description': watchlist['description'],
            'execute_day': watchlist['execute_day'],
            'fetch_day': watchlist['fetch_day'],
            'symbols': symbols
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-watchlist', methods=['POST'])
def delete_watchlist():
    """Delete a watchlist"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Missing watchlist name'}), 400
    
    try:
        import sqlite3
        conn = sqlite3.connect(config.Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM watchlists WHERE name = ?', (name,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Watchlist "{name}" deleted'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run on port 8080 to match redirect URL
    app.run(debug=True, port=8080, host='localhost')
