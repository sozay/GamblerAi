#!/bin/bash
# Start the Interactive Simulator on port 8503

echo "Starting Interactive Simulator on http://localhost:8503"
echo "======================================================="
echo ""
echo "Features:"
echo "  - Download historical data (up to 10 years)"
echo "  - Select custom date ranges"
echo "  - Choose scanners and strategies"
echo "  - Run simulations on-demand"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"

python -m streamlit run scripts/interactive_simulator_ui.py \
    --server.port 8503 \
    --server.headless true \
    --browser.gatherUsageStats false
