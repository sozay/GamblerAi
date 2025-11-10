# Trading Strategy Update - Mean Reversion

## ✅ Changes Applied

### Strategy Changed
**From:** Momentum Breakout
**To:** Mean Reversion / Relative Strength

### Stock List Updated
**Total Stocks:** 25 (was 24)
**Priority Stocks** (First 10 - as requested):
1. AAPL - Apple
2. MSFT - Microsoft
3. GOOGL - Google/Alphabet
4. AMZN - Amazon
5. TSLA - Tesla
6. NVDA - Nvidia
7. META - Meta/Facebook
8. AMD - Advanced Micro Devices
9. NFLX - Netflix
10. SPY - S&P 500 ETF ⭐ **NEW**

**Additional Stocks** (11-25):
ADBE, CSCO, INTC, QCOM, AVGO, TXN, ASML, ORCL, PYPL, CMCSA, PEP, COST, SBUX, ABNB, GILD

---

## 📊 Mean Reversion Strategy Details

### Entry Signals (BUY)
- **RSI < 30** (Oversold condition)
- **Price touches/below lower Bollinger Band** (2.5 standard deviations)
- **Volume spike ≥ 3x average** (Confirms climax selling)
- **Direction:** LONG only (buying oversold stocks)

### Exit Rules
- **Target:** Middle Bollinger Band (return to mean)
- **Stop Loss:** 1% below entry (tighter stop for mean reversion)
- **Time Stop:** Position automatically closes if held too long

### Technical Indicators
- **Bollinger Bands:** 20-period, 2.5 standard deviations
- **RSI:** 14-period
  - Oversold threshold: < 30
  - Overbought threshold: > 70 (not used for entries currently)
- **Volume:** Requires 3x average volume to confirm

### Strategy Logic

```
ENTRY CONDITIONS:
✓ Stock price drops below lower Bollinger Band (2.5σ)
✓ RSI falls below 30 (oversold)
✓ Volume spikes to 3x+ average (selling climax)
→ System BUYS, expecting bounce back to mean

EXIT CONDITIONS:
✓ Price reaches middle Bollinger Band (target hit)
✓ Loss exceeds 1% (stop loss triggered)
✓ Time limit exceeded
```

### Risk Management
- **Position Size:** $10,000 per trade
- **Stop Loss:** 1% (tighter than momentum strategy)
- **Risk/Reward:** Targets return to mean (typically 2-5%)
- **Max Concurrent Positions:** Unlimited (across different stocks)

---

## 🔄 Differences from Previous Strategy

| Aspect | Old (Momentum) | New (Mean Reversion) |
|--------|---------------|----------------------|
| **Entry Signal** | Price up 2%+ with volume | Price oversold (RSI<30, below BB) |
| **Direction** | Follows momentum UP | Buys dips / oversold conditions |
| **Stop Loss** | 2% | 1% (tighter) |
| **Target** | +4% profit | Middle Bollinger Band (mean) |
| **Volume** | 2x average | 3x average (stronger confirmation) |
| **Indicator** | Price change & volume | RSI + Bollinger Bands + Volume |
| **Style** | Trend following | Counter-trend (fading moves) |

---

## 📈 How It Works

### Example Trade Flow

1. **Scanning Phase:**
   - Every 60 seconds, checks all 25 stocks
   - Calculates RSI and Bollinger Bands from recent price data

2. **Signal Detection:**
   ```
   Stock: AAPL
   Price: $175 (at lower BB of $176)
   RSI: 28 (oversold)
   Volume: 4.2x average
   → BUY SIGNAL!
   ```

3. **Position Entry:**
   - Buys $10,000 worth of AAPL
   - Sets stop loss at $173.25 (-1%)
   - Target: Middle BB around $180 (+2.9%)

4. **Position Management:**
   - Monitors price every scan
   - If reaches middle BB → SELL (profit)
   - If drops 1% → SELL (stop loss)

5. **Mean Reversion:**
   - Expects price to "snap back" to average
   - Profits from overextended moves normalizing

---

## 🎯 Strategy Advantages

### Mean Reversion Benefits:
✅ **Buys dips** - Enters at oversold levels
✅ **Better risk/reward** - Buying weakness vs chasing strength
✅ **Higher win rate** - Mean reversion is statistically proven
✅ **Tighter stops** - 1% vs 2% reduces losses
✅ **Multiple indicators** - RSI + BB + Volume = stronger confirmation

### When It Works Best:
- Range-bound markets
- After sharp selloffs
- High liquidity stocks
- Normal market volatility

### When To Be Cautious:
- Strong trending markets (up or down)
- News-driven crashes
- Low volatility periods
- Extended bear markets

---

## 🛠️ Configuration

All strategy parameters are in `/home/ozay/GamblerAi/scripts/alpaca_paper_trading.py` lines 74-91:

```python
# Mean Reversion Strategy parameters
self.strategy_name = "Mean Reversion"
self.bb_period = 20              # Bollinger Band period
self.bb_std = 2.5                # BB standard deviations
self.rsi_oversold = 30           # RSI buy threshold
self.rsi_overbought = 70         # RSI sell threshold
self.stop_loss_pct = 1.0         # Stop loss %
self.target_bb_middle = True     # Target middle BB
self.position_size = 10000       # $10k per trade
```

To adjust parameters, edit these values and restart the service.

---

## 🚀 Running The Updated Strategy

The service file has been updated automatically. Just run:

```bash
cd /home/ozay/GamblerAi
./setup-services.sh
```

Or test manually first:

```bash
venv/bin/python scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,AMD,NFLX,SPY \
  --duration 10 \
  --interval 60
```

---

## 📊 Expected Output

When running, you'll see signals like:

```
⏰ 17:30:00 - Scanning 25 symbols...
   📊 AAPL: LONG RSI=28.5, BB Distance=-2.8%, Vol=4.2x
   📊 TSLA: LONG RSI=29.1, BB Distance=-3.1%, Vol=3.7x
   Active positions: 2, Closed trades: 5, Runtime: 45 min
```

---

## 📖 Further Reading

- **Bollinger Bands:** Measures volatility and overbought/oversold levels
- **RSI (Relative Strength Index):** Momentum oscillator (0-100 scale)
- **Mean Reversion:** Statistical concept that prices tend toward average
- **Volume Confirmation:** Ensures moves are significant, not noise

---

## ⚙️ Next Steps

1. **Setup Services:** Run `./setup-services.sh` to install
2. **Monitor Dashboard:** http://localhost:9090/static/alpaca_dashboard.html
3. **Check Logs:** `sudo journalctl -u gambler-trading -f`
4. **Review Trades:** Query database or check dashboard

**Strategy is ready to run continuously!** 🎯
