# Strategy Implementation Guide - Quick Reference

**For Architect/Developer Reference**

---

## Strategy Summary Table

| # | Strategy Name | Core Logic | Entry Trigger | Win Rate | Risk:Reward | Priority |
|---|---------------|------------|---------------|----------|-------------|----------|
| 0 | **Momentum Continuation** (Current) | Follow strong momentum | 2%+ move + 2x volume + 60%+ continuation prob | 60-65% | 1:1.5 | ✅ LIVE |
| 1 | **Mean Reversion** | Fade extremes | Price 2.5σ from mean + RSI <30 or >70 + 3x volume | 55-65% | 1:1.5 | 🔥 HIGH |
| 2 | **Volatility Breakout** | Trade expansion after compression | ATR <0.5x avg + breakout + 2x volume | 50-60% | 1:2.5 | 🔥 HIGH |
| 3 | **Multi-Timeframe Confluence** | Multiple timeframe alignment | 3+ confluence factors across 5m/15m/1h | 65-75% | 1:2.5 | 🔥 HIGH |
| 4 | **Smart Money Tracker** | Follow institutional flow | Volume spike 5x + absorption + VWAP reclaim | 60-70% | 1:3 | 🟡 MEDIUM |

---

## Implementation Checklist

### Common Infrastructure (Required for All)

```python
# New Modules Required
□ gambler_ai/analysis/indicators.py          # Technical indicators library
□ gambler_ai/analysis/base_strategy.py       # Base strategy class
□ gambler_ai/analysis/strategy_manager.py    # Multi-strategy orchestrator
□ gambler_ai/analysis/backtester.py          # Strategy backtesting engine

# Database Schema Updates
□ Create: strategy_events table (unified event storage)
□ Create: strategy_performance table (track strategy metrics)
□ Create: strategy_signals table (real-time signals)
□ Modify: Add strategy_type field to existing tables
```

### Base Classes Structure

```python
# gambler_ai/analysis/base_strategy.py

from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd

class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, config: Dict):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def detect_setup(self, data: pd.DataFrame) -> List[Dict]:
        """Detect trading setups in the data."""
        pass

    @abstractmethod
    def generate_signal(self, setup: Dict) -> Dict:
        """Generate entry signal from setup."""
        pass

    @abstractmethod
    def calculate_exit(self, entry: Dict, data: pd.DataFrame) -> Dict:
        """Calculate exit points."""
        pass

    def backtest(self, data: pd.DataFrame) -> Dict:
        """Backtest the strategy."""
        pass

    def get_metrics(self) -> Dict:
        """Return strategy performance metrics."""
        pass
```

---

## Strategy 1: Mean Reversion - Implementation Details

### Files to Create

```
gambler_ai/analysis/mean_reversion_detector.py    (350 lines)
gambler_ai/analysis/indicators.py                 (200 lines) *shared
tests/unit/test_mean_reversion.py                 (150 lines)
```

### Key Functions

