#!/bin/bash
# Start the Interactive Simulator on port 8503

echo "Starting Interactive Simulator on http://localhost:8503"
echo "======================================================="
echo ""

# Check if port 8503 is already in use
if lsof -Pi :8503 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 8503 is already in use. Stopping existing process..."
    kill $(lsof -ti:8503) 2>/dev/null
    sleep 2
    echo "✓ Stopped existing process"
    echo ""
fi

echo "Features:"
echo "  - Download historical data (up to 10 years)"
echo "  - Select custom date ranges"
echo "  - Choose scanners and strategies"
echo "  - Run simulations on-demand"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"

python3 -m streamlit run scripts/interactive_simulator_ui.py \
    --server.port 8503 \
    --server.headless true \
    --browser.gatherUsageStats false
