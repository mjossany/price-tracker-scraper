import json
import logging
import os
from datetime import datetime
from typing import Any, Dict


def get_logger(name: str = "price-tracker-scraper") -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level))

        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, log_level))

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger

class MetricsLogger:
    """
    Utility class for logging performance metrics.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics: Dict[str, Any] = {}

    def record(self, metric_name: str, value: Any) -> None:
        """Record a metric."""
        self.metrics[metric_name] = value

    def increment(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self.metrics[metric_name] = self.metrics.get(metric_name, 0) + value

    def log_metrics(self) -> None:
        """Log all recorded metrics."""
        self.logger.info(f"Metrics: {json.dumps(self.metrics)}")

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics = {}