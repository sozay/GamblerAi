# GamblerAI Quick Reference Guide

## Current System Status

### Single Instance Configuration
```
Trading Bot (1 process)
├── 25 tradeable symbols
├── Strategy: Mean Reversion + Relative Strength
├── Scan interval: 60 seconds
├── Position size: $10,000 per trade
└── Port: 9090 (Dashboard)
```

### Key Strategies Available

| Strategy | Entry Signal | Best Market | File |
|----------|-------------|-------------|------|
| **Mean Reversion** | Price oversold (RSI<30, BB) | Range/Bear | mean_reversion_detector.py |
| Volatility Breakout | Breakout from consolidation | Low vol periods | volatility_breakout_detector.py |
| Momentum | Price +2%, Volume 2x | Trending up | momentum_detector.py |
| Smart Money | Institutional patterns | Confirmation | smart_money_detector.py |
| Multi-Timeframe | Cross-timeframe confirms | Bull markets | multi_timeframe_analyzer.py |

### Relative Strength Filter (Currently Active)
```
Feature: Only trades stocks outperforming SPY
Period: 20 bars (100 minutes)
Logic: if (stock_return - spy_return) > 0: TRADE
Result: Filters 25 symbols → typically 12-15 trading candidates
```

---

## Mean Reversion Strategy Details

### Entry Conditions (ALL must be true)
```
1. Price < Lower Bollinger Band (2.5σ)
2. RSI < 30 (oversold)
3. Volume > 3x average
```

### Exit Conditions (First match wins)
```
1. Target Hit: Price reaches Middle Bollinger Band
2. Stop Loss: Price drops 1% below entry
3. Time Stop: Position held > 30 minutes
```

### Current Parameters
| Parameter | Value | Purpose |
|-----------|-------|---------|
| BB Period | 20 | Lookback for Bollinger Bands |
| BB Std Dev | 2.5 | Sensitivity (2.5σ = tighter) |
| RSI Period | 14 | Momentum calculation |
| RSI Threshold | 30 | Oversold definition |
| Volume Mult | 3.0 | Volume spike confirmation |
| Position Size | $10,000 | Risk per trade |
| Stop Loss | 1% | Max loss per trade |

---

## System Architecture

### Files to Know

**Core Trading Logic:**
- `/home/user/GamblerAi/scripts/alpaca_paper_trading.py` - Main trading bot (898 lines)

**Strategy Implementations:**
- `gambler_ai/analysis/mean_reversion_detector.py` - Mean Reversion detection
- `gambler_ai/analysis/adaptive_strategy.py` - Regime-based strategy selector

**Web API & Dashboard:**
- `gambler_ai/api/main.py` - FastAPI server
- `gambler_ai/api/routes/alpaca_trading.py` - Trading endpoints
- `static/alpaca_dashboard.html` - Web dashboard

**Services:**
- `gambler-trading.service` - Trading bot systemd service
- `gambler-api.service` - API server systemd service
- `setup-services.sh` - Deployment script

**Database:**
- `/home/ozay/GamblerAi/data/analytics.db` - SQLite database
- `gambler_ai/storage/models.py` - Data models

**Configuration:**
- `config.yaml` - Strategy definitions (create for multi-instance)
- `.env.template` - Environment variables

---

## Key API Endpoints

### Trading Endpoints
```
GET  /api/v1/alpaca/account          # Account balance & buying power
GET  /api/v1/alpaca/positions        # Currently open positions
GET  /api/v1/alpaca/sessions         # Trading session history
GET  /api/v1/alpaca/stats            # Performance statistics
POST /api/v1/alpaca/close-position   # Manually close a position
```

### Health & Status
```
GET  /health                         # API health check
GET  /api/v1/alpaca/health          # Trading system status
```

---

## Service Management Commands

### Start/Stop Services
```bash
# Start both
sudo systemctl start gambler-api gambler-trading

# Stop both
sudo systemctl stop gambler-api gambler-trading

# Restart both
sudo systemctl restart gambler-api gambler-trading

# Check status
sudo systemctl status gambler-api gambler-trading
```

### View Logs
```bash
# Live trading logs
sudo journalctl -u gambler-trading -f

# Live API logs
sudo journalctl -u gambler-api -f

# Recent logs (last 50 lines)
sudo journalctl -u gambler-trading -n 50
sudo journalctl -u gambler-api -n 50

# Logs from last hour
sudo journalctl -u gambler-trading --since "1 hour ago"
```

### Dashboard Access
```
URL: http://localhost:9090/static/alpaca_dashboard.html
Refreshes: Every 5 seconds
Shows: Account value, positions, P&L, trades
```

---

## Monitoring the System

### Quick Health Check
```bash
# Is API running?
curl http://localhost:9090/health

# How many positions open?
curl http://localhost:9090/api/v1/alpaca/positions | grep '"symbol"' | wc -l

# What's the portfolio P&L?
curl http://localhost:9090/api/v1/alpaca/stats | jq '.total_pnl'

# Are services running?
systemctl status gambler-trading gambler-api --no-pager | grep Active
```

### Database Queries
```bash
# Connect to database
sqlite3 /home/ozay/GamblerAi/data/analytics.db

# Recent trades
SELECT symbol, direction, entry_time, entry_price, pnl FROM position LIMIT 10;

# Win rate
SELECT COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) FROM position WHERE status = 'closed';

# Total P&L
SELECT SUM(pnl) FROM position WHERE status = 'closed';

# Trades per hour
SELECT strftime('%H', entry_time) AS hour, COUNT(*) FROM position GROUP BY hour;
```

---

