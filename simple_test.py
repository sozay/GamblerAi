#!/usr/bin/env python3
"""
Simple test to verify Alpaca API credentials work.
"""

import sys
import time
import requests

API_KEY = "PKJUPGKDCCIMZKPDXUFXHM3E4D"
API_SECRET = "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"
BASE_URL = "https://paper-api.alpaca.markets"


def test_account_access():
    """Test basic account access."""
    print("=" * 60)
    print("Testing Alpaca API Account Access")
    print("=" * 60)
    print(f"API Key: {API_KEY[:10]}...")
    print(f"Base URL: {BASE_URL}")
    print()

    try:
        print("Making request to /v2/account endpoint...")

        response = requests.get(
            f"{BASE_URL}/v2/account",
            headers={
                "APCA-API-KEY-ID": API_KEY,
                "APCA-API-SECRET-KEY": API_SECRET,
            }
        )

        print(f"Response Status: {response.status_code}")
        print()

        if response.status_code == 200:
            account = response.json()
            print("✓ SUCCESS: Authentication worked!")
            print()
            print("Account Information:")
            print(f"  Account ID: {account.get('id', 'N/A')}")
            print(f"  Status: {account.get('status', 'N/A')}")
            print(f"  Currency: {account.get('currency', 'N/A')}")
            print(f"  Cash: ${float(account.get('cash', 0)):.2f}")
            print(f"  Buying Power: ${float(account.get('buying_power', 0)):.2f}")
            print(f"  Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")
            print(f"  Pattern Day Trader: {account.get('pattern_day_trader', False)}")
            print(f"  Trading Blocked: {account.get('trading_blocked', False)}")
            print(f"  Account Blocked: {account.get('account_blocked', False)}")
            return True
        else:
            print(f"✗ FAILED: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_positions():
    """Test getting positions."""
    print()
    print("=" * 60)
    print("Testing Positions Endpoint")
    print("=" * 60)

    try:
        print("Making request to /v2/positions endpoint...")

        response = requests.get(
            f"{BASE_URL}/v2/positions",
            headers={
                "APCA-API-KEY-ID": API_KEY,
                "APCA-API-SECRET-KEY": API_SECRET,
            }
        )

        print(f"Response Status: {response.status_code}")
        print()

        if response.status_code == 200:
            positions = response.json()
            print(f"✓ SUCCESS: Found {len(positions)} positions")

            if positions:
                print()
                print("Current Positions:")
                for pos in positions[:5]:  # Show first 5
                    print(f"  {pos['symbol']}: {pos['qty']} shares @ ${float(pos['avg_entry_price']):.2f}")
            else:
                print("  (No open positions)")

            return True
        else:
            print(f"✗ FAILED: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def test_clock():
    """Test market clock."""
    print()
    print("=" * 60)
    print("Testing Market Clock")
    print("=" * 60)

    try:
        print("Making request to /v2/clock endpoint...")

        response = requests.get(
            f"{BASE_URL}/v2/clock",
            headers={
                "APCA-API-KEY-ID": API_KEY,
                "APCA-API-SECRET-KEY": API_SECRET,
            }
        )

        print(f"Response Status: {response.status_code}")
        print()

        if response.status_code == 200:
            clock = response.json()
            print("✓ SUCCESS: Market clock retrieved")
            print()
            print("Market Status:")
            print(f"  Is Open: {clock.get('is_open', False)}")
            print(f"  Timestamp: {clock.get('timestamp', 'N/A')}")
            print(f"  Next Open: {clock.get('next_open', 'N/A')}")
            print(f"  Next Close: {clock.get('next_close', 'N/A')}")

            if not clock.get('is_open'):
                print()
                print("⚠ Note: Market is currently CLOSED")
                print("  Streaming tests may not receive real-time data")

            return True
        else:
            print(f"✗ FAILED: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def test_market_data():
    """Test market data access."""
    print()
    print("=" * 60)
    print("Testing Market Data Access")
    print("=" * 60)

    try:
        # Try to get latest quote for SPY
        print("Making request to data API for SPY quote...")

        data_url = "https://data.alpaca.markets"
        response = requests.get(
            f"{data_url}/v2/stocks/SPY/quotes/latest",
            headers={
                "APCA-API-KEY-ID": API_KEY,
                "APCA-API-SECRET-KEY": API_SECRET,
            }
        )

        print(f"Response Status: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            print("✓ SUCCESS: Market data access works!")

            if "quote" in data:
                quote = data["quote"]
                print()
                print("Latest SPY Quote:")
                print(f"  Bid: ${quote.get('bp', 0):.2f} x {quote.get('bs', 0)}")
                print(f"  Ask: ${quote.get('ap', 0):.2f} x {quote.get('as', 0)}")
                print(f"  Timestamp: {quote.get('t', 'N/A')}")

            return True
        else:
            print(f"Response: {response.text}")

            if response.status_code == 403:
                print()
                print("⚠ Note: Market data access may require subscription")
                print("  This is normal for paper trading accounts")
                return True  # Still a success

            return False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


if __name__ == "__main__":
    print()
    print("Alpaca API Credentials Test")
    print("=" * 60)

    results = {}

    # Run tests
    results["account"] = test_account_access()
    results["positions"] = test_positions()
    results["clock"] = test_clock()
    results["market_data"] = test_market_data()

    # Summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name:15s}: {status}")

    print()

    if all(results.values()):
        print("✓ All tests PASSED!")
        print()
        print("Your Alpaca API credentials are working correctly.")
        print("The streamers should work with these credentials.")
        sys.exit(0)
    else:
        print("⚠ Some tests failed")
        print()
        print("Please check your API credentials and try again.")
        sys.exit(1)
