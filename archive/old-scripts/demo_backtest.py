#!/usr/bin/env python3
"""
Demo backtest script with simulated data to demonstrate the momentum strategy.

This creates synthetic realistic stock data to show how the backtesting works,
since Yahoo Finance has API limitations for historical intraday data.
"""

import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


class DemoBacktest:
    """Demo backtesting with synthetic data."""

    def __init__(self):
        self.min_price_change_pct = 2.0
        self.min_volume_ratio = 2.0
        self.window_minutes = 5
        self.stop_loss_pct = 2.0
        self.take_profit_pct = 4.0
        self.position_size = 10000

    def generate_synthetic_data(
        self, symbol: str, start_date: datetime, end_date: datetime, base_price: float = 150
    ) -> pd.DataFrame:
        """Generate realistic synthetic stock data with momentum events."""
        print(f"Generating synthetic data for {symbol}...")

        # Calculate number of 5-minute bars
        days = (end_date - start_date).days
        bars_per_day = 78  # 6.5 hours * 60 min / 5 min
        total_bars = days * bars_per_day

        # Generate timestamps
        timestamps = []
        current = start_date.replace(hour=9, minute=30)

        for _ in range(total_bars):
            timestamps.append(current)
            current += timedelta(minutes=5)

            # Skip weekends and after-hours
            if current.hour >= 16:
                current = (current + timedelta(days=1)).replace(hour=9, minute=30)
            if current.weekday() >= 5:  # Saturday/Sunday
                current = current + timedelta(days=7 - current.weekday())

        # Generate price data with realistic momentum events
        np.random.seed(hash(symbol) % 2**32)

        prices = []
        volumes = []
        current_price = base_price
        base_volume = 1000000

        in_momentum_event = False
        momentum_remaining = 0

        for i in range(len(timestamps)):
            # Check if we should start a new momentum event
            if not in_momentum_event and np.random.random() < 0.005:  # 0.5% chance per bar
                in_momentum_event = True
                momentum_remaining = 5  # 5-bar momentum event
                momentum_direction = np.random.choice([-1, 1])

            # Random walk with occasional momentum events
            if in_momentum_event and momentum_remaining > 0:
                # Strong directional move with high volume
                move_pct = momentum_direction * np.random.uniform(0.8, 1.2)
                volume_spike = np.random.uniform(2.5, 4.0)
                momentum_remaining -= 1
                if momentum_remaining == 0:
                    in_momentum_event = False
            else:
                # Normal market behavior
                move_pct = np.random.normal(0, 0.3)
                volume_spike = np.random.uniform(0.8, 1.2)

            # Apply price change
            current_price *= (1 + move_pct / 100)

            # Generate OHLC for this bar
            high = current_price * (1 + abs(move_pct) / 200)
            low = current_price * (1 - abs(move_pct) / 200)
            open_price = current_price * (1 - move_pct / 200)
            close = current_price

            volume = int(base_volume * volume_spike * np.random.uniform(0.9, 1.1))

            prices.append({
                "timestamp": timestamps[i],
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            })

        df = pd.DataFrame(prices)
        print(f"  ✓ Generated {len(df)} bars for {symbol}")
        return df

    def detect_momentum_events(self, df: pd.DataFrame, symbol: str) -> list:
        """Detect momentum events."""
        df = df.copy()
        df["avg_volume"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["avg_volume"]

        events = []

        for i in range(self.window_minutes, len(df) - 60):  # Leave room for continuation analysis
            window = df.iloc[i - self.window_minutes + 1 : i + 1]

            price_change_pct = (
                (window.iloc[-1]["close"] - window.iloc[0]["open"])
                / window.iloc[0]["open"]
                * 100
            )

            avg_vol_ratio = window["volume_ratio"].mean()

            if pd.isna(avg_vol_ratio):
                continue

            if (
                abs(price_change_pct) >= self.min_price_change_pct
                and avg_vol_ratio >= self.min_volume_ratio
            ):
                direction = "UP" if price_change_pct > 0 else "DOWN"

                # Analyze continuation
                continuation_bars = 0
                peak_price = window.iloc[-1]["close"]

                for j in range(i + 1, min(i + 60, len(df))):
                    if direction == "UP":
                        if df.iloc[j]["close"] > peak_price:
                            peak_price = df.iloc[j]["close"]
                            continuation_bars = j - i
                    else:
                        if df.iloc[j]["close"] < peak_price:
                            peak_price = df.iloc[j]["close"]
                            continuation_bars = j - i

                event = {
                    "symbol": symbol,
                    "timestamp": window.iloc[0]["timestamp"],
                    "end_idx": i,
                    "direction": direction,
                    "entry_price": float(window.iloc[-1]["close"]),
                    "initial_move_pct": abs(price_change_pct),
                    "volume_ratio": float(avg_vol_ratio),
                    "continuation_bars": continuation_bars,
                }

                events.append(event)

        return events

    def simulate_trades(self, symbol: str, df: pd.DataFrame, events: list) -> list:
        """Simulate trades."""
        trades = []

        for event in events:
            # Simple entry rule: enter if initial move >= 2.5%
            if event["initial_move_pct"] < 2.5:
                continue

            entry_idx = event["end_idx"]
            entry_price = event["entry_price"]
            direction = event["direction"]

            # Simulate exit
            if direction == "UP":
                stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
                take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
            else:
                stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)
                take_profit_price = entry_price * (1 - self.take_profit_pct / 100)

            # Check next 120 bars
            for j in range(entry_idx + 1, min(entry_idx + 120, len(df))):
                bar = df.iloc[j]

                if direction == "UP":
                    if bar["low"] <= stop_loss_price:
                        pnl_pct = ((stop_loss_price - entry_price) / entry_price) * 100
                        trades.append(self._create_trade(
                            symbol, event["timestamp"], entry_price, direction,
                            bar["timestamp"], stop_loss_price, "STOP_LOSS", pnl_pct, j - entry_idx
                        ))
                        break
                    elif bar["high"] >= take_profit_price:
                        pnl_pct = ((take_profit_price - entry_price) / entry_price) * 100
                        trades.append(self._create_trade(
                            symbol, event["timestamp"], entry_price, direction,
                            bar["timestamp"], take_profit_price, "TAKE_PROFIT", pnl_pct, j - entry_idx
                        ))
                        break
                else:
                    if bar["high"] >= stop_loss_price:
                        pnl_pct = ((entry_price - stop_loss_price) / entry_price) * 100
                        trades.append(self._create_trade(
                            symbol, event["timestamp"], entry_price, direction,
                            bar["timestamp"], stop_loss_price, "STOP_LOSS", pnl_pct, j - entry_idx
                        ))
                        break
                    elif bar["low"] <= take_profit_price:
                        pnl_pct = ((entry_price - take_profit_price) / entry_price) * 100
                        trades.append(self._create_trade(
                            symbol, event["timestamp"], entry_price, direction,
                            bar["timestamp"], take_profit_price, "TAKE_PROFIT", pnl_pct, j - entry_idx
                        ))
                        break

        return trades

    def _create_trade(
        self, symbol, entry_time, entry_price, direction, exit_time,
        exit_price, exit_reason, pnl_pct, duration_bars
    ):
        """Create trade dictionary."""
        return {
            "symbol": symbol,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "direction": direction,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl_pct": round(pnl_pct, 2),
            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
            "duration_minutes": duration_bars * 5,
        }

    def calculate_performance(self, trades: list) -> dict:
        """Calculate performance metrics."""
        if not trades:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0}

        df = pd.DataFrame(trades)
        winning = df[df["pnl_pct"] > 0]
        losing = df[df["pnl_pct"] <= 0]

        win_rate = len(winning) / len(df)
        total_pnl = df["pnl_dollars"].sum()
        avg_win = winning["pnl_dollars"].mean() if len(winning) > 0 else 0
        avg_loss = losing["pnl_dollars"].mean() if len(losing) > 0 else 0

        gross_profit = winning["pnl_dollars"].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing["pnl_dollars"].sum()) if len(losing) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        returns = df["pnl_pct"].values
        sharpe = (
            (returns.mean() / returns.std()) * np.sqrt(252)
            if returns.std() > 0 else 0
        )

        exit_reasons = df["exit_reason"].value_counts().to_dict()

        return {
            "total_trades": len(df),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate, 3),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(df["pnl_dollars"].mean(), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_win": round(winning["pnl_dollars"].max() if len(winning) > 0 else 0, 2),
            "max_loss": round(losing["pnl_dollars"].min() if len(losing) > 0 else 0, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "INF",
            "sharpe_ratio": round(sharpe, 2),
            "avg_duration_minutes": round(df["duration_minutes"].mean(), 1),
            "exit_reasons": exit_reasons,
        }

    def run_backtest(
        self, symbols: list, start_date: datetime, end_date: datetime
    ) -> dict:
        """Run complete backtest."""
        print("\n" + "=" * 80)
        print("MOMENTUM STRATEGY BACKTEST (DEMO WITH SYNTHETIC DATA)")
        print("=" * 80)
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Strategy: Momentum breakout with {self.stop_loss_pct}% stop loss, {self.take_profit_pct}% take profit")
        print("=" * 80 + "\n")

        base_prices = {"AAPL": 140, "MSFT": 280, "GOOGL": 2400, "TSLA": 650, "NVDA": 200}

        all_trades = []
        performance_by_symbol = {}

        for symbol in symbols:
            print(f"\nProcessing {symbol}...")

            # Generate synthetic data
            df = self.generate_synthetic_data(
                symbol, start_date, end_date, base_prices.get(symbol, 150)
            )

            # Detect events
            events = self.detect_momentum_events(df, symbol)
            print(f"  ✓ Detected {len(events)} momentum events")

            if not events:
                continue

            # Simulate trades
            trades = self.simulate_trades(symbol, df, events)
            print(f"  ✓ Simulated {len(trades)} trades")

            all_trades.extend(trades)

            if trades:
                performance_by_symbol[symbol] = self.calculate_performance(trades)

        # Calculate overall performance
        overall = self.calculate_performance(all_trades)

        # Print results
        self._print_results(overall, performance_by_symbol, start_date, end_date)

        return {
            "overall": overall,
            "by_symbol": performance_by_symbol,
            "trades": all_trades,
        }

    def _print_results(self, overall, by_symbol, start_date, end_date):
        """Print formatted results."""
        print("\n" + "=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print(f"\nPeriod: {start_date.date()} to {end_date.date()}")
        print(f"Total Trades: {overall['total_trades']}")

        if overall['total_trades'] > 0:
            print("\n" + "-" * 80)
            print("OVERALL PERFORMANCE")
            print("-" * 80)
            print(f"Win Rate:              {overall['win_rate'] * 100:.1f}%")
            print(f"Winning Trades:        {overall['winning_trades']}")
            print(f"Losing Trades:         {overall['losing_trades']}")
            print(f"Total P&L:             ${overall['total_pnl']:,.2f}")
            print(f"Avg P&L per Trade:     ${overall['avg_pnl_per_trade']:,.2f}")
            print(f"Average Win:           ${overall['avg_win']:,.2f}")
            print(f"Average Loss:          ${overall['avg_loss']:,.2f}")
            print(f"Max Win:               ${overall['max_win']:,.2f}")
            print(f"Max Loss:              ${overall['max_loss']:,.2f}")
            print(f"Profit Factor:         {overall['profit_factor']}")
            print(f"Sharpe Ratio:          {overall['sharpe_ratio']}")
            print(f"Avg Trade Duration:    {overall['avg_duration_minutes']:.1f} minutes")

            print("\n" + "-" * 80)
            print("EXIT REASON BREAKDOWN")
            print("-" * 80)
            for reason, count in overall["exit_reasons"].items():
                pct = (count / overall["total_trades"]) * 100
                print(f"{reason:20s}: {count:4d} ({pct:5.1f}%)")

            if by_symbol:
                print("\n" + "-" * 80)
                print("PERFORMANCE BY SYMBOL")
                print("-" * 80)
                for symbol, perf in by_symbol.items():
                    print(
                        f"{symbol:8s}: Trades={perf['total_trades']:3d}, "
                        f"Win Rate={perf['win_rate']*100:5.1f}%, "
                        f"Total P&L=${perf['total_pnl']:8,.2f}"
                    )

        print("\n" + "=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Demo Momentum Backtest with Synthetic Data"
    )
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,GOOGL",
        help="Comma-separated list of stock symbols",
    )
    parser.add_argument(
        "--start",
        default="2021-06-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default="2022-06-30",
        help="End date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    backtest = DemoBacktest()
    results = backtest.run_backtest(symbols, start_date, end_date)

    # Save results
    if results["trades"]:
        trades_df = pd.DataFrame(results["trades"])
        output_file = f"demo_backtest_results_{start_date.date()}_{end_date.date()}.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"✓ Detailed trade log saved to: {output_file}\n")


if __name__ == "__main__":
    main()
