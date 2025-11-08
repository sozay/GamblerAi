# Transaction Logging

## Overview

The GamblerAi transaction logging system provides comprehensive tracking of all trading activity across backtesting, paper trading, and live trading modes. All trades are logged to:

1. **Database** - PostgreSQL/SQLite for structured queries
2. **CSV File** - `logs/transactions.csv` for spreadsheet analysis
3. **JSON File** - `logs/transactions.jsonl` for programmatic processing

## Features

- Automatic logging of all trade entries and exits
- Complete trade metadata (entry/exit prices, stop loss, targets, P&L)
- Risk metrics (max adverse/favorable excursion)
- Strategy attribution
- Trading mode tracking (backtest/paper/live)
- Query interface for transaction analysis

## Quick Start

### 1. Run Database Migration

First, create the transactions table:

```bash
python scripts/migrate_add_transactions.py
```

### 2. Use with TradeManager (Backtesting)

```python
from gambler_ai.backtesting.trade import TradeManager, TradeDirection
from gambler_ai.utils.transaction_logger import TransactionLogger

# Initialize logger
logger = TransactionLogger(trading_mode="backtest")

# Initialize TradeManager with logger
trade_manager = TradeManager(
    initial_capital=100000.0,
    transaction_logger=logger,
)

# Open a trade (automatically logged)
trade = trade_manager.open_trade(
    symbol="AAPL",
    direction=TradeDirection.LONG,
    entry_time=datetime.now(),
    entry_price=150.50,
    stop_loss=147.00,
    target=156.00,
    strategy_name="momentum_breakout",
)

# Close the trade (automatically logged)
trade.close(
    exit_time=datetime.now(),
    exit_price=156.00,
    reason="target"
)
trade_manager.close_trade(trade)
```

### 3. Use with Paper Trading

```python
from gambler_ai.utils.transaction_logger import TransactionLogger
from scripts.alpaca_paper_trading import AlpacaPaperTrader

# Initialize logger
logger = TransactionLogger(trading_mode="paper")

# Initialize paper trader with logger
trader = AlpacaPaperTrader(
    api_key="your_key",
    api_secret="your_secret",
    transaction_logger=logger,
)

# All trades are now automatically logged
trader.run_paper_trading(symbols=["AAPL", "TSLA"])
```

### 4. Query Transactions

```python
from gambler_ai.utils.transaction_logger import TransactionLogger

logger = TransactionLogger()

# Get all transactions
all_txns = logger.get_all_transactions()

# Get only closed trades
closed = logger.get_all_transactions(status="CLOSED")

# Get transactions by symbol
aapl_trades = logger.get_transactions_by_symbol("AAPL")

# Get transactions by strategy
momentum_trades = logger.get_transactions_by_strategy("momentum_breakout")

# Analyze results
for txn in closed:
    print(f"{txn.symbol}: ${txn.pnl} ({txn.pnl_pct}%)")
```

## Database Schema

The `transactions` table includes:

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| symbol | String | Trading symbol |
| direction | String | LONG or SHORT |
| status | String | OPEN or CLOSED |
| entry_time | DateTime | Entry timestamp |
| entry_price | Decimal | Entry price |
| position_size | Decimal | Number of shares/contracts |
| stop_loss | Decimal | Stop loss price |
| target | Decimal | Take profit target |
| exit_time | DateTime | Exit timestamp |
| exit_price | Decimal | Exit price |
| exit_reason | String | Reason for exit |
| pnl | Decimal | Profit/loss in dollars |
| pnl_pct | Decimal | P&L percentage |
| return_pct | Decimal | Return percentage |
| max_adverse_excursion | Decimal | Worst drawdown during trade |
| max_favorable_excursion | Decimal | Best profit during trade |
| strategy_name | String | Trading strategy name |
| trading_mode | String | backtest/paper/live |
| duration_seconds | Integer | Trade duration |
| created_at | DateTime | Record creation time |
| updated_at | DateTime | Record update time |

## File Output Formats

### CSV Format

Standard CSV file with headers, suitable for:
- Excel/Google Sheets analysis
- Pandas DataFrame loading
- Data visualization tools

Location: `logs/transactions.csv`

### JSON Lines Format

Each line is a complete JSON object, suitable for:
- Stream processing
- Log aggregation tools
- Custom analysis scripts

Location: `logs/transactions.jsonl`

