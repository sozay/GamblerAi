"""
Unit tests for configuration module.
"""

import pytest

from gambler_ai.utils.config import Config, get_config


def test_get_config():
    """Test getting configuration instance."""
    config = get_config()
    assert isinstance(config, Config)
    assert config is not None


def test_config_database_urls():
    """Test database URL generation."""
    config = get_config()

    # Check that URLs are generated
    assert config.timeseries_db_url.startswith("postgresql://")
    assert config.analytics_db_url.startswith("postgresql://")
    assert "gambler" in config.timeseries_db_url


def test_config_get_value():
    """Test getting configuration values."""
    config = get_config()

    # Test getting nested values
    min_price_change = config.get("analysis.momentum_detection.min_price_change_pct")
    assert isinstance(min_price_change, (int, float))
    assert min_price_change > 0

    # Test default value
    non_existent = config.get("non.existent.key", "default")
    assert non_existent == "default"
