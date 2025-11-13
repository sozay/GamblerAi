# GamblerAI Trading Bot - Comprehensive Architecture Overview
## Mean Reversion + Relative Strength Strategy with 5 Parallel Instances

---

## EXECUTIVE SUMMARY

The GamblerAI trading system is a modular Python-based trading bot that connects to Alpaca's Paper Trading API to automatically detect and execute mean reversion trades. The current architecture supports single-instance operation with state persistence.

**Current State:**
- 1 Trading Service (gambler-trading.service)
- 1 API Service (gambler-api.service)  
- 25 tradeable symbols
- 60-second scan intervals
- Mean Reversion + Relative Strength filtering

---

## 1. CORE SYSTEM COMPONENTS

### 1.1 Trading Bot Architecture

**Main Script:** `/home/user/GamblerAi/scripts/alpaca_paper_trading.py` (898 lines)

**AlpacaPaperTrader Class Structure:**
```
AlpacaPaperTrader
├── Initialization
│   ├── API credentials (Alpaca)
│   ├── Strategy parameters (MR settings)
│   ├── Database connection
│   └── Transaction logging
├── Data Collection
│   ├── get_latest_bars() - Fetch from Alpaca
│   ├── get_account() - Account info
│   └── get_positions() - Open positions
├── Signal Detection
│   ├── detect_mean_reversion() - MR analysis
│   ├── scan_for_signals() - RS filtering + detection
│   └── enter_position() - Trade entry
├── Position Management
│   ├── place_order() - Bracket orders (SL/TP)
│   ├── check_positions() - Monitor & exit
│   └── _update_position_closed() - Track exits
└── State Management
    ├── _save_position() - Persist to DB
    ├── _save_checkpoint() - Periodic snapshots
    └── _check_for_crashed_sessions() - Recovery
```

### 1.2 Strategy Configuration (Current)

**Mean Reversion Parameters (Lines 74-91 in alpaca_paper_trading.py):**
```python
self.strategy_name = "Mean Reversion + Relative Strength"
self.bb_period = 20                    # Bollinger Band lookback
self.bb_std = 2.5                      # Standard deviations
self.rsi_oversold = 30                 # Entry threshold
self.rsi_overbought = 70               # Unused currently
self.stop_loss_pct = 1.0               # Tighter stop
self.target_bb_middle = True           # Target middle band
self.position_size = 10000             # $10k per trade
self.relative_strength_period = 20     # RS lookback
self.use_relative_strength = True      # RS filter enabled
```

**Signal Detection Logic (Lines 652-736):**
```
1. Fetch 100 5-min bars for all symbols + SPY
2. Apply Relative Strength Filter:
   - Calculate SPY return (20-bar)
   - Calculate stock return (20-bar)
   - Only trade stocks where: stock_return > spy_return
3. For filtered symbols:
   - Detect Mean Reversion setups:
     * Price < Lower Bollinger Band (2.5σ)
     * RSI < 30 (oversold)
     * Volume > 3x average
   - Enter position if all conditions met
4. Monitor positions:
   - Exit if target reached (middle BB)
   - Exit if stop loss hit (-1%)
   - Check every 60 seconds
```

### 1.3 System Services (systemd)

**File: `/home/user/GamblerAi/gambler-trading.service`**
```ini
[Unit]
Description=GamblerAI Alpaca Paper Trading Bot
After=network.target

[Service]
Type=simple
User=ozay
WorkingDirectory=/home/ozay/GamblerAi
ExecStart=/home/ozay/GamblerAi/venv/bin/python \
  scripts/alpaca_paper_trading.py \
  --continuous \
  --symbols AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,AMD,NFLX,SPY,... \
  --interval 60
Restart=always
RestartSec=10
StandardOutput=append:/home/ozay/GamblerAi/logs/trading.log
StandardError=append:/home/ozay/GamblerAi/logs/trading.error.log
```

