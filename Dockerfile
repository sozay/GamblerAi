FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gambler_ai/ ./gambler_ai/
COPY config.yaml .

# Expose ports
EXPOSE 8000 8501

# Default command (will be overridden in docker-compose)
CMD ["uvicorn", "gambler_ai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
