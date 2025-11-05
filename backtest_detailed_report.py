#!/usr/bin/env python3
"""
Detailed Backtest Report - Month by Month

Shows detailed trade history with:
- Month by month breakdown
- Stock selections
- Entry/exit dates and prices
- Individual trade P&L
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import random
from collections import defaultdict

np.random.seed(42)
random.seed(42)


def generate_realistic_data(symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Generate realistic price data with proper volatility."""
    days = (end_date - start_date).days + 100
    dates = pd.date_range(start=start_date - timedelta(days=100), periods=days, freq='D')

    # Symbol-specific characteristics
    symbol_params = {
        'AAPL': {'base': 180, 'trend': 0.15, 'vol': 0.018},
        'MSFT': {'base': 380, 'trend': 0.20, 'vol': 0.016},
        'GOOGL': {'base': 140, 'trend': 0.18, 'vol': 0.019},
        'AMZN': {'base': 175, 'trend': 0.12, 'vol': 0.022},
        'META': {'base': 480, 'trend': 0.25, 'vol': 0.024},
        'NVDA': {'base': 490, 'trend': 0.35, 'vol': 0.028},
        'TSLA': {'base': 245, 'trend': -0.05, 'vol': 0.032},
        'AMD': {'base': 165, 'trend': 0.22, 'vol': 0.026},
        'NFLX': {'base': 685, 'trend': 0.08, 'vol': 0.021},
        'JPM': {'base': 215, 'trend': 0.10, 'vol': 0.014},
        'BAC': {'base': 42, 'trend': 0.12, 'vol': 0.016},
        'WFC': {'base': 58, 'trend': 0.09, 'vol': 0.015},
        'JNJ': {'base': 155, 'trend': 0.05, 'vol': 0.011},
        'UNH': {'base': 520, 'trend': 0.14, 'vol': 0.013},
        'WMT': {'base': 70, 'trend': 0.11, 'vol': 0.012},
        'SPY': {'base': 470, 'trend': 0.15, 'vol': 0.012},
    }

    params = symbol_params.get(symbol, {'base': 150, 'trend': 0.10, 'vol': 0.020})

    base_price = params['base']
    trend_return = params['trend']
    daily_vol = params['vol']

    # Generate returns with trend + noise + cycles
    trend = np.linspace(0, trend_return, days)
    noise = np.random.normal(0, daily_vol, days)

    # Add market cycles (quarterly patterns)
    cycles = 0.03 * np.sin(np.linspace(0, 8 * np.pi, days))

    returns = trend + noise + cycles
    prices = base_price * np.cumprod(1 + returns)

    # Generate OHLC
    high = prices * (1 + np.abs(np.random.normal(0, 0.008, days)))
    low = prices * (1 - np.abs(np.random.normal(0, 0.008, days)))
    open_prices = np.roll(prices, 1)
    open_prices[0] = prices[0]

    # Volume with realistic patterns
    base_volume = random.randint(5_000_000, 20_000_000)
    volume = base_volume * (1 + np.random.normal(0, 0.25, days))

    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': prices,
        'volume': volume.astype(int),
    })

    return df


