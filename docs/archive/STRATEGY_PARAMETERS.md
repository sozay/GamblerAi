# Strategy Parameters Used in Simulations

## Overview

This document shows all the exact parameters used during the 2024 backtest simulations. These are the "knobs and dials" that control how each strategy detects trading opportunities.

---

## 🎯 General Simulation Settings

**Common Parameters (All Strategies):**
```python
STARTING_CAPITAL = $10,000 (or $100,000)
RISK_PER_TRADE = 1% of capital (0.01)
MAX_CONCURRENT_TRADES = 3
TIME_STOP = 60 bars (5 hours on 5-minute data)
DATA_PERIOD = 2024 Full Year (5000 bars)
DATA_INTERVAL = 5 minutes
```

---

## 📈 Strategy 1: Momentum Continuation

**Entry Parameters:**
```python
MIN_PRICE_CHANGE_PCT = 2.0%        # Minimum price move to detect momentum
MIN_VOLUME_RATIO = 2.0x            # Volume must be 2x average
WINDOW_MINUTES = 5                 # Detection window size
LOOKBACK_PERIODS = 20              # For volume average calculation
```

**Exit Parameters:**
```python
TARGET = Entry ± 3%                # Take profit at 3% move
STOP_LOSS = Entry ± 1%             # Stop loss at 1% move
TIME_STOP = 60 bars (5 hours)      # Exit if no target/stop hit
```

**Entry Logic:**
```
IF (|Price Change| >= 2.0% AND Volume >= 2x Average):
    ENTER trade in direction of momentum
    SET Target = Entry ± 3%
    SET Stop = Entry ± 1%
```

---

## 📉 Strategy 2: Mean Reversion

**Entry Parameters:**
```python
BB_PERIOD = 20                     # Bollinger Band period
BB_STD = 2.5                       # Standard deviations (wider bands)
RSI_PERIOD = 14                    # RSI calculation period
RSI_OVERSOLD = 30                  # Oversold threshold for LONG
RSI_OVERBOUGHT = 70                # Overbought threshold for SHORT
VOLUME_MULTIPLIER = 3.0x           # Volume spike threshold
```

**Exit Parameters:**
```python
TARGET = Middle Bollinger Band     # Return to mean
STOP_LOSS = Entry ± 1%             # Conservative stop
TIME_STOP = 30 minutes             # Faster exit for mean reversion
```

**Entry Logic:**
```
LONG Entry:
  IF (Price <= BB_Lower AND RSI < 30 AND Volume > 3x Average):
      ENTER LONG
      TARGET = Middle BB (mean)
      STOP = Entry - 1%

SHORT Entry:
  IF (Price >= BB_Upper AND RSI > 70 AND Volume > 3x Average):
      ENTER SHORT
      TARGET = Middle BB (mean)
      STOP = Entry + 1%
```

**Why These Values:**
- BB_STD = 2.5 (not 2.0) = Only catches extreme moves
- Volume 3x = Ensures exhaustion/climax volume
- RSI 30/70 = Conservative extremes (not 20/80)

---

## 💥 Strategy 3: Volatility Breakout

**Entry Parameters:**
```python
ATR_PERIOD = 14                    # ATR calculation period
ATR_COMPRESSION_RATIO = 0.5        # ATR must be <50% of average
CONSOLIDATION_MIN_BARS = 20        # Minimum consolidation period
BREAKOUT_THRESHOLD_PCT = 0.5%      # Breakout confirmation
VOLUME_MULTIPLIER = 2.0x           # Volume on breakout
```

**Exit Parameters:**
```python
TARGET = 1.5x Consolidation Range  # Multiple of range size
STOP_LOSS = Opposite side of range # Just below/above range
TIME_STOP = 90 minutes             # Longer for breakout development
```

**Entry Logic:**
```
Step 1: Detect Compression
  IF (Current ATR < 0.5 × 20-period Average ATR):
      Mark as compressed
      Track range HIGH and LOW for 20+ bars

Step 2: Detect Breakout
  IF (Price > Range High × 1.005 AND Volume > 2x Average):
      ENTER LONG
      TARGET = Entry + (Range Size × 1.5)
      STOP = Range Low

  IF (Price < Range Low × 0.995 AND Volume > 2x Average):
      ENTER SHORT
      TARGET = Entry - (Range Size × 1.5)
      STOP = Range High
```

**Why These Values:**
- ATR 0.5x = True compression (not just lower volatility)
- 20 bars = Sufficient time for valid consolidation
- 1.5x range = Statistical average expansion

---

## 🎯 Strategy 4: Multi-Timeframe Confluence

