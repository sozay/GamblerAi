# GamblerAI Paper Trading - Quick Start Guide

Complete guide to run the momentum trading strategy on Alpaca Paper Trading.

---

## 📋 Prerequisites

### System Requirements
- **Python:** 3.11+
- **OS:** Linux, macOS, or Windows
- **Internet:** Required for API access
- **RAM:** 2GB minimum
- **Disk:** 500MB free space

### Required Python Packages
```bash
pip install pandas numpy requests pyyaml
```

### Alpaca Account (Free)
1. Sign up at: **https://alpaca.markets**
2. Select **"Paper Trading"** (100% free)
3. Get $100,000 in paper money
4. Get API keys from dashboard

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Clone/Download Repository
```bash
cd /path/to/GamblerAi
```

### Step 2: Set Your API Credentials

**Option A: Environment Variables (Recommended)**
```bash
export ALPACA_API_KEY='PKJUPGKDCCIMZKPDXUFXHM3E4D'
export ALPACA_API_SECRET='CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H'
```

**Option B: Create .env File**
```bash
cat > .env << 'EOF'
ALPACA_API_KEY=PKJUPGKDCCIMZKPDXUFXHM3E4D
ALPACA_API_SECRET=CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H
EOF
```

**Option C: Pass as Arguments**
```bash
python3 scripts/alpaca_paper_trading.py \
  --api-key PKJUPGKDCCIMZKPDXUFXHM3E4D \
  --api-secret CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H
```

### Step 3: Run Paper Trading
```bash
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL \
  --duration 30 \
  --interval 60
```

**That's it!** The system will now:
- ✅ Connect to Alpaca Paper Trading
- ✅ Scan for momentum signals every 60 seconds
- ✅ Place paper trades automatically
- ✅ Manage positions with stop loss/take profit
- ✅ Report results after 30 minutes

---

## 📊 What Happens During Trading Session

### Initialization
```
================================================================================
ALPACA PAPER TRADING - LIVE SESSION
================================================================================
Symbols: AAPL, MSFT, GOOGL
Duration: 30 minutes
Scan Interval: 60 seconds
Strategy: 2.0% stop loss, 4.0% take profit
================================================================================

Testing Alpaca Paper Trading connection...
✓ Connected to Alpaca Paper Trading
  Account Status: ACTIVE
  Buying Power: $100,000.00
  Cash: $100,000.00
  Portfolio Value: $100,000.00
```

### Scanning for Signals
```
⏰ 14:30:15 - Scanning 3 symbols...
   📊 AAPL: UP 2.3% move, 2.4x volume
   No signals detected

   Active positions: 0, Closed trades: 0, Time remaining: 29 min
```

### Signal Detection & Order Placement
```
🔔 MOMENTUM SIGNAL: AAPL UP
   Entry: $175.50
   Size: 56 shares ($9,828)

✓ Order placed: BUY 56 AAPL @ market
  Stop Loss: $171.99
  Take Profit: $182.52
```

### Position Closure
```
✓ Position CLOSED: AAPL
   Entry: $175.50
   Direction: UP
   Duration: 8 minutes
```

### Final Report
```
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

## 🎛️ Command Line Options

### Basic Usage
```bash
python3 scripts/alpaca_paper_trading.py [OPTIONS]
```

### Available Options

| Option | Default | Description |
|--------|---------|-------------|
| `--api-key` | env var | Alpaca API Key |
| `--api-secret` | env var | Alpaca API Secret |
| `--symbols` | AAPL,MSFT,GOOGL,TSLA,NVDA | Comma-separated symbols |
| `--duration` | 60 | Session duration (minutes) |
| `--interval` | 60 | Scan interval (seconds) |

### Example Commands

**Short Test (5 minutes)**
```bash
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT \
  --duration 5 \
  --interval 30
```

**Full Trading Day (6.5 hours)**
```bash
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMD,META,NFLX \
  --duration 390 \
  --interval 60
```

**High Frequency Scanning (every 30 seconds)**
```bash
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL \
  --duration 60 \
  --interval 30
```

**Multiple Sessions Throughout Day**
```bash
# Morning session (9:30 AM - 11:30 AM)
python3 scripts/alpaca_paper_trading.py --duration 120 --interval 60

# Lunch session (12:00 PM - 1:00 PM)
python3 scripts/alpaca_paper_trading.py --duration 60 --interval 120

