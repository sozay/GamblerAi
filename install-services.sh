#!/bin/bash
# Install GamblerAI services

echo "Installing GamblerAI services..."

sudo cp gambler-trading.service /etc/systemd/system/
sudo cp gambler-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gambler-trading.service
sudo systemctl enable gambler-api.service
sudo systemctl start gambler-trading.service
sudo systemctl start gambler-api.service

echo ""
echo "Services installed and started!"
echo ""
echo "Check status:"
echo "  sudo systemctl status gambler-trading"
echo "  sudo systemctl status gambler-api"
echo ""
echo "View logs:"
echo "  sudo journalctl -u gambler-trading -f"
echo "  sudo journalctl -u gambler-api -f"
echo ""
echo "Dashboard: http://localhost:9090/static/alpaca_dashboard.html"
