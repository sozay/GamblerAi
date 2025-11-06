# GamblerAI - Alternative Trading Strategies

**Document Version:** 1.0
**Date:** 2025-11-05
**Purpose:** Alternative strategies to test against the current Momentum Continuation Strategy

---

## Executive Summary

This document outlines **4 alternative trading strategies** designed to complement and compete with the current Momentum Continuation Strategy. Each strategy targets different market conditions and price patterns, providing a comprehensive testing framework for optimal trading performance.

---

## Current Strategy: Momentum Continuation (Baseline)

### Overview
The baseline strategy detects rapid price movements and predicts continuation probability based on historical patterns.

### Key Parameters
- **Detection Threshold**: 2% price change in 5 minutes
- **Volume Confirmation**: 2x average volume
- **Entry Logic**: Continuation probability ≥60%
- **Timeframe**: Single (5min)

### Strengths
- ✓ Data-driven probabilistic approach
- ✓ Volume confirmation reduces false signals
- ✓ Works well in trending markets
- ✓ Clear entry/exit signals

### Weaknesses
- ✗ Misses mean reversion opportunities
- ✗ Ignores consolidation breakouts
- ✗ Single timeframe (no multi-timeframe confirmation)
- ✗ Performs poorly in ranging markets
- ✗ No volatility adaptation

---

## Strategy 1: Mean Reversion (Contrarian)

### Core Thesis
**"Overextended moves return to the mean"**

When price deviates significantly from its average, it tends to revert. This strategy profits from extreme moves by taking the opposite position.

### Detection Logic

```python
# Entry Conditions
1. Bollinger Band Extreme:
   - Price touches or exceeds outer Bollinger Band (2.5σ)
   - Price is >2.5 standard deviations from 20-period SMA

2. RSI Oversold/Overbought:
   - RSI < 30 (oversold) for LONG entry
   - RSI > 70 (overbought) for SHORT entry

3. Volume Confirmation:
   - Climax volume: >3x average volume
   - Suggests exhaustion

4. Price Extension:
   - 3%+ move in single direction without pullback
   - Distance from VWAP > 2%

# Entry Signal
LONG when:
  - Price < BB_lower AND RSI < 30 AND volume > 3x_avg

SHORT when:
  - Price > BB_upper AND RSI > 70 AND volume > 3x_avg

# Exit Logic
- Target: Return to middle Bollinger Band (20 SMA)
- Stop Loss: Beyond the extreme (e.g., if LONG, stop below recent low)
- Time Stop: Exit if no reversion within 30 minutes
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Bollinger Period | 20 | Standard statistical period |
| Bollinger StdDev | 2.5 | Captures extreme moves |
| RSI Period | 14 | Standard momentum period |
| RSI Oversold | 30 | Conservative extreme |
| RSI Overbought | 70 | Conservative extreme |
| Volume Multiplier | 3x | Exhaustion confirmation |
| Time Stop | 30 min | Prevents holding losers |
| Target | Middle BB | Natural reversion point |

### Risk Management

```python
# Position Sizing
- Risk 0.5% of capital per trade (conservative)
- Max 3 concurrent mean reversion trades

# Stop Loss
- LONG: 1% below entry or below recent swing low
- SHORT: 1% above entry or above recent swing high

# Profit Target
- Primary: Middle Bollinger Band (~1-2% typically)
- Secondary: Opposite Bollinger Band (let winners run)
- Trailing stop: Activate after 50% target reached
```

### Expected Performance Profile

- **Win Rate**: 55-65% (higher than momentum)
- **Risk/Reward**: 1:1.5 to 1:2
- **Best Market**: Ranging, choppy, high volatility
- **Worst Market**: Strong trending markets
- **Avg Trade Duration**: 15-45 minutes

### Statistical Metrics to Track

```python
metrics = {
    "bollinger_deviation": "Distance from middle band at entry",
    "rsi_level": "RSI value at entry",
    "volume_ratio": "Entry volume / avg volume",
    "time_to_reversion": "Minutes until price reaches target",
    "max_adverse_excursion": "Worst drawdown during trade",
    "reversion_success_rate": "% of trades reaching middle BB",
}
```

### Implementation Requirements

1. **New Indicators Module** (`gambler_ai/analysis/indicators.py`):
   - Bollinger Bands calculation
   - RSI calculation
   - VWAP calculation
   - Standard deviation distance

2. **Mean Reversion Detector** (`gambler_ai/analysis/mean_reversion_detector.py`):
   - Scan for extreme deviations
   - Identify exhaustion patterns
   - Calculate reversion probability

3. **Database Updates**:
   - New table: `mean_reversion_events`
   - Track: deviation level, RSI, reversion time, success rate

---

## Strategy 2: Volatility Breakout (Expansion)

### Core Thesis
**"Volatility contraction leads to volatility expansion"**

After periods of low volatility (consolidation), breakouts from tight ranges tend to lead to sustained moves.

### Detection Logic

```python
# Entry Conditions
1. Volatility Contraction:
   - ATR has been declining for 10+ periods
   - Current ATR < 0.5x the 20-period average ATR
   - Bollinger Band width in lowest 20th percentile

