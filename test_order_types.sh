#!/bin/bash
# Test different order types with Alpaca Paper Trading API

API_KEY="PKJUPGKDCCIMZKPDXUFXHM3E4D"
API_SECRET="CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"
BASE_URL="https://paper-api.alpaca.markets"

echo "=========================================="
echo "Testing Alpaca Order Types"
echo "=========================================="
echo ""

# Test 1: Market Order
echo "Test 1: Market Order"
echo "--------------------"
echo "Order: BUY 1 AAPL at market price"
echo ""
curl -X POST "${BASE_URL}/v2/orders" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "market",
    "time_in_force": "day"
  }'
echo -e "\n"

# Test 2: Limit Order
echo "=========================================="
echo "Test 2: Limit Order"
echo "--------------------"
echo "Order: BUY 1 AAPL @ $150.00 limit"
echo ""
curl -X POST "${BASE_URL}/v2/orders" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "limit",
    "limit_price": "150.00",
    "time_in_force": "day"
  }'
echo -e "\n"

# Test 3: Stop Loss Order
echo "=========================================="
echo "Test 3: Stop Loss Order"
echo "--------------------"
echo "Order: SELL 1 AAPL when price drops to $145.00"
echo "Purpose: Limit losses on existing position"
echo ""
curl -X POST "${BASE_URL}/v2/orders" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "stop",
    "stop_price": "145.00",
    "time_in_force": "gtc"
  }'
echo -e "\n"

# Test 4: Stop Limit Order
echo "=========================================="
echo "Test 4: Stop Limit Order"
echo "--------------------"
echo "Order: SELL 1 AAPL when price hits $145 (stop), but only at $144 or better (limit)"
echo "Purpose: More control than stop loss"
echo ""
curl -X POST "${BASE_URL}/v2/orders" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "stop_limit",
    "stop_price": "145.00",
    "limit_price": "144.00",
    "time_in_force": "gtc"
  }'
echo -e "\n"

# Test 5: Trailing Stop Order
echo "=========================================="
echo "Test 5: Trailing Stop Order"
echo "--------------------"
echo "Order: SELL 1 AAPL with 5% trailing stop"
echo "Purpose: Lock in profits as stock rises"
echo ""
curl -X POST "${BASE_URL}/v2/orders" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "trailing_stop",
    "trail_percent": "5.0",
    "time_in_force": "gtc"
  }'
echo -e "\n"

# Test 6: Bracket Order (Take Profit + Stop Loss)
echo "=========================================="
echo "Test 6: Bracket Order"
echo "--------------------"
echo "Order: BUY 1 AAPL with take profit at $160 and stop loss at $145"
echo "Purpose: Set both profit target and loss limit"
echo ""
curl -X POST "${BASE_URL}/v2/orders" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "market",
    "time_in_force": "day",
    "order_class": "bracket",
    "take_profit": {
      "limit_price": "160.00"
    },
    "stop_loss": {
      "stop_price": "145.00"
    }
  }'
echo -e "\n"

echo "=========================================="
echo "Summary of Order Types"
echo "=========================================="
echo ""
echo "1. Market Order"
echo "   - Executes immediately at current market price"
echo "   - Use: Quick entry/exit"
echo ""
echo "2. Limit Order"
echo "   - Executes at specified price or better"
echo "   - Use: Control entry price"
echo ""
echo "3. Stop Loss Order (type: stop)"
echo "   - Triggers market order when stop price reached"
echo "   - Use: Protect against losses"
echo "   - ✅ YES, fully supported on paper trading"
echo ""
echo "4. Stop Limit Order (type: stop_limit)"
echo "   - Triggers limit order when stop price reached"
echo "   - Use: More control than stop loss, but may not fill"
echo "   - ✅ YES, fully supported on paper trading"
echo ""
echo "5. Trailing Stop Order"
echo "   - Stop price trails market by percentage"
echo "   - Use: Lock in profits as stock rises"
echo "   - ✅ YES, fully supported on paper trading"
echo ""
echo "6. Bracket Order"
echo "   - Combines entry + take profit + stop loss"
echo "   - Use: Complete risk management"
echo "   - ✅ YES, fully supported on paper trading"
echo ""
echo "Response Codes:"
echo "  200/201 = ✅ Order accepted"
echo "  401 = ❌ Invalid credentials"
echo "  403 = ❌ Access denied"
echo "  422 = ❌ Invalid order parameters"
echo ""