```python
# gambler_ai/analysis/mean_reversion_detector.py

class MeanReversionDetector(BaseStrategy):

    def __init__(self):
        super().__init__()
        # Parameters
        self.bb_period = 20
        self.bb_std = 2.5
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.volume_multiplier = 3.0

    def detect_setup(self, data: pd.DataFrame) -> List[Dict]:
        """
        Detect extreme price deviations.

        Steps:
        1. Calculate Bollinger Bands (20, 2.5)
        2. Calculate RSI (14)
        3. Calculate volume ratio
        4. Identify extremes
        """
        # Add indicators
        data = self._add_bollinger_bands(data)
        data = self._add_rsi(data)
        data = self._add_volume_metrics(data)

        setups = []
        for i in range(len(data)):
            row = data.iloc[i]

            # LONG setup (oversold)
            if (row['close'] <= row['bb_lower'] and
                row['rsi'] < self.rsi_oversold and
                row['volume_ratio'] > self.volume_multiplier):

                setups.append({
                    'type': 'LONG',
                    'time': row['timestamp'],
                    'price': row['close'],
                    'rsi': row['rsi'],
                    'bb_distance': (row['bb_middle'] - row['close']) / row['close'],
                    'volume_ratio': row['volume_ratio'],
                })

            # SHORT setup (overbought)
            elif (row['close'] >= row['bb_upper'] and
                  row['rsi'] > self.rsi_overbought and
                  row['volume_ratio'] > self.volume_multiplier):

                setups.append({
                    'type': 'SHORT',
                    'time': row['timestamp'],
                    'price': row['close'],
                    'rsi': row['rsi'],
                    'bb_distance': (row['close'] - row['bb_middle']) / row['close'],
                    'volume_ratio': row['volume_ratio'],
                })

        return setups

    def generate_signal(self, setup: Dict) -> Dict:
        """
        Generate entry signal with targets and stops.
        """
        return {
            'strategy': 'MeanReversion',
            'direction': setup['type'],
            'entry_price': setup['price'],
            'target': self._calculate_target(setup),      # Middle BB
            'stop_loss': self._calculate_stop(setup),     # Beyond extreme
            'risk_reward': self._calculate_rr(setup),
            'confidence': self._calculate_confidence(setup),
        }

    def _add_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        df['bb_middle'] = df['close'].rolling(self.bb_period).mean()
        std = df['close'].rolling(self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (std * self.bb_std)
        return df

    def _add_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
```

### Database Schema

```sql
-- Mean Reversion specific table
CREATE TABLE mean_reversion_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ,
    direction VARCHAR(10),          -- 'LONG' or 'SHORT'

    -- Entry conditions
    entry_price DECIMAL(10,2),
    rsi_level DECIMAL(5,2),
    bb_distance_pct DECIMAL(5,2),   -- Distance from middle BB
    volume_ratio DECIMAL(5,2),

    -- Exit results
    exit_price DECIMAL(10,2),
    exit_time TIMESTAMPTZ,
    pnl_pct DECIMAL(5,2),
    time_in_trade_seconds INT,

    -- Outcome
    reached_target BOOLEAN,         -- Did price reach middle BB?
    max_adverse_excursion DECIMAL(5,2),
    strategy_type VARCHAR(50) DEFAULT 'mean_reversion',

    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX idx_mr_symbol_time ON mean_reversion_events(symbol, timestamp DESC);
```

---

## Strategy 2: Volatility Breakout - Implementation Details

### Files to Create

```
gambler_ai/analysis/volatility_breakout_detector.py    (380 lines)
gambler_ai/analysis/range_detector.py                  (200 lines)
tests/unit/test_volatility_breakout.py                 (150 lines)
```

### Key Functions