class DetailedBacktest:
    """Backtest with detailed reporting."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100_000.0,
        screening_interval_days: int = 7,
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
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA",
            "TSLA", "AMD", "NFLX", "JPM", "BAC", "WFC",
            "JNJ", "UNH", "WMT", "SPY"
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
        self.monthly_stats: Dict = defaultdict(lambda: {
            'trades': [],
            'capital_start': 0,
            'capital_end': 0,
            'screenings': [],
        })

    def load_data(self):
        """Load simulated data."""
        print(f"Generating realistic historical data for {len(self.universe)} symbols...")

        for symbol in self.universe:
            df = generate_realistic_data(symbol, self.start_date, self.end_date)
            self.historical_data[symbol] = df

        print(f"✓ Generated {len(self.historical_data)} symbols\n")

    def get_data_at_time(self, symbol: str, current_time: datetime, lookback: int = 100) -> pd.DataFrame:
        """Get data up to current time."""
        if symbol not in self.historical_data:
            return None

        df = self.historical_data[symbol]
        mask = df['timestamp'] <= current_time
        return df[mask].tail(lookback)

    def screen_stocks(self, current_time: datetime) -> List[str]:
        """Screen stocks with multiple strategies."""
        candidates = []

        for symbol in self.universe:
            if symbol == 'SPY':  # Skip benchmark
                continue

            data = self.get_data_at_time(symbol, current_time, lookback=30)

            if data is None or len(data) < 20:
                continue

            # Multiple scoring factors

            # 1. Momentum (20-day)
            start_price = data['close'].iloc[0]
            current_price = data['close'].iloc[-1]
            momentum_pct = ((current_price - start_price) / start_price) * 100

            # 2. Short-term momentum (5-day)
            short_momentum = ((data['close'].iloc[-1] - data['close'].iloc[-5]) /
                            data['close'].iloc[-5]) * 100

            # 3. Volume trend
            avg_volume = data['volume'].iloc[:15].mean()
            recent_volume = data['volume'].iloc[-5:].mean()
            volume_ratio = recent_volume / avg_volume

            # 4. Volatility (lower is better for risk)
            volatility = data['close'].pct_change().std() * 100

            # 5. Trend strength (SMA comparison)
            sma_20 = data['close'].rolling(20).mean().iloc[-1]
            trend_strength = ((current_price - sma_20) / sma_20) * 100

            # Composite score
            score = (
                momentum_pct * 0.30 +
                short_momentum * 0.25 +
                (volume_ratio - 1) * 100 * 0.15 +
                trend_strength * 0.20 +
                (5 - volatility) * 0.10  # Inverse volatility
            )

            candidates.append({
                'symbol': symbol,
                'score': score,
                'momentum': momentum_pct,
                'short_momentum': short_momentum,
                'volume_ratio': volume_ratio,
                'volatility': volatility,
                'price': current_price,
            })

        # Sort and select
        candidates.sort(key=lambda x: x['score'], reverse=True)
        selected = [c['symbol'] for c in candidates[:self.max_positions * 2]]

        # Store screening info
        screening_info = {
            'timestamp': current_time,
            'candidates': len(candidates),
            'selected': selected[:self.max_positions],
            'top_scores': [
                f"{c['symbol']}({c['score']:.1f})"
                for c in candidates[:self.max_positions]
            ],
        }
        self.screenings.append(screening_info)

        # Track monthly
        month_key = current_time.strftime('%Y-%m')
        self.monthly_stats[month_key]['screenings'].append(screening_info)

        return selected[:self.max_positions]

    def generate_signal(self, symbol: str, current_time: datetime) -> str:
        """Generate buy/sell signal."""
        data = self.get_data_at_time(symbol, current_time, lookback=50)

        if data is None or len(data) < 20:
            return None

        # Technical indicators
        sma_10 = data['close'].rolling(10).mean().iloc[-1]
        sma_20 = data['close'].rolling(20).mean().iloc[-1]
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2]

        # RSI
        deltas = data['close'].diff()
        gain = deltas.where(deltas > 0, 0).rolling(14).mean()
        loss = -deltas.where(deltas < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # MACD
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal_line = macd.ewm(span=9).mean()
        macd_cross = macd.iloc[-1] > signal_line.iloc[-1]

        # Not in position - look for buy
        if symbol not in self.positions:
            # Buy conditions: multiple confirmations
            bullish_momentum = sma_10 > sma_20 and current_price > prev_price
            oversold = current_rsi < 35
            macd_bullish = macd_cross

            if (bullish_momentum and macd_bullish) or oversold:
                return 'BUY'

        # In position - look for sell
        else:
            # Sell conditions
            bearish_momentum = sma_10 < sma_20 and current_price < prev_price
            overbought = current_rsi > 70
            macd_bearish = not macd_cross

            if (bearish_momentum and macd_bearish) or overbought:
                return 'SELL'

        return None

    def execute_trade(self, symbol: str, signal: str, current_time: datetime, current_price: float):
        """Execute trade and track monthly stats."""
        month_key = current_time.strftime('%Y-%m')

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

            trade = {
                'timestamp': current_time,
                'month': month_key,
                'symbol': symbol,
                'action': 'BUY',
                'shares': shares,
                'price': current_price,
                'value': cost,
                'capital_after': self.capital,
            }

            self.trades.append(trade)
            self.monthly_stats[month_key]['trades'].append(trade)

        elif signal == 'SELL' and symbol in self.positions:
            position = self.positions[symbol]
            proceeds = position['shares'] * current_price
            self.capital += proceeds

            cost = position['shares'] * position['entry_price']
            pnl = proceeds - cost
            pnl_pct = (pnl / cost) * 100
            hold_days = (current_time - position['entry_time']).days

            trade = {
                'timestamp': current_time,
                'month': month_key,
                'symbol': symbol,
                'action': 'SELL',
                'shares': position['shares'],
                'price': current_price,
                'value': proceeds,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'hold_days': hold_days,
                'entry_date': position['entry_time'].strftime('%Y-%m-%d'),
                'entry_price': position['entry_price'],
                'capital_after': self.capital,
            }

            self.trades.append(trade)
            self.monthly_stats[month_key]['trades'].append(trade)

            del self.positions[symbol]

    def check_stops(self, current_time: datetime):
        """Check stops."""
        for symbol in list(self.positions.keys()):
            data = self.get_data_at_time(symbol, current_time, lookback=1)

            if data is None or len(data) == 0:
                continue

            current_price = data['close'].iloc[-1]
            position = self.positions[symbol]

            if current_price <= position['stop_loss']:
                self.execute_trade(symbol, 'SELL', current_time, current_price)
            elif current_price >= position['take_profit']:
                self.execute_trade(symbol, 'SELL', current_time, current_price)

    def update_equity(self, current_time: datetime):
        """Update equity."""
        total_equity = self.capital

        for symbol, position in self.positions.items():
            data = self.get_data_at_time(symbol, current_time, lookback=1)
            if data is not None and len(data) > 0:
                current_price = data['close'].iloc[-1]
                total_equity += position['shares'] * current_price

        self.equity_curve.append((current_time, total_equity))

        # Update monthly end capital
        month_key = current_time.strftime('%Y-%m')
        self.monthly_stats[month_key]['capital_end'] = total_equity

    def run(self):
        """Run backtest."""
        print("="*100)
        print("DETAILED BACKTEST - MONTH BY MONTH REPORT")
        print("="*100)
        print(f"Period:           {self.start_date.date()} to {self.end_date.date()}")
        print(f"Initial Capital:  ${self.initial_capital:,.2f}")
        print(f"Max Positions:    {self.max_positions}")
        print(f"Position Size:    {self.position_size_pct*100:.0f}%")
        print(f"Stop Loss:        {self.stop_loss_pct*100:.1f}%")
        print(f"Take Profit:      {self.take_profit_pct*100:.1f}%")
        print(f"Screening:        Every {self.screening_interval.days} days")
        print("="*100)
        print()

        # Load data
        self.load_data()

        # Initialize monthly stats
        current_month = self.start_date.strftime('%Y-%m')
        self.monthly_stats[current_month]['capital_start'] = self.initial_capital

        # Simulation
        current_time = self.start_date
        next_screening = current_time

        # Initial screening
        self.watchlist = self.screen_stocks(current_time)
        self.update_equity(current_time)

        while current_time <= self.end_date:
            # Check for month change
            month_key = current_time.strftime('%Y-%m')
            if month_key not in self.monthly_stats or self.monthly_stats[month_key]['capital_start'] == 0:
                prev_month_equity = self.equity_curve[-1][1] if self.equity_curve else self.initial_capital
                self.monthly_stats[month_key]['capital_start'] = prev_month_equity

            # Periodic screening
            if current_time >= next_screening:
                self.watchlist = self.screen_stocks(current_time)
                next_screening = current_time + self.screening_interval

            # Generate signals
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
        for symbol in list(self.positions.keys()):
            data = self.get_data_at_time(symbol, self.end_date, lookback=1)
            if data is not None and len(data) > 0:
                current_price = data['close'].iloc[-1]
                self.execute_trade(symbol, 'SELL', self.end_date, current_price)

        # Final update
        self.update_equity(self.end_date)

        # Generate reports
        self.print_monthly_report()
        self.print_summary()
        self.save_reports()

    def print_monthly_report(self):
        """Print detailed month by month report."""
        print("\n")
        print("="*100)
        print("MONTH BY MONTH DETAILED REPORT")
        print("="*100)
        print()

        sorted_months = sorted(self.monthly_stats.keys())

        for month in sorted_months:
            stats = self.monthly_stats[month]

            if stats['capital_start'] == 0:
                continue

            print(f"\n{'='*100}")
            print(f"📅 MONTH: {month}")
            print(f"{'='*100}")

            # Capital change
            capital_start = stats['capital_start']
            capital_end = stats['capital_end'] if stats['capital_end'] > 0 else capital_start
            monthly_return = capital_end - capital_start
            monthly_return_pct = (monthly_return / capital_start) * 100 if capital_start > 0 else 0

            print(f"\n💰 CAPITAL:")
            print(f"  Start:  ${capital_start:>12,.2f}")
            print(f"  End:    ${capital_end:>12,.2f}")
            print(f"  Change: ${monthly_return:>12,.2f} ({monthly_return_pct:+.2f}%)")

            # Screenings
            if stats['screenings']:
                print(f"\n🔍 SCREENINGS: {len(stats['screenings'])} times")
                for i, screening in enumerate(stats['screenings'], 1):
                    date = screening['timestamp'].strftime('%Y-%m-%d')
                    selected = ', '.join(screening['selected'])
                    print(f"  {i}. {date}: Selected {selected}")

            # Trades
            trades = stats['trades']
            if trades:
                print(f"\n📊 TRADES: {len(trades)} total")
                print(f"\n  {'Date':<12} {'Action':<6} {'Symbol':<8} {'Shares':>7} {'Price':>10} {'Value':>12} {'P&L':>12} {'Hold':>6}")
                print(f"  {'-'*88}")

                for trade in trades:
                    date = trade['timestamp'].strftime('%Y-%m-%d')
                    action = trade['action']
                    symbol = trade['symbol']
                    shares = trade['shares']
                    price = trade['price']
                    value = trade['value']

                    if action == 'BUY':
                        print(f"  {date:<12} {action:<6} {symbol:<8} {shares:>7} ${price:>9.2f} ${value:>11,.2f}")
                    else:
                        pnl = trade.get('pnl', 0)
                        pnl_pct = trade.get('pnl_pct', 0)
                        hold_days = trade.get('hold_days', 0)
                        entry_date = trade.get('entry_date', 'N/A')
                        entry_price = trade.get('entry_price', 0)

                        pnl_str = f"${pnl:+.2f}" if pnl != 0 else ""
                        pct_str = f"({pnl_pct:+.1f}%)" if pnl != 0 else ""

                        print(f"  {date:<12} {action:<6} {symbol:<8} {shares:>7} ${price:>9.2f} ${value:>11,.2f} ${pnl:>10,.2f} {hold_days:>4}d")
                        print(f"    └─ Entry: {entry_date} @ ${entry_price:.2f}, P&L: {pnl_pct:+.2f}%")

                # Monthly trade summary
                sell_trades = [t for t in trades if t['action'] == 'SELL']
                if sell_trades:
                    total_pnl = sum(t.get('pnl', 0) for t in sell_trades)
                    winning = [t for t in sell_trades if t.get('pnl', 0) > 0]
                    losing = [t for t in sell_trades if t.get('pnl', 0) <= 0]

                    print(f"\n  📈 MONTHLY SUMMARY:")
                    print(f"    Closed Trades:   {len(sell_trades)}")
                    print(f"    Winners:         {len(winning)} ({len(winning)/len(sell_trades)*100:.1f}%)")
                    print(f"    Losers:          {len(losing)} ({len(losing)/len(sell_trades)*100:.1f}%)")
                    print(f"    Total P&L:       ${total_pnl:+,.2f}")
            else:
                print(f"\n📊 TRADES: No trades this month")

        print(f"\n{'='*100}\n")

    def print_summary(self):
        """Print overall summary."""
        print("\n")
        print("="*100)
        print("OVERALL SUMMARY")
        print("="*100)
        print()

        final_equity = self.equity_curve[-1][1]
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        print(f"💰 RETURNS:")
        print(f"  Initial Capital:  ${self.initial_capital:>15,.2f}")
        print(f"  Final Equity:     ${final_equity:>15,.2f}")
        print(f"  Total Return:     ${total_return:>15,.2f} ({total_return_pct:+.2f}%)")

        # Trade stats
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']

        if sell_trades:
            winning = [t for t in sell_trades if t['pnl'] > 0]
            losing = [t for t in sell_trades if t['pnl'] <= 0]

            win_rate = (len(winning) / len(sell_trades)) * 100
            avg_win = np.mean([t['pnl'] for t in winning]) if winning else 0
            avg_loss = np.mean([t['pnl'] for t in losing]) if losing else 0

            print(f"\n📊 TRADE STATISTICS:")
            print(f"  Total Trades:     {len(sell_trades)}")
            print(f"  Winning Trades:   {len(winning)} ({win_rate:.1f}%)")
            print(f"  Losing Trades:    {len(losing)} ({100-win_rate:.1f}%)")
            print(f"  Average Win:      ${avg_win:>12,.2f}")
            print(f"  Average Loss:     ${avg_loss:>12,.2f}")

            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss)
                print(f"  Profit Factor:    {profit_factor:>15.2f}")

            # Best and worst trades
            best = max(sell_trades, key=lambda x: x['pnl'])
            worst = min(sell_trades, key=lambda x: x['pnl'])

            print(f"\n🏆 BEST TRADE:")
            print(f"  {best['symbol']}: ${best['pnl']:+,.2f} ({best['pnl_pct']:+.2f}%) in {best['hold_days']} days")

            print(f"\n📉 WORST TRADE:")
            print(f"  {worst['symbol']}: ${worst['pnl']:+,.2f} ({worst['pnl_pct']:+.2f}%) in {worst['hold_days']} days")

        # Risk metrics
        if len(self.equity_curve) > 1:
            equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
            equity_df['returns'] = equity_df['equity'].pct_change()

            if equity_df['returns'].std() > 0:
                sharpe = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252)
                print(f"\n📈 RISK METRICS:")
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

                print(f"\n📊 BENCHMARK (SPY):")
                print(f"  SPY Return:       {spy_return:>14.2f}%")
                print(f"  Outperformance:   {total_return_pct - spy_return:>14.2f}%")

        print(f"\n{'='*100}\n")

    def save_reports(self):
        """Save detailed reports to files."""
        # All trades
        if self.trades:
            df = pd.DataFrame(self.trades)
            df.to_csv('detailed_trades.csv', index=False)
            print("✓ Saved detailed trades to: detailed_trades.csv")

        # Monthly summary
        monthly_summary = []
        for month in sorted(self.monthly_stats.keys()):
            stats = self.monthly_stats[month]
            if stats['capital_start'] == 0:
                continue

            sell_trades = [t for t in stats['trades'] if t['action'] == 'SELL']
            total_pnl = sum(t.get('pnl', 0) for t in sell_trades)
            winning = sum(1 for t in sell_trades if t.get('pnl', 0) > 0)

            monthly_summary.append({
                'month': month,
                'capital_start': stats['capital_start'],
                'capital_end': stats['capital_end'],
                'return': stats['capital_end'] - stats['capital_start'],
                'return_pct': ((stats['capital_end'] - stats['capital_start']) /
                              stats['capital_start'] * 100),
                'num_trades': len(sell_trades),
                'winners': winning,
                'total_pnl': total_pnl,
                'screenings': len(stats['screenings']),
            })

        if monthly_summary:
            df = pd.DataFrame(monthly_summary)
            df.to_csv('monthly_summary.csv', index=False)
            print("✓ Saved monthly summary to: monthly_summary.csv")

        # Equity curve
        if self.equity_curve:
            df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
            df.to_csv('detailed_equity_curve.csv', index=False)
            print("✓ Saved equity curve to: detailed_equity_curve.csv")

        print()


def main():
    """Run detailed backtest."""
    # Exactly 1 year: Nov 6, 2024 to Nov 5, 2025
    start_date = datetime(2024, 11, 6)
    end_date = datetime(2025, 11, 5)

    backtest = DetailedBacktest(
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