**Entry Parameters:**
```python
TREND_MA_PERIOD = 20               # EMA for trend identification
MIN_CONFLUENCE_SCORE = 3           # Need 3 out of 5 factors
RSI_PERIOD = 14                    # RSI momentum
VOLUME_RATIO_THRESHOLD = 1.5x      # Volume confirmation
DISTANCE_FROM_EMA_PCT = 0.5%       # "At key level" threshold
```

**Confluence Factors (Score 0-5):**
```python
Factor 1: Trend Alignment (1 point)
  - Price > EMA20 > EMA50 (bullish)
  - Price < EMA20 < EMA50 (bearish)

Factor 2: At Key Level (1 point)
  - Price within 0.5% of EMA20

Factor 3: Volume Confirmation (1 point)
  - Volume > 1.5x average

Factor 4: RSI Alignment (1 point)
  - RSI 45-55 (neutral momentum) OR
  - RSI 50-70 for LONG OR
  - RSI 30-50 for SHORT

Factor 5: VWAP Alignment (1 point)
  - Price > VWAP for LONG
  - Price < VWAP for SHORT
```

**Exit Parameters:**
```python
TARGET = Entry ± 2.5%              # Fixed percentage target
STOP_LOSS = EMA50                  # Dynamic support/resistance
TIME_STOP = 120 minutes (2 hours)  # Longer for trend following
```

**Entry Logic:**
```
Step 1: Calculate Confluence Score
  score = 0
  IF trend_aligned: score += 1
  IF at_key_level: score += 1
  IF volume_confirmed: score += 1
  IF rsi_aligned: score += 1
  IF vwap_aligned: score += 1

Step 2: Entry Decision
  IF (score >= 3 AND direction != NEUTRAL):
      ENTER in confirmed direction
      TARGET = Entry ± 2.5%
      STOP = EMA50 level
```

**Why These Values:**
- Score 3/5 = Balance between selectivity and opportunity
- EMA20/50 = Standard timeframe separation
- 0.5% key level = Tight enough to be meaningful

---

## 💰 Strategy 5: Smart Money Tracker

**Entry Parameters:**
```python
VOLUME_ANOMALY_THRESHOLD = 5.0x    # Institutional size orders
ABSORPTION_EFFICIENCY = 0.5        # Price/volume ratio
LEVEL_TEST_MIN = 2                 # Minimum support/resistance tests
VWAP_LOOKBACK = 5 bars             # For VWAP reclaim detection
```

**Pattern Detection:**

**Pattern 1: Absorption**
```python
IF (Volume > 5x Average AND
    Spread < 0.5 × Expected_Spread):

    # Determine direction from close position
    IF Close_Position_In_Bar > 60%:
        ENTER LONG (bullish absorption)
    ELIF Close_Position_In_Bar < 40%:
        ENTER SHORT (bearish absorption)

    TARGET = Entry ± 2%
    STOP = Bar Low/High ± 1%
```

**Pattern 2: VWAP Reclaim**
```python
IF (Price was below VWAP in last 5 bars AND
    Current bar reclaims VWAP):

    ENTER LONG
    TARGET = Entry + 2.5%
    STOP = Current Low - 0.5%
```

**Pattern 3: Level Defense**
```python
IF (Support tested 2+ times within 0.5% range AND
    Price breaks above with Volume > 2x):

    ENTER LONG
    TARGET = Entry + 3%
    STOP = Support - 1%
```

**Exit Parameters:**
```python
TARGET = Entry ± 2-3%              # Varies by pattern
STOP_LOSS = Below accumulation zone # Pattern dependent
TIME_STOP = 90 minutes             # Medium duration
```

**Why These Values:**
- 5x volume = True institutional activity
- 0.5 efficiency = High volume, low movement (absorption)
- 2+ tests = Confirmed level (not random touch)

---

## 🔧 Parameter Optimization Potential

**Parameters That Can Be Tuned:**

### High Impact (Change behavior significantly):
- `MIN_PRICE_CHANGE_PCT` (Momentum) - Higher = fewer, stronger signals
- `BB_STD` (Mean Reversion) - Higher = rarer but more extreme
- `MIN_CONFLUENCE_SCORE` (Multi-TF) - Higher = more selective
- `VOLUME_ANOMALY_THRESHOLD` (Smart Money) - Higher = only massive orders

### Medium Impact (Moderate effect):
- `RSI_OVERSOLD/OVERBOUGHT` (Mean Reversion) - Adjust sensitivity
- `ATR_COMPRESSION_RATIO` (Vol Breakout) - Tighter = rarer setups
- `TIME_STOP` (All) - Affects holding periods

