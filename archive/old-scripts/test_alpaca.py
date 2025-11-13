#!/usr/bin/env python3
"""Test Alpaca API credentials"""

import os
import yaml
import requests
from pathlib import Path

# Load config
config_path = Path('config.yaml')
with open(config_path) as f:
    config = yaml.safe_load(f)

alpaca_config = config.get('data_sources', {}).get('alpaca', {})

# Get API key
api_key = alpaca_config.get('api_key', '')
if api_key.startswith('${'):
    api_key = api_key.split(':')[1].rstrip('}')

# Get API secret from environment
api_secret = os.environ.get('ALPACA_API_SECRET', '')

print("="*80)
print("ALPACA API CREDENTIALS TEST")
print("="*80)
print(f"API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
print(f"API Secret: {'SET' if api_secret else 'NOT SET'}")
if api_secret:
    print(f"API Secret (masked): {api_secret[:4]}...{api_secret[-4:]}")
print("="*80)

if not api_key or not api_secret:
    print("\n❌ ERROR: Missing credentials!")
    print("Please set ALPACA_API_SECRET environment variable:")
    print("  export ALPACA_API_SECRET='your_secret'")
    exit(1)

# Test API connection
print("\n🔍 Testing API connection...")
base_url = "https://data.alpaca.markets/v2"
url = f"{base_url}/stocks/AAPL/bars"
print(f"Testing endpoint: {url}")
headers = {
    'accept': 'application/json',
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': api_secret
}
params = {
    'start': '2025-11-01',
    'end': '2025-11-02',
    'timeframe': '1Min',
    'limit': 10,
    'feed': 'iex'
}

try:
    response = requests.get(url, headers=headers, params=params)

    print(f"\n📡 Response Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'bars' in data and data['bars']:
            print(f"✅ SUCCESS! Retrieved {len(data['bars'])} bars")
            print(f"Sample bar: {data['bars'][0]}")
        else:
            print(f"⚠️  No data returned (might be outside market hours)")
            print(f"Response: {data}")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ EXCEPTION: {e}")

print("="*80)
