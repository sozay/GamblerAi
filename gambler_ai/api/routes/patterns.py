"""
Pattern analysis endpoints.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from gambler_ai.analysis import PatternAnalyzer
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/patterns/analyze")
async def analyze_patterns(
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    min_samples: int = Query(100, ge=10),
):
    """
    Analyze patterns from momentum events.

    - **symbol**: Optional symbol filter (analyzes all symbols if not provided)
    - **timeframe**: Optional timeframe filter
    - **min_samples**: Minimum number of samples required for pattern analysis
    """
    try:
        analyzer = PatternAnalyzer()
        patterns = analyzer.analyze_patterns(
            symbol=symbol, timeframe=timeframe, min_samples=min_samples
        )

        # Save patterns to database
        if patterns:
            analyzer.save_pattern_statistics(patterns)

        return {
            "success": True,
            "patterns_found": len(patterns),
            "patterns": patterns,
        }

    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/statistics")
async def get_pattern_statistics(
    pattern_type: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
):
    """
    Get pattern statistics with optional filters.

    - **pattern_type**: Filter by pattern type
    - **timeframe**: Filter by timeframe
    - **direction**: Filter by direction ('UP' or 'DOWN')
    - **min_confidence**: Minimum confidence score (0-1)
    """
    try:
        analyzer = PatternAnalyzer()
        patterns = analyzer.get_pattern_statistics(
            pattern_type=pattern_type,
            timeframe=timeframe,
            direction=direction,
            min_confidence=min_confidence,
        )

        # Convert to dict
        patterns_data = []
        for pattern in patterns:
            patterns_data.append({
                "pattern_type": pattern.pattern_type,
                "timeframe": pattern.timeframe,
                "direction": pattern.direction,
                "sample_size": pattern.sample_size,
                "avg_continuation_duration": pattern.avg_continuation_duration,
                "median_continuation_duration": pattern.median_continuation_duration,
                "avg_reversal_percentage": float(pattern.avg_reversal_percentage) if pattern.avg_reversal_percentage else None,
                "median_reversal_percentage": float(pattern.median_reversal_percentage) if pattern.median_reversal_percentage else None,
                "avg_reversal_time": pattern.avg_reversal_time,
                "median_reversal_time": pattern.median_reversal_time,
                "confidence_score": float(pattern.confidence_score) if pattern.confidence_score else None,
                "win_rate": float(pattern.win_rate) if pattern.win_rate else None,
                "last_updated": pattern.last_updated.isoformat() if pattern.last_updated else None,
            })

        return {
            "success": True,
            "count": len(patterns_data),
            "patterns": patterns_data,
        }

    except Exception as e:
        logger.error(f"Error fetching pattern statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/report")
async def get_pattern_report(
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
):
    """
    Generate a comprehensive pattern analysis report.

    - **symbol**: Optional symbol filter
    - **timeframe**: Optional timeframe filter
    """
    try:
        analyzer = PatternAnalyzer()
        report = analyzer.generate_pattern_report(symbol=symbol, timeframe=timeframe)

        return {
            "success": True,
            "report": report,
        }

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
