# GamblerAI - Stock Momentum Analysis System
## Architecture Design Document

## 1. Executive Summary

GamblerAI is a Python-based stock market momentum analysis system that analyzes historical price movements to identify patterns in rapid price changes. The system focuses on understanding:
- **Continuation patterns**: How long a price movement in one direction typically continues
- **Reversal timing**: When and at what percentage a price reverses direction
- **Entry point optimization**: Optimal timing to enter a position during a momentum event

## 2. System Overview

### 2.1 User Roles

1. **Analyzer Role**: Data scientists/analysts who run historical analysis, train models, and generate statistical insights
2. **Trader/User Role**: Users who query the system for real-time momentum predictions and entry/exit signals

### 2.2 Core Objectives

- Analyze historical stock price movements with focus on momentum events
- Identify statistically significant patterns in price continuation and reversal
- Provide probabilistic predictions for:
  - Duration of momentum continuation
  - Timing and percentage of reversals
  - Optimal entry points during momentum events

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Ingestion Layer                     │
├─────────────────────────────────────────────────────────────┤
│  - Historical Data Collector                                 │
│  - Real-time Data Stream (optional for future)              │
│  - Data Validation & Cleansing                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Storage Layer                       │
├─────────────────────────────────────────────────────────────┤
│  - Time-Series Database (Raw tick/minute data)              │
│  - Analysis Results Database (Patterns, Statistics)         │
│  - Feature Store (Computed features)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Engine Layer                     │
├─────────────────────────────────────────────────────────────┤
│  - Momentum Event Detector                                   │
│  - Pattern Analyzer                                          │
│  - Statistical Calculator                                    │
│  - Machine Learning Models (optional)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   API/Interface Layer                        │
├─────────────────────────────────────────────────────────────┤
│  - REST API (FastAPI)                                        │
│  - Analysis CLI Tools                                        │
│  - Reporting/Visualization Dashboard                        │
└─────────────────────────────────────────────────────────────┘
```

## 4. Component Design

### 4.1 Data Ingestion Layer

#### Components:
1. **Historical Data Collector** (`data_ingestion/historical_collector.py`)
   - Download historical price data from sources (Yahoo Finance, Alpha Vantage, etc.)
   - Support multiple timeframes (1min, 5min, 15min, 1hour, 1day)
   - Handle rate limiting and API quotas
   - Store in time-series format

2. **Data Validator** (`data_ingestion/validator.py`)
   - Check for missing data gaps
   - Identify anomalies (flash crashes, splits, dividends)
   - Ensure data quality and consistency

#### Technologies:
- `yfinance` or `alpaca-trade-api` for data fetching
- `pandas` for data manipulation
- `requests` for API calls

### 4.2 Data Storage Layer

#### Components:
1. **Time-Series Database**
   - Store OHLCV (Open, High, Low, Close, Volume) data
   - Efficient querying by symbol and time range
   - Technology: **TimescaleDB** (PostgreSQL extension) or **InfluxDB**

2. **Analysis Results Database**
   - Store detected momentum events
   - Store statistical patterns and probabilities
   - Technology: **PostgreSQL**

3. **Feature Store**
   - Pre-computed technical indicators
   - Momentum features (rate of change, acceleration)
   - Technology: **Redis** (for caching) + **PostgreSQL**

#### Schema Examples:

```sql
-- Raw price data
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    timeframe VARCHAR(10), -- '1min', '5min', etc.
    UNIQUE(symbol, timestamp, timeframe)
);

-- Momentum events
CREATE TABLE momentum_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    direction VARCHAR(10), -- 'UP' or 'DOWN'
    initial_price DECIMAL(10,2),
    peak_price DECIMAL(10,2),
    duration_seconds INT,
    max_move_percentage DECIMAL(5,2),
    continuation_duration_seconds INT,
    reversal_percentage DECIMAL(5,2),
    reversal_time_seconds INT
);

