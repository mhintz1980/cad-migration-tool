"""
Structured logging system for CAD migration tool.

Provides consistent, structured logging across all components.
"""

import logging
import sys
from pathlib import Path
from typing import Any
from datetime import datetime
import json


class StructuredLogger:
    """
    Structured logger with JSON output support.

    Provides consistent logging with structured context.
    """

    def __init__(
        self,
        name: str,
        level: str = "INFO",
        log_file: Path | None = None,
        structured: bool = False,
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically module name)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for logging
            structured: Use JSON structured logging
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.structured = structured

        # Remove existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        if structured:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

        self.logger.addHandler(console_handler)

        # File handler (if specified)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.upper()))

            if structured:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )

            self.logger.addHandler(file_handler)

    def _log_with_context(
        self, level: str, message: str, context: dict[str, Any] | None = None
    ):
        """Log message with optional context."""
        if self.structured and context:
            extra = {"context": context}
            getattr(self.logger, level)(message, extra=extra)
        else:
            getattr(self.logger, level)(message)

    def debug(self, message: str, **context):
        """Log debug message with context."""
        self._log_with_context("debug", message, context)

    def info(self, message: str, **context):
        """Log info message with context."""
        self._log_with_context("info", message, context)

    def warning(self, message: str, **context):
        """Log warning message with context."""
        self._log_with_context("warning", message, context)

    def error(self, message: str, **context):
        """Log error message with context."""
        self._log_with_context("error", message, context)

    def critical(self, message: str, **context):
        """Log critical message with context."""
        self._log_with_context("critical", message, context)

    def exception(self, message: str, exc_info: Exception | None = None, **context):
        """Log exception with traceback and context."""
        if exc_info:
            context["exception"] = {
                "type": type(exc_info).__name__,
                "message": str(exc_info),
            }
        self.logger.exception(message, extra={"context": context} if context else None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context if available
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data)


class LoggerFactory:
    """
    Factory for creating consistent loggers.

    Provides centralized logger configuration.
    """

    _default_level = "INFO"
    _default_log_dir = Path("logs")
    _structured = False

    @classmethod
    def configure(
        cls,
        level: str = "INFO",
        log_dir: Path | None = None,
        structured: bool = False,
    ):
        """
        Configure default logger settings.

        Args:
            level: Default logging level
            log_dir: Default log directory
            structured: Use structured (JSON) logging
        """
        cls._default_level = level
        if log_dir:
            cls._default_log_dir = log_dir
        cls._structured = structured

    @classmethod
    def get_logger(
        cls,
        name: str,
        level: str | None = None,
        log_file: str | None = None,
    ) -> StructuredLogger:
        """
        Get logger instance.

        Args:
            name: Logger name (typically __name__)
            level: Override default level
            log_file: Optional log file name (in default log dir)

        Returns:
            StructuredLogger instance
        """
        log_path = None
        if log_file:
            log_path = cls._default_log_dir / log_file

        return StructuredLogger(
            name=name,
            level=level or cls._default_level,
            log_file=log_path,
            structured=cls._structured,
        )


# Convenience function
def get_logger(name: str, **kwargs) -> StructuredLogger:
    """
    Get logger instance.

    Args:
        name: Logger name (typically __name__)
        **kwargs: Additional arguments for LoggerFactory.get_logger

    Returns:
        StructuredLogger instance
    """
    return LoggerFactory.get_logger(name, **kwargs)
