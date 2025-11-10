#!/bin/bash
# Setup GamblerAI as systemd services

echo "=== GamblerAI Service Setup ==="
echo ""

# Copy service files
echo "1. Copying service files to systemd..."
sudo cp /home/ozay/GamblerAi/gambler-trading.service /etc/systemd/system/
sudo cp /home/ozay/GamblerAi/gambler-api.service /etc/systemd/system/

# Reload systemd
echo "2. Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable services
echo "3. Enabling services to start on boot..."
sudo systemctl enable gambler-trading.service
sudo systemctl enable gambler-api.service

# Start services
echo "4. Starting services..."
sudo systemctl start gambler-trading.service
sudo systemctl start gambler-api.service

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Services Status:"
sudo systemctl status gambler-trading.service --no-pager | head -10
echo ""
sudo systemctl status gambler-api.service --no-pager | head -10
echo ""
echo "=== Useful Commands ==="
echo "View trading bot logs:  sudo journalctl -u gambler-trading.service -f"
echo "View API logs:          sudo journalctl -u gambler-api.service -f"
echo "Stop services:          sudo systemctl stop gambler-trading gambler-api"
echo "Restart services:       sudo systemctl restart gambler-trading gambler-api"
echo "Check status:           sudo systemctl status gambler-trading gambler-api"
echo ""
echo "=== Web Dashboard ==="
echo "Access the dashboard at: http://localhost:9090/static/alpaca_dashboard.html"
echo ""
