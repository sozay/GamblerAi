# Alpaca Paper Trading Setup Guide

This guide will help you run live paper trading with the Alpaca API using real market data.

---

## Step 1: Get Free Alpaca Paper Trading Account

1. Go to **https://alpaca.markets**
2. Click **"Sign Up"**
3. Choose **"Paper Trading"** (100% free, no credit card needed)
4. Complete registration
5. You'll get $100,000 in paper money to trade with

---

## Step 2: Get Your API Keys

1. Log into your Alpaca dashboard
2. Go to **"Your API Keys"** in the left menu
3. You'll see:
   - **API Key ID** (looks like: PKXXX...)
   - **Secret Key** (looks like: xxx...)
4. **IMPORTANT:** Make sure you're using **PAPER TRADING** keys (not live trading)

---

## Step 3: Set Up Environment Variables

### On Linux/Mac:

```bash
export ALPACA_API_KEY='PKxxxxxxxxxxxxxxxxxx'
export ALPACA_API_SECRET='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

### On Windows (PowerShell):

```powershell
$env:ALPACA_API_KEY='PKxxxxxxxxxxxxxxxxxx'
$env:ALPACA_API_SECRET='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

### Or create a `.env` file:

```bash
cd /home/user/GamblerAi
cat > .env << 'EOF'
ALPACA_API_KEY=PKxxxxxxxxxxxxxxxxxx
ALPACA_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

---

## Step 4: Install Required Packages

```bash
pip3 install --break-system-packages requests pandas
```

---

## Step 5: Run Paper Trading

### Quick Test (5 minutes):

```bash
cd /home/user/GamblerAi

python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL \
  --duration 5 \
  --interval 30
```

### Full Session (1 hour):

```bash
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL,TSLA,NVDA \
  --duration 60 \
  --interval 60
```

### With API Keys as Arguments:

```bash
python3 scripts/alpaca_paper_trading.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --symbols AAPL,MSFT \
  --duration 30
```

---

## What It Does

The script will:

1. ✅ **Connect** to Alpaca Paper Trading
2. ✅ **Scan** symbols every 60 seconds for momentum signals
3. ✅ **Detect** momentum events (2%+ move with 2x volume)
4. ✅ **Place** paper orders automatically
5. ✅ **Manage** positions with 2% stop loss and 4% take profit
6. ✅ **Report** performance at the end

---

## Example Output

```
================================================================================
ALPACA PAPER TRADING - LIVE SESSION
================================================================================
Symbols: AAPL, MSFT, GOOGL, TSLA, NVDA
Duration: 60 minutes
Scan Interval: 60 seconds
Strategy: 2.0% stop loss, 4.0% take profit
================================================================================

✓ Connected to Alpaca Paper Trading
  Account Status: ACTIVE
  Buying Power: $100,000.00
  Cash: $100,000.00
  Portfolio Value: $100,000.00

Starting Portfolio Value: $100,000.00

⏰ 14:30:15 - Scanning 5 symbols...
   📊 AAPL: UP 2.3% move, 2.4x volume

🔔 MOMENTUM SIGNAL: AAPL UP
   Entry: $175.50
   Size: 56 shares ($9,828)

✓ Order placed: BUY 56 AAPL @ market
  Stop Loss: $171.99
  Take Profit: $182.52

   Active positions: 1, Closed trades: 0, Time remaining: 59 min

⏰ 14:31:15 - Scanning 5 symbols...
   No signals detected
   Active positions: 1, Closed trades: 0, Time remaining: 58 min

✓ Position CLOSED: AAPL
   Entry: $175.50
   Direction: UP
   Duration: 8 minutes

================================================================================
SESSION COMPLETE
================================================================================

Initial Portfolio Value: $100,000.00
Final Portfolio Value:   $100,393.00
P&L:                     $393.00 (+0.39%)

Total Closed Trades: 1
Active Positions:    0

Closed Trades:
  AAPL: UP, 8 min