## 5-Instance Architecture Summary

### Purpose
Replace 1 single-strategy bot with 5 parallel bots using different strategies on different symbols

### Resource Layout
```
Instance 1: Mean Reversion (Bull)      - 8 tech stocks  - $50k
Instance 2: Mean Reversion (Bear)      - 8 ETFs         - $45k
Instance 3: Volatility Breakout        - 6 mid-cap      - $40k
Instance 4: Momentum Trend-Follow       - 6 momentum     - $45k
Instance 5: Relative Strength Leaders  - 6 sector leads - $50k
────────────────────────────────────────────────────────
Total: ~50 unique symbols              Total Capital: $230k
```

### Key Changes Needed
1. Create `config.yaml` with strategy definitions
2. Update database schema (add `instance_id`)
3. Modify `alpaca_paper_trading.py` to accept config
4. Create 5 service files (gambler-trading-{1-5}.service)
5. Update dashboard to show all instances

### Implementation Effort
- **Weeks 1-2:** Config system + testing
- **Weeks 2-3:** Strategy abstraction
- **Weeks 3-4:** Multi-instance deployment
- **Weeks 4-5:** Dashboard updates
- **Weeks 5-6:** Testing & optimization

---

## Troubleshooting

### Service won't start
```bash
# Check for errors
sudo journalctl -u gambler-trading -n 20

# Test connection manually
python scripts/alpaca_paper_trading.py --continuous --symbols AAPL --duration 1

# Verify API credentials
echo $ALPACA_API_KEY
echo $ALPACA_API_SECRET
```

### No trades being executed
```bash
# Check for signals
sudo journalctl -u gambler-trading -f | grep "📊"

# Verify symbols are being scanned
curl http://localhost:9090/api/v1/alpaca/positions

# Check market hours (Alpaca only trades 9:30-16:00 EST, M-F)
date
```

### Dashboard not loading
```bash
# Check API running
curl http://localhost:9090/health

# Check port is open
netstat -tulpn | grep 9090

# Test API endpoint
curl http://localhost:9090/api/v1/alpaca/account
```

### Database locked
```bash
# This shouldn't happen with SQLite, but if it does:
# Kill any stuck processes
pkill -f "alpaca_paper_trading"

# Restart service
sudo systemctl restart gambler-trading
```

---

## Performance Metrics to Track

### Daily Metrics
- Trades executed
- Win rate (% profitable trades)
- Average profit per trade
- Max consecutive losses
- Daily P&L
- Sharpe ratio

### Weekly Metrics
- Total P&L
- Max drawdown
- Win rate trend
- Strategy performance by symbol
- Capital utilization

### Health Metrics
- API response time (target: <500ms)
- Service uptime (target: 99.9%)
- Database query time (target: <100ms)
- Position tracking accuracy

---

## Parameter Tuning Guide

### To make strategy more aggressive (more trades)
- Lower RSI threshold: 30 → 25
- Lower volume requirement: 3x → 2.5x
- Widen BB bands: 2.5σ → 2.0σ

### To make strategy more conservative (fewer trades)
- Raise RSI threshold: 30 → 35
- Raise volume requirement: 3x → 4x
- Tighten BB bands: 2.5σ → 3.0σ

### To reduce risk
- Lower position size: $10k → $8k
- Tighten stop loss: 1% → 0.8%
- Reduce max concurrent positions: 10 → 5

---

## Recent Changes (Latest Commits)

1. **Add Relative Strength filtering** (f3c312b)
   - Filters symbols by outperformance vs SPY
   - Reduces noise, improves win rate

2. **Switch to Mean Reversion strategy** (e1904ee)
   - From momentum breakout to mean reversion
   - Added systemd service support
   - Implements state persistence

3. **Update API port to 9090** (315bf9a)
   - Changed from port 8000 to 9090
   - Dashboard accessible at :9090/static/alpaca_dashboard.html

4. **Add comprehensive session checkpointing** (ca70c4f)
   - Auto-saves every 30 seconds
   - Enables recovery from crashes

---

## Next Steps

### Immediate (This Week)
- [ ] Review current performance metrics
- [ ] Verify all 25 symbols are trading
- [ ] Check relative strength filter is working
- [ ] Monitor win rate (should be 50%+)

### Short-term (Next 2 Weeks)
- [ ] Create config.yaml for multi-instance
- [ ] Test with 2 instances (Bull + Bear)
- [ ] Update database schema
- [ ] Build config loader in alpaca_paper_trading.py

### Medium-term (Month 2)
- [ ] Deploy all 5 instances
- [ ] Update dashboard for multi-instance
- [ ] Implement circuit breakers
- [ ] Optimize database queries

### Long-term (Month 3+)
- [ ] Add ML-based parameter optimization
- [ ] Implement live trading (not just paper)
- [ ] Add alert notifications
- [ ] Build advanced analytics

---

## Key Contact Points

**Trading Bot Main File:**
- Location: `/home/user/GamblerAi/scripts/alpaca_paper_trading.py`
- Entry Point: `if __name__ == "__main__": main()`
- Key Class: `AlpacaPaperTrader`

**Web API:**
- Port: 9090
- Main File: `gambler_ai/api/main.py`
- Docs: http://localhost:9090/docs

**Database:**
- Type: SQLite
- Location: `/home/ozay/GamblerAi/data/analytics.db`
- Models: `gambler_ai/storage/models.py`

**Strategy Detectors:**
- All in: `gambler_ai/analysis/`
- Mean Reversion (active): `mean_reversion_detector.py`
- Others (available): volatility_breakout, momentum, smart_money, multi_timeframe

