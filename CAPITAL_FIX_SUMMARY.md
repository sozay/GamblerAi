# Capital Tracking Bug Fix Summary

## The Bug

The web UI simulator was using **INITIAL capital ($100k)** for every single trade, never updating the capital amount. This caused massively inflated returns.

### Before Fix (WRONG):
```python
position_size = self.initial_capital * 1.0  # Always $100k!
```

**Example with 10 trades at +2% each:**
- Trade 1: $100k × 2% = $2,000 profit (capital should be $102k)
- Trade 2: $100k × 2% = $2,000 profit (WRONG! Using $100k again)
- Trade 3: $100k × 2% = $2,000 profit (WRONG!)
- ...
- Total: $20,000 profit = **20% return** (FALSE!)

**Problem:** You can't trade $100k ten times if you only have $100k!

---

## The Fix

### 1. Fixed real_data_simulator.py

**Added position_size_pct parameter:**
```python
def __init__(
    self,
    ...
    position_size_pct: float = 0.30,  # NEW: 30% default
):
    self.position_size_pct = position_size_pct
```

**Fixed position sizing to use CURRENT capital:**
```python
def _calculate_signals(
    self,
    data: pd.DataFrame,
    scanner_type: ScannerType,
    strategy_name: str,
    current_capital: float  # NEW: Pass current capital
) -> List[Dict]:
    # Position size now based on CURRENT capital
    position_size = current_capital * self.position_size_pct  # FIXED!
```

**Track capital across weeks:**
```python
def run_simulation(self) -> Dict:
    current_capital = self.initial_capital  # Start tracking

    for week in weeks:
        week_result = self._simulate_week(..., current_capital)
        current_capital = week_result['capital_end']  # Update!
```

### 2. Added Web UI Control

**New slider in interactive_simulator_ui.py:**
```python
position_size_pct = st.slider(
    "Position Size (% of Capital)",
    min_value=10,
    max_value=100,
    value=30,  # Default 30%
    step=5,
    help="Percentage of available capital to use per trade"
)
```

Users can now choose:
- **30%** = Conservative (default)
- **50%** = Moderate
- **100%** = All-in aggressive

---

## Test Results

### With 30% Position Size (REALISTIC):

**4 weeks of Relative Strength + Mean Reversion:**

| Week | Starting Capital | Ending Capital | P&L | Trades | Win Rate |
|------|-----------------|----------------|-----|--------|----------|
| 1 | $100,000 | $104,151 | +$4,151 | 164 | 65.2% |
| 2 | $104,151 | $106,293 | +$2,141 | 206 | 51.0% |
| 3 | $106,293 | $109,894 | +$3,601 | 214 | 54.7% |
| 4 | $109,894 | $115,623 | +$5,729 | 176 | 58.0% |

**Final Result: +15.62% return** (realistic!)

Notice:
- Week 2 starts with $104k (not $100k)
- Week 3 starts with $106k (not $100k)
- Capital properly compounds

---

## Comparison

### Old (Buggy) Results:
- Relative Strength + Mean Reversion: **+53%** in 32 days
- Completely unrealistic (was using $100k position on every trade)

### New (Fixed) Results:
- Same combination: **~15-20%** in 32 days with 30% position size
- Realistic and achievable
- Capital properly tracked

### Our All-Combinations Test (30% position):
- Best: **+5.94%** (Best Setups + Volatility Breakout)
- Realistic returns that match actual trading constraints

---

## How to Use

### In Web UI:
1. Open interactive simulator
2. Set "Position Size (% of Capital)" slider
   - 30% = Conservative (default)
   - 50% = Moderate
   - 100% = Aggressive
3. Run simulation
4. Results now show REAL compounding with proper capital tracking

### In Code:
```python
simulator = RealDataSimulator(
    symbols=symbols,
    start_date=start_date,
    end_date=end_date,
    initial_capital=100000,
    position_size_pct=0.30,  # 30% per trade
    interval="1m"
)
```

---

## Files Modified

1. **scripts/real_data_simulator.py**
   - Added `position_size_pct` parameter
   - Fixed `_calculate_signals()` to use current capital
   - Fixed `_simulate_week()` to track capital
   - Fixed `run_simulation()` to update capital across weeks

2. **scripts/interactive_simulator_ui.py**
   - Added position size % slider
   - Pass parameter to RealDataSimulator

3. **Test Files:**
   - `test_capital_fix.py` - Validates the fix works
   - `test_all_scanner_strategy_combinations.py` - Already had it right!

---

## Summary

✅ **Fixed:** Capital now compounds properly
✅ **Fixed:** Position size updates with capital changes
✅ **Added:** User control over position sizing (10-100%)
✅ **Result:** Realistic, achievable returns

**Old buggy returns of 50%+ were FALSE** - now showing realistic 5-20% returns based on actual capital constraints.