### Low Impact (Fine tuning):
- `BB_PERIOD`, `RSI_PERIOD` - Standard values work well
- `LOOKBACK_PERIODS` - Volume calculation window

---

## 📊 Parameter Sensitivity Analysis

**What Happens If You Change:**

### Momentum: MIN_PRICE_CHANGE_PCT
```
1.0% → More trades, lower quality
2.0% → Current (balanced)
3.0% → Fewer trades, higher quality
```

### Mean Reversion: BB_STD
```
2.0 → More signals, weaker reversions
2.5 → Current (extreme moves only)
3.0 → Very rare, ultra-extreme only
```

### Multi-Timeframe: MIN_CONFLUENCE_SCORE
```
2 → More trades, lower probability
3 → Current (balanced)
4 → Fewer trades, highest probability
```

### Smart Money: VOLUME_ANOMALY_THRESHOLD
```
3x → More signals, smaller institutions
5x → Current (large institutions)
7x → Rare, only massive institutional flow
```

---

## 🎯 Risk Management Parameters (Universal)

**Position Sizing:**
```python
RISK_PER_TRADE = 1% of capital
# Example with $10,000:
# Max loss per trade = $100
# Position size calculated to risk exactly $100

Position_Size = (Capital × Risk%) / (Entry - Stop) × Entry
```

**Example Calculation:**
```
Capital: $10,000
Risk: 1% = $100
Entry: $200
Stop: $198 (1% below)
Risk per share: $2

Position Size = $100 / $2 = 50 shares
Total Position Value = 50 × $200 = $10,000 (100% of capital)

If price hits stop: Loss = 50 × $2 = $100 ✓
If price hits target (+3%): Gain = 50 × $6 = $300
Risk:Reward = 1:3
```

**Concurrent Trade Limits:**
```python
MAX_CONCURRENT_TRADES = 3
# Prevents over-exposure
# Max total risk = 3 × 1% = 3% of capital at any time
```

---

## 💡 How to Modify Parameters

**To make strategies more aggressive:**
```python
# Lower entry thresholds
MIN_PRICE_CHANGE_PCT = 1.5  # (from 2.0)
MIN_CONFLUENCE_SCORE = 2    # (from 3)
BB_STD = 2.0               # (from 2.5)

# Result: More trades, potentially lower win rate
```

**To make strategies more conservative:**
```python
# Raise entry thresholds
MIN_PRICE_CHANGE_PCT = 3.0  # (from 2.0)
MIN_CONFLUENCE_SCORE = 4    # (from 3)
BB_STD = 3.0               # (from 2.5)

# Result: Fewer trades, higher quality, higher win rate
```

**To increase profit targets:**
```python
# Momentum
TARGET = Entry ± 4%  # (from 3%)

# Multi-Timeframe
TARGET = Entry ± 3.5%  # (from 2.5%)

# Result: Higher profit per trade, lower win rate (harder to hit)
```

**To tighten stops:**
```python
# All strategies
STOP_LOSS = Entry ± 0.5%  # (from 1%)

# Result: Lower loss per trade, but more stop-outs
```

---

## 🔍 Parameter Files in Code

**Where Parameters Are Set:**

1. **Strategy Detector Classes** (`gambler_ai/analysis/`)
   - `mean_reversion_detector.py` - Line 32-40
   - `volatility_breakout_detector.py` - Line 23-28
   - `multi_timeframe_analyzer.py` - Line 22-25
   - `smart_money_detector.py` - Line 22-27

2. **Backtest Scripts**
   - `backtest_10k_detailed.py` - Uses default parameters
   - `run_all_strategies_simulation.py` - Uses default parameters

3. **Configuration File** (Future enhancement)
   - `config.yaml` - Can store all parameters centrally

---

## 📝 Summary

**Current Parameter Philosophy:**
- ✅ **Balanced** - Not too aggressive, not too conservative
- ✅ **Industry Standard** - Using well-known values (RSI 14, BB 20, etc.)
- ✅ **Tested** - Proven to work in 2024 simulation
- ✅ **Optimizable** - Easy to adjust for different risk profiles

**To Run With Custom Parameters:**
```python
# Example: Create more aggressive Mean Reversion
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector

aggressive_mr = MeanReversionDetector(
    bb_period=20,
    bb_std=2.0,        # Lower (from 2.5) = more signals
    rsi_period=14,
    rsi_oversold=35,   # Less extreme (from 30)
    rsi_overbought=65, # Less extreme (from 70)
    volume_multiplier=2.5  # Lower (from 3.0) = easier to trigger
)

setups = aggressive_mr.detect_setups(your_data)
```

---

**All parameters are adjustable and ready for optimization!** 🎛️
