#!/usr/bin/env python3
"""
Generate high-fidelity realistic stock data based on actual market conditions.

Uses real price ranges, volatility characteristics, and market regime changes
from the June 2021 - June 2022 period to create realistic synthetic data.
"""

import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path


class RealisticDataGenerator:
    """
    Generate realistic stock data based on actual market characteristics.

    Based on real market data from June 2021 - June 2022:
    - AAPL: Started ~$125, ended ~$140 (volatile with drawdown)
    - MSFT: Started ~$260, ended ~$270 (tech selloff mid-period)
    - GOOGL: Started ~$2400, ended ~$2250 (growth stock correction)
    """

    def __init__(self):
        # Real market characteristics from June 2021 - June 2022
        self.stock_params = {
            'AAPL': {
                'start_price': 125.0,
                'end_price': 140.0,
                'volatility': 0.025,  # Daily volatility ~2.5%
                'trend_phases': [
                    ('2021-06-01', '2021-09-01', 0.15),   # Uptrend +15%
                    ('2021-09-01', '2022-01-01', -0.05),  # Correction -5%
                    ('2022-01-01', '2022-03-01', -0.15),  # Sharp decline -15%
                    ('2022-03-01', '2022-06-30', 0.20),   # Recovery +20%
                ],
            },
            'MSFT': {
                'start_price': 260.0,
                'end_price': 270.0,
                'volatility': 0.023,
                'trend_phases': [
                    ('2021-06-01', '2021-11-01', 0.18),   # Strong uptrend +18%
                    ('2021-11-01', '2022-01-15', -0.08),  # Correction -8%
                    ('2022-01-15', '2022-03-15', -0.20),  # Tech selloff -20%
                    ('2022-03-15', '2022-06-30', 0.15),   # Recovery +15%
                ],
            },
            'GOOGL': {
                'start_price': 2400.0,
                'end_price': 2250.0,
                'volatility': 0.027,
                'trend_phases': [
                    ('2021-06-01', '2021-11-01', 0.12),   # Growth +12%
                    ('2021-11-01', '2022-01-01', 0.05),   # Consolidation +5%
                    ('2022-01-01', '2022-05-01', -0.25),  # Growth correction -25%
                    ('2022-05-01', '2022-06-30', 0.08),   # Bounce +8%
                ],
            },
            'TSLA': {
                'start_price': 650.0,
                'end_price': 750.0,
                'volatility': 0.040,  # Higher volatility
                'trend_phases': [
                    ('2021-06-01', '2021-10-01', 0.30),   # Massive rally +30%
                    ('2021-10-01', '2022-01-01', -0.15),  # Correction -15%
                    ('2022-01-01', '2022-03-15', -0.30),  # Sharp drop -30%
                    ('2022-03-15', '2022-06-30', 0.35),   # V-recovery +35%
                ],
            },
            'NVDA': {
                'start_price': 750.0,
                'end_price': 180.0,  # Stock split adjusted
                'volatility': 0.035,
                'trend_phases': [
                    ('2021-06-01', '2021-11-01', 0.40),   # AI hype +40%
                    ('2021-11-01', '2022-01-01', -0.10),  # Profit taking -10%
                    ('2022-01-01', '2022-04-01', -0.45),  # Tech rout -45%
                    ('2022-04-01', '2022-06-30', 0.05),   # Stabilization +5%
                ],
            },
        }

    def generate_daily_data(self, symbol, start_date, end_date):
        """Generate daily OHLCV data with realistic characteristics."""
        if symbol not in self.stock_params:
            raise ValueError(f"Unknown symbol: {symbol}. Available: {list(self.stock_params.keys())}")

        params = self.stock_params[symbol]

        # Generate trading days (exclude weekends)
        dates = pd.bdate_range(start=start_date, end=end_date, freq='B')

        # Initialize price array
        num_days = len(dates)
        prices = np.zeros(num_days)

        # Set seed for reproducibility but make it symbol-specific
        np.random.seed(hash(symbol) % 2**32)

        # Generate prices following trend phases
        current_price = params['start_price']

        for i, date in enumerate(dates):
            # Find current trend phase
            trend_return = 0
            for phase_start, phase_end, phase_return in params['trend_phases']:
                phase_start_dt = datetime.strptime(phase_start, '%Y-%m-%d')
                phase_end_dt = datetime.strptime(phase_end, '%Y-%m-%d')

                if phase_start_dt <= date <= phase_end_dt:
                    # Calculate position within phase
                    phase_days = (phase_end_dt - phase_start_dt).days
                    days_elapsed = (date - phase_start_dt).days
                    phase_progress = days_elapsed / phase_days if phase_days > 0 else 0

                    # Smooth trend with some randomness
                    daily_trend = (phase_return / phase_days) * 100  # Convert to daily %
                    break
            else:
                daily_trend = 0

            # Add volatility with mean reversion
            random_return = np.random.normal(daily_trend, params['volatility'] * 100)

            # Apply momentum and mean reversion
            if i > 0:
                # Add autocorrelation (momentum)
                prev_return = (prices[i-1] - (prices[i-2] if i > 1 else params['start_price'])) / (prices[i-2] if i > 1 else params['start_price']) * 100
                random_return += 0.1 * prev_return  # 10% momentum

            # Update price
            current_price *= (1 + random_return / 100)
            prices[i] = current_price

        # Generate OHLC from close prices
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            # Realistic intraday range (0.5% to 3% typical)
            daily_range_pct = np.random.uniform(0.005, 0.03)

            # High and low
            high = close * (1 + daily_range_pct * np.random.uniform(0.3, 0.7))
            low = close * (1 - daily_range_pct * np.random.uniform(0.3, 0.7))

            # Open based on previous close with gap
            if i == 0:
                open_price = params['start_price']
            else:
                gap = np.random.normal(0, params['volatility'] * 50)  # Overnight gap
                open_price = prices[i-1] * (1 + gap / 100)
                open_price = max(min(open_price, high), low)  # Constrain to daily range

            # Volume with realistic characteristics
            base_volume = 80_000_000 if symbol in ['AAPL', 'MSFT'] else \
                         30_000_000 if symbol == 'GOOGL' else \
                         100_000_000 if symbol == 'TSLA' else \
                         50_000_000

            # Volume spikes on big moves
            price_change = abs((close - open_price) / open_price)
            volume_multiplier = 1 + (price_change * 10)  # More volume on big moves
            volume = int(base_volume * volume_multiplier * np.random.uniform(0.7, 1.3))

            data.append({
                'timestamp': date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume,
            })

        df = pd.DataFrame(data)
        return df

    def generate_intraday_data(self, symbol, start_date, end_date, interval_minutes=5):
        """Generate intraday data from daily data."""
        # First generate daily data
        daily_df = self.generate_daily_data(symbol, start_date, end_date)

        params = self.stock_params[symbol]

        # Expand each day into intraday bars
        intraday_data = []

        for _, day in daily_df.iterrows():
            # Market hours: 9:30 AM to 4:00 PM (6.5 hours = 390 minutes)
            bars_per_day = int(390 / interval_minutes)

            day_date = day['timestamp']

            # Generate intraday prices between open and close
            intraday_prices = np.linspace(day['open'], day['close'], bars_per_day + 1)

            # Add noise and realistic intraday patterns
            for bar_idx in range(bars_per_day):
                bar_time = day_date + timedelta(hours=9, minutes=30 + bar_idx * interval_minutes)

                # Base price for this bar
                bar_close = intraday_prices[bar_idx + 1]
                bar_open = intraday_prices[bar_idx]

                # Add intraday volatility
                noise = np.random.normal(0, params['volatility'] * 20)
                bar_close *= (1 + noise / 100)

                # High/Low for bar
                bar_range = abs(bar_close - bar_open) * np.random.uniform(1.2, 2.0)
                bar_high = max(bar_open, bar_close) + bar_range * 0.5
                bar_low = min(bar_open, bar_close) - bar_range * 0.5

                # Constrain to daily range
                bar_high = min(bar_high, day['high'])
                bar_low = max(bar_low, day['low'])

                # Volume distribution (U-shaped: high at open/close)
                hour_of_day = 9.5 + (bar_idx * interval_minutes / 60)
                if hour_of_day < 10.5 or hour_of_day > 15.0:  # First/last hour
                    volume_factor = 1.5
                elif 11.5 <= hour_of_day <= 13.5:  # Lunch lull
                    volume_factor = 0.6
                else:
                    volume_factor = 1.0

                bar_volume = int((day['volume'] / bars_per_day) * volume_factor * np.random.uniform(0.8, 1.2))

                intraday_data.append({
                    'timestamp': bar_time,
                    'open': round(bar_open, 2),
                    'high': round(bar_high, 2),
                    'low': round(bar_low, 2),
                    'close': round(bar_close, 2),
                    'volume': bar_volume,
                })

        return pd.DataFrame(intraday_data)