**File: `/home/user/GamblerAi/gambler-api.service`**
```ini
[Unit]
Description=GamblerAI API and Dashboard Server

[Service]
Type=simple
ExecStart=/home/ozay/GamblerAi/venv/bin/uvicorn \
  gambler_ai.api.main:app --host 0.0.0.0 --port 9090
Restart=always
RestartSec=10
```

### 1.4 Web API Structure

**Base URL:** http://localhost:9090

**Routers:**
```
gambler_ai/api/
├── main.py - FastAPI app initialization
└── routes/
    ├── health.py - Health check
    ├── alpaca_trading.py - Trading endpoints
    ├── analysis.py - Analysis endpoints
    ├── patterns.py - Pattern statistics
    └── predictions.py - Predictions
```

**Key Endpoints:**
- `GET /health` - Health check
- `GET /api/v1/alpaca/account` - Account balance
- `GET /api/v1/alpaca/positions` - Open positions
- `GET /api/v1/alpaca/sessions` - Trading sessions
- `GET /api/v1/alpaca/stats` - Performance stats
- `POST /api/v1/analysis` - Run analysis

### 1.5 Web Dashboard

**File:** `/home/user/GamblerAi/static/alpaca_dashboard.html`

**Features:**
- Real-time account metrics
- Active positions with P&L
- Closed trades history
- Win rate & statistics
- Portfolio value updates every 5 seconds

---

## 2. AVAILABLE TRADING STRATEGIES

### 2.1 Mean Reversion (ACTIVE)

**File:** `gambler_ai/analysis/mean_reversion_detector.py`

**Theory:** Prices overshoot and revert to the average (middle Bollinger Band)

**Entry Conditions:**
```
IF (Price < Lower_BB_Band AND RSI < 30 AND Volume > 3x_avg) THEN BUY
```

**Parameters:**
- Bollinger Bands: 20-period, 2.5σ
- RSI: 14-period, threshold 30
- Volume: 3x 20-period average

**Exit Conditions:**
- Target: Price reaches middle BB (mean)
- Stop: 1% below entry
- Time: 30 minute max hold

**Performance:** Best in range-bound and bear markets

---

### 2.2 Volatility Breakout

**File:** `gambler_ai/analysis/volatility_breakout_detector.py`

**Theory:** Breakouts from quiet periods lead to trending moves

**Entry Conditions:**
```
IF (ATR < 50% of avg AND Consolidation_Bars > 20 AND 
    Breakout > 0.5% AND Volume > 2x) THEN BUY_BREAKOUT
```

**Performance:** Best when volatility is low before expansion

---

### 2.3 Momentum Detector

**File:** `gambler_ai/analysis/momentum_detector.py`

**Theory:** Trend-following strategy catching continuation momentum

**Entry Conditions:**
```
IF (Price_Change > 2% AND Volume > 2x AND 
    Continuation_Prob > 60%) THEN BUY_MOMENTUM
```

**Performance:** Best in trending markets

---

### 2.4 Smart Money Detector

**File:** `gambler_ai/analysis/smart_money_detector.py`

Identifies accumulation patterns and institutional buying signals

---

### 2.5 Multi-Timeframe Analyzer

**File:** `gambler_ai/analysis/multi_timeframe_analyzer.py`

Confirms signals across 1min, 5min, 15min, 1hour timeframes

---

### 2.6 Adaptive Strategy Selector

**File:** `gambler_ai/analysis/adaptive_strategy.py`

**Auto-selects strategy based on market regime:**
```
Regime Detection
    ↓
├─ BULL + Low Vol → Multi-Timeframe
├─ BULL + High Vol → Mean Reversion  
├─ BEAR → Mean Reversion
└─ RANGE → Mean Reversion
```

**Status:** Implemented but NOT currently used in alpaca_paper_trading.py

---

## 3. RELATIVE STRENGTH FILTERING DEEP DIVE

**File:** `scripts/alpaca_paper_trading.py` (lines 652-712)

**How It Works:**

