# GamblerAI Paper Trading - Troubleshooting Guide

Common issues and solutions for running the paper trading system.

---

## 🔌 Connection Issues

### ❌ "Connection failed: 403 - Access denied"

**Cause:** Invalid API credentials or network block

**Solutions:**

1. **Verify API Keys**
   ```bash
   # Check if keys are set
   echo $ALPACA_API_KEY
   echo $ALPACA_API_SECRET

   # Should output your keys, not empty
   ```

2. **Check Key Format**
   - API Key should start with `PK`
   - API Secret is a long alphanumeric string
   - No spaces or quotes in the values

3. **Verify Keys in Alpaca Dashboard**
   - Log into https://app.alpaca.markets
   - Go to "API Keys"
   - Confirm you're using **Paper Trading** keys (not live)
   - Regenerate keys if needed

4. **Test Keys Directly**
   ```bash
   curl -X GET "https://paper-api.alpaca.markets/v2/account" \
     -H "APCA-API-KEY-ID: YOUR_KEY" \
     -H "APCA-API-SECRET-KEY: YOUR_SECRET"
   ```

5. **Network/Firewall Issues**
   - Check if your network blocks Alpaca API
   - Try from different network
   - Check firewall rules
   - Verify DNS resolution: `ping paper-api.alpaca.markets`

---

### ❌ "ERROR: Alpaca API credentials required!"

**Cause:** API keys not set

**Solution:**

```bash
# Set environment variables
export ALPACA_API_KEY='PKJUPGKDCCIMZKPDXUFXHM3E4D'
export ALPACA_API_SECRET='CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H'

# Or pass as arguments
python3 scripts/alpaca_paper_trading.py \
  --api-key PKJUPGKDCCIMZKPDXUFXHM3E4D \
  --api-secret CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H
```

---

### ❌ "Connection timeout"

**Cause:** Network issues or Alpaca API down

**Solutions:**

1. **Check Alpaca Status**
   - Visit: https://status.alpaca.markets
   - Look for API outages

2. **Test Internet Connection**
   ```bash
   ping -c 4 google.com
   curl -I https://alpaca.markets
   ```

3. **Try Again**
   - Network issues may be temporary
   - Wait 1-2 minutes and retry

---

## 📊 Data Issues

### ❌ "No signals detected" (for entire session)

**Cause:** Market conditions or parameters too strict

**Solutions:**

1. **Check Market Hours**
   - Must run during 9:30 AM - 4:00 PM Eastern Time
   - Outside hours = no data

2. **Verify Symbols Are Trading**
   ```bash
   # Check if market is open
   curl -X GET "https://paper-api.alpaca.markets/v2/clock" \
     -H "APCA-API-KEY-ID: YOUR_KEY" \
     -H "APCA-API-SECRET-KEY: YOUR_SECRET"
   ```

3. **Relax Parameters**
   Edit `scripts/alpaca_paper_trading.py`:
   ```python
   self.min_price_change_pct = 1.5  # Lower from 2.0
   self.min_volume_ratio = 1.5      # Lower from 2.0
   ```

4. **Add More Symbols**
   ```bash
   python3 scripts/alpaca_paper_trading.py \
     --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMD,META,NFLX,DIS,AMZN
   ```

5. **Increase Scan Frequency**
   ```bash
   python3 scripts/alpaca_paper_trading.py --interval 30  # Every 30 seconds
   ```

---

### ❌ "Failed to get bars: 422"

**Cause:** Invalid timeframe or date range

**Solutions:**

1. **Check Timeframe**
   - Valid: `1Min`, `5Min`, `15Min`, `1Hour`, `1Day`
   - Case-sensitive!

2. **Verify Date Range**
   - Can't request future dates
   - Historical limit varies by timeframe

---

### ❌ "No data returned for symbol"

**Cause:** Symbol doesn't exist or not available

**Solutions:**

1. **Verify Symbol**
   - Check correct ticker (e.g., `GOOGL` not `GOOGLE`)
   - Symbol must trade on US exchanges

2. **Check Symbol Availability**
   ```bash
   curl -X GET "https://data.alpaca.markets/v2/stocks/AAPL/bars?timeframe=5Min&limit=1" \
     -H "APCA-API-KEY-ID: YOUR_KEY" \
     -H "APCA-API-SECRET-KEY: YOUR_SECRET"
   ```

---

## 💰 Order Issues

### ❌ "Order failed: insufficient buying power"

**Cause:** Not enough cash in paper account

**Solutions:**

1. **Check Account Balance**
   ```bash
   curl -X GET "https://paper-api.alpaca.markets/v2/account" \
     -H "APCA-API-KEY-ID: YOUR_KEY" \
     -H "APCA-API-SECRET-KEY: YOUR_SECRET"
   ```

2. **Reset Paper Account**
   - Log into Alpaca dashboard
   - Go to "Settings"
   - Click "Reset Paper Account"
   - Resets to $100,000

