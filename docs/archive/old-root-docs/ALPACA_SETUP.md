# Alpaca API Setup Guide

This guide explains how to set up Alpaca API credentials for downloading extended historical data (1+ months of 1-minute data).

## Why Alpaca?

- **Yahoo Finance**: Limited to 7 days of 1-minute data
- **Alpaca**: Can download months/years of 1-minute data with free paper trading account

## Setup Instructions

### 1. Get Your Alpaca API Credentials

1. Go to [Alpaca Paper Trading Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
2. Sign up for a free paper trading account (if you haven't already)
3. Navigate to "Your API Keys" section
4. Click "Generate New Key" or view existing keys
5. Copy your:
   - **API Key ID** (looks like: `PKXXXXXXXXXXXXXXXX`)
   - **Secret Key** (looks like: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

⚠️ **IMPORTANT**: Keep your Secret Key private! Never commit it to git or share it publicly.

### 2. Configure Your Environment

**Option A: Using .env file (Recommended)**

1. Copy the template file:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` and add your Secret Key:
   ```bash
   ALPACA_API_SECRET=your_actual_secret_key_here
   ```

3. The `.env` file is already in `.gitignore` so it won't be committed

**Option B: Using Environment Variable**

Set the environment variable before running:

```bash
# Linux/Mac
export ALPACA_API_SECRET='your_actual_secret_key_here'

# Windows (PowerShell)
$env:ALPACA_API_SECRET='your_actual_secret_key_here'

# Windows (CMD)
set ALPACA_API_SECRET=your_actual_secret_key_here
```

### 3. Test Your Credentials

Run the test script:

```bash
python3 test_alpaca.py
```

You should see:
```
✅ SUCCESS! Retrieved X bars
```

If you see `❌ ERROR: 403` - your API Secret is incorrect. Double-check it from the Alpaca dashboard.

### 4. Start the Simulator

```bash
./run_simulator.sh
```

Or on Windows:
```cmd
run_simulator.bat
```

### 5. Download Data

1. Open http://localhost:8503
2. In Step 1, you'll see a simple download form:
   - **Days of history**: Enter number of days (1-365)
   - **Interval**: Select 1m, 5m, 15m, 1h, or 1d
   - Click **Download**

The system will automatically:
- Use **Yahoo Finance** for ≤7 days of 1-minute data
- Use **Alpaca** for >7 days of 1-minute data
- Skip download if data already exists

## Troubleshooting

### "Access denied" or 403 error

- Your `ALPACA_API_SECRET` is incorrect or not set
- Check your credentials in the Alpaca dashboard
- Make sure you're using paper trading credentials (not live)
- Verify the secret key is correctly copied (no extra spaces)

### "No module named 'dotenv'"

Install python-dotenv:
```bash
pip install python-dotenv
```

Or it will work without it if you use environment variables

### Data download fails

- Check that you have internet connection
- For 1-minute data >7 days, Alpaca credentials are required
- Try a shorter period first (e.g., 7 days)
- Check the logs for specific error messages

## Data Limits

| Source | 1-Minute Data | 5-Minute Data | Daily Data |
|--------|---------------|---------------|------------|
| Yahoo Finance | 7 days | 60 days | 10 years |
| Alpaca | Unlimited* | Unlimited* | Unlimited* |

*Alpaca free tier has rate limits but should handle typical backtesting needs

## Security Best Practices

1. ✅ Always use `.env` file for secrets (it's in `.gitignore`)
2. ✅ Never commit API secrets to git
3. ✅ Use paper trading credentials (not live trading)
4. ✅ Regenerate keys if they're accidentally exposed
5. ❌ Don't share your `.env` file
6. ❌ Don't put secrets in code files

## Need Help?

- [Alpaca Documentation](https://alpaca.markets/docs/)
- [Alpaca Data API](https://alpaca.markets/docs/api-references/market-data-api/)
- Check project README.md for general setup