1. **Fetch SPY bars** (benchmark)
   ```python
   spy_return = (spy[-1] - spy[-20]) / spy[-20]
   ```

2. **For each stock:**
   ```python
   stock_return = (stock[-1] - stock[-20]) / stock[-20]
   relative_strength = stock_return - spy_return
   ```

3. **Filter:**
   ```python
   if relative_strength > 0:
       # Stock outperforming SPY, add to trading list
   ```

4. **Display results:**
   ```
   ✓ Relative Strength Filter: 12/25 stocks outperforming SPY
   Top performers: NVDA(+2.3%), TSLA(+1.8%), AAPL(+1.2%)
   ```

**Configuration:**
- Period: 20 bars (100 minutes at 5-min intervals)
- Threshold: > 0 (positive outperformance)
- Benchmark: SPY (automatically added to symbol list)

---

## 4. DATABASE & STATE PERSISTENCE

**Database:** SQLite at `/home/ozay/GamblerAi/data/analytics.db`

**Models** (`gambler_ai/storage/models.py`):

### TradingSession
```sql
id (PK), session_id (UUID), start_time, end_time,
status (active|completed|crashed),
symbols (CSV), initial_portfolio_value, final_portfolio_value,
pnl, pnl_pct, total_trades, duration_minutes
```

### Position
```sql
id (PK), session_id (FK), symbol, entry_time, exit_time,
entry_price, exit_price, qty, direction, side,
stop_loss, take_profit, order_id, status (active|closed),
pnl, pnl_pct, duration_minutes, exit_reason
```

### PositionCheckpoint
```sql
id (PK), session_id (FK), checkpoint_time,
positions_snapshot (JSON), account_snapshot (JSON),
active_positions_count, closed_trades_count
```

**Checkpoint Mechanism:**
- Auto-saves every 30 seconds
- Snapshots active positions and account state
- Enables recovery from crashes

---

## 5. SINGLE-INSTANCE LIMITATIONS

| Issue | Current | Problem |
|-------|---------|---------|
| Single Process | 1 trading bot | Can only monitor 25 symbols serially |
| Sequential Scanning | Loop through symbols | 100+ symbols gets slow |
| Single API Account | One Alpaca account | Can't segment by strategy |
| Single Database | SQLite local | Concurrent access issues |
| Hardcoded Strategy | Mean Reversion only | Can't run multiple strategies |
| Fixed Position Size | $10,000 all trades | No strategy differentiation |
| No Allocation | All capital to one strategy | Inefficient capital use |

---

## 6. ARCHITECTURE FOR 5 PARALLEL INSTANCES

### 6.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│              Shared Infrastructure                           │
├─────────────────────────────────────────────────────────────┤
│ • Alpaca API Account (shared credentials)                   │
│ • PostgreSQL Database (w/ row-level locking)                │
│ • Redis Cache (position state, market data)                 │
│ • REST API on port 9090                                     │
│ • Web Dashboard                                             │
└─────────────────────────────────────────────────────────────┘
         ▲
         │ (DB, API, Redis)
         │
    ┌────┴──────────────────────────────────────────────────┐
    │                                                       │
    ▼                                                       ▼
┌─────────────────┐                              ┌──────────────────┐
│  Instance 1     │                              │  Instance 5      │
│ Mean Reversion  │ ──────── ... ────────        │ Relative         │
│ (Bull Markets)  │                              │ Strength Leader  │
│                 │                              │ Following        │
│ 8 symbols       │                              │                  │
│ $50k capital    │                              │ 6 symbols        │
│ 60s interval    │                              │ $50k capital     │
└─────────────────┘                              └──────────────────┘
    │
    Instance 2: Mean Reversion (Bear/ETFs)
    Instance 3: Volatility Breakout
    Instance 4: Momentum Trend-Follow
