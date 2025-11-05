"""
Analysis endpoints for data collection and momentum detection.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from gambler_ai.analysis import MomentumDetector
from gambler_ai.data_ingestion import HistoricalDataCollector, DataValidator
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class CollectionRequest(BaseModel):
    """Request model for data collection."""

    symbols: List[str]
    start_date: datetime
    end_date: datetime
    intervals: List[str] = ["5m"]


class DetectionRequest(BaseModel):
    """Request model for momentum detection."""

    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: str = "5min"


@router.post("/collect")
async def collect_data(request: CollectionRequest):
    """
    Collect historical price data for symbols.

    - **symbols**: List of stock ticker symbols
    - **start_date**: Start date for data collection
    - **end_date**: End date for data collection
    - **intervals**: List of intervals to collect (default: ["5m"])
    """
    try:
        collector = HistoricalDataCollector()
        stats = collector.collect_and_save(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            intervals=request.intervals,
        )

        return {
            "success": True,
            "message": f"Collected data for {stats['symbols_processed']} symbols",
            "statistics": stats,
        }

    except Exception as e:
        logger.error(f"Error collecting data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-momentum")
async def detect_momentum(request: DetectionRequest):
    """
    Detect momentum events for a symbol.

    - **symbol**: Stock ticker symbol
    - **start_date**: Start date for detection
    - **end_date**: End date for detection
    - **timeframe**: Timeframe to analyze (default: "5min")
    """
    try:
        detector = MomentumDetector()
        events = detector.detect_events(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            timeframe=request.timeframe,
            save_to_db=True,
        )

        return {
            "success": True,
            "symbol": request.symbol,
            "events_detected": len(events),
            "events": events,
        }

    except Exception as e:
        logger.error(f"Error detecting momentum: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/momentum-events/{symbol}")
async def get_momentum_events(
    symbol: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    direction: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get momentum events for a symbol with optional filters.

    - **symbol**: Stock ticker symbol
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    - **direction**: Filter by direction ('UP' or 'DOWN')
    - **timeframe**: Filter by timeframe
    - **limit**: Maximum number of events to return (default: 100)
    """
    try:
        detector = MomentumDetector()
        events = detector.get_events(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            direction=direction,
            timeframe=timeframe,
        )

        # Convert to dict and limit results
        events_data = []
        for event in events[:limit]:
            events_data.append({
                "id": event.id,
                "symbol": event.symbol,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "direction": event.direction,
                "initial_price": float(event.initial_price) if event.initial_price else None,
                "peak_price": float(event.peak_price) if event.peak_price else None,
                "max_move_percentage": float(event.max_move_percentage) if event.max_move_percentage else None,
                "continuation_duration_seconds": event.continuation_duration_seconds,
                "reversal_percentage": float(event.reversal_percentage) if event.reversal_percentage else None,
                "reversal_time_seconds": event.reversal_time_seconds,
                "timeframe": event.timeframe,
            })

        return {
            "success": True,
            "symbol": symbol,
            "count": len(events_data),
            "events": events_data,
        }

    except Exception as e:
        logger.error(f"Error fetching events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-data")
async def validate_data(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    timeframe: str = "5min",
):
    """
    Validate data quality for a symbol.

    - **symbol**: Stock ticker symbol
    - **start_date**: Start date for validation
    - **end_date**: End date for validation
    - **timeframe**: Timeframe to validate
    """
    try:
        validator = DataValidator()
        results = validator.validate_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )

        # Log results
        validator.log_quality_check(results)

        return {
            "success": True,
            "validation": results,
        }

    except Exception as e:
        logger.error(f"Error validating data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
