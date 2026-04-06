"""
Structured JSON logging utilities for PrivaLoom.

Provides consistent logging across client and server components with
structured JSON output, correlation IDs, and performance tracking.
Replaces print() statements throughout the codebase.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Setup structured JSON logger.

    Args:
        name: Logger name (typically module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    # JSON formatter
    formatter = JSONFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


class JSONFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Add any extra fields from the record
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def log_info(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """
    Log info message with structured data.

    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional structured data to include
    """
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_data = kwargs
    logger.handle(record)


def log_error(logger: logging.Logger, message: str, error: Optional[Exception] = None, **kwargs: Any) -> None:
    """
    Log error with structured data and optional exception.

    Args:
        logger: Logger instance
        message: Log message
        error: Optional exception to include
        **kwargs: Additional structured data to include
    """
    record = logger.makeRecord(
        name=logger.name,
        level=logging.ERROR,
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=(type(error), error, error.__traceback__) if error else None
    )
    record.extra_data = kwargs
    logger.handle(record)


def log_warning(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """
    Log warning message with structured data.

    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional structured data to include
    """
    record = logger.makeRecord(
        name=logger.name,
        level=logging.WARNING,
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_data = kwargs
    logger.handle(record)


def log_training_step(logger: logging.Logger, step: int, loss: float, **kwargs: Any) -> None:
    """
    Log training step with metrics.

    Args:
        logger: Logger instance
        step: Training step number
        loss: Training loss value
        **kwargs: Additional metrics to include
    """
    log_info(logger, f"Training step {step}", step=step, loss=loss, **kwargs)


def log_update_received(logger: logging.Logger, update_count: int, **kwargs: Any) -> None:
    """
    Log update reception with metadata.

    Args:
        logger: Logger instance
        update_count: Number of updates received
        **kwargs: Additional metadata to include
    """
    log_info(logger, f"Update received (total: {update_count})",
             update_count=update_count, **kwargs)


def log_aggregation_event(logger: logging.Logger, round_num: int, num_updates: int, **kwargs: Any) -> None:
    """
    Log aggregation event with round metadata (backward compatibility).

    Args:
        logger: Logger instance
        round_num: Aggregation round number
        num_updates: Number of updates being aggregated
        **kwargs: Additional metadata to include
    """
    log_info(logger, f"Aggregation round {round_num} (updates: {num_updates})",
             round=round_num, updates=num_updates, **kwargs)


def log_aggregation_start(logger: logging.Logger, round_num: int, num_updates: int, **kwargs: Any) -> None:
    """
    Log the start of an aggregation round.

    Args:
        logger: Logger instance
        round_num: Aggregation round number
        num_updates: Number of updates being aggregated
        **kwargs: Additional metadata to include
    """
    log_info(logger, f"Starting aggregation round {round_num}",
             round=round_num, updates=num_updates, phase="start", **kwargs)


def log_aggregation_complete(logger: logging.Logger, round_num: int,
                           duration_ms: float, memory_mb: Optional[float] = None, **kwargs: Any) -> None:
    """
    Log aggregation completion with performance metrics.

    Args:
        logger: Logger instance
        round_num: Completed round number
        duration_ms: Aggregation duration in milliseconds
        memory_mb: Memory usage in MB (optional)
        **kwargs: Additional metrics to include
    """
    log_data = {
        "round": round_num,
        "duration_ms": duration_ms,
        "phase": "complete",
        **kwargs
    }
    if memory_mb is not None:
        log_data["memory_mb"] = memory_mb

    log_info(logger, f"Completed aggregation round {round_num} ({duration_ms:.1f}ms)",
             **log_data)