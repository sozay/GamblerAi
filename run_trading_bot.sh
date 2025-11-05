#!/bin/bash
# Quick start script for trading bot

echo "=========================================="
echo "GamblerAI Automated Trading Bot"
echo "=========================================="
echo ""

# Check if credentials are set
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_API_SECRET" ]; then
    echo "⚠️  Warning: Alpaca API credentials not set"
    echo ""
    echo "Using hardcoded default credentials (may not work)"
    echo ""
    echo "To set your own credentials:"
    echo "  export ALPACA_API_KEY='your_key'"
    echo "  export ALPACA_API_SECRET='your_secret'"
    echo ""
    echo "Or create a .env file:"
    echo "  ALPACA_API_KEY=your_key"
    echo "  ALPACA_API_SECRET=your_secret"
    echo ""
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "❌ Error: Python is not installed"
        exit 1
    fi
    PYTHON=python3
else
    PYTHON=python
fi

echo "Using Python: $PYTHON"
echo ""

# Check dependencies
echo "Checking dependencies..."
$PYTHON -c "import pandas, requests, websocket" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies"
    echo ""
    echo "Installing required packages..."
    pip install -r requirements.txt
    echo ""
fi

# Show configuration
echo "=========================================="
echo "Configuration"
echo "=========================================="
echo "Paper Trading: ✅ Enabled"
echo "Symbols: SPY, QQQ, AAPL, MSFT"
echo "Max Position: \$10,000"
echo "Stop Loss: 3%"
echo "Take Profit: 6%"
echo "Risk Per Trade: 2%"
echo ""

# Confirm before starting
read -p "Start trading bot? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "=========================================="
echo "Starting Trading Bot..."
echo "=========================================="
echo ""
echo "📊 Bot is now running"
echo "📈 Monitoring real-time market data"
echo "🤖 Adaptive strategy selection enabled"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the bot
$PYTHON trading_bot.py

# Cleanup
echo ""
echo "=========================================="
echo "Bot stopped"
echo "=========================================="