```python
# gambler_ai/analysis/volatility_breakout_detector.py

class VolatilityBreakoutDetector(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.atr_period = 14
        self.atr_compression = 0.5  # <50% of avg = compressed
        self.consolidation_min = 20  # minutes
        self.breakout_threshold = 0.005  # 0.5%
        self.volume_multiplier = 2.0

    def detect_setup(self, data: pd.DataFrame) -> List[Dict]:
        """
        Detect volatility compression + breakout.

        Steps:
        1. Calculate ATR and detect compression
        2. Identify consolidation ranges
        3. Detect breakouts from ranges
        4. Confirm with volume
        """
        data = self._add_atr(data)
        data = self._add_bollinger_width(data)
        ranges = self._detect_consolidation_ranges(data)

        setups = []
        for range_data in ranges:
            breakout = self._detect_breakout(data, range_data)
            if breakout:
                setups.append(breakout)

        return setups

    def _detect_consolidation_ranges(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify tight consolidation ranges.
        """
        ranges = []
        in_range = False
        range_start = None
        range_high = None
        range_low = None

        for i in range(len(df)):
            row = df.iloc[i]

            # Check if ATR is compressed
            is_compressed = (
                row['atr'] < row['atr_avg'] * self.atr_compression
            )

            if is_compressed and not in_range:
                # Start new range
                in_range = True
                range_start = i
                range_high = row['high']
                range_low = row['low']

            elif is_compressed and in_range:
                # Extend range
                range_high = max(range_high, row['high'])
                range_low = min(range_low, row['low'])

            elif not is_compressed and in_range:
                # End range
                range_duration = i - range_start

                if range_duration >= self.consolidation_min:
                    range_size = (range_high - range_low) / range_low

                    ranges.append({
                        'start_idx': range_start,
                        'end_idx': i - 1,
                        'duration': range_duration,
                        'high': range_high,
                        'low': range_low,
                        'size_pct': range_size * 100,
                    })

                in_range = False

        return ranges

    def _detect_breakout(self, df: pd.DataFrame, range_data: Dict) -> Dict:
        """
        Detect breakout from consolidation range.
        """
        end_idx = range_data['end_idx']
        range_high = range_data['high']
        range_low = range_data['low']

        # Look for breakout in next 10 bars
        for i in range(end_idx + 1, min(end_idx + 11, len(df))):
            row = df.iloc[i]

            # Bullish breakout
            if (row['close'] > range_high * (1 + self.breakout_threshold) and
                row['volume_ratio'] > self.volume_multiplier):

                return {
                    'type': 'LONG',
                    'time': row['timestamp'],
                    'entry_price': row['close'],
                    'range_high': range_high,
                    'range_low': range_low,
                    'range_size': range_data['size_pct'],
                    'compression_duration': range_data['duration'],
                    'volume_ratio': row['volume_ratio'],
                }

            # Bearish breakout
            elif (row['close'] < range_low * (1 - self.breakout_threshold) and
                  row['volume_ratio'] > self.volume_multiplier):

                return {
                    'type': 'SHORT',
                    'time': row['timestamp'],
                    'entry_price': row['close'],
                    'range_high': range_high,
                    'range_low': range_low,
                    'range_size': range_data['size_pct'],
                    'compression_duration': range_data['duration'],
                    'volume_ratio': row['volume_ratio'],
                }

        return None

    def _add_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Average True Range."""
        df['tr'] = df[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])),
            axis=1
        )
        df['atr'] = df['tr'].rolling(self.atr_period).mean()
        df['atr_avg'] = df['atr'].rolling(20).mean()
        return df
```

### Database Schema

```sql
-- Volatility Breakout specific table
CREATE TABLE volatility_breakout_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ,
    direction VARCHAR(10),

    -- Compression phase
    compression_duration_minutes INT,
    atr_compression_ratio DECIMAL(5,2),
    range_size_pct DECIMAL(5,2),

    -- Breakout phase
    entry_price DECIMAL(10,2),
    breakout_magnitude_pct DECIMAL(5,2),
    volume_ratio DECIMAL(5,2),

    -- Exit results
    exit_price DECIMAL(10,2),
    expansion_distance_pct DECIMAL(5,2),    -- How far it ran
    false_breakout BOOLEAN,                  -- Did it fail?

    strategy_type VARCHAR(50) DEFAULT 'volatility_breakout'
);

CREATE INDEX idx_vb_symbol_time ON volatility_breakout_events(symbol, timestamp DESC);
```

---

## Strategy 3: Multi-Timeframe Confluence - Implementation Details

### Files to Create

```
gambler_ai/analysis/mtf_analyzer.py           (450 lines)
gambler_ai/analysis/timeframe_aligner.py      (250 lines)
tests/unit/test_mtf_analyzer.py               (180 lines)
```

### Key Functions

