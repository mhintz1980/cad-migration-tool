"""
Abstract base class for CAD transformers.

Defines the interface for transforming parsed drawings according to standards.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any
import logging

from ..parsers.base_parser import ParsedDrawing
from ...data.models.standards import StandardConfig

logger = logging.getLogger(__name__)


@dataclass
class TransformationResult:
    """Result of a transformation operation."""

    success: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    changes: Dict[str, int] = field(
        default_factory=dict
    )  # e.g., {"layers_renamed": 5}
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(message)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        logger.error(message)
        self.success = False

    def increment_change(self, change_type: str, count: int = 1) -> None:
        """Increment a change counter."""
        self.changes[change_type] = self.changes.get(change_type, 0) + count

    def merge(self, other: "TransformationResult") -> None:
        """Merge another result into this one."""
        self.success = self.success and other.success
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)

        for change_type, count in other.changes.items():
            self.increment_change(change_type, count)

        self.metadata.update(other.metadata)


class BaseTransformer(ABC):
    """Abstract base class for CAD drawing transformers."""

    def __init__(self, standards: StandardConfig):
        """
        Initialize transformer.

        Args:
            standards: Standards configuration to apply
        """
        self.standards = standards
        logger.debug(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def transform(self, drawing: ParsedDrawing) -> TransformationResult:
        """
        Transform drawing according to standards.

        Args:
            drawing: Parsed drawing to transform (modified in-place)

        Returns:
            TransformationResult with success status and change details
        """
        pass

    @abstractmethod
    def can_transform(self, drawing: ParsedDrawing) -> bool:
        """
        Check if this transformer can handle the drawing.

        Args:
            drawing: Parsed drawing

        Returns:
            True if transformer can be applied
        """
        pass

    @abstractmethod
    def validate(self, drawing: ParsedDrawing) -> TransformationResult:
        """
        Validate drawing without transforming.

        Args:
            drawing: Parsed drawing

        Returns:
            TransformationResult with validation warnings/errors
        """
        pass

    def get_name(self) -> str:
        """Get transformer name."""
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(standards={self.standards.name})"