2. Price Consolidation:
   - Trading range < 1% for 20+ minutes
   - Price squeezed between tight support/resistance

3. Breakout Confirmation:
   - Price breaks above/below consolidation range by >0.5%
   - Volume spike: >2x average volume on breakout bar
   - Momentum confirmation: Price continues in breakout direction

4. Trend Alignment:
   - Breakout direction aligns with larger trend (20-period SMA)

# Entry Signal
LONG when:
  - ATR compressed + price breaks above consolidation + volume spike

SHORT when:
  - ATR compressed + price breaks below consolidation + volume spike

# Exit Logic
- Target: 1x-2x the consolidation range
- Stop Loss: Opposite side of consolidation range
- Trailing Stop: Adjust stop to breakeven after 1x range move
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| ATR Period | 14 | Standard volatility measure |
| ATR Compression | <0.5x avg | Identifies tight ranges |
| Consolidation Min | 20 min | Sufficient compression |
| Breakout Threshold | 0.5% | Meaningful break |
| Volume Multiplier | 2x | Confirms participation |
| BB Width Percentile | <20% | Statistical compression |
| Target Multiple | 1.5x range | Historical avg expansion |

### Risk Management

```python
# Position Sizing
- Risk 1% of capital per trade
- Max 2 concurrent breakout trades

# Stop Loss
- Place just inside consolidation range
- Typically 0.3-0.5% depending on range size

# Profit Targets
- Target 1: 1x consolidation range (take 50%)
- Target 2: 1.5x consolidation range (take 30%)
- Target 3: 2x consolidation range (let 20% run)
```

### Expected Performance Profile

- **Win Rate**: 50-60%
- **Risk/Reward**: 1:2 to 1:3 (better R:R than mean reversion)
- **Best Market**: Transitioning from range to trend
- **Worst Market**: Highly choppy, false breakouts
- **Avg Trade Duration**: 30-90 minutes

### Statistical Metrics to Track

```python
metrics = {
    "atr_compression_ratio": "Current ATR / 20-period avg ATR",
    "consolidation_duration": "Minutes in tight range",
    "breakout_magnitude": "% beyond consolidation range",
    "followthrough_distance": "How far price travels post-breakout",
    "false_breakout_rate": "% of breakouts that fail",
    "expansion_ratio": "Actual move / consolidation range",
}
```

### Implementation Requirements

1. **Range Detection Module** (`gambler_ai/analysis/range_detector.py`):
   - Identify consolidation periods
   - Calculate range boundaries
   - Detect breakouts

2. **Volatility Module** (`gambler_ai/analysis/volatility_analyzer.py`):
   - ATR calculation and compression detection
   - Bollinger Band width percentiles
   - Volatility expansion patterns

3. **Database Updates**:
   - New table: `volatility_breakout_events`
   - Track: compression ratio, range duration, expansion distance

---

## Strategy 3: Multi-Timeframe Confluence (Pyramid)

### Core Thesis
**"Alignment across timeframes increases probability"**

Trades with confirmation from multiple timeframes have significantly higher success rates. This strategy only takes trades when 3+ timeframes align.

### Detection Logic

