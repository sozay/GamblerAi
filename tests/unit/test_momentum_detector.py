"""
Unit tests for momentum detector.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from gambler_ai.analysis import MomentumDetector


@pytest.fixture
def detector():
    """Create a MomentumDetector instance."""
    return MomentumDetector()


def test_detector_initialization(detector):
    """Test momentum detector initialization."""
    assert detector is not None
    assert detector.min_price_change_pct > 0
    assert detector.min_volume_ratio > 0
    assert detector.window_minutes > 0


def test_calculate_indicators(detector):
    """Test technical indicator calculations."""
    # Create sample data
    dates = pd.date_range(start="2024-01-01", periods=30, freq="5min")
    data = pd.DataFrame({
        "timestamp": dates,
        "open": [100 + i * 0.5 for i in range(30)],
        "high": [101 + i * 0.5 for i in range(30)],
        "low": [99 + i * 0.5 for i in range(30)],
        "close": [100.5 + i * 0.5 for i in range(30)],
        "volume": [1000000 + i * 10000 for i in range(30)],
    })

    # Calculate indicators
    result = detector._calculate_indicators(data)

    # Check that indicators were added
    assert "avg_volume" in result.columns
    assert "volume_ratio" in result.columns
    assert "price_change_pct" in result.columns
