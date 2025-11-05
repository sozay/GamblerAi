# GamblerAI Project Summary

## What We Built

A comprehensive **Python-based stock momentum analysis system** that answers critical trading questions:

> "When a stock shows a big price jump, how long will it continue? When will it reverse? At what percentage?"

## The Problem It Solves

Traders face a critical decision when seeing rapid stock price movements:
- **Should I enter this trade?**
- **How long will this momentum last?**
- **When should I exit before reversal?**
- **What's the probability of success?**

GamblerAI analyzes historical data to provide **statistical answers** to these questions.

## System Overview

### Architecture Components

1. **Data Ingestion Layer**
   - Collects historical stock price data (minute-by-minute)
   - Validates data quality
   - Supports multiple data sources (Yahoo Finance, Alpha Vantage)

2. **Storage Layer**
   - **TimescaleDB**: Optimized for time-series stock data
   - **PostgreSQL**: Stores analysis results and patterns
   - **Redis**: Caches frequently accessed data

3. **Analysis Engine**
   - **Momentum Detector**: Identifies significant price movements
   - **Pattern Analyzer**: Analyzes continuation vs reversal behavior
   - **Statistics Engine**: Calculates probabilities and expected values

4. **Interface Layer**
   - **REST API**: Query analysis results programmatically
   - **CLI Tools**: Command-line interface for analysts
   - **Dashboard**: Interactive web visualization

### Data Flow Example

```
1. Collect Data
   └─> Download 1 year of 5-minute price data for AAPL

2. Detect Events
   └─> Find all instances where price moved >2% in 5 minutes

3. Analyze Patterns
   └─> For each event, measure:
       • How long did momentum continue?
       • When did price reverse?
       • What percentage did it retrace?

4. Calculate Statistics
   └─> Result: "When AAPL rises 2.5% in 5min:
       • 65% probability it continues rising for 15+ minutes
       • Average reversal: 3.2% from peak
       • Average time to reversal: 23 minutes"

5. Expose Results
   └─> API, Dashboard, or CLI access
```

## Key Features

### For Analysts (Analyzer Role)

- **Historical Data Collection**: Automated fetching and validation
- **Momentum Detection**: Configurable thresholds for event identification
- **Pattern Analysis**: Statistical analysis of continuation/reversal behavior
- **Backtesting**: Test trading strategies against historical patterns
- **Report Generation**: Comprehensive analysis reports

### For Traders (User Role)

- **Real-time Queries**: "Should I enter this momentum trade?"
- **Probability Estimates**: Statistical confidence for each decision
- **Pattern Matching**: Compare current situation to historical patterns
- **Risk/Reward Ratios**: Expected gains vs potential losses

## Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11+ | Core development |
| Time-Series DB | TimescaleDB | Stock price data |
| Database | PostgreSQL | Analysis results |
| Cache | Redis | Performance optimization |
| API | FastAPI | REST endpoints |
| Analysis | Pandas, NumPy, SciPy | Data processing |
| Visualization | Plotly, Streamlit | Dashboard |
| Task Queue | Celery | Async processing |

## Project Structure

```
GamblerAi/
├── ARCHITECTURE.md          # Detailed system design
├── README.md                # User documentation
├── SETUP_GUIDE.md           # Installation instructions
├── config.yaml              # Configuration
├── docker-compose.yml       # Easy deployment
├── requirements.txt         # Python dependencies
│
├── gambler_ai/              # Main application
│   ├── data_ingestion/      # Data collection
│   ├── storage/             # Database interfaces
│   ├── analysis/            # Core analysis engine
│   ├── api/                 # REST API
│   ├── cli/                 # Command-line tools
│   ├── dashboard/           # Web interface
│   └── utils/               # Utilities
│
├── scripts/                 # Database initialization
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Example Use Cases

### Use Case 1: Historical Analysis

**Scenario**: Analyst wants to understand AAPL momentum patterns

```bash
# 1. Collect 1 year of data
python -m gambler_ai.cli.analyzer collect \
    --symbol AAPL --start 2024-01-01 --end 2024-12-31

# 2. Detect momentum events
python -m gambler_ai.cli.analyzer detect-momentum \
    --symbol AAPL --threshold 2.0

# 3. Analyze patterns
python -m gambler_ai.cli.analyzer analyze-patterns \
    --symbol AAPL --output reports/aapl_analysis.json
```

**Result**: Report showing:
- 143 momentum events detected
- Average continuation: 18 minutes
- Win rate: 67% for entries within first 2 minutes
- Average reversal: 3.5% from peak

### Use Case 2: Real-Time Query

**Scenario**: Trader sees AAPL rising 2.8% in last 5 minutes

```bash
# Query API for prediction
curl -X POST http://localhost:8000/api/v1/predict/continuation \
  -d '{
    "symbol": "AAPL",
    "initial_move_pct": 2.8,
    "volume_ratio": 3.2,
    "timeframe": "5min"
  }'
