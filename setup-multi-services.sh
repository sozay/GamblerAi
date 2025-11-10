#!/bin/bash
# Setup GamblerAI Multi-Instance Trading Services
# This script deploys 5 parallel trading instances with different strategy combinations

set -e  # Exit on error

echo "========================================================"
echo "   GamblerAI Multi-Instance Service Setup"
echo "========================================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/ozay/GamblerAi"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/venv"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run with sudo: sudo ./setup-multi-services.sh${NC}"
    exit 1
fi

echo "Step 1/7: Checking prerequisites..."
# Check if config.yaml exists
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
    echo -e "${RED} config.yaml not found!${NC}"
    echo "  Please ensure config.yaml exists in $PROJECT_DIR"
    exit 1
fi
echo -e "${GREEN} config.yaml found${NC}"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}  Virtual environment not found at $VENV_DIR${NC}"
    echo "  Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
fi
echo -e "${GREEN} Virtual environment ready${NC}"

# Create logs directory
echo ""
echo "Step 2/7: Creating log directories..."
mkdir -p "$LOG_DIR"
chown ozay:ozay "$LOG_DIR"
echo -e "${GREEN} Log directory created: $LOG_DIR${NC}"

# Apply database migration
echo ""
echo "Step 3/7: Applying database migrations..."
if [ -f "$PROJECT_DIR/migrations/add_instance_id.sql" ]; then
    # Check if SQLite or PostgreSQL
    if command -v sqlite3 &> /dev/null; then
        DB_PATH="$PROJECT_DIR/data/analytics.db"
        if [ -f "$DB_PATH" ]; then
            echo "  Applying migration to SQLite database..."
            # SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we check first
            sqlite3 "$DB_PATH" << 'EOF'
.timeout 2000
PRAGMA journal_mode=WAL;

-- Check if columns exist before adding
SELECT CASE
    WHEN COUNT(*) = 0 THEN
        'ALTER TABLE trading_sessions ADD COLUMN instance_id INTEGER NOT NULL DEFAULT 1;'
    ELSE
        'SELECT ''Column instance_id already exists'';'
END
FROM pragma_table_info('trading_sessions')
WHERE name='instance_id';

-- Execute the result (this is a workaround for SQLite)
-- We'll do it via python instead for safety
EOF

            # Use Python to safely add columns
            "$VENV_DIR/bin/python" << 'PYTHON_EOF'
import sqlite3
import os