```python
# gambler_ai/analysis/mtf_analyzer.py

class MultiTimeframeAnalyzer(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.timeframes = ['5min', '15min', '1hour']
        self.trend_ma_period = 20
        self.min_confluence_score = 3

    def detect_setup(self, symbol: str, current_time: datetime) -> List[Dict]:
        """
        Detect multi-timeframe confluence.

        Steps:
        1. Fetch data for all timeframes
        2. Calculate trend for each timeframe
        3. Score confluence factors
        4. Generate signal if score >= threshold
        """
        # Fetch all timeframes
        data_5m = self._fetch_data(symbol, '5min', current_time)
        data_15m = self._fetch_data(symbol, '15min', current_time)
        data_1h = self._fetch_data(symbol, '1hour', current_time)

        # Analyze each timeframe
        analysis_5m = self._analyze_timeframe(data_5m, '5min')
        analysis_15m = self._analyze_timeframe(data_15m, '15min')
        analysis_1h = self._analyze_timeframe(data_1h, '1hour')

        # Calculate confluence
        confluence = self._calculate_confluence({
            '5min': analysis_5m,
            '15min': analysis_15m,
            '1hour': analysis_1h,
        })

        if confluence['score'] >= self.min_confluence_score:
            return [{
                'symbol': symbol,
                'time': current_time,
                'confluence_score': confluence['score'],
                'direction': confluence['direction'],
                'factors': confluence['factors'],
                'timeframe_states': {
                    '5min': analysis_5m,
                    '15min': analysis_15m,
                    '1hour': analysis_1h,
                },
            }]

        return []

    def _calculate_confluence(self, analyses: Dict) -> Dict:
        """
        Calculate confluence score (0-5).
        """
        score = 0
        factors = []

        # Factor 1: Trend alignment (all same direction)
        trends = [a['trend'] for a in analyses.values()]
        if len(set(trends)) == 1 and trends[0] != 'NEUTRAL':
            score += 1
            factors.append('trend_alignment')

        # Factor 2: Price at key level on 5min
        if analyses['5min']['at_key_level']:
            score += 1
            factors.append('key_level')

        # Factor 3: Volume confirmation
        if (analyses['5min']['volume_ratio'] > 2.0 and
            analyses['15min']['volume_ratio'] > 1.5):
            score += 1
            factors.append('volume_confirmation')

        # Factor 4: RSI alignment (momentum but not extreme)
        rsi_aligned = all(
            30 < a['rsi'] < 70 for a in analyses.values()
        )
        if rsi_aligned and len(set([a['rsi_direction'] for a in analyses.values()])) == 1:
            score += 1
            factors.append('rsi_alignment')

        # Factor 5: VWAP alignment
        vwap_aligned = all(
            a['above_vwap'] == analyses['5min']['above_vwap']
            for a in analyses.values()
        )
        if vwap_aligned:
            score += 1
            factors.append('vwap_alignment')

        direction = trends[0] if score >= 3 else 'NEUTRAL'

        return {
            'score': score,
            'direction': direction,
            'factors': factors,
        }

    def _analyze_timeframe(self, data: pd.DataFrame, tf: str) -> Dict:
        """
        Analyze single timeframe.
        """
        latest = data.iloc[-1]

        # Trend (price vs 20 EMA)
        ema_20 = data['close'].ewm(span=20).mean().iloc[-1]
        trend = 'UP' if latest['close'] > ema_20 else 'DOWN'

        # RSI
        rsi = self._calculate_rsi(data)

        # VWAP
        vwap = self._calculate_vwap(data)

        # Volume
        avg_volume = data['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = latest['volume'] / avg_volume

        return {
            'timeframe': tf,
            'trend': trend,
            'price': latest['close'],
            'ema_20': ema_20,
            'at_key_level': abs(latest['close'] - ema_20) / ema_20 < 0.002,
            'rsi': rsi,
            'rsi_direction': 'UP' if rsi > 50 else 'DOWN',
            'vwap': vwap,
            'above_vwap': latest['close'] > vwap,
            'volume_ratio': volume_ratio,
        }
```

### Database Schema

