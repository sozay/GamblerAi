# GamblerAI - Stock Momentum Analysis System

A Python-based application for analyzing stock market momentum patterns, identifying continuation and reversal probabilities, and optimizing entry points during significant price movements.

## Overview

GamblerAI analyzes historical stock price movements to answer critical trading questions:
- When a stock shows rapid price movement, how long will it continue?
- What is the probability of reversal and at what percentage?
- What are the optimal entry and exit points during momentum events?

## Key Features

- **Historical Data Analysis**: Collect and analyze minute-by-minute stock price data
- **Momentum Detection**: Automatically identify significant price movements
- **Pattern Recognition**: Classify momentum events by continuation/reversal behavior
- **Statistical Analysis**: Calculate probabilities and expected values
- **REST API**: Query analysis results programmatically
- **Interactive Dashboard**: Visualize patterns and statistics
- **CLI Tools**: Command-line interface for analysts

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

### High-Level Components

1. **Data Ingestion Layer**: Fetches historical stock data
2. **Storage Layer**: TimescaleDB for time-series, PostgreSQL for analytics
3. **Analysis Engine**: Detects momentum events and analyzes patterns
4. **API Layer**: FastAPI REST endpoints
5. **Dashboard**: Streamlit-based visualization

## Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.11+, PostgreSQL 15+, Redis 7+

### Option 1: Docker Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd GamblerAi

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

Services will be available at:
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- Flower (Celery monitor): http://localhost:5555
- API Docs: http://localhost:8000/docs

### Option 2: Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up databases
# Install PostgreSQL with TimescaleDB extension
# Install Redis

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Initialize databases
python -m gambler_ai.storage.init_db

# Run API server
uvicorn gambler_ai.api.main:app --reload

# Run Celery worker (in another terminal)
celery -A gambler_ai.tasks worker --loglevel=info

# Run dashboard (in another terminal)
streamlit run gambler_ai/dashboard/app.py
```

## Usage

### 1. Collect Historical Data

```bash
# Using CLI
python -m gambler_ai.cli.analyzer collect \
  --symbol AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --timeframe 5min

# Or for multiple symbols
python -m gambler_ai.cli.analyzer collect \
  --symbols AAPL,MSFT,GOOGL \
  --start 2024-01-01 \
  --end 2024-12-31
```

### 2. Run Analysis

```bash
# Detect momentum events
python -m gambler_ai.cli.analyzer detect-momentum \
  --symbol AAPL \
  --threshold 2.0 \
  --window 5min

# Analyze patterns
python -m gambler_ai.cli.analyzer analyze-patterns \
  --symbol AAPL \
  --output reports/aapl_patterns.json
```

### 3. Query via API

```bash
# Get momentum events for a symbol
curl http://localhost:8000/api/v1/momentum-events/AAPL?start=2024-01-01

# Get pattern statistics
curl http://localhost:8000/api/v1/patterns/statistics?timeframe=5min

# Get continuation probability
curl -X POST http://localhost:8000/api/v1/predict/continuation \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "initial_move_pct": 2.5,
    "volume_ratio": 3.0,
    "timeframe": "5min"
  }'
```

### 4. Use Dashboard

Navigate to http://localhost:8501 to access the interactive dashboard.

Features:
- View recent momentum events
- Explore pattern statistics
- Analyze continuation/reversal probabilities
- Screen for current momentum opportunities

## Project Structure

```
GamblerAi/
├── gambler_ai/              # Main application package
│   ├── data_ingestion/      # Data collection modules
│   ├── storage/             # Database models and interfaces
│   ├── analysis/            # Analysis engine
│   ├── api/                 # FastAPI application
│   ├── cli/                 # Command-line tools
│   ├── dashboard/           # Streamlit dashboard
│   └── utils/               # Utilities and helpers
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
├── docs/                    # Documentation
├── config.yaml              # Configuration
├── docker-compose.yml       # Docker setup
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Configuration

Edit `config.yaml` to customize:

```yaml
analysis:
  momentum_detection:
    min_price_change_pct: 2.0   # Minimum % move to detect
    min_volume_ratio: 2.0        # Volume spike threshold
    window_minutes: 5            # Detection window

stocks:
  watchlist:
    - AAPL
    - MSFT
    # Add more symbols...
```

## API Documentation

Once the API is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

```
GET  /api/v1/momentum-events/{symbol}     # Historical momentum events
GET  /api/v1/patterns/statistics          # Pattern statistics
POST /api/v1/predict/continuation         # Continuation prediction
GET  /api/v1/stocks/screener              # Current momentum screener
POST /api/v1/analyze/backtest             # Backtest a strategy
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gambler_ai --cov-report=html

# Run specific test
pytest tests/unit/test_momentum_detector.py
```

### Code Quality

```bash
# Format code
black gambler_ai/

# Sort imports
isort gambler_ai/

# Lint
flake8 gambler_ai/

# Type check
mypy gambler_ai/
```

## Data Flow Example

1. **Historical Analysis**:
   ```
   Data Collection → Event Detection → Pattern Analysis → Statistics → API/Dashboard
   ```

2. **Example Scenario**:
   - Collect 1 year of 5-minute data for AAPL
   - Detect all instances where price moved >2% in 5 minutes
   - For each event, measure how long momentum continued
   - Calculate: "When AAPL rises 2% in 5min, it continues rising for avg 15min with 65% probability"
   - Store results for API queries

## Performance Considerations

- **Data Volume**: 1 year of 1-minute data for 100 stocks ≈ 25M rows
- **Analysis Speed**: Process 1 year of data in ~30 minutes
- **API Response**: <500ms for most queries (cached results)
- **Database**: TimescaleDB provides 10-100x speedup for time-series queries

## Roadmap

### Phase 1: Foundation ✓
- [x] Architecture design
- [ ] Database setup
- [ ] Data collection
- [ ] Basic analysis engine

### Phase 2: Core Features
- [ ] Momentum detection
- [ ] Pattern analysis
- [ ] Statistical calculations
- [ ] REST API

### Phase 3: Interface
- [ ] CLI tools
- [ ] Dashboard
- [ ] Visualization

### Phase 4: Advanced
- [ ] Real-time data
- [ ] Machine learning models
- [ ] Alert system
- [ ] Strategy backtesting

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[To be determined]

## Support

For questions or issues:
- Open an issue on GitHub
- Contact: [your-email@example.com]

## Acknowledgments

- Built with FastAPI, Pandas, TimescaleDB, and Streamlit
- Market data provided by Yahoo Finance / Alpha Vantage
