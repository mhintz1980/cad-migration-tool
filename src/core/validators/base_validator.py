"""
Abstract base class for validators.

Defines the interface for validation operations.
"""

from abc import ABC, abstractmethod
from typing import List
import logging

from ..parsers.base_parser import ParsedDrawing
from ...data.models.standards import StandardConfig
from ...data.models.validation import ValidationResult, ValidationIssue

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Abstract base class for CAD validators."""

    def __init__(self, standards: StandardConfig):
        """
        Initialize validator.

        Args:
            standards: Standards configuration to validate against
        """
        self.standards = standards
        logger.debug(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def validate(self, drawing: ParsedDrawing) -> ValidationResult:
        """
        Validate drawing against standards.

        Args:
            drawing: Parsed drawing to validate

        Returns:
            ValidationResult with issues found
        """
        pass

    def get_name(self) -> str:
        """Get validator name."""
        return self.__class__.__name__

    def create_issue(
        self,
        rule_name: str,
        severity: str,
        message: str,
        entity_type: str = None,
        layer_name: str = None,
        location: str = None,
    ) -> ValidationIssue:
        """
        Helper to create validation issue.

        Args:
            rule_name: Rule that failed
            severity: "error" or "warning"
            message: Description of issue
            entity_type: Optional entity type
            layer_name: Optional layer name
            location: Optional location description

        Returns:
            ValidationIssue
        """
        return ValidationIssue(
            rule_name=rule_name,
            severity=severity,
            message=message,
            entity_type=entity_type,
            layer_name=layer_name,
            location=location,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(standards={self.standards.name})"
