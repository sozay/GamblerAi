#!/usr/bin/env python3
"""
Backtest Automatic Stock Screening - DEMO VERSION with Simulated Data

Demonstrates the backtest functionality with simulated historical data.
For real backtesting, use backtest_screening.py with valid API credentials.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import random

np.random.seed(42)
random.seed(42)


def generate_simulated_data(symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Generate simulated price data for a symbol.

    Args:
        symbol: Stock symbol
        start_date: Start date
        end_date: End date

    Returns:
        DataFrame with OHLCV data
    """
    days = (end_date - start_date).days + 100  # Extra buffer
    dates = pd.date_range(start=start_date - timedelta(days=100), periods=days, freq='D')

    # Base price varies by symbol
    base_price = random.uniform(50, 500)

    # Simulate price movement with trend and noise
    trend = np.linspace(0, random.uniform(-0.3, 0.5), days)  # -30% to +50% trend
    noise = np.random.normal(0, 0.02, days)  # 2% daily volatility
    returns = trend + noise

    prices = base_price * np.cumprod(1 + returns)

    # Generate OHLC from close prices
    high = prices * (1 + np.abs(np.random.normal(0, 0.01, days)))
    low = prices * (1 - np.abs(np.random.normal(0, 0.01, days)))
    open_prices = np.roll(prices, 1)
    open_prices[0] = prices[0]

    # Volume
    base_volume = random.randint(1_000_000, 10_000_000)
    volume = base_volume * (1 + np.random.normal(0, 0.3, days))

    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': prices,
        'volume': volume.astype(int),
    })

    return df


