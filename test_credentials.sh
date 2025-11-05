#!/bin/bash
# Test Alpaca API Credentials with curl

API_KEY="PKJUPGKDCCIMZKPDXUFXHM3E4D"
API_SECRET="CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"

echo "=========================================="
echo "Testing Alpaca API Credentials"
echo "=========================================="
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Test 1: Paper Trading API
echo "Test 1: Paper Trading API"
echo "Endpoint: https://paper-api.alpaca.markets/v2/account"
echo ""
curl -v -X GET "https://paper-api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}"
echo -e "\n"

# Test 2: Live Trading API
echo "=========================================="
echo "Test 2: Live Trading API"
echo "Endpoint: https://api.alpaca.markets/v2/account"
echo ""
curl -v -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}"
echo -e "\n"

# Test 3: Market Clock
echo "=========================================="
echo "Test 3: Market Clock (Paper)"
echo "Endpoint: https://paper-api.alpaca.markets/v2/clock"
echo ""
curl -X GET "https://paper-api.alpaca.markets/v2/clock" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}"
echo -e "\n"

# Test 4: Broker API Sandbox
echo "=========================================="
echo "Test 4: Broker API Sandbox"
echo "Endpoint: https://broker-api.sandbox.alpaca.markets/v1/accounts"
echo ""
curl -X GET "https://broker-api.sandbox.alpaca.markets/v1/accounts" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}"
echo -e "\n"

# Test 5: Broker API Production
echo "=========================================="
echo "Test 5: Broker API Production"
echo "Endpoint: https://broker-api.alpaca.markets/v1/accounts"
echo ""
curl -X GET "https://broker-api.alpaca.markets/v1/accounts" \
  -H "APCA-API-KEY-ID: ${API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${API_SECRET}"
echo -e "\n"

echo "=========================================="
echo "Testing Complete"
echo "=========================================="
echo ""
echo "Expected Results:"
echo "  - 200 OK: Credentials are valid"
echo "  - 401 Unauthorized: Invalid credentials"
echo "  - 403 Forbidden: Valid credentials but no access to this resource"
echo "  - 404 Not Found: Wrong endpoint"
echo ""