```

**Response**:
```json
{
  "symbol": "AAPL",
  "prediction": {
    "continuation_probability": 0.68,
    "expected_continuation_minutes": 16,
    "expected_additional_gain_pct": 1.2,
    "reversal_probability": 0.32,
    "expected_reversal_pct": 3.1,
    "expected_reversal_time_minutes": 24
  },
  "recommendation": "ENTER",
  "confidence": 0.85,
  "sample_size": 847
}
```

### Use Case 3: Dashboard Analysis

Navigate to http://localhost:8501 to:
- View real-time momentum events
- Explore pattern statistics
- Analyze probability distributions
- Screen for current opportunities

## Key Metrics Tracked

### Momentum Event Metrics

1. **Initial Momentum**
   - Time window (e.g., 5 minutes)
   - Price change percentage
   - Volume compared to average
   - Direction (UP/DOWN)

2. **Continuation Phase**
   - Duration of continued movement
   - Additional percentage gain/loss
   - Peak price reached
   - Volume profile

3. **Reversal Phase**
   - Time to reversal from start
   - Reversal percentage from peak
   - Speed of reversal
   - Volume during reversal

## Development Phases

### ✓ Phase 1: Architecture & Design (COMPLETE)
- [x] System architecture design
- [x] Database schema design
- [x] API design
- [x] Component specifications
- [x] Development environment setup

### Phase 2: Data Foundation (Next: Weeks 1-2)
- [ ] Implement data collector
- [ ] Set up databases
- [ ] Data validation pipeline
- [ ] Collect initial dataset

### Phase 3: Analysis Engine (Weeks 3-4)
- [ ] Momentum event detector
- [ ] Pattern analyzer
- [ ] Statistical calculator
- [ ] Initial analysis reports

### Phase 4: API & Interface (Week 5)
- [ ] REST API implementation
- [ ] CLI tools
- [ ] Dashboard

### Phase 5: Testing & Optimization (Week 6)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Documentation

## How to Get Started

### Quick Start (Docker)

```bash
# Start all services
docker-compose up -d

# Access services
# - API: http://localhost:8000/docs
# - Dashboard: http://localhost:8501
```

### Local Development

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Set up databases
# See SETUP_GUIDE.md

# 3. Run services
uvicorn gambler_ai.api.main:app --reload
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

## Configuration

Customize analysis parameters in `config.yaml`:

```yaml
analysis:
  momentum_detection:
    min_price_change_pct: 2.0    # Minimum % move
    min_volume_ratio: 2.0         # Volume threshold
    window_minutes: 5             # Detection window

stocks:
  watchlist:
    - AAPL
    - MSFT
    - GOOGL
    # Add your symbols...
```

## API Endpoints

```
GET  /api/v1/momentum-events/{symbol}     # Historical events
GET  /api/v1/patterns/statistics          # Pattern stats
POST /api/v1/predict/continuation         # Predict continuation
GET  /api/v1/stocks/screener              # Find opportunities
POST /api/v1/analyze/backtest             # Backtest strategy
```

Full API documentation: http://localhost:8000/docs

## Key Design Decisions

### 1. TimescaleDB for Time-Series Data
- **Why**: 10-100x faster queries on time-series data
- **Benefit**: Efficient storage and retrieval of minute-level data

### 2. Separate Databases
- **TimescaleDB**: Raw price data (optimized for time queries)
- **PostgreSQL**: Analysis results (optimized for complex queries)

### 3. Redis for Caching
- **Why**: Frequently accessed patterns don't need DB queries
- **Benefit**: Sub-millisecond response times

### 4. Celery for Async Processing
- **Why**: Analysis can take minutes to hours
- **Benefit**: Non-blocking API, scalable processing

### 5. FastAPI for API
- **Why**: Modern, fast, automatic documentation
- **Benefit**: Easy to use, well-documented endpoints

## Success Metrics

### Data Quality
- <0.1% missing data points
- Data validation before analysis

### Performance
- Process 1 year of data in <30 minutes
- API response time <500ms (95th percentile)

### Statistical Significance
- Minimum 100 samples per pattern
- 95% confidence level for predictions
- Backtested win rate >55%

## Security Considerations

- Environment variables for secrets
- JWT authentication for API
- Rate limiting
- Input validation
- SQL injection prevention (parameterized queries)

## Scalability

### Current Design Handles:
- 100+ stocks
- 1-minute resolution
- 1+ years of data
- 1000+ API requests/minute

### Future Scaling:
- Horizontal scaling with Kubernetes
- Microservices architecture
- Load balancing
- Data partitioning

## Documentation

1. **ARCHITECTURE.md**: Detailed system design and technical specifications
2. **README.md**: User guide and usage examples
3. **SETUP_GUIDE.md**: Installation and configuration instructions
4. **API Docs**: Auto-generated at http://localhost:8000/docs

## Support & Contributing

- **Issues**: Open GitHub issue
- **Questions**: Contact development team
- **Contributing**: See README.md for workflow

## What Makes This System Unique

1. **Statistical Foundation**: Based on actual historical patterns, not gut feeling
2. **Probability-Based**: Provides confidence levels, not just yes/no
3. **Time-Specific**: Tracks exact timing of continuations and reversals
4. **Backtestable**: Every prediction can be validated against history
5. **Configurable**: Adjust parameters for different trading styles
6. **Scalable**: Designed to handle large datasets and real-time data

## Next Steps

1. **Review**: Read ARCHITECTURE.md for full design details
2. **Setup**: Follow SETUP_GUIDE.md to install
3. **Develop**: Pick a component from the roadmap
4. **Test**: Add tests for new features
5. **Deploy**: Use Docker for easy deployment

---

**Project Status**: Architecture Complete, Ready for Development

**Estimated Timeline**: 6 weeks to MVP

**Team Size**: 2-4 developers recommended