-- Pattern statistics
CREATE TABLE pattern_statistics (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50),
    timeframe VARCHAR(10),
    avg_continuation_duration INT,
    avg_reversal_percentage DECIMAL(5,2),
    avg_reversal_time INT,
    confidence_score DECIMAL(3,2),
    sample_size INT,
    last_updated TIMESTAMPTZ
);
```

### 4.3 Analysis Engine Layer

#### Components:

1. **Momentum Event Detector** (`analysis/momentum_detector.py`)
   - Scan historical data for significant price movements
   - Define momentum event criteria:
     ```python
     # Example criteria
     - Minimum price change: 2% in 5 minutes
     - Minimum volume: 2x average volume
     - Consecutive moves in same direction
     ```
   - Tag events with metadata (time, magnitude, volume profile)

2. **Pattern Analyzer** (`analysis/pattern_analyzer.py`)
   - Analyze each momentum event lifecycle:
     - **Continuation Phase**: How long price continues in initial direction
     - **Reversal Point**: When price starts moving opposite direction
     - **Reversal Magnitude**: Percentage retracement
   - Group patterns by:
     - Time of day
     - Market conditions (trending vs ranging)
     - Stock characteristics (volatility, sector)

3. **Statistical Calculator** (`analysis/statistics_engine.py`)
   - Calculate probabilities:
     ```
     P(continuation > X minutes | initial move)
     P(reversal within Y minutes | continuation of X minutes)
     Expected reversal percentage given momentum magnitude
     ```
   - Generate distribution curves
   - Confidence intervals

4. **Feature Engineering** (`analysis/feature_engine.py`)
   - Technical indicators:
     - RSI (Relative Strength Index)
     - Volume profile
     - Price acceleration
     - ATR (Average True Range)
   - Custom features:
     - Momentum score
     - Time-weighted price change
     - Volume surge indicator

#### Key Algorithms:

```python
# Pseudo-code for momentum detection
def detect_momentum_events(price_data, window_minutes=5, threshold_pct=2.0):
    """
    Detect significant price movements in rolling windows
    """
    events = []

    for window in rolling_windows(price_data, window_minutes):
        price_change_pct = (window.close[-1] - window.open[0]) / window.open[0] * 100
        volume_ratio = window.volume.mean() / historical_avg_volume

        if abs(price_change_pct) >= threshold_pct and volume_ratio >= 2.0:
            # Analyze continuation
            continuation = analyze_continuation(window.end_time, price_data)

            # Analyze reversal
            reversal = analyze_reversal(window.end_time, price_data)

            events.append({
                'start': window.start_time,
                'direction': 'UP' if price_change_pct > 0 else 'DOWN',
                'magnitude': abs(price_change_pct),
                'continuation_duration': continuation['duration'],
                'reversal_time': reversal['time'],
                'reversal_pct': reversal['percentage']
            })

    return events
```

### 4.4 API/Interface Layer

#### Components:

1. **REST API** (`api/main.py`)
   - Framework: **FastAPI**
   - Endpoints:
     ```
     GET  /api/v1/analyze/symbol/{symbol}          # Run analysis on symbol
     GET  /api/v1/momentum-events/{symbol}         # Get historical events
     GET  /api/v1/patterns/statistics              # Get pattern statistics
     POST /api/v1/predict/continuation             # Predict continuation
     GET  /api/v1/stocks/screener                  # Screen for current momentum
     ```

2. **Analysis CLI** (`cli/analyzer.py`)
   - Command-line tools for analysts:
     ```bash
     python -m cli.analyzer run --symbol AAPL --start 2024-01-01 --end 2024-12-31
     python -m cli.analyzer patterns --timeframe 5min
     python -m cli.analyzer backtest --strategy momentum_continuation
     ```

3. **Dashboard** (`dashboard/app.py`)
   - Framework: **Streamlit** or **Dash**
   - Visualizations:
     - Momentum event heatmaps
     - Probability distributions
     - Pattern success rates
     - Real-time screening results

## 5. Data Flow

### 5.1 Historical Analysis Flow

```
1. Data Collection
   └─> Historical Collector fetches data
       └─> Validator checks quality
           └─> Store in TimescaleDB

