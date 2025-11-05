# GamblerAI Setup Guide

This guide will help you set up the GamblerAI development environment.

## Prerequisites

Choose one of the following setup methods:

### Option A: Docker Setup (Recommended for Quick Start)
- Docker 20.10+
- Docker Compose 2.0+

### Option B: Local Development Setup
- Python 3.11+
- PostgreSQL 15+ with TimescaleDB extension
- Redis 7+
- Git

## Quick Start with Docker

### 1. Clone and Navigate

```bash
git clone <your-repo-url>
cd GamblerAi
```

### 2. Start All Services

```bash
# Start all services in background
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Verify Services

```bash
# Check if all services are running
docker-compose ps

# Test API
curl http://localhost:8000/health

# Test Redis
docker-compose exec redis redis-cli ping
# Should return: PONG

# Test Database
docker-compose exec timescaledb psql -U gambler -d gambler_timeseries -c "SELECT 1;"
```

### 4. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **Celery Flower**: http://localhost:5555
- **TimescaleDB**: localhost:5432
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379

### 5. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes all data)
docker-compose down -v
```

## Local Development Setup

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-contrib \
    redis-server \
    build-essential libpq-dev
```

#### macOS
```bash
brew install python@3.11 postgresql@15 redis
```

#### Windows
- Install Python 3.11 from python.org
- Install PostgreSQL from https://www.postgresql.org/download/windows/
- Install Redis from https://github.com/microsoftarchive/redis/releases

### 2. Install TimescaleDB Extension

#### Ubuntu/Debian
```bash
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y timescaledb-2-postgresql-15
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

#### macOS
```bash
brew tap timescale/tap
brew install timescaledb
```

### 3. Set Up Databases

```bash
# Start PostgreSQL and Redis
sudo systemctl start postgresql
sudo systemctl start redis

# Create databases and user
sudo -u postgres psql <<EOF
CREATE USER gambler WITH PASSWORD 'gambler_pass';
CREATE DATABASE gambler_timeseries OWNER gambler;
CREATE DATABASE gambler_analytics OWNER gambler;
GRANT ALL PRIVILEGES ON DATABASE gambler_timeseries TO gambler;
GRANT ALL PRIVILEGES ON DATABASE gambler_analytics TO gambler;
EOF

# Enable TimescaleDB extension
sudo -u postgres psql -d gambler_timeseries -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Initialize schema
psql -U gambler -d gambler_timeseries -f scripts/init_db.sql
```

### 4. Set Up Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env  # or your preferred editor
```

Example `.env`:
```
TIMESCALE_HOST=localhost
TIMESCALE_PORT=5432
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DB_USER=gambler
DB_PASSWORD=gambler_pass
REDIS_HOST=localhost
REDIS_PORT=6379
LOG_LEVEL=INFO
```

### 6. Verify Installation

```bash
# Test database connection
python -c "from gambler_ai.utils.config import get_config; config = get_config(); print(config.timeseries_db_url)"

# Test Redis connection
redis-cli ping
```

## Running the Application

### Start Individual Components

#### Terminal 1: API Server
```bash
source venv/bin/activate
uvicorn gambler_ai.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2: Celery Worker
```bash
source venv/bin/activate
celery -A gambler_ai.tasks worker --loglevel=info
```

#### Terminal 3: Dashboard
```bash
source venv/bin/activate
streamlit run gambler_ai/dashboard/app.py
```

#### Terminal 4: Celery Flower (Optional)
```bash
source venv/bin/activate
celery -A gambler_ai.tasks flower --port=5555
```

## First Steps After Setup

### 1. Collect Historical Data

```bash
# Activate virtual environment
source venv/bin/activate

# Collect data for a symbol
python -m gambler_ai.cli.analyzer collect \
    --symbol AAPL \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --timeframe 5min

# Or collect for multiple symbols
python -m gambler_ai.cli.analyzer collect \
    --symbols AAPL,MSFT,GOOGL,AMZN \
    --start 2024-01-01 \
    --end 2024-12-31
```

### 2. Run Analysis

```bash
# Detect momentum events
python -m gambler_ai.cli.analyzer detect-momentum \
    --symbol AAPL \
    --threshold 2.0 \
    --window 5

# Analyze patterns
python -m gambler_ai.cli.analyzer analyze-patterns \
    --symbol AAPL
```

### 3. Test the API