3. **Reduce Position Size**
   Edit script:
   ```python
   self.position_size = 5000  # Reduce from 10000
   ```

---

### ❌ "Order failed: symbol not tradable"

**Cause:** Market closed or symbol suspended

**Solutions:**

1. **Check Market Hours**
   - Paper trading follows real market hours
   - 9:30 AM - 4:00 PM ET

2. **Check Symbol Status**
   ```bash
   curl -X GET "https://paper-api.alpaca.markets/v2/assets/AAPL" \
     -H "APCA-API-KEY-ID: YOUR_KEY" \
     -H "APCA-API-SECRET-KEY: YOUR_SECRET"
   ```

---

### ❌ "Position size too small"

**Cause:** Stock price too high for $10k position

**Solutions:**

1. **Increase Position Size**
   ```python
   self.position_size = 20000  # Increase from 10000
   ```

2. **Trade Lower-Priced Stocks**
   ```bash
   python3 scripts/alpaca_paper_trading.py --symbols AMD,F,BAC,AAL
   ```

---

## 🐍 Python Issues

### ❌ "ModuleNotFoundError: No module named 'pandas'"

**Cause:** Required packages not installed

**Solution:**
```bash
pip install pandas numpy requests pyyaml
# or
pip install -r requirements.txt
```

---

### ❌ "ImportError: cannot import name 'X'"

**Cause:** Wrong Python version or corrupted installation

**Solution:**
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Reinstall packages
pip3 uninstall pandas numpy requests
pip3 install pandas numpy requests
```

---

### ❌ "SyntaxError" or "IndentationError"

**Cause:** Script was modified incorrectly

**Solution:**
```bash
# Restore original script
git checkout scripts/alpaca_paper_trading.py

# Or re-download from repository
```

---

## ⏱️ Performance Issues

### ❌ Script running very slowly

**Cause:** Network latency or too many symbols

**Solutions:**

1. **Reduce Number of Symbols**
   ```bash
   python3 scripts/alpaca_paper_trading.py --symbols AAPL,MSFT,GOOGL  # Only 3
   ```

2. **Increase Scan Interval**
   ```bash
   python3 scripts/alpaca_paper_trading.py --interval 120  # Every 2 minutes
   ```

3. **Check Network Speed**
   ```bash
   speedtest-cli  # or visit speedtest.net
   ```

---

### ❌ "Rate limit exceeded"

**Cause:** Too many API requests

**Solutions:**

1. **Increase Scan Interval**
   ```bash
   python3 scripts/alpaca_paper_trading.py --interval 60  # Minimum 60 seconds
   ```

2. **Reduce Number of Symbols**
   - Each symbol = 1 API call
   - Limit to 5-10 symbols max

3. **Wait and Retry**
   - Rate limits reset after 1 minute
   - Script will retry automatically

---

## 📝 Log Issues

### ❌ "Permission denied" when saving logs

**Cause:** No write permissions

**Solution:**
```bash
# Create logs directory
mkdir -p logs
chmod 755 logs

# Run with proper permissions
python3 scripts/alpaca_paper_trading.py 2>&1 | tee logs/session.log
```

---

### ❌ Logs not saving

**Cause:** Output not redirected

**Solution:**
```bash
# Save to log file
python3 scripts/alpaca_paper_trading.py 2>&1 | tee session.log

# Or redirect both stdout and stderr
python3 scripts/alpaca_paper_trading.py > session.log 2>&1
```

---

## 🎯 Strategy Issues

### ❌ Too many losing trades

**Cause:** Market conditions or parameters

**Solutions:**

1. **Tighten Entry Criteria**
   ```python
   self.min_price_change_pct = 2.5  # Increase from 2.0
   self.min_volume_ratio = 2.5      # Increase from 2.0
   ```

2. **Adjust Risk/Reward**
   ```python
   self.stop_loss_pct = 1.5         # Tighter stop
   self.take_profit_pct = 3.0       # Smaller target
   ```

3. **Add Time Filters**
   - Avoid first 10 minutes after open
   - Avoid lunch hour (12:00-1:00 PM)
   - Focus on best times (9:30-10:30 AM, 3:00-4:00 PM)

4. **Run Backtest First**
   ```bash
   python3 scripts/demo_backtest.py --symbols AAPL,MSFT,GOOGL
   ```

---

### ❌ Positions not closing

**Cause:** Stop/take profit not hit

**Solutions:**

1. **Check Alpaca Dashboard**
   - View open orders
   - Verify bracket orders are active

2. **Check Market Hours**
   - Orders only execute during market hours
   - After-hours: orders queued for next day

3. **Manual Close**
   - Log into Alpaca dashboard
   - Go to "Positions"
   - Click "Close Position"

---

## 🔧 Configuration Issues

### ❌ "FileNotFoundError: config.yaml"

**Cause:** Wrong directory

**Solution:**
```bash
# Make sure you're in project root
cd /path/to/GamblerAi