```python
# Multi-Timeframe Analysis
Timeframes: 5min, 15min, 1hour

# Entry Conditions
1. Higher Timeframe Trend:
   - 1hour: Price above/below 20 EMA (defines major trend)
   - 15min: Price in same direction, momentum building

2. Lower Timeframe Entry:
   - 5min: Momentum event detected (using current logic)
   - 5min: Pullback to key level (20 EMA or VWAP)

3. Confluence Factors (need 3+ of 5):
   ✓ All timeframes show momentum in same direction
   ✓ Price at/near key moving average (20 EMA)
   ✓ Volume increasing across timeframes
   ✓ RSI alignment (all showing momentum, none extreme)
   ✓ VWAP alignment (price on correct side)

# Entry Signal
LONG when:
  - 1h trend UP + 15min momentum UP + 5min pullback complete + 3+ confluence

SHORT when:
  - 1h trend DOWN + 15min momentum DOWN + 5min pullback complete + 3+ confluence

# Exit Logic
- Target: Based on higher timeframe resistance/support
- Stop Loss: Below multi-timeframe support
- Partial profits at each timeframe level
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Timeframes | 5m, 15m, 1h | Short-term scalping to intraday |
| Trend MA | 20 EMA | Dynamic support/resistance |
| Min Confluence | 3 of 5 | High probability filter |
| Volume Trend | Increasing | Confirms strength |
| Entry Timing | 5min pullback | Optimal risk/reward |

### Confluence Scoring System

```python
def calculate_confluence_score(data):
    """Score 0-5 based on alignment factors."""
    score = 0

    # Factor 1: Trend alignment
    if (data['1h_trend'] == data['15m_trend'] == data['5m_trend']):
        score += 1

    # Factor 2: Price at key level
    if abs(data['price'] - data['key_level']) < 0.2:  # Within 0.2%
        score += 1

    # Factor 3: Volume confirmation
    if (data['5m_volume'] > 2x and
        data['15m_volume'] > 1.5x):
        score += 1

    # Factor 4: RSI alignment (momentum but not extreme)
    if (30 < data['5m_rsi'] < 70 and
        30 < data['15m_rsi'] < 70 and
        same_direction):
        score += 1

    # Factor 5: VWAP alignment
    if correct_side_of_vwap_all_timeframes:
        score += 1

    return score

# Trade only when score >= 3
```

### Risk Management

```python
# Position Sizing
- Risk 1% of capital per trade
- Scale into position (30% at 5m entry, 40% at 15m confirm, 30% at 1h confirm)
- Max 2 confluence trades at once

# Stop Loss
- Use 1h timeframe support/resistance as stop
- Typically 1.5-2% stop loss

# Profit Targets
- Target 1: 15min resistance (50% position)
- Target 2: 1hour resistance (30% position)
- Target 3: Trail remaining 20% with 1h EMA
```

### Expected Performance Profile

- **Win Rate**: 65-75% (highest of all strategies)
- **Risk/Reward**: 1:2 to 1:3
- **Best Market**: Trending markets with pullbacks
- **Worst Market**: Choppy, whipsaw markets
- **Avg Trade Duration**: 60-180 minutes (longer holds)

### Statistical Metrics to Track

```python
metrics = {
    "confluence_score": "Score at entry (0-5)",
    "timeframe_alignment_duration": "How long alignment lasted",
    "entry_timing_quality": "Distance from optimal entry",
    "higher_tf_support": "Distance to 1h support/resistance",
    "win_rate_by_confluence": "Win rate stratified by score",
    "avg_profit_by_score": "Higher scores = higher profit?",
}
```

### Implementation Requirements

1. **Multi-Timeframe Analyzer** (`gambler_ai/analysis/mtf_analyzer.py`):
   - Fetch and align multiple timeframes
   - Calculate confluence score
   - Identify key levels across timeframes

2. **Timeframe Alignment Module**:
   - Synchronize data across timeframes
   - Detect trend alignment
   - Track momentum consistency

3. **Database Updates**:
   - New table: `mtf_confluence_events`
   - Track: confluence score, timeframe states, win rate by score

---

## Strategy 4: Smart Money Tracker (Order Flow)

### Core Thesis
**"Follow the institutions, not the retail crowd"**

Large institutional orders leave footprints in volume and price patterns. This strategy detects and follows "smart money" activity.

### Detection Logic

```python
# Entry Conditions
1. Volume Anomaly Detection:
   - Single bar volume >5x average (large order)
   - Price doesn't move proportionally (absorption/accumulation)
   - Volume profile shows concentration at specific price

