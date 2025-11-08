#!/usr/bin/env python3
"""Test Alpaca API connection"""

import requests
import os
from base64 import b64encode

# Get credentials
api_key = os.getenv('ALPACA_API_KEY', 'PKJUPGKDCCIMZKPDXUFXHM3E4D')
api_secret = os.getenv('ALPACA_API_SECRET', 'CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H')

print(f"Testing connection...")
print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
print(f"API Secret: {api_secret[:10]}...{api_secret[-4:]}")
print()

# Test connection to paper trading API
base_url = "https://paper-api.alpaca.markets"
headers = {
    "APCA-API-KEY-ID": api_key,
    "APCA-API-SECRET-KEY": api_secret
}

print(f"Testing URL: {base_url}/v2/account")
print()

try:
    response = requests.get(f"{base_url}/v2/account", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()

    if response.status_code == 200:
        account = response.json()
        print("✓ Connection successful!")
        print(f"  Account ID: {account.get('id')}")
        print(f"  Buying Power: ${account.get('buying_power')}")
        print(f"  Cash: ${account.get('cash')}")
        print(f"  Portfolio Value: ${account.get('portfolio_value')}")
    else:
        print(f"✗ Connection failed!")
        print(f"  Error: {response.text}")

except Exception as e:
    print(f"✗ Exception occurred: {e}")
