"""
Custom exceptions for CAD migration system.
"""


class CADMigrationError(Exception):
    """Base exception for CAD migration errors."""

    pass


class ParsingError(CADMigrationError):
    """Error parsing CAD file."""

    pass


class TransformationError(CADMigrationError):
    """Error during transformation."""

    pass


class ValidationError(CADMigrationError):
    """Validation failed."""

    def __init__(self, message: str, errors: list):
        super().__init__(message)
        self.errors = errors


class PDMError(CADMigrationError):
    """Error interacting with PDM system."""

    pass


class ConfigurationError(CADMigrationError):
    """Error in configuration."""

    pass


class RollbackError(CADMigrationError):
    """Error during rollback."""

    pass