```bash
# Get health status
curl http://localhost:8000/health

# Get momentum events
curl http://localhost:8000/api/v1/momentum-events/AAPL

# Get pattern statistics
curl http://localhost:8000/api/v1/patterns/statistics
```

### 4. Open the Dashboard

Navigate to http://localhost:8501 in your browser.

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gambler_ai --cov-report=html

# Run specific test file
pytest tests/unit/test_momentum_detector.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black gambler_ai/

# Sort imports
isort gambler_ai/

# Lint
flake8 gambler_ai/

# Type checking
mypy gambler_ai/

# Run all quality checks
black gambler_ai/ && isort gambler_ai/ && flake8 gambler_ai/ && mypy gambler_ai/
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Description of changes"

# Push to remote
git push origin feature/your-feature-name
```

## Common Issues and Solutions

### Issue: TimescaleDB extension not found

**Solution:**
```bash
sudo -u postgres psql -d gambler_timeseries -c "CREATE EXTENSION timescaledb;"
```

### Issue: Permission denied for database

**Solution:**
```bash
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gambler_timeseries TO gambler;"
```

### Issue: Redis connection refused

**Solution:**
```bash
# Start Redis
sudo systemctl start redis
# OR
redis-server
```

### Issue: Port already in use

**Solution:**
```bash
# Find process using port
lsof -i :8000  # Replace 8000 with your port

# Kill process
kill -9 <PID>
```

### Issue: Module not found errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Database connection errors in Docker

**Solution:**
```bash
# Check if containers are running
docker-compose ps

# Restart containers
docker-compose restart

# Check logs
docker-compose logs timescaledb
```

## Performance Optimization

### Database Indexing

The init script creates necessary indexes, but you can add more:

```sql
-- Add custom indexes for your queries
CREATE INDEX idx_custom ON stock_prices (symbol, timestamp DESC)
WHERE timeframe = '5min';
```

### Redis Caching

Adjust cache TTL in `config.yaml`:

```yaml
redis:
  ttl: 7200  # 2 hours
```

### Celery Workers

Scale Celery workers based on workload:

```bash
# Start multiple workers
celery -A gambler_ai.tasks worker --concurrency=4 --loglevel=info
```

## Monitoring

### Check Service Health

```bash
# API health
curl http://localhost:8000/health

# Celery status
celery -A gambler_ai.tasks status

# Database connections
psql -U gambler -d gambler_timeseries -c "SELECT count(*) FROM pg_stat_activity;"

# Redis info
redis-cli info
```

### View Logs

```bash
# Docker logs
docker-compose logs -f api
docker-compose logs -f celery_worker

# Local logs
tail -f logs/gambler_ai.log
```

## Backup and Restore

### Backup Databases

```bash
# Backup TimescaleDB
pg_dump -U gambler gambler_timeseries > backup_timeseries.sql

# Backup Analytics DB
pg_dump -U gambler gambler_analytics > backup_analytics.sql
```

### Restore Databases

```bash
# Restore TimescaleDB
psql -U gambler gambler_timeseries < backup_timeseries.sql

# Restore Analytics DB
psql -U gambler gambler_analytics < backup_analytics.sql
```

## Next Steps

1. **Read the Architecture**: Review [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Understand the Data Flow**: See data flow diagrams in architecture doc
3. **Start Development**: Choose a component from the roadmap in README.md
4. **Write Tests**: Add tests for any new features
5. **Document Your Work**: Update docs as you build

## Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [README.md](README.md) for usage examples
- Open an issue on GitHub for bugs
- Contact the team for questions

## Useful Commands Reference

```bash
# Docker
docker-compose up -d              # Start all services
docker-compose down               # Stop all services
docker-compose logs -f [service]  # View logs
docker-compose restart [service]  # Restart service
docker-compose ps                 # List services

# Python
source venv/bin/activate          # Activate virtual env
pip install -r requirements.txt   # Install dependencies
python -m pytest                  # Run tests

# Database
psql -U gambler -d gambler_timeseries   # Connect to DB
pg_dump -U gambler database > backup.sql # Backup
psql -U gambler database < backup.sql    # Restore

# Redis
redis-cli                         # Connect to Redis
redis-cli ping                    # Test connection
redis-cli flushall                # Clear all data (CAUTION)

# Git
git status                        # Check status
git add .                         # Stage all changes
git commit -m "message"           # Commit
git push origin branch-name       # Push to remote
```