```

### 6.2 Instance Allocation Strategy

**Instance 1: Mean Reversion - Bull Markets**
```
Strategy: MeanReversionDetector (BB 20/2.5, RSI 30)
Symbols: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, AMD
Focus: Large-cap tech (natural mean reversion)
Position Size: $10,000
Capital Allocation: $50,000
Scan Interval: 60 seconds
Win Rate Target: 55%+
```

**Instance 2: Mean Reversion - Bear/ETFs**
```
Strategy: MeanReversionDetector (BB 20/2.0, RSI 25) [Tighter]
Symbols: SPY, QQQ, IWM, EEM, FXI, GLD, TLT, USO
Focus: ETFs and market downturns (lower risk)
Position Size: $8,000 (smaller for ETFs)
Capital Allocation: $45,000
Scan Interval: 45 seconds (more active)
Win Rate Target: 58%+
```

**Instance 3: Volatility Breakout**
```
Strategy: VolatilityBreakoutDetector
Symbols: ADBE, CSCO, INTC, QCOM, PYPL, AVGO
Focus: Mid-cap tech (volatile, range-bound)
Position Size: $12,000 (wider ranges)
Capital Allocation: $40,000
Scan Interval: 30 seconds
Win Rate Target: 52%+
```

**Instance 4: Momentum Trend-Following**
```
Strategy: MomentumDetector
Symbols: NFLX, ASML, GILD, ABNB, SBUX, COST
Focus: High momentum stocks
Position Size: $10,000
Capital Allocation: $45,000
Scan Interval: 60 seconds
Win Rate Target: 54%+
```

**Instance 5: Relative Strength Leaders**
```
Strategy: AdaptiveStrategySelector (RS filter)
Symbols: PEP, CMCSA, TXN, ORCL, CRM, NOW
Focus: Sector leaders outperforming market
Position Size: $10,000
Capital Allocation: $50,000
Scan Interval: 60 seconds
Win Rate Target: 53%+
```

**Total Resource Allocation:**
- Unique Symbols: ~40-50 (minimal overlap)
- Total Capital: $230,000
- Max Concurrent Positions: ~100 across all instances
- Diversification: Strategy + Symbol + Sector spread

---

## 7. IMPLEMENTATION CHANGES

### 7.1 Configuration File (config.yaml)

Create `/home/user/GamblerAi/config.yaml`:

```yaml
strategies:
  mean-reversion-bull:
    detector_class: MeanReversionDetector
    parameters:
      bb_period: 20
      bb_std: 2.5
      rsi_oversold: 30
      volume_multiplier: 3.0
    position_size: 10000
    stop_loss_pct: 1.0
    max_holding_minutes: 30
  
  mean-reversion-bear:
    detector_class: MeanReversionDetector
    parameters:
      bb_period: 20
      bb_std: 2.0      # Tighter
      rsi_oversold: 25 # More aggressive
      volume_multiplier: 3.0
    position_size: 8000
    stop_loss_pct: 0.8
  
  volatility-breakout:
    detector_class: VolatilityBreakoutDetector
    parameters:
      atr_period: 14
      atr_compression_ratio: 0.5
      consolidation_min_bars: 20
    position_size: 12000
  
  momentum:
    detector_class: MomentumDetector
    parameters:
      min_price_change: 2.0
      min_volume_ratio: 2.0
    position_size: 10000
  
  relative-strength:
    detector_class: AdaptiveStrategySelector
    parameters:
      relative_strength_period: 20
      use_rs_filter: true
    position_size: 10000

instances:
  1:
    name: "Mean Reversion - Bull Markets"
    strategy: mean-reversion-bull
    symbols: [AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, AMD]
    interval_seconds: 60
    allocated_capital: 50000
    max_positions: 10
  
  2:
    name: "Mean Reversion - Bear/ETFs"
    strategy: mean-reversion-bear
    symbols: [SPY, QQQ, IWM, EEM, FXI, GLD, TLT, USO]
    interval_seconds: 45
    allocated_capital: 45000
    max_positions: 8
  
  3:
    name: "Volatility Breakout"
    strategy: volatility-breakout
    symbols: [ADBE, CSCO, INTC, QCOM, PYPL, AVGO]
    interval_seconds: 30
    allocated_capital: 40000
    max_positions: 6
  
  4:
    name: "Momentum Trend-Following"
    strategy: momentum
    symbols: [NFLX, ASML, GILD, ABNB, SBUX, COST]
    interval_seconds: 60
    allocated_capital: 45000
    max_positions: 8
  
  5:
    name: "Relative Strength Leaders"
    strategy: relative-strength
    symbols: [PEP, CMCSA, TXN, ORCL, CRM, NOW]
    interval_seconds: 60
    allocated_capital: 50000
    max_positions: 8