2. Event Detection
   └─> Momentum Detector scans historical data
       └─> Identifies significant moves
           └─> Store events in momentum_events table

3. Pattern Analysis
   └─> Pattern Analyzer processes each event
       └─> Calculates continuation/reversal metrics
           └─> Groups by patterns
               └─> Store in pattern_statistics table

4. Statistical Aggregation
   └─> Statistics Engine computes probabilities
       └─> Generates distribution models
           └─> Cache results in Redis
               └─> Expose via API
```

### 5.2 Query Flow (Future Real-time)

```
User Request: "AAPL showing 2.5% rise in last 5 min, should I enter?"

1. API receives request
   └─> Extract current momentum features
       └─> Query similar historical patterns
           └─> Calculate probabilities:
               - P(continuation > 10 min) = 65%
               - Expected continuation: 15 minutes
               - Expected reversal: 3.2% retracement
           └─> Return recommendation with confidence
```

## 6. Technology Stack

### 6.1 Core Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Core development |
| Data Processing | Pandas, NumPy | Data manipulation |
| Time-Series DB | TimescaleDB | Price data storage |
| Relational DB | PostgreSQL | Analysis results |
| Cache | Redis | Feature caching |
| API Framework | FastAPI | REST API |
| Analysis | scikit-learn, scipy | Statistical analysis |
| Visualization | Plotly, Matplotlib | Charts and graphs |
| Dashboard | Streamlit | Web interface |
| Task Queue | Celery + Redis | Async analysis jobs |
| Testing | pytest | Unit/integration tests |

### 6.2 Python Package Structure

```
gambler_ai/
├── data_ingestion/
│   ├── __init__.py
│   ├── historical_collector.py
│   ├── validator.py
│   └── connectors/
│       ├── yahoo_finance.py
│       └── alpha_vantage.py
├── storage/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models
│   ├── timeseries_db.py       # TimescaleDB interface
│   └── feature_store.py       # Redis cache interface
├── analysis/
│   ├── __init__.py
│   ├── momentum_detector.py
│   ├── pattern_analyzer.py
│   ├── statistics_engine.py
│   └── feature_engine.py
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   │   ├── analysis.py
│   │   ├── patterns.py
│   │   └── predictions.py
│   └── schemas.py             # Pydantic models
├── cli/
│   ├── __init__.py
│   └── analyzer.py
├── dashboard/
│   ├── __init__.py
│   └── app.py
├── utils/
│   ├── __init__.py
│   ├── config.py
│   └── logging.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── README.md
└── config.yaml
```

## 7. Key Metrics and Analysis

### 7.1 Momentum Event Metrics

1. **Initial Momentum**
   - Time window (e.g., 5 minutes)
   - Price change percentage
   - Volume ratio vs average
   - Direction (UP/DOWN)

2. **Continuation Metrics**
   - Duration (time in minutes/seconds)
   - Additional percentage gain/loss
   - Peak price reached
   - Volume profile during continuation

3. **Reversal Metrics**
   - Time to reversal (from momentum start)
   - Reversal percentage (from peak)
   - Speed of reversal
   - Volume during reversal

### 7.2 Statistical Analysis

1. **Probability Distributions**
   - P(continuation > t | initial_move = x%)
   - P(reversal_pct > y% | continuation_time = t)
   - Expected value calculations

2. **Pattern Classification**
   - Strong continuation (>70% follow-through)
   - Weak continuation (30-70% follow-through)
   - Immediate reversal (<30% follow-through)

3. **Success Metrics**
   - Win rate for entry strategies
   - Average R:R (Risk:Reward) ratio
   - Sharpe ratio of strategies

## 8. Development Phases

### Phase 1: Data Foundation (Weeks 1-2)
- [ ] Set up database infrastructure
- [ ] Implement historical data collector
- [ ] Build data validation pipeline
- [ ] Collect initial dataset (1-2 years of minute data for 50-100 stocks)

### Phase 2: Analysis Engine (Weeks 3-4)
- [ ] Implement momentum event detector
- [ ] Build pattern analyzer
- [ ] Develop statistical calculator
- [ ] Create initial analysis reports

### Phase 3: API & Interface (Week 5)
- [ ] Build REST API with FastAPI
- [ ] Create CLI tools for analysts
- [ ] Implement basic dashboard

### Phase 4: Optimization & Testing (Week 6)
- [ ] Performance optimization
- [ ] Backtesting framework
- [ ] Unit and integration tests
- [ ] Documentation

### Phase 5: Advanced Features (Future)
- [ ] Real-time data integration
- [ ] Machine learning models
- [ ] Alert system
- [ ] Multi-asset support

## 9. Communication Patterns

### 9.1 Internal Component Communication

1. **Data Ingestion → Storage**
   - Protocol: Direct database writes
   - Format: Pandas DataFrame → SQL
   - Frequency: Batch processing (hourly/daily for historical)

2. **Analysis Engine → Storage**
   - Protocol: Read from DB, write results back
   - Format: SQLAlchemy ORM
   - Frequency: On-demand or scheduled (Celery tasks)

3. **API → Analysis Engine**
   - Protocol: Function calls (synchronous) or Celery tasks (async)
   - Format: Python objects / Pydantic models
   - Frequency: On-demand (API requests)

### 9.2 External Communication

1. **Analyst → System**
   - Method: CLI commands or API requests
   - Authentication: API keys
   - Response: JSON or formatted CLI output

2. **Dashboard → API**
   - Method: HTTP REST calls
   - Format: JSON
   - Real-time: WebSocket (future) for live updates

## 10. Configuration Management

### 10.1 config.yaml Example

```yaml
database:
  timeseries:
    host: localhost
    port: 5432
    name: gambler_timeseries

  analytics:
    host: localhost
    port: 5432
    name: gambler_analytics