Example:
```json
{"id": 1, "symbol": "AAPL", "direction": "LONG", "entry_price": 150.50, "pnl": 550.00}
{"id": 2, "symbol": "TSLA", "direction": "LONG", "entry_price": 250.00, "pnl": -250.00}
```

## Examples

See `examples/test_transaction_logging.py` for complete examples:

```bash
python examples/test_transaction_logging.py
```

This demonstrates:
- Basic transaction logging
- TradeManager integration
- Querying transactions
- File output locations

## Integration Points

### Backtest Engine

The `BacktestEngine` can be configured with a `TransactionLogger`:

```python
from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.utils.transaction_logger import TransactionLogger

logger = TransactionLogger(trading_mode="backtest")
trade_manager = TradeManager(transaction_logger=logger)

engine = BacktestEngine(trade_manager=trade_manager)
# All trades are now logged
```

### Real Data Simulator

```python
from scripts.real_data_simulator import RealDataSimulator
from gambler_ai.utils.transaction_logger import TransactionLogger

logger = TransactionLogger(trading_mode="backtest")
simulator = RealDataSimulator(transaction_logger=logger)
```

### Alpaca Paper Trading

```python
from scripts.alpaca_paper_trading import AlpacaPaperTrader
from gambler_ai.utils.transaction_logger import TransactionLogger

logger = TransactionLogger(trading_mode="paper")
trader = AlpacaPaperTrader(
    api_key="key",
    api_secret="secret",
    transaction_logger=logger
)
```

## Analysis Queries

### SQL Queries

Connect directly to the database for advanced analysis:

```sql
-- Total P&L by strategy
SELECT strategy_name,
       COUNT(*) as trades,
       SUM(pnl) as total_pnl,
       AVG(pnl_pct) as avg_return
FROM transactions
WHERE status = 'CLOSED'
GROUP BY strategy_name;

-- Win rate by symbol
SELECT symbol,
       COUNT(*) as trades,
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM transactions
WHERE status = 'CLOSED'
GROUP BY symbol;

-- Average trade duration
SELECT strategy_name,
       AVG(duration_seconds) / 60 as avg_duration_minutes
FROM transactions
WHERE status = 'CLOSED'
GROUP BY strategy_name;
```

### Python Analysis

```python
import pandas as pd
from gambler_ai.utils.transaction_logger import TransactionLogger

logger = TransactionLogger()

# Load into pandas
closed_trades = logger.get_all_transactions(status="CLOSED")
df = pd.DataFrame([{
    'symbol': t.symbol,
    'pnl': float(t.pnl),
    'pnl_pct': float(t.pnl_pct),
    'strategy': t.strategy_name,
    'duration': t.duration_seconds,
} for t in closed_trades])

# Analysis
print(df.groupby('strategy')['pnl'].sum())
print(df.groupby('symbol')['pnl_pct'].mean())
```

## Best Practices

1. **Always enable logging** - Transaction logs are essential for:
   - Performance analysis
   - Strategy optimization
   - Compliance and auditing
   - Post-trade review

2. **Regular backups** - Back up your transaction logs:
   ```bash
   cp logs/transactions.csv logs/transactions_backup_$(date +%Y%m%d).csv
   ```

3. **Monitor disk space** - Transaction logs grow over time, especially with high-frequency strategies

4. **Use appropriate trading_mode** - Set the correct mode for accurate tracking:
   - `backtest` - Historical simulation
   - `paper` - Paper trading
   - `live` - Real money trading

5. **Error handling** - The logger includes error handling to prevent trade failures if logging fails

## Troubleshooting

### Database not found

Run the migration script:
```bash
python scripts/migrate_add_transactions.py
```

### Logging not working

Check that TransactionLogger is passed to TradeManager:
```python
logger = TransactionLogger()
trade_manager = TradeManager(transaction_logger=logger)  # Must pass logger
```

### File permissions

Ensure the `logs/` directory is writable:
```bash
mkdir -p logs
chmod 755 logs
```

## Recovery Features

Transaction logs support recovery from:
- System crashes (all logged trades persist)
- Backtest interruptions (completed trades are saved)
- Analysis across multiple sessions (historical data retained)

## Future Enhancements

Planned features:
- Real-time trade streaming
- Webhook notifications on trade events
- Advanced analytics dashboard
- Trade replay functionality
- Performance attribution analysis