# Afternoon session (2:00 PM - 4:00 PM)
python3 scripts/alpaca_paper_trading.py --duration 120 --interval 60
```

---

## ⚙️ Strategy Configuration

### Default Parameters (in script)

```python
# Entry criteria
min_price_change_pct = 2.0    # Momentum threshold
min_volume_ratio = 2.0         # Volume confirmation

# Exit criteria
stop_loss_pct = 2.0           # Stop loss percentage
take_profit_pct = 4.0         # Take profit percentage

# Position sizing
position_size = 10000         # $10k per trade
```

### How to Customize

**Option 1: Edit the Script**

Open `scripts/alpaca_paper_trading.py` and modify:

```python
# Around line 48-52
self.min_price_change_pct = 2.0    # Change to 1.5 for more signals
self.min_volume_ratio = 2.0         # Change to 1.5 for more signals
self.stop_loss_pct = 2.0            # Change to 1.5 for tighter stops
self.take_profit_pct = 4.0          # Change to 6.0 for larger targets
self.position_size = 10000          # Change to 5000 for smaller trades
```

**Option 2: Create Custom Version**

```bash
cp scripts/alpaca_paper_trading.py scripts/my_custom_strategy.py
# Edit my_custom_strategy.py with your parameters
python3 scripts/my_custom_strategy.py
```

---

## 📈 Monitoring Your Session

### Real-Time Monitoring

The script outputs to both console and log file:

```bash
# Watch in real-time
python3 scripts/alpaca_paper_trading.py | tee session.log

# In another terminal, tail the log
tail -f session.log
```

### Alpaca Dashboard

Monitor in parallel:
1. Open **https://app.alpaca.markets**
2. Go to **"Paper Trading"** dashboard
3. View:
   - Account balance
   - Open positions
   - Order history
   - P&L charts

### Save Session Logs

```bash
# Save with timestamp
python3 scripts/alpaca_paper_trading.py 2>&1 | tee "session_$(date +%Y%m%d_%H%M%S).log"
```

---

## 🔄 Running Multiple Sessions

### Sequential Sessions
```bash
# Run 3 sessions back-to-back
for i in {1..3}; do
  echo "Starting session $i..."
  python3 scripts/alpaca_paper_trading.py --duration 30
  sleep 60  # Wait 1 minute between sessions
done
```

### Continuous Trading (All Day)
```bash
# Run continuously during market hours
while true; do
  hour=$(date +%H)
  # Market hours: 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC)
  if [ $hour -ge 14 ] && [ $hour -lt 21 ]; then
    python3 scripts/alpaca_paper_trading.py --duration 60
  else
    echo "Outside market hours, sleeping..."
    sleep 3600  # Sleep 1 hour
  fi
done
```

### Scheduled Sessions (Cron)
```bash
# Add to crontab: run every hour during market hours
30 9-15 * * 1-5 cd /path/to/GamblerAi && python3 scripts/alpaca_paper_trading.py --duration 60
```

---

## 📊 Understanding the Output

### Signal Detection
```
📊 AAPL: UP 2.3% move, 2.4x volume
```
- **AAPL**: Symbol detected
- **UP**: Bullish momentum (DOWN = bearish)
- **2.3%**: Price moved 2.3% in 5 minutes
- **2.4x**: Volume is 2.4 times average

### Order Placement
```
✓ Order placed: BUY 56 AAPL @ market
  Stop Loss: $171.99
  Take Profit: $182.52
```
- **BUY 56 AAPL**: Long position, 56 shares
- **Stop Loss**: Exit if price drops to $171.99 (2% loss)
- **Take Profit**: Exit if price rises to $182.52 (4% gain)

### Position Status
```
Active positions: 1, Closed trades: 0, Time remaining: 29 min
```
- **Active positions**: Currently open trades
- **Closed trades**: Completed trades this session
- **Time remaining**: Minutes left in session

---

## 🎯 Best Practices

### 1. Start During Market Hours
- **9:30 AM - 4:00 PM Eastern Time**
- Most momentum in first/last hour
- Avoid pre-market (4:00-9:30 AM) and after-hours (4:00-8:00 PM)

### 2. Begin with Short Sessions
```bash
# Test with 5-minute session first
python3 scripts/alpaca_paper_trading.py --duration 5 --symbols AAPL,MSFT

