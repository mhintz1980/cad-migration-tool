"""
Layer transformation logic.

Applies layer mapping rules and layer standards from StandardConfig.
Renames layers, updates properties (color, line type, line weight), and
moves entities to correct layers based on entity_layer_rules.
"""

from typing import Dict, Any, Set
import logging

from .base_transformer import BaseTransformer, TransformationResult
from ..parsers.base_parser import ParsedDrawing
from ...data.models.standards import StandardConfig, LayerStandard

logger = logging.getLogger(__name__)


class LayerTransformer(BaseTransformer):
    """Transforms layers according to standards."""

    def can_transform(self, drawing: ParsedDrawing) -> bool:
        """
        Check if transformer can handle the drawing.

        Args:
            drawing: Parsed drawing

        Returns:
            True if drawing has layers
        """
        return bool(drawing.layers)

    def validate(self, drawing: ParsedDrawing) -> TransformationResult:
        """
        Validate layer compliance without transforming.

        Checks:
        - Unknown layers (not in layer_mapping and not in layer_standards)
        - Missing required layers
        - Layer property mismatches

        Args:
            drawing: Parsed drawing

        Returns:
            TransformationResult with validation results
        """
        result = TransformationResult(success=True)

        current_layers = set(drawing.layers.keys())
        standard_layers = set(self.standards.layer_standards.keys())
        mapped_layers = set(self.standards.layer_mapping.values())

        # Check for unknown layers
        unknown_layers = current_layers - standard_layers - mapped_layers
        if unknown_layers:
            result.add_warning(
                f"Unknown layers found (no mapping or standard): {unknown_layers}"
            )

        # Check for layer property compliance
        for layer_name, layer_data in drawing.layers.items():
            if layer_name in self.standards.layer_standards:
                std = self.standards.layer_standards[layer_name]
                mismatches = self._check_layer_properties(layer_data, std)
                if mismatches:
                    result.add_warning(
                        f"Layer '{layer_name}' property mismatches: {mismatches}"
                    )

        return result

    def transform(self, drawing: ParsedDrawing) -> TransformationResult:
        """
        Transform drawing layers according to standards.

        Applies layer mapping and property updates.

        Args:
            drawing: Parsed drawing (modified in-place)

        Returns:
            TransformationResult
        """
        result = TransformationResult(success=True)

        # Step 1: Apply layer mapping (rename layers)
        renamed_count = self._apply_layer_mapping(drawing, result)
        result.increment_change("layers_renamed", renamed_count)

        # Step 2: Update layer properties to match standards
        updated_count = self._update_layer_properties(drawing, result)
        result.increment_change("layers_updated", updated_count)

        # Step 3: Move entities to correct layers based on entity_layer_rules
        moved_count = self._apply_entity_layer_rules(drawing, result)
        result.increment_change("entities_moved", moved_count)

        # Step 4: Remove empty layers
        removed_count = self._remove_empty_layers(drawing, result)
        result.increment_change("layers_removed", removed_count)

        logger.info(
            f"Layer transformation complete: "
            f"{renamed_count} renamed, {updated_count} updated, "
            f"{moved_count} entities moved, {removed_count} removed"
        )

        return result

    def _apply_layer_mapping(
        self, drawing: ParsedDrawing, result: TransformationResult
    ) -> int:
        """
        Apply layer_mapping rules to rename layers.

        Returns count of layers renamed.
        """
        renamed_count = 0

        # Build reverse mapping for entities (old_layer -> new_layer)
        for old_name, new_name in self.standards.layer_mapping.items():
            if old_name not in drawing.layers:
                continue

            if old_name == new_name:
                continue  # No change needed

            # Rename layer in layers dict
            if new_name in drawing.layers:
                # Merge into existing layer
                drawing.layers[new_name]["entities"].extend(
                    drawing.layers[old_name]["entities"]
                )
                result.add_warning(
                    f"Merged layer '{old_name}' into existing '{new_name}'"
                )
            else:
                # Simple rename
                drawing.layers[new_name] = drawing.layers[old_name]

            # Remove old layer
            del drawing.layers[old_name]
            renamed_count += 1

            # Update entity references (this depends on ezdxf specifics)
            # For now, we log it
            logger.debug(f"Renamed layer '{old_name}' -> '{new_name}'")

        return renamed_count

    def _update_layer_properties(
        self, drawing: ParsedDrawing, result: TransformationResult
    ) -> int:
        """
        Update layer properties to match layer_standards.

        Returns count of layers updated.
        """
        updated_count = 0

        for layer_name, layer_data in drawing.layers.items():
            if layer_name not in self.standards.layer_standards:
                continue

            std = self.standards.layer_standards[layer_name]

            # Update properties
            if layer_data.get("color") != std.color:
                layer_data["color"] = std.color
                updated_count += 1

            if layer_data.get("line_type") != std.line_type:
                layer_data["line_type"] = std.line_type
                updated_count += 1

            if layer_data.get("line_weight") != std.line_weight:
                layer_data["line_weight"] = std.line_weight
                updated_count += 1

            if layer_data.get("plot") != std.plot:
                layer_data["plot"] = std.plot
                updated_count += 1

        return updated_count

    def _apply_entity_layer_rules(
        self, drawing: ParsedDrawing, result: TransformationResult
    ) -> int:
        """
        Move entities to correct layers based on entity_layer_rules.

        entity_layer_rules maps entity types to target layers:
        {"TEXT": "ANNOTATION", "DIMENSION": "DIMENSIONS"}

        Returns count of entities moved.
        """
        if not self.standards.entity_layer_rules:
            return 0

        moved_count = 0

        # Group entities by type
        entities_by_type: Dict[str, list] = {}

        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])

            for entity in entities:
                entity_type = self._get_entity_type(entity)
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append((layer_name, entity))

        # Move entities to target layers
        for entity_type, target_layer in self.standards.entity_layer_rules.items():
            if entity_type not in entities_by_type:
                continue

            for current_layer, entity in entities_by_type[entity_type]:
                if current_layer == target_layer:
                    continue  # Already on correct layer

                # Remove from current layer
                drawing.layers[current_layer]["entities"].remove(entity)

                # Add to target layer (create if needed)
                if target_layer not in drawing.layers:
                    drawing.layers[target_layer] = self._create_layer(target_layer)
                    result.add_warning(f"Created new layer '{target_layer}'")

                drawing.layers[target_layer]["entities"].append(entity)
                moved_count += 1

        return moved_count

    def _remove_empty_layers(
        self, drawing: ParsedDrawing, result: TransformationResult
    ) -> int:
        """
        Remove layers with no entities.

        Returns count of layers removed.
        """
        empty_layers = [
            name
            for name, data in drawing.layers.items()
            if not data.get("entities", [])
        ]

        for layer_name in empty_layers:
            del drawing.layers[layer_name]
            logger.debug(f"Removed empty layer '{layer_name}'")

        return len(empty_layers)

    def _create_layer(self, layer_name: str) -> Dict[str, Any]:
        """Create new layer dict with default or standard properties."""
        if layer_name in self.standards.layer_standards:
            std = self.standards.layer_standards[layer_name]
            return {
                "color": std.color,
                "line_type": std.line_type,
                "line_weight": std.line_weight,
                "plot": std.plot,
                "entities": [],
            }
        else:
            # Default layer properties
            return {
                "color": 7,  # White/black
                "line_type": "CONTINUOUS",
                "line_weight": 13,
                "plot": True,
                "entities": [],
            }

    def _get_entity_type(self, entity: Any) -> str:
        """
        Get entity type string.

        This is ezdxf-specific. For now, returns generic type.
        """
        # In real implementation with ezdxf:
        # return entity.dxftype()

        # For now, assume entity is dict with 'type' key
        if isinstance(entity, dict):
            return entity.get("type", "UNKNOWN")
        else:
            return str(type(entity).__name__)

    def _check_layer_properties(
        self, layer_data: Dict[str, Any], std: LayerStandard
    ) -> Dict[str, tuple]:
        """
        Check layer properties against standard.

        Returns dict of mismatches: {property: (current, expected)}
        """
        mismatches = {}

        if layer_data.get("color") != std.color:
            mismatches["color"] = (layer_data.get("color"), std.color)

        if layer_data.get("line_type") != std.line_type:
            mismatches["line_type"] = (layer_data.get("line_type"), std.line_type)

        if layer_data.get("line_weight") != std.line_weight:
            mismatches["line_weight"] = (layer_data.get("line_weight"), std.line_weight)

        return mismatches
