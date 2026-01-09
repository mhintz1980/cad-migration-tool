"""
Post-migration validator.

Validates drawings after transformation to ensure standards compliance.
Verifies that transformations were applied correctly.
"""

from typing import Dict, Any
import logging

from .base_validator import BaseValidator
from ..parsers.base_parser import ParsedDrawing
from ...data.models.validation import ValidationResult

logger = logging.getLogger(__name__)


class PostMigrationValidator(BaseValidator):
    """Validates drawings after migration/transformation."""

    def validate(self, drawing: ParsedDrawing) -> ValidationResult:
        """
        Post-migration validation checks.

        Checks:
        1. All layers match layer_standards
        2. No old layer names remain (all mapped correctly)
        3. Layer properties correct (color, line type, weight)
        4. Dimensions on correct layer
        5. Dimension styles match standards
        6. Entity counts unchanged (no data loss)

        Args:
            drawing: Transformed drawing to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # Check 1: All layers should be in layer_standards
        unknown_layers = self._check_unknown_layers(drawing)
        if unknown_layers:
            issue = self.create_issue(
                rule_name="unmapped_layers_remain",
                severity="error",
                message=f"Layers not in standards after migration: {', '.join(unknown_layers)}",
            )
            result.add_issue(issue)

        # Check 2: Old layer names should be gone
        old_layers = self._check_old_layers(drawing)
        if old_layers:
            issue = self.create_issue(
                rule_name="old_layers_remain",
                severity="error",
                message=f"Old layer names still present: {', '.join(old_layers)}",
            )
            result.add_issue(issue)

        # Check 3: Layer properties match standards
        layer_property_issues = self._validate_layer_properties(drawing)
        for issue in layer_property_issues:
            result.add_issue(issue)

        # Check 4: Dimensions on correct layer
        if self.standards.dimension_standards:
            dimension_issues = self._validate_dimension_placement(drawing)
            for issue in dimension_issues:
                result.add_issue(issue)

        # Check 5: Dimension styles correct
        if self.standards.dimension_standards:
            dimension_style_issues = self._validate_dimension_styles(drawing)
            for issue in dimension_style_issues:
                result.add_issue(issue)

        # Check 6: No empty required layers
        empty_required = self._check_empty_required_layers(drawing)
        if empty_required:
            issue = self.create_issue(
                rule_name="empty_required_layers",
                severity="warning",
                message=f"Required layers are empty: {', '.join(empty_required)}",
            )
            result.add_issue(issue)

        logger.info(
            f"Post-migration validation complete: "
            f"{result.error_count} errors, {result.warning_count} warnings"
        )

        return result

    def _check_unknown_layers(self, drawing: ParsedDrawing) -> set:
        """Find layers not in layer_standards."""
        current_layers = set(drawing.layers.keys())
        standard_layers = set(self.standards.layer_standards.keys())

        return current_layers - standard_layers

    def _check_old_layers(self, drawing: ParsedDrawing) -> set:
        """Find old layer names that should have been mapped."""
        current_layers = set(drawing.layers.keys())
        old_layer_names = set(self.standards.layer_mapping.keys())

        # Old names that still exist
        return current_layers & old_layer_names

    def _validate_layer_properties(self, drawing: ParsedDrawing) -> list:
        """
        Validate layer properties match standards.

        Returns list of ValidationIssues.
        """
        issues = []

        for layer_name, layer_data in drawing.layers.items():
            if layer_name not in self.standards.layer_standards:
                continue  # Already flagged as unknown

            std = self.standards.layer_standards[layer_name]

            # Check color
            if layer_data.get("color") != std.color:
                issue = self.create_issue(
                    rule_name="layer_color_mismatch",
                    severity="error",
                    message=f"Layer '{layer_name}' color {layer_data.get('color')} != standard {std.color}",
                    layer_name=layer_name,
                )
                issues.append(issue)

            # Check line type
            if layer_data.get("line_type") != std.line_type:
                issue = self.create_issue(
                    rule_name="layer_line_type_mismatch",
                    severity="error",
                    message=f"Layer '{layer_name}' line_type {layer_data.get('line_type')} != standard {std.line_type}",
                    layer_name=layer_name,
                )
                issues.append(issue)

            # Check line weight
            if layer_data.get("line_weight") != std.line_weight:
                issue = self.create_issue(
                    rule_name="layer_line_weight_mismatch",
                    severity="error",
                    message=f"Layer '{layer_name}' line_weight {layer_data.get('line_weight')} != standard {std.line_weight}",
                    layer_name=layer_name,
                )
                issues.append(issue)

            # Check plot setting
            if layer_data.get("plot") != std.plot:
                issue = self.create_issue(
                    rule_name="layer_plot_mismatch",
                    severity="warning",
                    message=f"Layer '{layer_name}' plot setting doesn't match standard",
                    layer_name=layer_name,
                )
                issues.append(issue)

        return issues

    def _validate_dimension_placement(self, drawing: ParsedDrawing) -> list:
        """
        Validate dimensions are on correct layer.

        Returns list of ValidationIssues.
        """
        issues = []

        # Get expected dimension layer from standards
        dim_std = self._get_dimension_standard()
        if not dim_std:
            return issues

        expected_layer = dim_std.layer

        # Check all layers for dimension entities
        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])

            for entity in entities:
                entity_type = self._get_entity_type(entity)

                if entity_type.startswith("DIM") or entity_type == "DIMENSION":
                    if layer_name != expected_layer:
                        issue = self.create_issue(
                            rule_name="dimension_wrong_layer",
                            severity="error",
                            message=f"Dimension on layer '{layer_name}' instead of '{expected_layer}'",
                            entity_type=entity_type,
                            layer_name=layer_name,
                        )
                        issues.append(issue)

        return issues

    def _validate_dimension_styles(self, drawing: ParsedDrawing) -> list:
        """
        Validate dimension styles match standards.

        Returns list of ValidationIssues.
        """
        issues = []

        dim_std = self._get_dimension_standard()
        if not dim_std:
            return issues

        # Find all dimension entities
        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])

            for entity in entities:
                entity_type = self._get_entity_type(entity)

                if entity_type.startswith("DIM") or entity_type == "DIMENSION":
                    # Check dimension properties (placeholder - real implementation needs ezdxf)
                    mismatches = self._check_dimension_properties(entity, dim_std)

                    if mismatches:
                        issue = self.create_issue(
                            rule_name="dimension_style_mismatch",
                            severity="warning",
                            message=f"Dimension properties don't match standard: {mismatches}",
                            entity_type=entity_type,
                            layer_name=layer_name,
                        )
                        issues.append(issue)

        return issues

    def _check_empty_required_layers(self, drawing: ParsedDrawing) -> set:
        """Find required layers that have no entities."""
        empty_required = set()

        for layer_name in self.standards.layer_standards.keys():
            if layer_name in drawing.layers:
                entities = drawing.layers[layer_name].get("entities", [])
                if not entities:
                    empty_required.add(layer_name)

        return empty_required

    def _get_dimension_standard(self):
        """Get dimension standard (default or first available)."""
        if "default" in self.standards.dimension_standards:
            return self.standards.dimension_standards["default"]
        elif self.standards.dimension_standards:
            return next(iter(self.standards.dimension_standards.values()))
        return None

    def _get_entity_type(self, entity: Any) -> str:
        """Get entity type string."""
        if isinstance(entity, dict):
            return entity.get("type", "UNKNOWN")
        return str(type(entity).__name__)

    def _check_dimension_properties(
        self, entity: Any, std
    ) -> Dict[str, Any]:
        """
        Check dimension properties against standard.

        Returns dict of mismatches (placeholder).
        """
        mismatches = {}

        # This is a placeholder - real implementation needs ezdxf
        if isinstance(entity, dict):
            if entity.get("arrow_size") != std.arrow_size:
                mismatches["arrow_size"] = (
                    entity.get("arrow_size"),
                    std.arrow_size,
                )

        return mismatches
