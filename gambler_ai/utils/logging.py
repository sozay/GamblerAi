"""
Logging configuration for GamblerAI application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from gambler_ai.utils.config import get_config


class Logger:
    """Centralized logging manager."""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        Get or create a logger instance.

        Args:
            name: Logger name (typically __name__ of the module)
            log_file: Optional log file path

        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]

        config = get_config()
        log_level = config.get("logging.level", "INFO")
        log_format = config.get(
            "logging.format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level))

        # Remove existing handlers
        logger.handlers = []

        # Create formatter
        formatter = logging.Formatter(log_format)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if log_file specified or from config)
        if log_file is None:
            log_file = config.get("logging.file", "logs/gambler_ai.log")

        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(getattr(logging, log_level))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Prevent propagation to root logger
        logger.propagate = False

        cls._loggers[name] = logger
        return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Convenience function to get a logger.

    Usage:
        from gambler_ai.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Message")
    """
    return Logger.get_logger(name)