2. Price Action Clues:
   - Wide spread bar with close near high (bullish absorption)
   - Narrow spread on high volume (accumulation)
   - Multiple tests of level with decreasing spread (spring)

3. Order Flow Patterns:
   - Iceberg orders: Consistent buying without price rise
   - Sweep orders: Rapid clearing of sell side
   - Failed breakdown: Price quickly recovers after stop hunt

4. Smart Money Confirmation:
   - Volume weighted average price (VWAP) reclaim
   - Prior resistance becomes support (institutions defending)
   - Options flow alignment (if available)

# Entry Signal
LONG when:
  - Large volume absorption + price holds/rises + VWAP reclaim

SHORT when:
  - Large volume distribution + price holds/falls + VWAP rejection

# Exit Logic
- Target: Previous swing high/low (where institutions likely exit)
- Stop Loss: Below absorption zone
- Trail with VWAP once profitable
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Volume Anomaly | 5x avg | Institutional size |
| Spread Analysis | Volume/Range ratio | Order absorption |
| VWAP Reclaim | Price > VWAP + hold | Trend shift |
| Time Window | 10-20 min | Accumulation period |
| Failed Test | 3+ touches | Strong support/resistance |

### Smart Money Patterns

```python
# Pattern 1: Absorption (Wyckoff Spring)
- High volume, narrow spread
- Tests support multiple times
- Sudden reversal with momentum
- Entry: Break above test range

# Pattern 2: Iceberg Buy/Sell
- Consistent volume at price level
- Price doesn't move proportionally
- Institutional accumulation
- Entry: Break of accumulation range

# Pattern 3: Stop Hunt + Reversal
- Break below support on high volume
- Rapid reversal back above level
- Retail stops triggered, institutions buy
- Entry: Reclaim of broken level

# Pattern 4: End of Day Positioning
- Last 30 minutes, unusual volume
- Price pushed to specific level
- Institutional positioning for next day
- Entry: Follow the EOD direction next morning
```

### Risk Management

```python
# Position Sizing
- Risk 1% of capital per trade
- Larger size on high-confidence patterns (3+ confirmations)
- Max 3 concurrent smart money trades

# Stop Loss
- Below/above the accumulation/distribution zone
- Typically 0.8-1.2% (tighter stops)

# Profit Targets
- Target 1: Previous swing point (60%)
- Target 2: Next major level (30%)
- Trail 10% with VWAP
```

### Expected Performance Profile

- **Win Rate**: 60-70%
- **Risk/Reward**: 1:2.5 to 1:4 (best R:R)
- **Best Market**: All conditions (institutions always active)
- **Worst Market**: Extremely low volume
- **Avg Trade Duration**: 45-120 minutes

### Statistical Metrics to Track

```python
metrics = {
    "volume_anomaly_size": "Volume spike magnitude",
    "spread_efficiency": "Price move / volume ratio",
    "absorption_success_rate": "% of absorptions that lead to moves",
    "time_to_breakout": "Time from absorption to move",
    "level_defense_count": "How many times level tested before break",
    "smart_money_win_rate": "Win rate by pattern type",
}
```

### Implementation Requirements

1. **Volume Profile Analyzer** (`gambler_ai/analysis/volume_profile.py`):
   - Calculate volume-weighted price levels
   - Detect volume anomalies
   - Identify absorption/accumulation

2. **Order Flow Detector** (`gambler_ai/analysis/order_flow_detector.py`):
   - Pattern recognition (spring, absorption, iceberg)
   - Smart money footprint detection
   - Level defense tracking

3. **Database Updates**:
   - New table: `smart_money_events`
   - Track: pattern type, volume spike, success rate by pattern

---

## Strategy Comparison Matrix

| Strategy | Win Rate | Risk:Reward | Best Market | Avg Duration | Complexity |
|----------|----------|-------------|-------------|--------------|------------|
| **Momentum (Current)** | 60-65% | 1:1.5 | Trending | 15-30 min | Medium |
| **Mean Reversion** | 55-65% | 1:1.5 | Ranging | 15-45 min | Medium |
| **Volatility Breakout** | 50-60% | 1:2.5 | Transition | 30-90 min | High |
| **Multi-Timeframe** | 65-75% | 1:2.5 | Trending | 60-180 min | High |
| **Smart Money** | 60-70% | 1:3 | All | 45-120 min | Very High |