redis:
  host: localhost
  port: 6379

data_sources:
  yahoo_finance:
    enabled: true
  alpha_vantage:
    enabled: false
    api_key: ${ALPHA_VANTAGE_KEY}

analysis:
  momentum_detection:
    min_price_change_pct: 2.0
    min_volume_ratio: 2.0
    window_minutes: 5

  timeframes:
    - 1min
    - 5min
    - 15min

api:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:3000
```

## 11. Security Considerations

1. **Data Security**
   - Encrypt sensitive data at rest
   - Use environment variables for secrets
   - No API keys in code

2. **API Security**
   - JWT authentication
   - Rate limiting
   - Input validation

3. **Database Security**
   - Parameterized queries (SQL injection prevention)
   - Least privilege access
   - Regular backups

## 12. Scalability Considerations

1. **Data Volume**
   - Partition tables by date
   - Archive old data
   - Use time-series DB optimizations

2. **Compute**
   - Celery for distributed processing
   - Cache frequently accessed patterns
   - Async API endpoints for long operations

3. **Future Growth**
   - Microservices architecture (if needed)
   - Kubernetes deployment
   - Load balancing

## 13. Success Criteria

1. **Data Quality**
   - <0.1% missing data points
   - Real-time data latency <1 second (future)

2. **Analysis Performance**
   - Process 1 year of data in <30 minutes
   - API response time <500ms (95th percentile)

3. **Statistical Significance**
   - Minimum 1000 samples per pattern
   - Confidence level >95% for predictions
   - Backtested win rate >55% for entry strategies

## 14. Next Steps

1. **Immediate**: Set up development environment
   - Install PostgreSQL with TimescaleDB extension
   - Install Redis
   - Create Python virtual environment
   - Install required packages

2. **First Sprint**: Build data foundation
   - Implement historical data collector
   - Set up database schemas
   - Collect initial dataset for testing

3. **Documentation**:
   - API documentation
   - Analyst user guide
   - Development setup guide
