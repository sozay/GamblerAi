@echo off
REM Install required packages for GamblerAI Interactive Simulator

echo ================================================================
echo Installing GamblerAI Requirements
echo ================================================================
echo.
echo This will install all required Python packages including:
echo   - streamlit (for the web UI)
echo   - plotly (for interactive charts)
echo   - yfinance (for downloading market data)
echo   - pandas, numpy (for data processing)
echo   - and more...
echo.
echo This may take a few minutes...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install main requirements
echo.
echo Installing core packages...
python -m pip install pandas numpy scipy

echo.
echo Installing data providers...
python -m pip install yfinance alpaca-trade-api requests

echo.
echo Installing visualization and UI packages...
python -m pip install streamlit plotly matplotlib seaborn

echo.
echo Installing analysis tools...
python -m pip install scikit-learn statsmodels

echo.
echo Installing utilities...
python -m pip install python-dotenv pyyaml python-dateutil pytz

echo.
echo Installing database packages...
python -m pip install sqlalchemy

echo.
echo ================================================================
echo Installation Complete!
echo ================================================================
echo.
echo You can now run the simulator with:
echo   run_simulator.bat
echo.
echo Or manually with:
echo   python -m streamlit run scripts\interactive_simulator_ui.py --server.port 8503
echo.
pause
