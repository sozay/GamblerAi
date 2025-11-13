# Interactive Simulator - Usage Guide

## Quick Start

### Starting the Simulator

**Windows:**
```bash
run_simulator.bat
```

**Linux/Mac:**
```bash
chmod +x run_simulator.sh
./run_simulator.sh
```

**Or manually:**
```bash
python -m streamlit run scripts/interactive_simulator_ui.py --server.port 8503
```

The app will start on: **http://localhost:8503**

## How to Use

### Step 1: Download Historical Data

1. When you first open the app, you'll see the data download section
2. Configure your download:
   - **Years of history**: Choose 1-10 years (default: 10)
   - **Data interval**: Choose from 1d, 1h, 15m, 5m
   - **Symbols**: Enter stock symbols separated by commas (default: AAPL, MSFT, etc.)
3. Click **"Download Data"** button
4. Wait for the download to complete (may take a few minutes)

**Note:** The data is cached locally in `market_data_cache/` directory, so you only need to download once.

### Step 2: Configure Your Simulation

Once data is downloaded, you'll see the configuration section:

#### Select Date Range
- The app shows you the full range of available data
- **Select any custom date range** within the available data
- Quick select buttons: Last 1 Year, Last 2 Years, Last 3 Years, Last 5 Years, Full Period
- For 7 days: Use the date picker to select your exact 7-day range

#### Choose Scanners
Select which stock scanners to test:
- Top Movers
- High Volume
- Best Setups
- Relative Strength
- Gap Scanner
- Volatility Range
- Sector Leaders
- Market Cap Weighted

#### Choose Strategies
Select which trading strategies to test:
- Momentum
- Mean Reversion
- Volatility Breakout

#### Set Parameters
- **Initial Capital**: Starting amount (default: $100,000)
- **Chart Update Speed**: How fast the live charts update (0.1-2.0 seconds)

### Step 3: Run Simulation

1. Review your configuration summary
2. Click **"START SIMULATION"** button
3. The simulation will run week by week
4. Progress will be shown in the terminal/console
5. Results will appear automatically when complete

### Step 4: View Results

Once complete, you'll see:
- **Performance Chart**: Line chart showing cumulative P&L for all combinations
- **Rankings Table**: Leaderboard of best performing combinations
- Metrics: Return %, Final P&L, Win Rate, Total Trades

## Running a 7-Day Simulation with 1-Minute Data

To run a simulation on 7 days of real 1-minute data:

1. **Download Data**:
   - Select interval: **5m** or **15m** (minute data is limited)
   - Download 1-2 years of data

2. **Configure Simulation**:
   - Use the date pickers to select exactly 7 days
   - Or use "Quick Select" and then adjust the end date

3. **Run Simulation**:
   - Click "START SIMULATION"
   - The simulation will process your selected 7-day period

## Troubleshooting

### Error: "KeyError: 'timestamp'"

This has been fixed in the latest version. If you still see this:
1. Stop the simulator (Ctrl+C)
2. Delete the `market_data_cache/` directory
3. Restart the simulator and re-download the data

### No data downloaded

Make sure you have:
- Working internet connection
- Python packages installed: `pip install yfinance pandas streamlit plotly`

### Simulation taking too long

- Reduce the date range (fewer days = faster)
- Select fewer scanners and strategies
- Use daily data instead of minute data

## Data Limitations

- **1-minute data**: Only available for last 7 days (Yahoo Finance limitation)
- **5-minute data**: Available for last 60 days
- **Daily data**: Available for many years

For simulations longer than 7 days, we recommend using daily (1d) or hourly (1h) data.

## Files Created

- `market_data_cache/`: Downloaded historical data (cached)
- `market_data_cache/metadata.json`: Information about downloaded data
- `simulation_results_live/`: Simulation results
- `simulation_results_live/live_results.json`: Latest simulation results

## Need Help?

Check the console/terminal output for detailed logs and any error messages.
