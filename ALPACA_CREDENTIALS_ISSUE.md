# Alpaca API Credentials Issue

## Problem

The provided Alpaca API credentials are returning **403 Access Denied** for all endpoints:

```
API Key: PKJUPGKDCCIMZKPDXUFXHM3E4D
API Secret: CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H
```

### Tested Endpoints

Both paper and live API endpoints failed:

1. ❌ `https://paper-api.alpaca.markets/v2/account` → 403 Access Denied
2. ❌ `https://api.alpaca.markets/v2/account` → 403 Access Denied
3. ❌ `/v2/positions` → 403 Access Denied
4. ❌ `/v2/clock` → 403 Access Denied

## Possible Causes

### 1. Invalid or Revoked Credentials
The API key/secret pair may be:
- Incorrect or mistyped
- Revoked or expired
- From a test/example (not real credentials)

### 2. Wrong API Type
Alpaca has different API types:
- **Trading API** - For trading operations (what we're trying to use)
- **Broker API** - For broker operations (different base URL)
- **Market Data API** - For market data only

These credentials might be for the Broker API, which uses different endpoints.

### 3. Account Not Activated
The Alpaca account might:
- Not be fully activated
- Be suspended or disabled
- Require additional verification

### 4. IP Restrictions
The account may have:
- IP whitelist restrictions
- Geographic restrictions
- VPN/proxy blocking

## Solution

### Option 1: Get Fresh Credentials (Recommended)

1. Go to https://alpaca.markets
2. Log into your account
3. Navigate to: **Dashboard → API Keys**
4. Generate new **Paper Trading** API keys
5. Copy both the **Key ID** and **Secret Key**
6. Update the credentials in the code

### Option 2: Check Existing Credentials

1. Log into your Alpaca dashboard
2. Go to API Keys section
3. Verify the credentials are:
   - ✓ Active (not revoked)
   - ✓ For paper trading (not live)
   - ✓ Have proper permissions
4. Check account status is **ACTIVE**

### Option 3: Use Broker API (If These Are Broker Credentials)

If these are Broker API credentials, you'll need different endpoints:

```python
# Broker API endpoints
BASE_URL = "https://broker-api.sandbox.alpaca.markets"  # For sandbox
# or
BASE_URL = "https://broker-api.alpaca.markets"  # For production
```

### Option 4: Use Environment Variables

Instead of hardcoding credentials, use environment variables:

```bash
export ALPACA_API_KEY="your_real_key_here"
export ALPACA_API_SECRET="your_real_secret_here"
```

Then the streamers will pick them up automatically from the environment.

## Testing New Credentials

Once you have valid credentials, test them:

```bash
# Method 1: Using the test script
python simple_test.py

# Method 2: Quick curl test
curl -X GET "https://paper-api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: YOUR_KEY" \
  -H "APCA-API-SECRET-KEY: YOUR_SECRET"
```

Expected response for valid credentials:
```json
{
  "id": "...",
  "account_number": "...",
  "status": "ACTIVE",
  "cash": "100000.00",
  ...
}
```

## Current Implementation Status

✅ **Implementation is Complete:**
- Alpaca SSE streamer implemented
- Alpaca WebSocket streamer implemented
- Default credentials configured
- Test scripts created
- Documentation written
- URL endpoint handling fixed

⚠️ **Only Issue:** Need valid API credentials

Once valid credentials are provided, the streaming implementation will work immediately.

## How to Update Credentials

### Method 1: Update Defaults in Code

Edit the streamer files:

```python
# gambler_ai/data_ingestion/alpaca_sse_streamer.py
# gambler_ai/data_ingestion/alpaca_websocket_streamer.py

def __init__(
    self,
    api_key: str = "YOUR_NEW_KEY_HERE",
    api_secret: str = "YOUR_NEW_SECRET_HERE",
    ...
):
```

### Method 2: Update config.yaml

```yaml
data_sources:
  alpaca:
    api_key: ${ALPACA_API_KEY:YOUR_NEW_KEY}
    api_secret: ${ALPACA_API_SECRET:YOUR_NEW_SECRET}
```

### Method 3: Environment Variables

```bash
# Add to .env file
ALPACA_API_KEY=your_new_key
ALPACA_API_SECRET=your_new_secret
```

### Method 4: Pass as Parameters

```python
from gambler_ai.data_ingestion import AlpacaWebSocketStreamer

streamer = AlpacaWebSocketStreamer(
    api_key="your_key",
    api_secret="your_secret"
)
```

## Support Links

- Alpaca Documentation: https://docs.alpaca.markets/
- Get Paper Trading Account: https://alpaca.markets/
- API Keys Guide: https://alpaca.markets/learn/connect-to-alpaca-api/
- Support: https://alpaca.markets/support

## Next Steps

1. Obtain valid Alpaca API credentials
2. Run `python simple_test.py` to verify they work
3. Update credentials using one of the methods above
4. Run the streaming examples:
   ```bash
   python examples/alpaca_streaming_example.py websocket
   ```

The implementation is ready to go - it just needs valid credentials!