```sql
-- Multi-Timeframe Confluence table
CREATE TABLE mtf_confluence_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ,
    direction VARCHAR(10),

    -- Confluence
    confluence_score INT,           -- 0-5
    factors JSONB,                  -- List of confluence factors

    -- Timeframe states (JSON)
    tf_5min_state JSONB,
    tf_15min_state JSONB,
    tf_1hour_state JSONB,

    -- Entry
    entry_price DECIMAL(10,2),
    entry_timeframe VARCHAR(10),

    -- Exit results
    exit_price DECIMAL(10,2),
    pnl_pct DECIMAL(5,2),

    strategy_type VARCHAR(50) DEFAULT 'mtf_confluence'
);

CREATE INDEX idx_mtf_symbol_score ON mtf_confluence_events(symbol, confluence_score DESC);
```

---

## Strategy 4: Smart Money Tracker - Implementation Details

### Files to Create

```
gambler_ai/analysis/smart_money_detector.py       (420 lines)
gambler_ai/analysis/volume_profile.py             (300 lines)
gambler_ai/analysis/order_flow_analyzer.py        (280 lines)
tests/unit/test_smart_money.py                    (150 lines)
```

### Key Functions

```python
# gambler_ai/analysis/smart_money_detector.py

class SmartMoneyDetector(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.volume_anomaly_threshold = 5.0  # 5x avg
        self.pattern_types = ['absorption', 'spring', 'iceberg', 'stop_hunt']

    def detect_setup(self, data: pd.DataFrame) -> List[Dict]:
        """
        Detect smart money patterns.

        Patterns:
        1. Absorption: High volume, narrow spread
        2. Spring (Wyckoff): Test support + reversal
        3. Iceberg: Consistent volume at price level
        4. Stop Hunt: Break + rapid reversal
        """
        setups = []

        # Detect each pattern type
        absorptions = self._detect_absorption(data)
        springs = self._detect_spring(data)
        icebergs = self._detect_iceberg(data)
        stop_hunts = self._detect_stop_hunt(data)

        setups.extend(absorptions)
        setups.extend(springs)
        setups.extend(icebergs)
        setups.extend(stop_hunts)

        return setups

    def _detect_absorption(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect volume absorption patterns.

        Absorption: High volume but price doesn't move proportionally
        Indicates large orders being absorbed by institutions.
        """
        setups = []

        for i in range(20, len(df)):
            row = df.iloc[i]
            avg_volume = df.iloc[i-20:i]['volume'].mean()
            volume_ratio = row['volume'] / avg_volume

            # High volume
            if volume_ratio < self.volume_anomaly_threshold:
                continue

            # Calculate spread efficiency
            price_range = row['high'] - row['low']
            price_change_pct = price_range / row['open'] * 100

            # Expected move based on volume
            avg_move_per_volume = self._calculate_avg_move_per_volume(df, i)
            expected_move = volume_ratio * avg_move_per_volume

            # Absorption: actual move << expected move
            if price_change_pct < expected_move * 0.5:  # Less than 50% of expected

                # Determine direction based on close position
                close_position = (row['close'] - row['low']) / price_range
                direction = 'LONG' if close_position > 0.6 else 'SHORT'

                setups.append({
                    'type': direction,
                    'pattern': 'absorption',
                    'time': row['timestamp'],
                    'price': row['close'],
                    'volume_ratio': volume_ratio,
                    'spread': price_change_pct,
                    'absorption_score': expected_move / price_change_pct,
                })

        return setups

    def _detect_spring(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Wyckoff Spring pattern.

        Spring: Multiple tests of support, then breakdown + rapid reversal
        Stop hunt by institutions before real move.
        """
        setups = []

        # Find support levels (multiple touches)
        support_levels = self._find_support_resistance(df)

        for level in support_levels['support']:
            # Look for spring: break below + reversal
            spring = self._check_spring_pattern(df, level)
            if spring:
                setups.append(spring)

        return setups

    def _detect_iceberg(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect iceberg orders.

        Iceberg: Consistent volume at specific price, minimal price movement
        Institutions accumulating/distributing.
        """
        # Group by price level and sum volume
        volume_profile = self._create_volume_profile(df)

        # Find price levels with unusually high volume
        high_volume_levels = volume_profile[
            volume_profile['volume'] > volume_profile['volume'].quantile(0.95)
        ]

        setups = []
        for _, level in high_volume_levels.iterrows():
            # Check if price is accumulating at this level
            duration = level['bar_count']
            if duration >= 5:  # At least 5 bars at this level
                setups.append({
                    'pattern': 'iceberg',
                    'price_level': level['price'],
                    'total_volume': level['volume'],
                    'duration_bars': duration,
                    'direction': 'LONG',  # Assume accumulation for now
                })

        return setups
```