```

### 7.2 Database Schema Addition

```sql
ALTER TABLE trading_session 
ADD COLUMN instance_id INTEGER NOT NULL DEFAULT 1;

ALTER TABLE trading_session 
ADD COLUMN strategy_name VARCHAR(50);

ALTER TABLE trading_session 
ADD COLUMN allocated_capital DECIMAL(12,2);

CREATE INDEX idx_session_instance 
ON trading_session(instance_id, start_time);
```

### 7.3 Service Files (One per Instance)

Create `/etc/systemd/system/gambler-trading-{1-5}.service`

Example for Instance 1:
```ini
[Unit]
Description=GamblerAI Trading Bot - Instance 1 (Mean Reversion Bull)
After=network.target

[Service]
Type=simple
User=ozay
WorkingDirectory=/home/ozay/GamblerAi
Environment="PATH=/home/ozay/GamblerAi/venv/bin"
ExecStart=/home/ozay/GamblerAi/venv/bin/python \
  scripts/alpaca_paper_trading.py \
  --continuous \
  --instance-id 1 \
  --strategy mean-reversion-bull \
  --config config.yaml
Restart=always
RestartSec=15
StandardOutput=append:/home/ozay/GamblerAi/logs/trading-1.log
StandardError=append:/home/ozay/GamblerAi/logs/trading-1.error.log

[Install]
WantedBy=multi-user.target
```

### 7.4 Code Changes to alpaca_paper_trading.py

**Add to __init__:**
```python
def __init__(
    self,
    api_key: str,
    api_secret: str,
    instance_id: int = 1,
    strategy_name: str = "mean-reversion-bull",
    config_file: str = "config.yaml",
    ...
):
    self.instance_id = instance_id
    self.strategy_name = strategy_name
    
    # Load config
    with open(config_file) as f:
        self.config = yaml.safe_load(f)
    
    self.instance_config = self.config['instances'][instance_id]
    self.strategy_config = self.config['strategies'][strategy_name]
    
    # Load strategy parameters
    self.bb_period = self.strategy_config['parameters'].get('bb_period', 20)
    self.bb_std = self.strategy_config['parameters'].get('bb_std', 2.5)
    self.position_size = self.strategy_config.get('position_size', 10000)
    
    # Initialize detector based on strategy
    detector_class = self._get_detector_class(
        self.strategy_config['detector_class']
    )
    self.detector = detector_class(**self.strategy_config['parameters'])
```

**Update logging:**
```python
logging.basicConfig(
    format=f'[INST-{self.instance_id}] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        FileHandler(f'logs/trading-{self.instance_id}.log'),
        StreamHandler()
    ]
)
```

**Update scan_for_signals:**
```python
def scan_for_signals(self, symbols: List[str]):
    print(f"\n[INST-{self.instance_id}] ⏰ {datetime.now().strftime('%H:%M:%S')} - Scanning {len(symbols)}...")
    
    bars_data = self.get_latest_bars(symbols, timeframe='5Min', limit=100)
    
    # Apply strategy-specific filtering
    if self.strategy_config.get('use_rs_filter'):
        symbols = self._apply_relative_strength_filter(symbols, bars_data)
    
    # Detect setups using strategy detector
    for symbol in symbols:
        bars = bars_data.get(symbol, [])
        if not bars:
            continue
        
        # Convert bars to DataFrame
        df = self._bars_to_dataframe(bars)
        
        # Detect setups
        setups = self.detector.detect_setups(df)
        
        for setup in setups:
            if self.can_enter_position(symbol):
                self.enter_position({
                    'symbol': symbol,
                    'entry_price': setup['entry_price'],
                    'target': setup['target'],
                    'stop_loss': setup['stop_loss'],
                    'strategy': self.strategy_name,
                })
