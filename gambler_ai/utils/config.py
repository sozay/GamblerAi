"""
Configuration management for GamblerAI application.
"""

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str
    port: int
    name: str
    user: str
    password: str


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str
    port: int
    db: int = 0
    ttl: int = 3600


class MomentumDetectionConfig(BaseModel):
    """Momentum detection parameters."""
    min_price_change_pct: float = 2.0
    min_volume_ratio: float = 2.0
    window_minutes: int = 5
    lookback_periods: int = 20


class AnalysisConfig(BaseModel):
    """Analysis configuration."""
    momentum_detection: MomentumDetectionConfig
    timeframes: list[str]


class Settings(BaseSettings):
    """Application settings loaded from environment and config file."""

    # Environment variables
    timescale_host: str = "localhost"
    timescale_port: int = 5432
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    db_user: str = "gambler"
    db_password: str = "gambler_pass"
    redis_host: str = "localhost"
    redis_port: int = 6379
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class Config:
    """Main configuration class."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file and environment."""
        self.settings = Settings()
        self.config_path = Path(config_path)
        self._config_data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        # Replace environment variable placeholders
        config = self._substitute_env_vars(config)
        return config

    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables in config."""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # Parse ${VAR:default} format
            var_spec = config[2:-1]
            if ":" in var_spec:
                var_name, default = var_spec.split(":", 1)
                return os.getenv(var_name, default)
            else:
                return os.getenv(var_spec, "")
        return config

    @property
    def timeseries_db_url(self) -> str:
        """Get TimescaleDB connection URL."""
        db_config = self._config_data["database"]["timeseries"]
        return (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
        )

    @property
    def analytics_db_url(self) -> str:
        """Get Analytics PostgreSQL connection URL."""
        db_config = self._config_data["database"]["analytics"]
        return (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
        )

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        redis_config = self._config_data["redis"]
        return f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['db']}"

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path.

        Example: config.get("analysis.momentum_detection.min_price_change_pct")
        """
        keys = key_path.split(".")
        value = self._config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


# Global configuration instance
_config_instance = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get global configuration instance (singleton)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