db_path = "/home/ozay/GamblerAi/data/analytics.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check and add instance_id
    cursor.execute("PRAGMA table_info(trading_sessions)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'instance_id' not in columns:
        cursor.execute("ALTER TABLE trading_sessions ADD COLUMN instance_id INTEGER NOT NULL DEFAULT 1")
        print("   Added instance_id column")
    else:
        print("   instance_id column already exists")

    if 'strategy_name' not in columns:
        cursor.execute("ALTER TABLE trading_sessions ADD COLUMN strategy_name VARCHAR(100)")
        print("   Added strategy_name column")
    else:
        print("   strategy_name column already exists")

    if 'allocated_capital' not in columns:
        cursor.execute("ALTER TABLE trading_sessions ADD COLUMN allocated_capital DECIMAL(12,2)")
        print("   Added allocated_capital column")
    else:
        print("   allocated_capital column already exists")

    # Create indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_instance_id ON trading_sessions(instance_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_strategy ON trading_sessions(strategy_name)")
        print("   Created indexes")
    except:
        pass

    conn.commit()
    conn.close()
    print("   Database migration completed")
else:
    print("    Database not found, will be created on first run")
PYTHON_EOF
        fi
    fi
    echo -e "${GREEN} Database migration applied${NC}"
else
    echo -e "${YELLOW}  Migration file not found, skipping${NC}"
fi

# Stop existing services
echo ""
echo "Step 4/7: Stopping existing services..."
systemctl stop gambler-trading.service 2>/dev/null || true
systemctl stop gambler-api.service 2>/dev/null || true
for i in {1..5}; do
    systemctl stop gambler-trading-$i.service 2>/dev/null || true
done
echo -e "${GREEN} Existing services stopped${NC}"

# Copy service files
echo ""
echo "Step 5/7: Installing service files..."

# Copy API service
cp "$PROJECT_DIR/gambler-api.service" /etc/systemd/system/
echo -e "${GREEN}   gambler-api.service${NC}"

# Copy trading instance services
for i in {1..5}; do
    cp "$PROJECT_DIR/gambler-trading-$i.service" /etc/systemd/system/
    echo -e "${GREEN}   gambler-trading-$i.service${NC}"
done

# Reload systemd
echo ""
echo "Step 6/7: Reloading systemd daemon..."
systemctl daemon-reload
echo -e "${GREEN} Systemd reloaded${NC}"

# Enable and start services
echo ""
echo "Step 7/7: Enabling and starting services..."

# Start API service
systemctl enable gambler-api.service
systemctl start gambler-api.service
echo -e "${GREEN}   API service started${NC}"

# Start trading instances
for i in {1..5}; do
    systemctl enable gambler-trading-$i.service
    systemctl start gambler-trading-$i.service
    echo -e "${GREEN}   Trading instance $i started${NC}"
    sleep 2  # Brief delay between starts
done

echo ""
echo "========================================================"
echo -e "${GREEN}   Multi-Instance Setup Complete!${NC}"
echo "========================================================"
echo ""

# Show service status
echo "Service Status:"
echo "----------------------------------------"
for i in {1..5}; do
    status=$(systemctl is-active gambler-trading-$i.service)
    if [ "$status" = "active" ]; then
        echo -e "  Instance $i: ${GREEN}$status${NC}"
    else
        echo -e "  Instance $i: ${RED}$status${NC}"
    fi
done
echo ""

# Configuration summary from config.yaml
echo "Instance Configuration:"
echo "----------------------------------------"
echo "  Instance 1: Mean Reversion + Relative Strength"
echo "              Symbols: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, AMD"
echo "              Capital: \$50,000 | Interval: 60s"
echo ""
echo "  Instance 2: Gap Scanner + Mean Reversion"
echo "              Symbols: SPY, QQQ, IWM, NFLX, ABNB, PYPL, SQ, COIN"
echo "              Capital: \$45,000 | Interval: 45s"
echo ""
echo "  Instance 3: Best Setup + Mean Reversion"
echo "              Symbols: ADBE, CSCO, INTC, QCOM, AVGO, TXN, MU, AMAT"
echo "              Capital: \$50,000 | Interval: 60s"
echo ""
echo "  Instance 4: Relative Strength + Volatility Breakout"
echo "              Symbols: ASML, GILD, PEP, CMCSA, ORCL, CRM, NOW, SHOP"
echo "              Capital: \$48,000 | Interval: 45s"
echo ""
echo "  Instance 5: Best Setup + Volatility Breakout"
echo "              Symbols: SBUX, COST, PG, KO, NKE, DIS, UNH, JNJ"
echo "              Capital: \$50,000 | Interval: 60s"
echo ""
echo "Total Allocated Capital: \$243,000"
echo "Total Symbols: 42 (unique across instances)"
echo ""

# Useful commands
echo "========================================================"
echo "Useful Commands:"
echo "========================================================"
echo ""
echo "View all instance status:"
echo "  sudo systemctl status gambler-trading-{1..5}"
echo ""
echo "View logs for specific instance:"
echo "  sudo journalctl -u gambler-trading-1 -f"
echo "  tail -f $LOG_DIR/trading-1.log"
echo ""
echo "View logs for all instances:"
echo "  tail -f $LOG_DIR/trading-*.log"
echo ""
echo "Stop all instances:"
echo "  sudo systemctl stop gambler-trading-{1..5}"
echo ""
echo "Restart all instances:"
echo "  sudo systemctl restart gambler-trading-{1..5}"
echo ""
echo "Stop specific instance:"
echo "  sudo systemctl stop gambler-trading-3"
echo ""
echo "Dashboard URL:"
echo "  http://localhost:9090/static/alpaca_dashboard.html"
echo ""
echo "API Health Check:"
echo "  curl http://localhost:9090/health"
echo ""
echo "========================================================"
echo ""