```

---

## 8. DEPLOYMENT SCRIPT

Create `setup-multi-services.sh`:

```bash
#!/bin/bash

echo "=== GamblerAI Multi-Instance Service Setup ==="

# Create logs directory
mkdir -p /home/ozay/GamblerAi/logs

# Copy API service
sudo cp /home/ozay/GamblerAi/gambler-api.service /etc/systemd/system/

# Create and enable trading services for instances 1-5
for i in {1..5}; do
    SERVICE="/etc/systemd/system/gambler-trading-$i.service"
    
    case $i in
        1) STRATEGY="mean-reversion-bull" ;;
        2) STRATEGY="mean-reversion-bear" ;;
        3) STRATEGY="volatility-breakout" ;;
        4) STRATEGY="momentum" ;;
        5) STRATEGY="relative-strength" ;;
    esac
    
    sudo tee "$SERVICE" > /dev/null << EOF
[Unit]
Description=GamblerAI Trading Bot - Instance $i
After=network.target

[Service]
Type=simple
User=ozay
WorkingDirectory=/home/ozay/GamblerAi
Environment="PATH=/home/ozay/GamblerAi/venv/bin"
ExecStart=/home/ozay/GamblerAi/venv/bin/python \\
  scripts/alpaca_paper_trading.py \\
  --continuous \\
  --instance-id $i \\
  --strategy $STRATEGY \\
  --config config.yaml
Restart=always
RestartSec=15
StandardOutput=append:/home/ozay/GamblerAi/logs/trading-$i.log
StandardError=append:/home/ozay/GamblerAi/logs/trading-$i.error.log

[Install]
WantedBy=multi-user.target
EOF
    
    echo "✓ Created $SERVICE"
done

# Reload systemd
sudo systemctl daemon-reload

# Enable all services
sudo systemctl enable gambler-api
for i in {1..5}; do
    sudo systemctl enable gambler-trading-$i
done

# Start all services
sudo systemctl start gambler-api
for i in {1..5}; do
    sudo systemctl start gambler-trading-$i
done

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Manage services:"
echo "  sudo systemctl {start|stop|restart|status} gambler-api"
echo "  sudo systemctl {start|stop|restart|status} gambler-trading-{1-5}"
echo ""
echo "View logs:"
echo "  sudo journalctl -u gambler-api -f"
echo "  sudo journalctl -u gambler-trading-{1-5} -f"
echo ""
echo "Dashboard: http://localhost:9090/static/alpaca_dashboard.html"
```

---

## 9. RISK MANAGEMENT FRAMEWORK

### 9.1 Position Limits

**Per Instance:**
- Max concurrent positions: Varies (6-10)
- Max position size: Strategy-specific (8-12K)
- Max daily loss: -5% of allocated capital

**Across All Instances:**
- Max total positions: 50
- Max daily portfolio loss: -10%
- Max margin usage: 50%

### 9.2 Circuit Breakers

```python
def check_circuit_breakers(self):
    if self.daily_pnl < -self.max_daily_loss:
        self.pause_trading("Daily loss limit")
    
    recent = self.get_recent_closed_trades(10)
    if all(t['pnl'] < 0 for t in recent):
        self.pause_trading("10 consecutive losses")
    
    if self.total_exposure > self.max_exposure:
        self.reduce_position_size()
```

---

## 10. MONITORING & OPERATIONS

### Health Check Commands

```bash
# Check all instances
for i in {1..5}; do
  echo "Instance $i:"
  sudo systemctl status gambler-trading-$i --no-pager | grep Active
done

# Check API
curl http://localhost:9090/health