### Database Schema

```sql
-- Smart Money Events table
CREATE TABLE smart_money_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ,
    direction VARCHAR(10),

    -- Pattern info
    pattern_type VARCHAR(50),       -- 'absorption', 'spring', 'iceberg', 'stop_hunt'
    volume_anomaly_ratio DECIMAL(5,2),

    -- Pattern-specific metrics
    absorption_score DECIMAL(5,2),  -- For absorption patterns
    level_defense_count INT,        -- For springs (# of tests)
    accumulation_duration INT,      -- For icebergs (bars)

    -- Entry/Exit
    entry_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    pnl_pct DECIMAL(5,2),

    strategy_type VARCHAR(50) DEFAULT 'smart_money'
);

CREATE INDEX idx_sm_pattern ON smart_money_events(pattern_type, timestamp DESC);
```

---

## Unified Strategy Manager

### Central Orchestrator

```python
# gambler_ai/analysis/strategy_manager.py

class StrategyManager:
    """Manages multiple strategies and coordinates execution."""

    def __init__(self):
        self.strategies = {
            'momentum': MomentumDetector(),
            'mean_reversion': MeanReversionDetector(),
            'volatility_breakout': VolatilityBreakoutDetector(),
            'mtf_confluence': MultiTimeframeAnalyzer(),
            'smart_money': SmartMoneyDetector(),
        }
        self.active_strategies = []

    def enable_strategy(self, strategy_name: str):
        """Enable a strategy for signal generation."""
        if strategy_name in self.strategies:
            self.active_strategies.append(strategy_name)

    def scan_market(self, symbols: List[str]) -> Dict:
        """
        Scan market with all active strategies.

        Returns: Dictionary of signals by strategy
        """
        all_signals = {}

        for strategy_name in self.active_strategies:
            strategy = self.strategies[strategy_name]
            signals = []

            for symbol in symbols:
                # Run strategy detection
                setups = strategy.detect_setup(symbol)
                for setup in setups:
                    signal = strategy.generate_signal(setup)
                    signal['symbol'] = symbol
                    signals.append(signal)

            all_signals[strategy_name] = signals

        return all_signals

    def backtest_all(self, data: Dict, start: datetime, end: datetime) -> Dict:
        """
        Backtest all strategies and compare performance.
        """
        results = {}

        for name, strategy in self.strategies.items():
            logger.info(f"Backtesting {name}...")
            results[name] = strategy.backtest(data, start, end)

        # Compare performance
        comparison = self._compare_strategies(results)

        return {
            'individual_results': results,
            'comparison': comparison,
        }

    def _compare_strategies(self, results: Dict) -> pd.DataFrame:
        """Create comparison table of strategy performance."""
        comparison_data = []

        for strategy_name, result in results.items():
            comparison_data.append({
                'strategy': strategy_name,
                'win_rate': result['win_rate'],
                'profit_factor': result['profit_factor'],
                'total_return': result['total_return_pct'],
                'max_drawdown': result['max_drawdown_pct'],
                'sharpe_ratio': result['sharpe_ratio'],
                'num_trades': result['num_trades'],
            })

        return pd.DataFrame(comparison_data)
```

---

## Testing Checklist

### Unit Tests (Per Strategy)

