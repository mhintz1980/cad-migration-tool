"""
Validation data models.

Define data structures for validation results and issues.
"""

from dataclasses import dataclass, field
from typing import List, Any, Optional


@dataclass
class ValidationIssue:
    """Single validation issue."""

    rule_name: str
    severity: str  # error, warning
    message: str

    # Optional context
    entity_type: Optional[str] = None
    layer_name: Optional[str] = None
    location: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "entity_type": self.entity_type,
            "layer_name": self.layer_name,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationIssue":
        """Create from dictionary."""
        return cls(
            rule_name=data["rule_name"],
            severity=data["severity"],
            message=data["message"],
            entity_type=data.get("entity_type"),
            layer_name=data.get("layer_name"),
            location=data.get("location"),
        )

    def __str__(self) -> str:
        """String representation."""
        return f"[{self.severity.upper()}] {self.rule_name}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation operation."""

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    # Summary statistics
    error_count: int = field(init=False)
    warning_count: int = field(init=False)

    def __post_init__(self):
        """Calculate statistics."""
        self.error_count = sum(1 for issue in self.issues if issue.severity == "error")
        self.warning_count = sum(1 for issue in self.issues if issue.severity == "warning")

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add validation issue."""
        self.issues.append(issue)
        if issue.severity == "error":
            self.error_count += 1
        elif issue.severity == "warning":
            self.warning_count += 1

        # Update validity
        if issue.severity == "error":
            self.is_valid = False

    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [issue for issue in self.issues if issue.severity == "error"]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues."""
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        """Create from dictionary."""
        issues = [ValidationIssue.from_dict(issue_data) for issue_data in data.get("issues", [])]
        return cls(is_valid=data["is_valid"], issues=issues)

    def __str__(self) -> str:
        """String representation."""
        lines = [
            f"Validation Result: {'PASS' if self.is_valid else 'FAIL'}",
            f"  Errors: {self.error_count}",
            f"  Warnings: {self.warning_count}",
        ]

        if self.issues:
            lines.append("\nIssues:")
            for issue in self.issues:
                lines.append(f"  {issue}")

        return "\n".join(lines)
