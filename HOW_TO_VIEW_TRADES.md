# How to View and Verify Trades from Web UI

## What's New ✅

The simulator now **automatically saves ALL trades to CSV files** after each simulation run!

## Where to Find the CSV Files

After running a simulation in the web UI, check this folder:
```
simulation_results_real/
```

You'll find these files:

### 1. **all_trades.csv** - ALL trades from ALL combinations
Contains every single trade from the entire simulation run.

### 2. **{scanner}_{strategy}_trades.csv** - Per-combination trades
Individual CSV files for each scanner+strategy combination.

Examples:
- `top_movers_Mean_Reversion_trades.csv`
- `relative_strength_Momentum_trades.csv`
- `best_setups_Volatility_Breakout_trades.csv`

## CSV Format

Each CSV contains these columns:

| Column | Description | Example |
|--------|-------------|---------|
| scanner | Which scanner selected the stock | `relative_strength` |
| strategy | Which strategy generated the trade | `Mean Reversion` |
| symbol | Stock symbol | `AAPL` |
| week_number | Week number in simulation | `1` |
| entry_price | Actual entry price from real data | `223.45` |
| exit_price | Actual exit price from real data | `225.12` |
| pnl_pct | Percentage P&L | `0.0074` (0.74%) |
| pnl_dollars | Dollar P&L | `167.50` |
| week_start | Week start timestamp | `2025-09-09` |
| week_end | Week end timestamp | `2025-09-16` |

## How to Verify Trades are REAL

### Method 1: Check Prices on Trading View or Yahoo Finance

1. Open `all_trades.csv` in Excel or Google Sheets
2. Pick any trade, note the:
   - Symbol (e.g., AAPL)
   - Entry price (e.g., $223.45)
   - Week dates (e.g., 2025-09-09 to 2025-09-16)
3. Go to TradingView.com or Yahoo Finance
4. Look up the stock for that week
5. Verify the entry price actually happened during that week!

### Method 2: Check Price Range

```python
import pandas as pd

# Load the trades
trades = pd.read_csv('simulation_results_real/all_trades.csv')

# Show summary
print(f"Total trades: {len(trades)}")
print(f"Symbols traded: {trades['symbol'].unique()}")
print(f"Average P&L: ${trades['pnl_dollars'].mean():.2f}")
print(f"Win rate: {(trades['pnl_dollars'] > 0).sum() / len(trades) * 100:.1f}%")

# Show first 10 trades
print("\nFirst 10 trades:")
print(trades[['symbol', 'entry_price', 'exit_price', 'pnl_dollars']].head(10))
```

### Method 3: Check Data Timestamps

Every trade happens during actual market hours (9:30 AM - 4:00 PM ET), using real 1-minute price bars downloaded from Alpaca.

## Example: Verifying a Trade

Let's say you see this trade in the CSV:

```
scanner,strategy,symbol,week_number,entry_price,exit_price,pnl_pct,pnl_dollars,week_start,week_end
relative_strength,Mean Reversion,AAPL,2,223.45,225.12,0.00747,334.50,2025-09-16,2025-09-23
```

**To verify:**
1. Symbol: AAPL
2. Entry: $223.45
3. Exit: $225.12
4. Week: Sep 16-23, 2025

Go to TradingView → AAPL → 1-minute chart → Sep 16-23, 2025:
- ✅ Check if $223.45 price existed that week
- ✅ Check if $225.12 price existed that week
- ✅ Verify price moved from entry to exit

## Quick Stats Script

Save this as `analyze_trades.py`:

```python
import pandas as pd

trades = pd.read_csv('simulation_results_real/all_trades.csv')

print("="*80)
print("TRADE ANALYSIS")
print("="*80)

print(f"\n📊 Total Trades: {len(trades)}")
print(f"📈 Winning Trades: {(trades['pnl_dollars'] > 0).sum()}")
print(f"📉 Losing Trades: {(trades['pnl_dollars'] <= 0).sum()}")
print(f"💰 Total P&L: ${trades['pnl_dollars'].sum():,.2f}")
print(f"📊 Win Rate: {(trades['pnl_dollars'] > 0).sum() / len(trades) * 100:.1f}%")

print("\n🎯 By Symbol:")
symbol_stats = trades.groupby('symbol').agg({
    'pnl_dollars': ['count', 'sum', 'mean']
}).round(2)
print(symbol_stats)

print("\n🔍 By Scanner + Strategy:")
combo_stats = trades.groupby(['scanner', 'strategy']).agg({
    'pnl_dollars': ['count', 'sum']
}).round(2)
print(combo_stats)

print("\n💎 Top 10 Best Trades:")
print(trades.nlargest(10, 'pnl_dollars')[['symbol', 'entry_price', 'exit_price', 'pnl_dollars']])

print("\n💀 Top 10 Worst Trades:")
print(trades.nsmallest(10, 'pnl_dollars')[['symbol', 'entry_price', 'exit_price', 'pnl_dollars']])
```

Run with:
```bash
python analyze_trades.py
```

## Summary

✅ **Trades are automatically saved to CSV**
✅ **Every trade has real entry/exit prices**
✅ **You can verify trades against actual market data**
✅ **Individual CSVs per strategy for detailed analysis**

No more guessing - now you have complete transparency into every trade!