```python
# tests/unit/test_mean_reversion.py

def test_bollinger_calculation():
    """Test Bollinger Bands are calculated correctly."""
    pass

def test_rsi_calculation():
    """Test RSI calculation."""
    pass

def test_extreme_detection():
    """Test detection of overbought/oversold conditions."""
    pass

def test_signal_generation():
    """Test entry signal generation."""
    pass

def test_exit_calculation():
    """Test target and stop loss calculation."""
    pass
```

### Integration Tests

```python
# tests/integration/test_strategy_integration.py

def test_strategy_manager_initialization():
    """Test all strategies can be loaded."""
    pass

def test_multi_strategy_scan():
    """Test scanning with multiple strategies active."""
    pass

def test_strategy_backtest():
    """Test backtesting each strategy."""
    pass

def test_database_storage():
    """Test events are stored correctly for each strategy."""
    pass
```

---

## API Endpoints to Add

```python
# gambler_ai/api/routes/strategies.py

# List all available strategies
GET /api/v1/strategies
Response: [
    {"name": "momentum", "active": true, "win_rate": 0.62},
    {"name": "mean_reversion", "active": true, "win_rate": 0.58},
    ...
]

# Enable/disable a strategy
POST /api/v1/strategies/{strategy_name}/toggle
Body: {"active": true}

# Get signals for a strategy
GET /api/v1/strategies/{strategy_name}/signals?symbol=AAPL
Response: [
    {
        "time": "2024-12-01T10:30:00",
        "direction": "LONG",
        "confidence": 0.75,
        ...
    }
]

# Backtest a strategy
POST /api/v1/strategies/{strategy_name}/backtest
Body: {
    "symbols": ["AAPL", "MSFT"],
    "start": "2024-01-01",
    "end": "2024-12-31"
}

# Compare all strategies
GET /api/v1/strategies/compare
Response: {
    "comparison_table": [...],
    "equity_curves": {...},
    "metrics": {...}
}
```

---

## Priority Implementation Order

### Phase 1: Foundation (Week 1)
1. ✅ Create `indicators.py` (Bollinger, RSI, ATR, VWAP)
2. ✅ Create `base_strategy.py` (Base class)
3. ✅ Create `strategy_manager.py` (Orchestrator)
4. ✅ Update database schemas

### Phase 2: High Priority Strategies (Week 2)
1. 🔥 **Mean Reversion** (easiest, high value)
2. 🔥 **Multi-Timeframe** (highest win rate)

### Phase 3: Medium Priority (Week 3)
3. 🔥 **Volatility Breakout** (good R:R)

### Phase 4: Advanced Strategy (Week 4)
4. 🟡 **Smart Money** (complex but unique edge)

### Phase 5: Integration & Testing (Week 5-6)
- Backtest all strategies
- Build comparison dashboard
- Optimize parameters
- Deploy multi-strategy system

---

## Quick Command Reference

```bash
# Test all strategies on AAPL
gambler-cli test-strategies --symbol AAPL --start 2024-01-01

# Run specific strategy
gambler-cli run-strategy mean_reversion --symbols AAPL,MSFT

# Compare strategies
gambler-cli compare-strategies --period 6months

# Enable strategies for live scanning
gambler-cli enable-strategy mean_reversion
gambler-cli enable-strategy mtf_confluence

# Get current signals
gambler-cli get-signals --all-strategies
```

---

## Success Metrics

Track these for each strategy:

```python
metrics_to_track = {
    "win_rate": "% winning trades",
    "profit_factor": "Gross profit / gross loss",
    "sharpe_ratio": "Risk-adjusted returns",
    "max_drawdown": "Largest peak-to-trough loss",
    "avg_trade_duration": "Time in trade",
    "risk_reward_ratio": "Avg win / avg loss",
    "num_trades": "Total opportunities",
}
```

---

**END OF IMPLEMENTATION GUIDE**

Ready for architect review and development.