class SimulatedBacktest:
    """Simplified backtest with simulated data."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100_000.0,
        screening_interval_days: int = 1,
        max_positions: int = 5,
        position_size_pct: float = 0.20,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.screening_interval = timedelta(days=screening_interval_days)
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        # Universe
        self.universe = [
            "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA",
            "TSLA", "AMD", "JPM", "BAC", "WFC", "JNJ", "UNH", "WMT"
        ]

        # State
        self.capital = initial_capital
        self.positions: Dict[str, Dict] = {}
        self.watchlist: List[str] = []
        self.historical_data: Dict[str, pd.DataFrame] = {}

        # Tracking
        self.trades: List[Dict] = []
        self.equity_curve: List = []
        self.screenings: List[Dict] = []

    def load_data(self):
        """Load simulated historical data."""
        print(f"Generating simulated data for {len(self.universe)} symbols...")

        for symbol in self.universe:
            df = generate_simulated_data(symbol, self.start_date, self.end_date)
            self.historical_data[symbol] = df

        print(f"✓ Generated data for {len(self.historical_data)} symbols\n")

    def get_data_at_time(self, symbol: str, current_time: datetime, lookback: int = 100) -> pd.DataFrame:
        """Get data up to current time."""
        if symbol not in self.historical_data:
            return None

        df = self.historical_data[symbol]
        mask = df['timestamp'] <= current_time
        return df[mask].tail(lookback)

    def screen_stocks(self, current_time: datetime) -> List[str]:
        """
        Simple screening: select stocks with positive momentum.
        """
        candidates = []

        for symbol in self.universe:
            data = self.get_data_at_time(symbol, current_time, lookback=20)

            if data is None or len(data) < 20:
                continue

            # Calculate momentum
            start_price = data['close'].iloc[0]
            current_price = data['close'].iloc[-1]
            momentum = ((current_price - start_price) / start_price) * 100

            # Calculate volume trend
            avg_volume = data['volume'].mean()
            recent_volume = data['volume'].tail(5).mean()
            volume_ratio = recent_volume / avg_volume

            # Score
            score = momentum * volume_ratio

            candidates.append({
                'symbol': symbol,
                'score': score,
                'momentum': momentum,
                'volume_ratio': volume_ratio,
                'price': current_price,
            })

        # Sort by score and select top N
        candidates.sort(key=lambda x: x['score'], reverse=True)
        selected = [c['symbol'] for c in candidates[:self.max_positions]]

        self.screenings.append({
            'timestamp': current_time,
            'candidates': len(candidates),
            'selected': selected,
        })

        return selected

    def generate_signal(self, symbol: str, current_time: datetime) -> str:
        """
        Simple signal generation based on momentum and RSI.
        """
        data = self.get_data_at_time(symbol, current_time, lookback=50)

        if data is None or len(data) < 20:
            return None

        # Simple momentum
        sma_10 = data['close'].rolling(10).mean().iloc[-1]
        sma_20 = data['close'].rolling(20).mean().iloc[-1]
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]

        # Simple RSI
        deltas = data['close'].diff()
        gain = deltas.where(deltas > 0, 0).rolling(14).mean()
        loss = -deltas.where(deltas < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # Not in position - look for buy
        if symbol not in self.positions:
            # Buy signal: bullish momentum crossover or oversold bounce
            if (sma_10 > sma_20 and current_price > prev_price) or (current_rsi < 35):
                return 'BUY'

        # In position - look for sell
        else:
            # Sell signal: bearish crossover or overbought
            if (sma_10 < sma_20 and current_price < prev_price) or (current_rsi > 70):
                return 'SELL'

        return None

    def execute_trade(self, symbol: str, signal: str, current_time: datetime, current_price: float):
        """Execute a trade."""
        if signal == 'BUY' and symbol not in self.positions:
            if len(self.positions) >= self.max_positions:
                return

            position_value = self.capital * self.position_size_pct
            shares = int(position_value / current_price)

            if shares < 1:
                return

            cost = shares * current_price

            if cost > self.capital:
                return

            self.capital -= cost

            self.positions[symbol] = {
                'shares': shares,
                'entry_price': current_price,
                'entry_time': current_time,
                'stop_loss': current_price * (1 - self.stop_loss_pct),
                'take_profit': current_price * (1 + self.take_profit_pct),
            }

            print(f"  BUY  {shares:3d} {symbol:6s} @ ${current_price:7.2f} = ${cost:10,.2f}")

            self.trades.append({
                'timestamp': current_time,
                'symbol': symbol,
                'action': 'BUY',
                'shares': shares,
                'price': current_price,
                'value': cost,
            })

        elif signal == 'SELL' and symbol in self.positions:
            position = self.positions[symbol]
            proceeds = position['shares'] * current_price
            self.capital += proceeds

            cost = position['shares'] * position['entry_price']
            pnl = proceeds - cost
            pnl_pct = (pnl / cost) * 100
            hold_days = (current_time - position['entry_time']).days

            print(f"  SELL {position['shares']:3d} {symbol:6s} @ ${current_price:7.2f} = ${proceeds:10,.2f} "
                  f"(P&L: ${pnl:+8.2f} / {pnl_pct:+6.2f}%, {hold_days}d)")

            self.trades.append({
                'timestamp': current_time,
                'symbol': symbol,
                'action': 'SELL',
                'shares': position['shares'],
                'price': current_price,
                'value': proceeds,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'hold_days': hold_days,
            })

            del self.positions[symbol]

    def check_stops(self, current_time: datetime):
        """Check stop loss and take profit."""
        for symbol in list(self.positions.keys()):
            data = self.get_data_at_time(symbol, current_time, lookback=1)

            if data is None or len(data) == 0:
                continue

            current_price = data['close'].iloc[-1]
            position = self.positions[symbol]

            if current_price <= position['stop_loss']:
                print(f"  ⚠️  STOP LOSS triggered for {symbol}")
                self.execute_trade(symbol, 'SELL', current_time, current_price)
            elif current_price >= position['take_profit']:
                print(f"  🎯 TAKE PROFIT hit for {symbol}")
                self.execute_trade(symbol, 'SELL', current_time, current_price)

    def update_equity(self, current_time: datetime):
        """Update equity curve."""
        total_equity = self.capital

        for symbol, position in self.positions.items():
            data = self.get_data_at_time(symbol, current_time, lookback=1)
            if data is not None and len(data) > 0:
                current_price = data['close'].iloc[-1]
                total_equity += position['shares'] * current_price

        self.equity_curve.append((current_time, total_equity))

    def run(self):
        """Run the backtest."""
        print("="*80)
        print("SIMULATED BACKTEST - AUTOMATIC SCREENING")
        print("="*80)
        print(f"Period:           {self.start_date.date()} to {self.end_date.date()}")
        print(f"Initial Capital:  ${self.initial_capital:,.2f}")
        print(f"Max Positions:    {self.max_positions}")
        print(f"Position Size:    {self.position_size_pct*100:.0f}%")
        print(f"Stop Loss:        {self.stop_loss_pct*100:.1f}%")
        print(f"Take Profit:      {self.take_profit_pct*100:.1f}%")
        print("="*80)
        print()

        # Load data
        self.load_data()

        # Run simulation
        current_time = self.start_date
        next_screening = current_time
        screening_count = 0

        print("RUNNING SIMULATION...")
        print("="*80)
        print()

        while current_time <= self.end_date:
            # Periodic screening
            if current_time >= next_screening:
                screening_count += 1
                print(f"\n[{current_time.strftime('%Y-%m-%d')}] Screening #{screening_count}")
                print("-"*80)

                self.watchlist = self.screen_stocks(current_time)

                print(f"Selected {len(self.watchlist)} stocks: {', '.join(self.watchlist)}")
                print()

                next_screening = current_time + self.screening_interval

            # Generate signals for watchlist
            for symbol in self.watchlist:
                signal = self.generate_signal(symbol, current_time)

                if signal:
                    data = self.get_data_at_time(symbol, current_time, lookback=1)
                    if data is not None and len(data) > 0:
                        current_price = data['close'].iloc[-1]
                        self.execute_trade(symbol, signal, current_time, current_price)

            # Check stops
            self.check_stops(current_time)

            # Update equity
            self.update_equity(current_time)

            # Next day
            current_time += timedelta(days=1)

        # Close remaining positions
        print(f"\n[{self.end_date.strftime('%Y-%m-%d')}] Closing all positions")
        print("-"*80)

        for symbol in list(self.positions.keys()):
            data = self.get_data_at_time(symbol, self.end_date, lookback=1)
            if data is not None and len(data) > 0:
                current_price = data['close'].iloc[-1]
                self.execute_trade(symbol, 'SELL', self.end_date, current_price)

        # Results
        self.show_results()

    def show_results(self):
        """Show backtest results."""
        print("\n")
        print("="*80)
        print("BACKTEST RESULTS")
        print("="*80)
        print()

        final_equity = self.equity_curve[-1][1]
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        print(f"Initial Capital:  ${self.initial_capital:>15,.2f}")
        print(f"Final Equity:     ${final_equity:>15,.2f}")
        print(f"Total Return:     ${total_return:>15,.2f} ({total_return_pct:+.2f}%)")
        print()

        # Trade statistics
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']

        if sell_trades:
            winning_trades = [t for t in sell_trades if t['pnl'] > 0]
            losing_trades = [t for t in sell_trades if t['pnl'] <= 0]

            win_rate = (len(winning_trades) / len(sell_trades)) * 100
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            total_pnl = sum(t['pnl'] for t in sell_trades)

            print("Trade Statistics:")
            print(f"  Total Trades:     {len(sell_trades)}")
            print(f"  Winning Trades:   {len(winning_trades)} ({win_rate:.1f}%)")
            print(f"  Losing Trades:    {len(losing_trades)} ({100-win_rate:.1f}%)")
            print(f"  Average Win:      ${avg_win:>12,.2f}")
            print(f"  Average Loss:     ${avg_loss:>12,.2f}")
            print(f"  Total P&L:        ${total_pnl:>12,.2f}")

            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss) if losing_trades else float('inf')
                print(f"  Profit Factor:    {profit_factor:>15.2f}")
            print()

        # Screening stats
        print("Screening Statistics:")
        print(f"  Total Screenings: {len(self.screenings)}")

        # Equity curve stats
        if len(self.equity_curve) > 1:
            equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
            equity_df['returns'] = equity_df['equity'].pct_change()

            if equity_df['returns'].std() > 0:
                sharpe = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252)
                print(f"\nRisk Metrics:")
                print(f"  Sharpe Ratio:     {sharpe:>15.2f}")

            cummax = equity_df['equity'].cummax()
            drawdown = (equity_df['equity'] - cummax) / cummax
            max_drawdown = drawdown.min() * 100
            print(f"  Max Drawdown:     {max_drawdown:>14.2f}%")

        # Benchmark
        spy_data = self.historical_data.get('SPY')
        if spy_data is not None:
            spy_period = spy_data[
                (spy_data['timestamp'] >= self.start_date) &
                (spy_data['timestamp'] <= self.end_date)
            ]

            if len(spy_period) > 1:
                spy_return = ((spy_period['close'].iloc[-1] - spy_period['close'].iloc[0]) /
                             spy_period['close'].iloc[0]) * 100

                print(f"\nBenchmark (SPY Buy & Hold):")
                print(f"  SPY Return:       {spy_return:>14.2f}%")
                print(f"  Outperformance:   {total_return_pct - spy_return:>14.2f}%")

        print()
        print("="*80)

        # Save results
        if self.equity_curve:
            equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
            equity_df.to_csv('backtest_demo_equity_curve.csv', index=False)
            print("\n✓ Saved equity curve to: backtest_demo_equity_curve.csv")

        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv('backtest_demo_trades.csv', index=False)
            print("✓ Saved trades to: backtest_demo_trades.csv")

        print()


def main():
    """Run demo backtest."""
    start_date = datetime(2024, 11, 6)
    end_date = datetime(2025, 11, 5)

    backtest = SimulatedBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000.0,
        screening_interval_days=7,  # Weekly screening
        max_positions=5,
        position_size_pct=0.20,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
    )

    backtest.run()


if __name__ == "__main__":
    main()