---

## Strategy Portfolio Approach

### Diversification Benefits

Instead of choosing one strategy, running **all strategies simultaneously** provides:

1. **Market Condition Coverage**: Different strategies profit in different conditions
2. **Risk Diversification**: Uncorrelated strategies smooth equity curve
3. **Opportunity Maximization**: Capture more trading opportunities
4. **Strategy Validation**: Compare real-time performance

### Portfolio Allocation

```python
# Suggested Capital Allocation
capital_allocation = {
    "Momentum Continuation": 25%,      # Trending markets
    "Mean Reversion": 20%,             # Ranging markets
    "Volatility Breakout": 15%,        # Transition periods
    "Multi-Timeframe": 25%,            # High confidence setups
    "Smart Money": 15%,                # Opportunistic
}

# Risk per strategy
max_risk_per_strategy = 2%  # Of allocated capital
max_portfolio_risk = 5%     # Total across all strategies
```

---

## Testing Framework

### Backtesting Requirements

```python
test_framework = {
    "Data Period": "2 years historical data",
    "Symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY"],
    "Timeframes": ["5min", "15min", "1hour"],
    "Metrics": [
        "Total Return",
        "Win Rate",
        "Avg Risk:Reward",
        "Max Drawdown",
        "Sharpe Ratio",
        "Profit Factor",
        "Avg Trade Duration",
        "# Trades",
    ],
    "Market Conditions": [
        "Trending Up",
        "Trending Down",
        "Ranging/Choppy",
        "High Volatility",
        "Low Volatility",
    ],
}
```

### Performance Comparison

Test each strategy independently, then test portfolio:

```python
# Individual Strategy Testing
for strategy in [momentum, mean_reversion, breakout, mtf, smart_money]:
    results = backtest_strategy(strategy, data, params)
    analyze_performance(results)

# Portfolio Testing
portfolio_results = backtest_portfolio(
    strategies=[momentum, mean_reversion, breakout, mtf, smart_money],
    allocation=capital_allocation,
    data=data
)
```

### Success Criteria

A strategy is considered "successful" if it meets **3 of 5 criteria**:

1. ✓ Win Rate > 55%
2. ✓ Profit Factor > 1.5
3. ✓ Sharpe Ratio > 1.0
4. ✓ Max Drawdown < 15%
5. ✓ Positive returns in 3+ market conditions

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Implement technical indicators module
- [ ] Create base detector classes
- [ ] Set up testing framework

### Phase 2: Strategy Implementation (Week 2-3)
- [ ] Implement Mean Reversion detector
- [ ] Implement Volatility Breakout detector
- [ ] Implement Multi-Timeframe analyzer
- [ ] Implement Smart Money detector

### Phase 3: Database & Storage (Week 4)
- [ ] Create new event tables
- [ ] Modify data models
- [ ] Set up strategy-specific logging

### Phase 4: API & Dashboard (Week 5)
- [ ] Add strategy selection endpoints
- [ ] Create strategy comparison dashboard
- [ ] Implement multi-strategy backtesting API

### Phase 5: Testing & Optimization (Week 6-8)
- [ ] Backtest each strategy individually
- [ ] Test strategy portfolio
- [ ] Optimize parameters
- [ ] Generate performance reports

---

## Next Steps

1. **Review & Approve**: Architect reviews strategies and approves for implementation
2. **Prioritization**: Decide which strategies to implement first (recommend: Mean Reversion + Multi-Timeframe)
3. **Resource Allocation**: Assign developers to each strategy
4. **Timeline**: Set milestones for implementation phases
5. **Success Metrics**: Define KPIs for each strategy

---

## Conclusion

These 4 alternative strategies provide comprehensive coverage of different market conditions:

- **Mean Reversion**: Profits from overextension
- **Volatility Breakout**: Captures expansion from consolidation
- **Multi-Timeframe**: Leverages alignment for high probability
- **Smart Money**: Follows institutional order flow

Together with the current **Momentum Continuation** strategy, this creates a **5-strategy portfolio** that can adapt to any market condition and significantly improve overall trading performance.

**Recommended Action**: Implement all 5 strategies in parallel for comprehensive market coverage and robust performance across varying conditions.
