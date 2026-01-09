"""
Custom exception hierarchy for CAD migration tool.

Provides structured error handling with specific exception types.
"""


class CADMigrationError(Exception):
    """Base exception for all CAD migration errors."""

    def __init__(self, message: str, context: dict | None = None):
        """
        Initialize error with message and optional context.

        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}


# Parser Errors
class ParserError(CADMigrationError):
    """Base error for parsing operations."""

    pass


class FileNotFoundError(ParserError):
    """File not found."""

    pass


class UnsupportedFileFormatError(ParserError):
    """Unsupported file format."""

    pass


class CorruptedFileError(ParserError):
    """File is corrupted or invalid."""

    pass


# Transformation Errors
class TransformationError(CADMigrationError):
    """Base error for transformation operations."""

    pass


class LayerNotFoundError(TransformationError):
    """Required layer not found."""

    pass


class InvalidTransformationError(TransformationError):
    """Transformation would produce invalid result."""

    pass


# Validation Errors
class ValidationError(CADMigrationError):
    """Base error for validation operations."""

    pass


class StandardsValidationError(ValidationError):
    """Drawing does not meet standards."""

    pass


class PreMigrationValidationError(ValidationError):
    """Pre-migration validation failed."""

    pass


class PostMigrationValidationError(ValidationError):
    """Post-migration validation failed."""

    pass


# Database Errors
class DatabaseError(CADMigrationError):
    """Base error for database operations."""

    pass


class MigrationNotFoundError(DatabaseError):
    """Migration record not found."""

    pass


class DatabaseCorruptionError(DatabaseError):
    """Database is corrupted."""

    pass


class CheckpointError(DatabaseError):
    """Checkpoint operation failed."""

    pass


# Batch Processing Errors
class BatchProcessingError(CADMigrationError):
    """Base error for batch processing."""

    pass


class WorkerError(BatchProcessingError):
    """Worker process encountered error."""

    pass


class TooManyFailuresError(BatchProcessingError):
    """Too many files failed processing."""

    pass


class RollbackError(BatchProcessingError):
    """Rollback operation failed."""

    pass


# PDM Errors
class PDMError(CADMigrationError):
    """Base error for PDM operations."""

    pass


class PDMConnectionError(PDMError):
    """Could not connect to PDM vault."""

    pass


class PDMFileNotFoundError(PDMError):
    """File not found in vault."""

    pass


class PDMFileLockedError(PDMError):
    """File is locked by another user."""

    pass


class PDMPermissionError(PDMError):
    """Insufficient permissions for operation."""

    pass


# Learning Errors
class LearningError(CADMigrationError):
    """Base error for learning operations."""

    pass


class InsufficientSamplesError(LearningError):
    """Not enough samples for learning."""

    pass


class LowConfidenceError(LearningError):
    """Learned rules have low confidence."""

    pass


# Configuration Errors
class ConfigurationError(CADMigrationError):
    """Base error for configuration issues."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Configuration is invalid."""

    pass


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    pass


# CLI Errors
class CLIError(CADMigrationError):
    """Base error for CLI operations."""

    pass


class InvalidArgumentError(CLIError):
    """Invalid command-line argument."""

    pass


class CommandFailedError(CLIError):
    """Command execution failed."""

    pass
