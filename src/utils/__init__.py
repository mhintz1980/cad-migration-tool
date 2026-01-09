"""
Utility modules for CAD migration tool.

Provides logging, configuration, and exception handling.
"""

from .logging import get_logger, LoggerFactory, StructuredLogger
from .config import get_config, set_config, load_config, AppConfig
from .exceptions import (
    CADMigrationError,
    ParserError,
    TransformationError,
    ValidationError,
    DatabaseError,
    BatchProcessingError,
    PDMError,
    LearningError,
    ConfigurationError,
    CLIError,
)

__all__ = [
    # Logging
    "get_logger",
    "LoggerFactory",
    "StructuredLogger",
    # Configuration
    "get_config",
    "set_config",
    "load_config",
    "AppConfig",
    # Exceptions
    "CADMigrationError",
    "ParserError",
    "TransformationError",
    "ValidationError",
    "DatabaseError",
    "BatchProcessingError",
    "PDMError",
    "LearningError",
    "ConfigurationError",
    "CLIError",
]
