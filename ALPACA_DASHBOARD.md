# Alpaca Paper Trading Dashboard

Real-time web dashboard for monitoring your Alpaca paper trading activity.

## Features

- **Real-time Monitoring**: Auto-refreshes every 5 seconds to show live trading data
- **Active Positions**: View all currently open positions with entry prices, stop loss, and take profit levels
- **Closed Positions**: Review recently closed trades with P&L metrics
- **Trading Sessions**: Track all your trading sessions with performance stats
- **Statistics Overview**: Key metrics including total P&L, win rate, and best/worst trades
- **Beautiful UI**: Modern, responsive design with color-coded P&L

## Quick Start

### 1. Start the FastAPI Server

Make sure you have the database and dependencies set up, then start the API server:

```bash
# From the project root
python -m gambler_ai.api.main
```

Or using uvicorn directly:

```bash
uvicorn gambler_ai.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

### 2. Open the Dashboard

Open your browser and navigate to:

```
http://localhost:8000/static/alpaca_dashboard.html
```

That's it! The dashboard will automatically connect to the API and start displaying your trading data.

## API Endpoints

The following REST API endpoints are available for Alpaca trading data:

### Sessions
- `GET /api/v1/alpaca/sessions` - List recent trading sessions
  - Query params: `limit` (default: 10), `status` (active/completed/crashed)
- `GET /api/v1/alpaca/sessions/{session_id}` - Get specific session details

### Positions
- `GET /api/v1/alpaca/positions/active` - Get all active positions
- `GET /api/v1/alpaca/positions/closed` - Get recently closed positions
  - Query params: `limit` (default: 20)

### Trades
- `GET /api/v1/alpaca/trades/recent` - Get recent trades from transactions
  - Query params: `limit` (default: 20), `status` (OPEN/CLOSED)

### Orders
- `GET /api/v1/alpaca/orders/recent` - Get recent orders from order journal
  - Query params: `limit` (default: 20)

### Statistics
- `GET /api/v1/alpaca/stats` - Get overall trading statistics

## API Documentation

Once the server is running, you can access the interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Dashboard Controls

- **Auto-refresh Toggle**: Enable/disable automatic data refresh (updates every 5 seconds when enabled)
- **Load More Buttons**: Load different amounts of closed positions (10, 20, or 50 trades)
- **Last Updated**: Shows when data was last refreshed

## Data Display

### Statistics Cards
- Total Sessions: Number of trading sessions run
- Active Sessions: Currently running sessions
- Open Positions: Active trades currently in the market
- Total Trades: All trades (open + closed)
- Total P&L: Cumulative profit/loss across all closed trades
- Win Rate: Percentage of profitable trades
- Avg P&L/Trade: Average profit/loss per trade
- Best Trade: Highest single trade profit

### Active Positions Table
Shows all currently open positions with:
- Symbol, Direction (UP/DOWN), Side (buy/sell)
- Entry Price, Quantity
- Stop Loss and Take Profit levels
- Entry Time
- Alpaca Order ID

### Closed Positions Table
Shows recently closed trades with:
- Symbol, Direction
- Entry and Exit prices
- Quantity
- P&L (absolute and percentage)
- Duration
- Exit Reason (stop_loss_hit, take_profit_hit, manual, etc.)
- Exit Time

### Sessions Table
Shows recent trading sessions with:
- Status (active/completed/crashed) with visual indicator
- Start and End times
- Symbols traded
- Number of trades
- Portfolio values (initial and final)
- Session P&L

## Color Coding

- **Green**: Positive P&L, winning trades
- **Red**: Negative P&L, losing trades
- **Blue badges**: Active status
- **Gray badges**: Closed/completed status
- **Pulsing dot**: Active sessions

## Requirements

- FastAPI server running on port 8000
- Database with trading data (positions, sessions, transactions)
- Modern web browser with JavaScript enabled
- Active internet connection (uses CDN fonts)

## Troubleshooting

### Dashboard shows "Failed to load data"
- Check that the FastAPI server is running on `http://localhost:8000`
- Verify database connection in `config.yaml`
- Check browser console for error messages

### No data displayed
- Make sure you've run the `alpaca_paper_trading.py` script to generate trading data
- Verify database tables exist and contain data
- Check API endpoints directly: `http://localhost:8000/api/v1/alpaca/stats`

### CORS errors
- The API is configured to allow requests from localhost
- If accessing from a different domain, update CORS settings in `gambler_ai/api/main.py`

## Running Alpaca Paper Trading

To generate trading data that will appear in the dashboard:

```bash
python scripts/alpaca_paper_trading.py
```

Make sure you have:
1. Set up your Alpaca API credentials in `.env`:
   ```
   ALPACA_API_KEY=your_key_here
   ALPACA_API_SECRET=your_secret_here
   ```
2. Database is running (TimescaleDB or PostgreSQL)
3. Required Python packages installed

## File Locations

- Dashboard UI: `/static/alpaca_dashboard.html`
- API Routes: `/gambler_ai/api/routes/alpaca_trading.py`
- Main API: `/gambler_ai/api/main.py`
- Database Models: `/gambler_ai/storage/models.py`
- Trading Script: `/scripts/alpaca_paper_trading.py`

## Future Enhancements

Potential features to add:
- Real-time WebSocket updates (instead of polling)
- Live price updates for open positions
- P&L charts and performance graphs
- Trade filtering and search
- Export data to CSV/JSON
- Position sizing calculator
- Risk management metrics
- Trade alerts and notifications