# Then 30 minutes
python3 scripts/alpaca_paper_trading.py --duration 30

# Then full hour
python3 scripts/alpaca_paper_trading.py --duration 60
```

### 3. Monitor First Few Sessions
- Watch the output carefully
- Check Alpaca dashboard
- Verify orders execute correctly
- Confirm P&L calculations

### 4. Keep Logs
```bash
mkdir -p logs
python3 scripts/alpaca_paper_trading.py 2>&1 | tee "logs/session_$(date +%Y%m%d_%H%M%S).log"
```

### 5. Review Performance Daily
```bash
# Analyze your logs
grep "SESSION COMPLETE" logs/*.log
grep "P&L:" logs/*.log
```

---

## 🚨 Important Trading Hours

### US Market Hours (Eastern Time)

| Period | Hours (ET) | Activity |
|--------|------------|----------|
| Pre-Market | 4:00 AM - 9:30 AM | Low volume, avoid |
| **Market Open** | **9:30 AM - 10:30 AM** | **High volatility, best for momentum** |
| Mid-Day | 10:30 AM - 2:00 PM | Lower activity |
| Lunch | 12:00 PM - 1:00 PM | Lowest volume |
| **Market Close** | **3:00 PM - 4:00 PM** | **High volatility, good for momentum** |
| After-Hours | 4:00 PM - 8:00 PM | Low volume, avoid |

### Recommended Trading Times
```bash
# Best: First hour after open
python3 scripts/alpaca_paper_trading.py --duration 60  # 9:30-10:30 AM

# Best: Last hour before close
python3 scripts/alpaca_paper_trading.py --duration 60  # 3:00-4:00 PM

# Avoid: Lunch hour
# (Don't run between 12:00-1:00 PM)
```

---

## 📁 File Structure

```
GamblerAi/
├── scripts/
│   ├── alpaca_paper_trading.py          # Main paper trading script
│   ├── backtest_screening.py            # Historical backtest
│   ├── demo_backtest.py                 # Demo with synthetic data
│   ├── optimize_parameters.py           # Parameter optimization
│   └── visualize_backtest.py            # Performance charts
├── config.yaml                          # Configuration file
├── .env                                 # Your API credentials (create this)
├── PAPER_TRADING_SETUP.md              # Detailed setup guide
├── RUNNING_INSTRUCTIONS.md             # This file
└── logs/                               # Session logs (create this)
```

---

## 🔐 Security Notes

### Protecting Your API Keys

**Never commit API keys to git:**
```bash
echo ".env" >> .gitignore
echo "*.log" >> .gitignore
```

**Use environment variables:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export ALPACA_API_KEY='your_key'
export ALPACA_API_SECRET='your_secret'
```

**File permissions:**
```bash
chmod 600 .env  # Only you can read/write
```

### API Key Safety
- ✅ Use **Paper Trading** keys only
- ✅ Never share your secret key
- ✅ Regenerate keys if exposed
- ✅ Don't use production keys for testing
- ✅ Keep keys out of version control

---

## 📞 Next Steps

1. **Set up credentials** (2 minutes)
   ```bash
   export ALPACA_API_KEY='PKJUPGKDCCIMZKPDXUFXHM3E4D'
   export ALPACA_API_SECRET='CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H'
   ```

2. **Test connection** (1 minute)
   ```bash
   python3 scripts/alpaca_paper_trading.py --duration 1
   ```

3. **Run first session** (30 minutes)
   ```bash
   python3 scripts/alpaca_paper_trading.py --duration 30 --symbols AAPL,MSFT
   ```

4. **Review results** (5 minutes)
   - Check final P&L
   - Review Alpaca dashboard
   - Analyze trades

5. **Optimize and scale** (ongoing)
   - Adjust parameters
   - Add more symbols
   - Run longer sessions

---

## 🎓 Learning Resources

- **Alpaca Docs**: https://alpaca.markets/docs
- **API Reference**: https://alpaca.markets/docs/api-references/trading-api/
- **Paper Trading Dashboard**: https://app.alpaca.markets
- **Market Data**: https://alpaca.markets/docs/market-data/

---

**Ready to trade!** 🚀📈

Run your first session now:
```bash
python3 scripts/alpaca_paper_trading.py --symbols AAPL,MSFT,GOOGL --duration 30
```
