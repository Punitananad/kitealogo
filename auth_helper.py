"""
Kite API Authentication Helper

Run this script to generate access token:
1. Opens browser for Kite login
2. You login and authorize
3. Copy the request_token from redirect URL
4. Script generates access_token and saves to .env
"""

from kiteconnect import KiteConnect
import config
from urllib.parse import urlparse, parse_qs

def generate_login_url():
    """Generate Kite login URL"""
    kite = KiteConnect(api_key=config.Config.KITE_API_KEY)
    login_url = kite.login_url()
    
    print("=" * 60)
    print("KITE API AUTHENTICATION")
    print("=" * 60)
    print("\n1. Open this URL in your browser:")
    print(f"\n{login_url}\n")
    print("2. Login with your Zerodha credentials")
    print("3. After authorization, you'll be redirected to:")
    print(f"   {config.Config.KITE_REDIRECT_URL}?request_token=XXXXX&action=login&status=success")
    print("\n4. Copy the FULL redirect URL and paste below:")
    print("=" * 60)
    
    return kite

def extract_request_token(redirect_url):
    """Extract request_token from redirect URL"""
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    
    if 'request_token' in params:
        return params['request_token'][0]
    else:
        raise ValueError("request_token not found in URL")

def generate_access_token(kite, request_token):
    """Generate access token using request token"""
    data = kite.generate_session(
        request_token=request_token,
        api_secret=config.Config.KITE_API_SECRET
    )
    
    access_token = data['access_token']
    return access_token

def save_access_token(access_token):
    """Save access token to .env file"""
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    with open('.env', 'w') as f:
        for line in lines:
            if line.startswith('KITE_ACCESS_TOKEN='):
                f.write(f'KITE_ACCESS_TOKEN={access_token}\n')
            else:
                f.write(line)
    
    print("\n✓ Access token saved to .env file")
    print(f"✓ Token: {access_token[:20]}...")

def main():
    try:
        # Step 1: Generate login URL
        kite = generate_login_url()
        
        # Step 2: Get redirect URL from user
        redirect_url = input("\nPaste the redirect URL here: ").strip()
        
        # Step 3: Extract request token
        request_token = extract_request_token(redirect_url)
        print(f"\n✓ Request token extracted: {request_token[:20]}...")
        
        # Step 4: Generate access token
        access_token = generate_access_token(kite, request_token)
        print(f"✓ Access token generated: {access_token[:20]}...")
        
        # Step 5: Save to .env
        save_access_token(access_token)
        
        print("\n" + "=" * 60)
        print("AUTHENTICATION SUCCESSFUL!")
        print("=" * 60)
        print("\nYou can now run the application:")
        print("  python app.py")
        print("\nNote: Access token is valid until end of trading day.")
        print("You'll need to re-authenticate daily.")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("- Make sure you copied the FULL redirect URL")
        print("- Check that API key and secret are correct in .env")
        print("- Ensure redirect URL matches Kite app settings")

if __name__ == '__main__':
    main()