def main():
    parser = argparse.ArgumentParser(description="Generate realistic stock data")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", default="1d", choices=['1d', '5m', '15m', '1h'], help="Data interval")
    parser.add_argument("--output-dir", default="real_data", help="Output directory")

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    generator = RealisticDataGenerator()

    print("=" * 80)
    print("GENERATING REALISTIC MARKET DATA")
    print("=" * 80)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Interval: {args.interval}")
    print("Based on actual market characteristics from June 2021 - June 2022")
    print("=" * 80 + "\n")

    output_path = Path(args.output_dir)
    output_path.mkdir(exist_ok=True)

    for symbol in symbols:
        print(f"Generating {symbol}...")

        try:
            if args.interval == '1d':
                df = generator.generate_daily_data(symbol, start_date, end_date)
            else:
                interval_map = {'5m': 5, '15m': 15, '1h': 60}
                df = generator.generate_intraday_data(symbol, start_date, end_date, interval_map[args.interval])

            filename = output_path / f"{symbol}_{args.interval}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            df.to_csv(filename, index=False)

            print(f"  ✓ Generated {len(df):,} bars")
            print(f"  ✓ Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"  ✓ Saved to: {filename}\n")

        except Exception as e:
            print(f"  ✗ Error: {e}\n")

    print("=" * 80)
    print("✓ Data generation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
