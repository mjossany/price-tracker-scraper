import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
import traceback

class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for CloudWatch structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)

class StructuredLogger:
    """
    Wrapper around Python logger that provides structured logging capabilities
    """

    def __init__(self, name: str = "price-tracker-scraper", context: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(name)
        self.context = context or {}

        if not self.logger.handlers:
            log_level = os.getenv("LOG_LEVEL", "INFO").upper()
            self.logger.setLevel(getattr(logging, log_level))

            handler = logging.StreamHandler()
            handler.setLevel(getattr(logging, log_level))
            handler.setFormatter(JsonFormatter())

            self.logger.addHandler(handler)
            self.logger.propagate = False

    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge logger context with extra fields."""
        merged = self.context.copy()
        if extra:
            merged.update(extra)
        return merged

    def info(self, message: str, **kwargs):
        """Log info message with optional extra fields."""
        extra_fields = self._add_context(kwargs)
        self.logger.info(message, extra={"extra_fields": extra_fields})

    def error(self, message: str, **kwargs):
        """Log error message with optional extra fields."""
        extra_fields = self._add_context(kwargs)
        self.logger.error(message, extra={"extra_fields": extra_fields})
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional extra fields."""
        extra_fields = self._add_context(kwargs)
        self.logger.warning(message, extra={"extra_fields": extra_fields})

    def debug(self, message: str, **kwargs):
        """Log debug message with optional extra fields."""
        extra_fields = self._add_context(kwargs)
        self.logger.debug(message, extra={"extra_fields": extra_fields})

    def exception(self, message: str, **kwargs):
        """Log exception with traceback and optional extra fields."""
        extra_fields = self._add_context(kwargs)
        self.logger.exception(message, extra={"extra_fields": extra_fields})

def get_logger(name: str = "price-tracker-scraper", lambda_context=None) -> StructuredLogger:
    """
    Get a configured structured logger instance.

    Args:
        name: Logger name
        lambda_context: AWS Lambda context object (optional)

    Returns:
        Configured StructuredLogger instance
    """
    context = {}

    if lambda_context:
        context = {
            "request_id": lambda_context.aws_request_id,
            "function_name": lambda_context.function_name,
            "function_version": lambda_context.function_version,
            "memory_limit_mb": lambda_context.memory_limit_in_mb,
        }

    return StructuredLogger(name, context)

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