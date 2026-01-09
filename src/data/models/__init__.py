"""
Data models for CAD migration system.

This package contains all data structures used throughout the migration tool.
"""

from .standards import (
    LayerStandard,
    DimensionStandard,
    TitleBlockStandard,
    PropertyMapping,
    ValidationRule,
    StandardConfig,
)
from .migration import Migration, MigrationItem, MigrationStatus
from .part_card import PartCardData, PartType
from .validation import ValidationResult, ValidationIssue

__all__ = [
    # Standards
    "LayerStandard",
    "DimensionStandard",
    "TitleBlockStandard",
    "PropertyMapping",
    "ValidationRule",
    "StandardConfig",
    # Migration
    "Migration",
    "MigrationItem",
    "MigrationStatus",
    # Part card
    "PartCardData",
    "PartType",
    # Validation
    "ValidationResult",
    "ValidationIssue",
]
