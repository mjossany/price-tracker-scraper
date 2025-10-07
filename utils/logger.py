import json
import logging
import os
import time
import psutil
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
    Enhanced utility class for logging performance metrics with timing and memory tracking.
    """

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.metrics: Dict[str, Any] = {}
        self.timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = {}
        self.start_time = time.time()

    def record(self, metric_name: str, value: Any) -> None:
        """Record a metric."""
        self.metrics[metric_name] = value

    def increment(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self.counters[metric_name] = self.counters.get(metric_name, 0) + value
    
    def start_timer(self, timer_name: str) -> None:
        """Start a timer for measuring duration."""
        self.timers[f"{timer_name}_start"] = time.time()
    
    def end_timer(self, timer_name: str) -> float:
        """End a timer and return the duration in seconds."""
        if f"{timer_name}_start" not in self.timers:
            self.logger.warning(f"Timer '{timer_name}' was not started")
            return 0.0
        
        start_time = self.timers[f"{timer_name}_start"]
        duration = time.time() - start_time
        self.record(f"{timer_name}_duration_seconds", duration)
        return duration
    
    def record_memory_usage(self) -> None:
        """Record current memory usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            self.record("memory_used_mb", memory_info.rss / 1024 / 1024)
            self.record("memory_percent", process.memory_percent())
        except Exception as e:
            self.logger.warning("Could not record memory usage", error=str(e))

    def record_execution_metrics(self) -> None:
        """Record overall execution metrics."""
        total_duration = time.time() - self.start_time
        self.record("total_execution_time_seconds", total_duration)
        self.record("execution_timestamp", datetime.utcnow().isoformat() + "Z")

        # Calculate success rate if we have success/failure counts
        total_attempts = self.counters.get("successful_operations", 0) + self.counters.get("failed_operations", 0)
        if total_attempts > 0:
            success_rate = self.counters.get("successful_operations", 0) / total_attempts
            self.record("success_rate", round(success_rate, 3))

    def log_metrics(self) -> None:
        """Log all recorded metrics in structured format."""
        self.record_execution_metrics()
        self.record_memory_usage()

        # Combine all metrics
        all_metrics = {
            **self.metrics,
            **{f"counter_{k}": v for k, v in self.counters.items()}
        }
        
        self.logger.info("Performance metrics", metrics=all_metrics)

    def reset(self) -> None:
        """Reset all metrics and timers."""
        self.metrics = {}
        self.timers = {}
        self.counters = {}
        self.start_time = time.time()
    
    # Convenience methods for common metrics
    def record_scraping_metrics(self, store: str, products_processed: int, success_count: int, failure_count: int, duration: float) -> None:
        """Record scraping-specific metrics."""
        self.record(f"{store}_products_processed", products_processed)
        self.record(f"{store}_success_count", success_count)
        self.record(f"{store}_failure_count", failure_count)
        self.record(f"{store}_duration_seconds", duration)
        self.record(f"{store}_success_rate", success_count / products_processed if products_processed > 0 else 0)
        
        self.increment("total_products_processed", products_processed)
        self.increment("successful_operations", success_count)
        self.increment("failed_operations", failure_count)

    def record_database_metrics(self, operation: str, duration: float, success: bool) -> None:
        """Record database operation metrics."""
        self.record(f"db_{operation}_duration_seconds", duration)
        self.increment(f"db_{operation}_attempts")
        if success:
            self.increment(f"db_{operation}_success")
        else:
            self.increment(f"db_{operation}_failures")