================================================================================
```

---

## Strategy Details

### Entry Criteria:
- **Price Move:** 2%+ in 5-minute window
- **Volume:** 2x average volume
- **Direction:** Long or short

### Exit Criteria:
- **Stop Loss:** 2% from entry
- **Take Profit:** 4% from entry
- **Bracket Orders:** Both set automatically

### Position Sizing:
- **$10,000 per trade**
- Automatically calculates number of shares

---

## Monitoring

While running, the script will:

- Scan every 60 seconds (configurable)
- Print detected signals
- Show order placement
- Track position status
- Report P&L continuously

---

## Safety Features

1. ✅ **Paper Trading Only** - Uses paper trading endpoint
2. ✅ **Bracket Orders** - Stop loss and take profit set automatically
3. ✅ **Position Limits** - One position per symbol
4. ✅ **Error Handling** - Catches API errors gracefully
5. ✅ **Manual Override** - Can stop anytime with Ctrl+C

---

## Troubleshooting

### "Connection failed: 403"
- Check your API keys are correct
- Make sure you're using PAPER trading keys
- Verify keys are not expired

### "No signals detected"
- Market may not have momentum right now
- Try during market hours (9:30 AM - 4:00 PM ET)
- Increase scan duration or add more symbols

### "Position size too small"
- Stock price too high for $10k position
- Increase `position_size` in script
- Or trade lower-priced stocks

### "Already in position"
- Script prevents duplicate positions
- Wait for current position to close
- Or trade different symbols

---

## Tips for Success

1. **Run During Market Hours**
   - 9:30 AM - 4:00 PM Eastern Time
   - Most momentum during first/last hour

2. **Start Small**
   - Test with 1-2 symbols first
   - Run for 30 minutes initially
   - Verify orders work correctly

3. **Monitor Carefully**
   - Watch the output
   - Check Alpaca dashboard
   - Verify orders execute properly

4. **Adjust Parameters**
   - Edit `min_price_change_pct` in script
   - Modify `stop_loss_pct` and `take_profit_pct`
   - Change `scan_interval_seconds`

---

## Advanced Usage

### Customize Strategy Parameters:

Edit these lines in `alpaca_paper_trading.py`:

```python
self.min_price_change_pct = 2.0  # Momentum threshold
self.min_volume_ratio = 2.0       # Volume confirmation
self.stop_loss_pct = 2.0          # Stop loss %
self.take_profit_pct = 4.0        # Take profit %
self.position_size = 10000        # $ per trade
```

### Run Multiple Sessions:

```bash
# Morning session (high volatility)
python3 scripts/alpaca_paper_trading.py --duration 120 --interval 30

# Lunch session (low volatility)
python3 scripts/alpaca_paper_trading.py --duration 60 --interval 120

# Afternoon session
python3 scripts/alpaca_paper_trading.py --duration 90 --interval 45
```

---

## Next Steps After Paper Trading

Once you've tested and are satisfied:

1. **Analyze Results**
   - Check win rate
   - Review P&L
   - Identify patterns

2. **Optimize Parameters**
   - Adjust thresholds
   - Test different timeframes
   - Fine-tune exits

3. **Expand Testing**
   - Add more symbols
   - Run longer sessions
   - Test different market conditions

4. **Consider Live Trading** (if profitable)
   - Start with small capital
   - Use same parameters
   - Monitor closely

---

## Important Notes

⚠️ **This is paper trading with fake money**
- No real financial risk
- Perfect for testing
- Results may differ in live trading

⚠️ **Market hours only**
- Run during 9:30 AM - 4:00 PM ET
- Outside hours = limited data

⚠️ **Rate limits**
- Alpaca free tier has API limits
- Don't scan too frequently (<30 seconds)

⚠️ **Not financial advice**
- This is educational software
- Test thoroughly before any real trading
- Understand risks fully

---

## Support

If you have issues:

1. Check Alpaca status: https://status.alpaca.markets
2. Review Alpaca docs: https://alpaca.markets/docs
3. Verify API keys in dashboard
4. Check logs for error messages

---

## Ready to Trade!

Once you have your API keys:

```bash
cd /home/user/GamblerAi

# Set your keys
export ALPACA_API_KEY='your_key_here'
export ALPACA_API_SECRET='your_secret_here'

# Run it!
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL \
  --duration 30 \
  --interval 60
```

**Good luck with your paper trading!** 🚀📈