# Verify config exists
ls config.yaml

# Run from correct directory
python3 scripts/alpaca_paper_trading.py
```

---

### ❌ "YAML parsing error"

**Cause:** Invalid YAML syntax in config.yaml

**Solution:**
```bash
# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Or restore original
git checkout config.yaml
```

---

## 🆘 Getting Help

### Check Alpaca Status
- **API Status**: https://status.alpaca.markets
- **Documentation**: https://alpaca.markets/docs
- **Community**: https://forum.alpaca.markets

### Debug Mode

Add debug output to script:

```python
# At top of script
import logging
logging.basicConfig(level=logging.DEBUG)

# Before API calls
print(f"DEBUG: Calling {url} with {params}")
```

### Capture Full Output

```bash
# Save everything
python3 scripts/alpaca_paper_trading.py 2>&1 | tee debug.log

# Share debug.log for help
```

### Test Each Component

**1. Test API Connection:**
```bash
curl -X GET "https://paper-api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: YOUR_KEY" \
  -H "APCA-API-SECRET-KEY: YOUR_SECRET"
```

**2. Test Data Fetch:**
```bash
curl -X GET "https://data.alpaca.markets/v2/stocks/AAPL/bars?timeframe=5Min&limit=10" \
  -H "APCA-API-KEY-ID: YOUR_KEY" \
  -H "APCA-API-SECRET-KEY: YOUR_SECRET"
```

**3. Test Script Import:**
```python
python3 -c "from scripts.alpaca_paper_trading import AlpacaPaperTrader; print('✓ Import OK')"
```

---

## 📋 Pre-Flight Checklist

Before each session, verify:

- [ ] Python 3.11+ installed: `python3 --version`
- [ ] Packages installed: `pip list | grep -E "(pandas|numpy|requests)"`
- [ ] API keys set: `echo $ALPACA_API_KEY`
- [ ] Network connection: `ping paper-api.alpaca.markets`
- [ ] Market hours: 9:30 AM - 4:00 PM ET
- [ ] Alpaca status: https://status.alpaca.markets
- [ ] Paper account funded: Check dashboard
- [ ] In correct directory: `ls scripts/alpaca_paper_trading.py`

---

## 🔍 Quick Diagnostic

Run this to check your setup:

```bash
#!/bin/bash
echo "=== GamblerAI Paper Trading Diagnostic ==="
echo ""
echo "1. Python Version:"
python3 --version
echo ""
echo "2. Required Packages:"
pip3 list | grep -E "(pandas|numpy|requests)" || echo "❌ Missing packages"
echo ""
echo "3. API Keys Set:"
if [ -n "$ALPACA_API_KEY" ]; then
  echo "✓ ALPACA_API_KEY set"
else
  echo "❌ ALPACA_API_KEY not set"
fi
if [ -n "$ALPACA_API_SECRET" ]; then
  echo "✓ ALPACA_API_SECRET set"
else
  echo "❌ ALPACA_API_SECRET not set"
fi
echo ""
echo "4. Network Test:"
ping -c 2 paper-api.alpaca.markets 2>/dev/null && echo "✓ Network OK" || echo "❌ Network issue"
echo ""
echo "5. Files:"
ls scripts/alpaca_paper_trading.py 2>/dev/null && echo "✓ Script exists" || echo "❌ Script missing"
ls config.yaml 2>/dev/null && echo "✓ Config exists" || echo "❌ Config missing"
echo ""
echo "=== Diagnostic Complete ==="
```

Save as `diagnostic.sh`, make executable, and run:
```bash
chmod +x diagnostic.sh
./diagnostic.sh
```

---

## 💡 Tips for Success

1. **Start Small**: Test with 1-2 symbols and 5-minute sessions
2. **Monitor First Sessions**: Watch output carefully
3. **Check Alpaca Dashboard**: Verify orders execute correctly
4. **Keep Logs**: Save output for analysis
5. **Run During Active Hours**: 9:30-10:30 AM or 3:00-4:00 PM
6. **Be Patient**: Momentum signals don't happen every minute
7. **Paper Trade First**: Don't go live until strategy is proven

---

## 🎓 Common Mistakes to Avoid

1. ❌ Running outside market hours
2. ❌ Using live trading keys instead of paper
3. ❌ Scanning too frequently (< 30 seconds)
4. ❌ Trading too many symbols at once
5. ❌ Not checking account balance
6. ❌ Modifying script without backup
7. ❌ Expecting signals every minute
8. ❌ Not monitoring first sessions
9. ❌ Ignoring API rate limits
10. ❌ Not keeping logs

---

**Still having issues?** Check:
1. This troubleshooting guide
2. PAPER_TRADING_SETUP.md
3. RUNNING_INSTRUCTIONS.md
4. Alpaca documentation

**Ready to trade!** 🚀
