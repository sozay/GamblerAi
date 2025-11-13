# GamblerAI Service Setup

This guide will help you run both the trading bot and web dashboard as persistent system services that never go down.

## What's Included

1. **Trading Bot Service** (`gambler-trading.service`)
   - Runs continuously scanning 24 Nasdaq stocks
   - Automatically places trades based on momentum signals
   - Saves all trades to SQLite database
   - Auto-restarts if it crashes

2. **API & Dashboard Service** (`gambler-api.service`)
   - Serves the web dashboard at `http://localhost:9090`
   - Provides REST API for trading data
   - Real-time updates on active positions and trades

## Quick Setup

Run the setup script:

```bash
cd /home/ozay/GamblerAi
./setup-services.sh
```

This will:
- Install both services to systemd
- Enable them to start on boot
- Start them immediately

## Access the Dashboard

Once the services are running, access the web dashboard at:

**http://localhost:9090/static/alpaca_dashboard.html**

The dashboard shows:
- Real-time account balance
- Active positions
- Recent trades
- Performance metrics

## Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# Copy service files
sudo cp gambler-trading.service /etc/systemd/system/
sudo cp gambler-api.service /etc/systemd/system/

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable gambler-trading gambler-api
sudo systemctl start gambler-trading gambler-api
```

## Service Management Commands

```bash
# View status
sudo systemctl status gambler-trading
sudo systemctl status gambler-api

# Stop services
sudo systemctl stop gambler-trading gambler-api

# Start services
sudo systemctl start gambler-trading gambler-api

# Restart services
sudo systemctl restart gambler-trading gambler-api

# View logs (live)
sudo journalctl -u gambler-trading -f
sudo journalctl -u gambler-api -f

# View all logs
sudo journalctl -u gambler-trading --no-pager
sudo journalctl -u gambler-api --no-pager
```

## Log Files

Logs are also written to:
- Trading bot: `/home/ozay/GamblerAi/logs/trading.log`
- API server: `/home/ozay/GamblerAi/logs/api.log`
- Error logs: `/home/ozay/GamblerAi/logs/*.error.log`

## Configuration

### Change Trading Symbols

Edit `/etc/systemd/system/gambler-trading.service` and modify the `ExecStart` line:

```ini
ExecStart=/home/ozay/GamblerAi/venv/bin/python scripts/alpaca_paper_trading.py --continuous --symbols YOUR,SYMBOLS,HERE --interval 60
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gambler-trading
```

### Change Scan Interval

Modify `--interval 60` to your desired seconds (e.g., `--interval 30` for 30 seconds).

### Change API Port

Edit `/etc/systemd/system/gambler-api.service` and modify the port in `ExecStart`:

```ini
ExecStart=/home/ozay/GamblerAi/venv/bin/uvicorn gambler_ai.api.main:app --host 0.0.0.0 --port YOUR_PORT
```

## Database

All trading data is stored in:
- `/home/ozay/GamblerAi/data/analytics.db` (SQLite database)

You can query it with:
```bash
sqlite3 /home/ozay/GamblerAi/data/analytics.db
```

## Troubleshooting

### Services won't start

Check logs:
```bash
sudo journalctl -u gambler-trading -n 50
sudo journalctl -u gambler-api -n 50
```

### Dashboard not accessible

1. Check if API service is running:
   ```bash
   sudo systemctl status gambler-api
   ```

2. Check if port 9090 is open:
   ```bash
   curl http://localhost:9090/health
   ```

3. Check firewall (if applicable):
   ```bash
   sudo ufw allow 9090
   ```

### Database errors

The services automatically create the SQLite database. If you see errors, ensure the data directory exists and is writable:

```bash
mkdir -p /home/ozay/GamblerAi/data
chmod 755 /home/ozay/GamblerAi/data
```

## Stopping Services Permanently

To disable auto-start on boot:

```bash
sudo systemctl disable gambler-trading gambler-api
sudo systemctl stop gambler-trading gambler-api
```

To remove completely:

```bash
sudo systemctl stop gambler-trading gambler-api
sudo systemctl disable gambler-trading gambler-api
sudo rm /etc/systemd/system/gambler-trading.service
sudo rm /etc/systemd/system/gambler-api.service
sudo systemctl daemon-reload
```
