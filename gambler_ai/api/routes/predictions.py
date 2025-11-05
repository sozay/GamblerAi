"""
Prediction endpoints for momentum trading.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gambler_ai.analysis import StatisticsEngine
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ContinuationPredictionRequest(BaseModel):
    """Request model for continuation prediction."""

    symbol: str
    initial_move_pct: float
    volume_ratio: float
    timeframe: str = "5min"
    direction: Optional[str] = None


class RiskRewardRequest(BaseModel):
    """Request model for risk/reward calculation."""

    entry_price: float
    expected_continuation_pct: float
    expected_reversal_pct: float
    stop_loss_pct: float = 1.0


@router.post("/predict/continuation")
async def predict_continuation(request: ContinuationPredictionRequest):
    """
    Predict continuation probability and metrics for a current momentum event.

    - **symbol**: Stock ticker symbol
    - **initial_move_pct**: Initial price move percentage
    - **volume_ratio**: Current volume vs average
    - **timeframe**: Timeframe (default: "5min")
    - **direction**: Optional direction ('UP' or 'DOWN')

    Returns probability of continuation, expected duration, and trading recommendation.
    """
    try:
        engine = StatisticsEngine()
        prediction = engine.predict_continuation(
            symbol=request.symbol,
            initial_move_pct=request.initial_move_pct,
            volume_ratio=request.volume_ratio,
            timeframe=request.timeframe,
            direction=request.direction,
        )

        return {
            "success": True,
            "prediction": prediction,
        }

    except Exception as e:
        logger.error(f"Error predicting continuation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/risk-reward")
async def calculate_risk_reward(request: RiskRewardRequest):
    """
    Calculate risk/reward ratio for a potential trade.

    - **entry_price**: Entry price
    - **expected_continuation_pct**: Expected continuation percentage
    - **expected_reversal_pct**: Expected reversal percentage
    - **stop_loss_pct**: Stop loss percentage (default: 1.0)

    Returns target price, stop loss, and risk/reward ratio.
    """
    try:
        engine = StatisticsEngine()
        rr_metrics = engine.calculate_risk_reward(
            entry_price=request.entry_price,
            expected_continuation_pct=request.expected_continuation_pct,
            expected_reversal_pct=request.expected_reversal_pct,
            stop_loss_pct=request.stop_loss_pct,
        )

        return {
            "success": True,
            "risk_reward": rr_metrics,
        }

    except Exception as e:
        logger.error(f"Error calculating risk/reward: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict/distribution/{symbol}")
async def get_distribution(
    symbol: str,
    timeframe: str = "5min",
    direction: Optional[str] = None,
    metric: str = "continuation_duration_seconds",
):
    """
    Get probability distribution for a specific metric.

    - **symbol**: Stock ticker symbol
    - **timeframe**: Timeframe (default: "5min")
    - **direction**: Optional direction filter
    - **metric**: Metric to analyze (default: "continuation_duration_seconds")

    Available metrics:
    - continuation_duration_seconds
    - reversal_percentage
    - reversal_time_seconds
    - max_move_percentage
    """
    try:
        engine = StatisticsEngine()
        distribution = engine.get_probability_distribution(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            metric=metric,
        )

        return {
            "success": True,
            "distribution": distribution,
        }

    except Exception as e:
        logger.error(f"Error getting distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
