#!/bin/bash
# Test if credentials can get stock prices and place paper trades

API_KEY="PKJUPGKDCCIMZKPDXUFXHM3E4D"
API_SECRET="CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"

echo "=========================================="
echo "Testing Alpaca Trading Capabilities"
echo "=========================================="
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Test 1: Get Account Info (Paper Trading)
echo "Test 1: Get Account Info (Paper Trading)"
echo "Endpoint: GET /v2/account"
echo "Purpose: Check if account exists and has buying power"
echo ""
ACCOUNT_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "https://paper-api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}")

HTTP_STATUS=$(echo "$ACCOUNT_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$ACCOUNT_RESPONSE" | sed '/HTTP_STATUS/d')

echo "Status: $HTTP_STATUS"
echo "Response: $RESPONSE_BODY"

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ SUCCESS: Account accessible"
    # Extract buying power if available
    BUYING_POWER=$(echo "$RESPONSE_BODY" | grep -o '"buying_power":"[^"]*"' | cut -d'"' -f4)
    if [ ! -z "$BUYING_POWER" ]; then
        echo "   Buying Power: \$$BUYING_POWER"
    fi
else
    echo "❌ FAILED: Cannot access account (Status: $HTTP_STATUS)"
fi
echo ""

# Test 2: Get Stock Price (Latest Quote)
echo "=========================================="
echo "Test 2: Get Stock Price for AAPL"
echo "Endpoint: GET /v2/stocks/AAPL/quotes/latest"
echo "Purpose: Check if can retrieve real-time stock prices"
echo ""
QUOTE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "https://data.alpaca.markets/v2/stocks/AAPL/quotes/latest" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}")

HTTP_STATUS=$(echo "$QUOTE_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$QUOTE_RESPONSE" | sed '/HTTP_STATUS/d')

echo "Status: $HTTP_STATUS"
echo "Response: $RESPONSE_BODY"

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ SUCCESS: Can get stock prices"
else
    echo "❌ FAILED: Cannot get stock prices (Status: $HTTP_STATUS)"
    if [ "$HTTP_STATUS" == "403" ]; then
        echo "   Note: 403 may indicate no market data subscription"
    fi
fi
echo ""

# Test 3: Get Latest Trade for SPY
echo "=========================================="
echo "Test 3: Get Latest Trade for SPY"
echo "Endpoint: GET /v2/stocks/SPY/trades/latest"
echo "Purpose: Check if can retrieve trade data"
echo ""
TRADE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "https://data.alpaca.markets/v2/stocks/SPY/trades/latest" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}")

HTTP_STATUS=$(echo "$TRADE_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$TRADE_RESPONSE" | sed '/HTTP_STATUS/d')

echo "Status: $HTTP_STATUS"
echo "Response: $RESPONSE_BODY"

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ SUCCESS: Can get trade data"
else
    echo "❌ FAILED: Cannot get trade data (Status: $HTTP_STATUS)"
fi
echo ""

# Test 4: Check Current Positions
echo "=========================================="
echo "Test 4: Check Current Positions"
echo "Endpoint: GET /v2/positions"
echo "Purpose: Check if can view current holdings"
echo ""
POSITIONS_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "https://paper-api.alpaca.markets/v2/positions" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}")

HTTP_STATUS=$(echo "$POSITIONS_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$POSITIONS_RESPONSE" | sed '/HTTP_STATUS/d')

echo "Status: $HTTP_STATUS"
echo "Response: $RESPONSE_BODY"

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ SUCCESS: Can view positions"
    # Count positions
    POSITION_COUNT=$(echo "$RESPONSE_BODY" | grep -o '"symbol"' | wc -l)
    echo "   Current Positions: $POSITION_COUNT"
else
    echo "❌ FAILED: Cannot view positions (Status: $HTTP_STATUS)"
fi
echo ""

# Test 5: Place a Paper Trade (Market Order - DRY RUN)
echo "=========================================="
echo "Test 5: Place Paper Trade (Market Order)"
echo "Endpoint: POST /v2/orders"
echo "Purpose: Test if can place trades on paper account"
echo ""
echo "⚠️  This will attempt to place a REAL paper trade!"
echo "    Order: BUY 1 share of AAPL at market price"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    ORDER_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "https://paper-api.alpaca.markets/v2/orders" \
      -H "APCA-API-KEY-ID: ${API_KEY}" \
      -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
      -H "Content-Type: application/json" \
      -d '{
        "symbol": "AAPL",
        "qty": 1,
        "side": "buy",
        "type": "market",
        "time_in_force": "day"
      }')

    HTTP_STATUS=$(echo "$ORDER_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$ORDER_RESPONSE" | sed '/HTTP_STATUS/d')

    echo "Status: $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"

    if [ "$HTTP_STATUS" == "200" ] || [ "$HTTP_STATUS" == "201" ]; then
        echo "✅ SUCCESS: Can place paper trades!"
        ORDER_ID=$(echo "$RESPONSE_BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        if [ ! -z "$ORDER_ID" ]; then
            echo "   Order ID: $ORDER_ID"
        fi
    else
        echo "❌ FAILED: Cannot place trades (Status: $HTTP_STATUS)"
    fi
else
    echo "⏭️  Skipped trade test"
fi
echo ""

# Test 6: Get Market Clock
echo "=========================================="
echo "Test 6: Check Market Hours"
echo "Endpoint: GET /v2/clock"
echo "Purpose: Check if market is open"
echo ""
CLOCK_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "https://paper-api.alpaca.markets/v2/clock" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}")

HTTP_STATUS=$(echo "$CLOCK_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$CLOCK_RESPONSE" | sed '/HTTP_STATUS/d')

echo "Status: $HTTP_STATUS"
echo "Response: $RESPONSE_BODY"

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ SUCCESS: Can check market hours"
    IS_OPEN=$(echo "$RESPONSE_BODY" | grep -o '"is_open":[^,]*' | cut -d: -f2)
    if [ "$IS_OPEN" == "true" ]; then
        echo "   Market Status: OPEN 🟢"
    else
        echo "   Market Status: CLOSED 🔴"
    fi
else
    echo "❌ FAILED: Cannot check market hours (Status: $HTTP_STATUS)"
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
echo "Capabilities:"
echo "  [ ] Access account information"
echo "  [ ] Get real-time stock prices"
echo "  [ ] Get trade data"
echo "  [ ] View positions"
echo "  [ ] Place paper trades"
echo "  [ ] Check market hours"
echo ""
echo "Based on HTTP status codes:"
echo "  200/201 = ✅ Working"
echo "  401 = ❌ Invalid credentials"
echo "  403 = ❌ Access denied (valid creds but no permission)"
echo "  404 = ❌ Endpoint not found"
echo ""
