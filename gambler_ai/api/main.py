"""
FastAPI application main entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from gambler_ai.api.routes import analysis, health, patterns, predictions, alpaca_trading, recordings
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)

# Load configuration
config = get_config()

# Create FastAPI app
app = FastAPI(
    title="GamblerAI API",
    description="Stock momentum analysis and prediction API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
cors_origins = config.get("api.cors_origins", ["http://localhost:3000", "http://localhost:8501"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(patterns.router, prefix="/api/v1", tags=["Patterns"])
app.include_router(predictions.router, prefix="/api/v1", tags=["Predictions"])
app.include_router(alpaca_trading.router, prefix="/api/v1/alpaca", tags=["Alpaca Trading"])
app.include_router(recordings.router, tags=["Recordings"])

# Mount static files for dashboard
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Root redirect to multi-instance dashboard
@app.get("/")
async def root():
    """Redirect root URL to multi-instance dashboard."""
    return RedirectResponse(url="/static/alpaca_dashboard_multi.html")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting GamblerAI API server...")
    logger.info(f"API documentation available at http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down GamblerAI API server...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
