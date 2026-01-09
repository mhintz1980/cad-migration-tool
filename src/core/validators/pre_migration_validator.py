"""
Pre-migration validator.

Validates drawings before transformation to catch issues early.
Checks for missing layers, invalid entities, standards compliance, etc.
"""

from typing import Set
import logging

from .base_validator import BaseValidator
from ..parsers.base_parser import ParsedDrawing
from ...data.models.validation import ValidationResult

logger = logging.getLogger(__name__)


class PreMigrationValidator(BaseValidator):
    """Validates drawings before migration/transformation."""

    def validate(self, drawing: ParsedDrawing) -> ValidationResult:
        """
        Pre-migration validation checks.

        Checks:
        1. File can be parsed (already done if we have ParsedDrawing)
        2. Required layers exist or can be mapped
        3. Unknown layers are identified
        4. Title block has required fields
        5. No corrupt entities
        6. File size reasonable

        Args:
            drawing: Parsed drawing to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # Check 1: Drawing has layers
        if not drawing.layers:
            issue = self.create_issue(
                rule_name="has_layers",
                severity="error",
                message="Drawing has no layers",
            )
            result.add_issue(issue)
            return result  # Can't proceed without layers

        # Check 2: Unknown layers (no mapping or standard defined)
        unknown_layers = self._check_unknown_layers(drawing)
        if unknown_layers:
            issue = self.create_issue(
                rule_name="unknown_layers",
                severity="warning",
                message=f"Layers with no mapping or standard: {', '.join(unknown_layers)}",
            )
            result.add_issue(issue)

        # Check 3: Required layers after mapping
        missing_required = self._check_required_layers(drawing)
        if missing_required:
            issue = self.create_issue(
                rule_name="missing_required_layers",
                severity="error",
                message=f"Required layers missing after mapping: {', '.join(missing_required)}",
            )
            result.add_issue(issue)

        # Check 4: Title block validation
        if self.standards.title_block_standard:
            title_block_issues = self._validate_title_block(drawing)
            for issue in title_block_issues:
                result.add_issue(issue)

        # Check 5: Entity count reasonable
        entity_count = sum(
            len(layer_data.get("entities", []))
            for layer_data in drawing.layers.values()
        )
        if entity_count == 0:
            issue = self.create_issue(
                rule_name="no_entities",
                severity="warning",
                message="Drawing has no entities",
            )
            result.add_issue(issue)
        elif entity_count > 100000:
            issue = self.create_issue(
                rule_name="too_many_entities",
                severity="warning",
                message=f"Drawing has {entity_count} entities (may be slow to process)",
            )
            result.add_issue(issue)

        # Check 6: Validation rules from standards
        for rule in self.standards.validation_rules:
            rule_issues = self._apply_validation_rule(drawing, rule)
            for issue in rule_issues:
                result.add_issue(issue)

        logger.info(
            f"Pre-migration validation complete: "
            f"{result.error_count} errors, {result.warning_count} warnings"
        )

        return result

    def _check_unknown_layers(self, drawing: ParsedDrawing) -> Set[str]:
        """
        Find layers with no mapping or standard defined.

        Returns set of unknown layer names.
        """
        current_layers = set(drawing.layers.keys())
        known_layers = set(self.standards.layer_standards.keys())
        mapped_layers = set(self.standards.layer_mapping.keys())

        # Unknown = current layers that aren't in standards and aren't mapped
        unknown = current_layers - known_layers - mapped_layers

        return unknown

    def _check_required_layers(self, drawing: ParsedDrawing) -> Set[str]:
        """
        Check if required layers will exist after mapping.

        Returns set of missing required layer names.
        """
        # Determine what layers will exist after mapping
        current_layers = set(drawing.layers.keys())

        # After mapping: mapped targets + unmapped current layers
        post_mapping_layers = set()
        for layer in current_layers:
            if layer in self.standards.layer_mapping:
                post_mapping_layers.add(self.standards.layer_mapping[layer])
            else:
                post_mapping_layers.add(layer)

        # Check which standard layers are required (have entities that need them)
        # For now, consider all layer_standards as required
        required_layers = set(self.standards.layer_standards.keys())

        # Missing = required layers not in post-mapping set
        missing = required_layers - post_mapping_layers

        return missing

    def _validate_title_block(self, drawing: ParsedDrawing) -> list:
        """
        Validate title block fields.

        Returns list of ValidationIssues.
        """
        issues = []
        tb_std = self.standards.title_block_standard

        # Check required fields
        for field in tb_std.required_fields:
            if field not in drawing.title_block or not drawing.title_block[field]:
                issue = self.create_issue(
                    rule_name="title_block_required_field",
                    severity="error",
                    message=f"Required title block field missing: {field}",
                )
                issues.append(issue)

        # Validate date format if date present
        if "date" in drawing.title_block and drawing.title_block["date"]:
            try:
                from datetime import datetime

                datetime.strptime(drawing.title_block["date"], tb_std.date_format)
            except ValueError:
                issue = self.create_issue(
                    rule_name="title_block_date_format",
                    severity="warning",
                    message=f"Date format doesn't match {tb_std.date_format}",
                )
                issues.append(issue)

        # Validate revision format if present
        if "revision" in drawing.title_block and drawing.title_block["revision"]:
            import re

            if not re.match(tb_std.revision_format, drawing.title_block["revision"]):
                issue = self.create_issue(
                    rule_name="title_block_revision_format",
                    severity="warning",
                    message=f"Revision format doesn't match {tb_std.revision_format}",
                )
                issues.append(issue)

        return issues

    def _apply_validation_rule(self, drawing: ParsedDrawing, rule) -> list:
        """
        Apply a custom validation rule.

        Returns list of ValidationIssues.
        """
        issues = []

        # Rule types:
        # - layer_exists: Check if a specific layer exists
        # - entity_count: Check entity count in range
        # - custom: Custom validation logic (not implemented yet)

        if rule.rule_type == "layer_exists":
            required_layer = rule.config.get("layer_name")
            if required_layer and required_layer not in drawing.layers:
                issue = self.create_issue(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Required layer not found: {required_layer}",
                    layer_name=required_layer,
                )
                issues.append(issue)

        elif rule.rule_type == "entity_count":
            min_count = rule.config.get("min", 0)
            max_count = rule.config.get("max", float("inf"))
            entity_count = sum(
                len(layer_data.get("entities", []))
                for layer_data in drawing.layers.values()
            )

            if entity_count < min_count:
                issue = self.create_issue(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Entity count {entity_count} below minimum {min_count}",
                )
                issues.append(issue)
            elif entity_count > max_count:
                issue = self.create_issue(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Entity count {entity_count} exceeds maximum {max_count}",
                )
                issues.append(issue)

        return issues
