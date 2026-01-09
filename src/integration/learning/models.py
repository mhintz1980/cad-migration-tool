"""
Data models for standards learning system.

Defines the structures for learned rules, observations, and learning results.
"""

from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
from pathlib import Path


@dataclass
class Observation:
    """Single observation from a sample file pair."""

    source: str  # What was observed in old file
    target: str  # What was observed in new file
    file_pair: tuple[Path, Path]  # (old_file, new_file)
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context


@dataclass
class LearnedRule:
    """Single learned mapping rule with confidence scoring."""

    rule_type: str  # "layer_mapping", "dimension_style", "property_mapping", etc.
    source_pattern: str  # What to match in old file
    target_value: Any  # What to produce in new file
    confidence: float  # 0.0-1.0 based on sample agreement
    sample_count: int  # How many samples contributed
    observations: List[Observation] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)  # Files that disagreed
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Human-readable representation."""
        agreement = self.sample_count - len(self.exceptions)
        return (
            f"{self.rule_type}: '{self.source_pattern}' -> '{self.target_value}' "
            f"(confidence: {self.confidence:.2f}, samples: {agreement}/{self.sample_count})"
        )


@dataclass
class LearningResult:
    """Result of learning process with extracted rules and metadata."""

    rules: List[LearnedRule]
    sample_count: int  # Total sample pairs processed
    successful_pairs: int  # Pairs successfully parsed
    failed_pairs: List[tuple[Path, Path, str]] = field(default_factory=list)  # (old, new, error)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def high_confidence_rules(self, threshold: float = 0.8) -> List[LearnedRule]:
        """Get rules with confidence >= threshold."""
        return [rule for rule in self.rules if rule.confidence >= threshold]

    @property
    def low_confidence_rules(self, threshold: float = 0.8) -> List[LearnedRule]:
        """Get rules with confidence < threshold."""
        return [rule for rule in self.rules if rule.confidence < threshold]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rules": [
                {
                    "rule_type": rule.rule_type,
                    "source_pattern": rule.source_pattern,
                    "target_value": rule.target_value,
                    "confidence": rule.confidence,
                    "sample_count": rule.sample_count,
                    "exceptions": rule.exceptions,
                }
                for rule in self.rules
            ],
            "sample_count": self.sample_count,
            "successful_pairs": self.successful_pairs,
            "failed_pairs": [
                {"old": str(old), "new": str(new), "error": err}
                for old, new, err in self.failed_pairs
            ],
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class LayerMapping:
    """Learned layer name mapping."""

    old_name: str
    new_name: str
    confidence: float
    observations: List[Observation] = field(default_factory=list)


@dataclass
class DimensionStyleMapping:
    """Learned dimension style properties."""

    property_name: str
    old_value: Any
    new_value: Any
    confidence: float
    observations: List[Observation] = field(default_factory=list)


@dataclass
class PropertyMapping:
    """Learned property/attribute mapping."""

    old_property: str
    new_property: str
    confidence: float
    observations: List[Observation] = field(default_factory=list)