# Check database
psql -h localhost -U gambler -d gambler_analytics \
  -c "SELECT instance_id, COUNT(*) FROM trading_session GROUP BY instance_id;"
```

### Backup Strategy

```bash
# Daily backup
BACKUP_DIR="/backups/gambler-ai/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Database
pg_dump -U gambler gambler_analytics > "$BACKUP_DIR/analytics.sql"

# Keep 7 days
find /backups/gambler-ai -mtime +7 -exec rm -rf {} \;
```

---

## 11. IMPLEMENTATION TIMELINE

### Week 1-2: Core Infrastructure
- [ ] Design config.yaml structure
- [ ] Update database schema for instance_id
- [ ] Create strategy factory pattern
- [ ] Test with Instance 1 only

### Week 2-3: Strategy Integration
- [ ] Make detector selection dynamic
- [ ] Add per-instance logging
- [ ] Implement configurable parameters
- [ ] Test with Instances 1-2

### Week 3-4: Multi-Instance Deployment
- [ ] Create 5 service files
- [ ] Update setup script
- [ ] Deploy and test all instances
- [ ] Verify no resource conflicts

### Week 4-5: Dashboard & Monitoring
- [ ] Add instance selector
- [ ] Create per-instance stats
- [ ] Portfolio overview
- [ ] Pause/resume endpoints

### Week 5-6: Testing & Optimization
- [ ] Load test (5 instances, 50 symbols)
- [ ] Optimize DB queries
- [ ] Tune position limits
- [ ] Document procedures

---

## 12. KEY FILES & DIRECTORIES

```
/home/user/GamblerAi/
├── config.yaml                          # NEW: Strategy definitions
├── scripts/
│   └── alpaca_paper_trading.py         # MODIFIED: Multi-instance support
├── gambler_ai/
│   ├── analysis/
│   │   ├── mean_reversion_detector.py
│   │   ├── volatility_breakout_detector.py
│   │   ├── momentum_detector.py
│   │   ├── smart_money_detector.py
│   │   ├── multi_timeframe_analyzer.py
│   │   └── adaptive_strategy.py
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   │       ├── alpaca_trading.py
│   │       └── health.py
│   ├── storage/
│   │   └── models.py                   # MODIFIED: Add instance_id
│   ├── trading/
│   │   ├── state_manager.py
│   │   └── checkpoint_manager.py
│   └── utils/
│       ├── config.py
│       └── logging.py
├── static/
│   └── alpaca_dashboard.html           # ENHANCED: Multi-instance views
├── logs/
│   ├── trading-1.log
│   ├── trading-2.log
│   └── ...
├── setup-multi-services.sh             # NEW: Multi-instance deployment
└── /etc/systemd/system/
    ├── gambler-trading-1.service       # NEW
    ├── gambler-trading-2.service       # NEW
    └── ...
```

---

## 13. SUCCESS METRICS

**By End of Month 1:**
- [ ] All 5 instances running stably
- [ ] 50+ unique symbols traded
- [ ] Dashboard shows all instances
- [ ] Combined win rate > 54%

**By End of Month 2:**
- [ ] $100k+ deployed across instances
- [ ] Daily P&L stable and positive
- [ ] 0 crashes in 30 days
- [ ] Response time < 2s (all endpoints)

**By End of Month 3:**
- [ ] Dynamic strategy switching working
- [ ] ML-assisted parameter optimization
- [ ] Real trading (not just paper)
- [ ] 60%+ win rate on best instance

---

## CONCLUSION

The current Mean Reversion + Relative Strength strategy is well-architected but limited to single-instance operation. By implementing the 5-instance design outlined above, you can:

1. **Increase capacity** from 25 to 50 symbols
2. **Diversify risk** across 5 different strategies
3. **Test multiple hypotheses** simultaneously
4. **Improve win rate** through specialization
5. **Scale capital** efficiently

The implementation is straightforward (mostly configuration changes and service files), with estimated effort of 4-6 weeks for full deployment with monitoring.

