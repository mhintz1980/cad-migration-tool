"""
Dimension transformation logic.

Applies dimension style standards from StandardConfig.
Updates dimension properties (arrow size, text height, precision, etc.)
and ensures dimensions are on the correct layer.
"""

from typing import Dict, Any, List
import logging

from .base_transformer import BaseTransformer, TransformationResult
from ..parsers.base_parser import ParsedDrawing
from ...data.models.standards import DimensionStandard

logger = logging.getLogger(__name__)


class DimensionTransformer(BaseTransformer):
    """Transforms dimensions according to standards."""

    def can_transform(self, drawing: ParsedDrawing) -> bool:
        """
        Check if transformer can handle the drawing.

        Args:
            drawing: Parsed drawing

        Returns:
            True if drawing has dimension standards configured
        """
        return bool(self.standards.dimension_standards)

    def validate(self, drawing: ParsedDrawing) -> TransformationResult:
        """
        Validate dimension compliance without transforming.

        Checks:
        - Dimensions on wrong layers
        - Dimension style mismatches
        - Inconsistent precision/units

        Args:
            drawing: Parsed drawing

        Returns:
            TransformationResult with validation results
        """
        result = TransformationResult(success=True)

        # Get dimension entities
        dimension_entities = self._get_dimension_entities(drawing)

        if not dimension_entities:
            result.add_warning("No dimension entities found")
            return result

        # Get default dimension standard (or first available)
        dim_std = self._get_dimension_standard()
        if not dim_std:
            result.add_warning("No dimension standard configured")
            return result

        # Check each dimension
        for entity in dimension_entities:
            layer = self._get_entity_layer(entity)

            # Check if on correct layer
            if layer != dim_std.layer:
                result.add_warning(
                    f"Dimension on layer '{layer}', expected '{dim_std.layer}'"
                )

            # Check properties
            mismatches = self._check_dimension_properties(entity, dim_std)
            if mismatches:
                result.add_warning(f"Dimension property mismatches: {mismatches}")

        return result

    def transform(self, drawing: ParsedDrawing) -> TransformationResult:
        """
        Transform dimensions according to standards.

        Applies dimension style and layer corrections.

        Args:
            drawing: Parsed drawing (modified in-place)

        Returns:
            TransformationResult
        """
        result = TransformationResult(success=True)

        # Get dimension entities
        dimension_entities = self._get_dimension_entities(drawing)

        if not dimension_entities:
            logger.debug("No dimension entities to transform")
            return result

        # Get dimension standard
        dim_std = self._get_dimension_standard()
        if not dim_std:
            result.add_error("No dimension standard configured")
            return result

        # Step 1: Update dimension properties
        updated_count = self._update_dimension_properties(
            dimension_entities, dim_std, result
        )
        result.increment_change("dimensions_updated", updated_count)

        # Step 2: Move dimensions to correct layer
        moved_count = self._move_to_correct_layer(
            drawing, dimension_entities, dim_std, result
        )
        result.increment_change("dimensions_moved", moved_count)

        logger.info(
            f"Dimension transformation complete: "
            f"{updated_count} updated, {moved_count} moved to layer '{dim_std.layer}'"
        )

        return result

    def _get_dimension_standard(self) -> DimensionStandard | None:
        """Get dimension standard to use (default or first available)."""
        if "default" in self.standards.dimension_standards:
            return self.standards.dimension_standards["default"]
        elif self.standards.dimension_standards:
            # Return first available
            return next(iter(self.standards.dimension_standards.values()))
        else:
            return None

    def _get_dimension_entities(self, drawing: ParsedDrawing) -> List[Any]:
        """
        Extract all dimension entities from drawing.

        Returns list of dimension entities.
        """
        dimensions = []

        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])

            for entity in entities:
                entity_type = self._get_entity_type(entity)

                # Match dimension entity types
                if entity_type.startswith("DIM") or entity_type == "DIMENSION":
                    dimensions.append(entity)

        return dimensions

    def _update_dimension_properties(
        self,
        entities: List[Any],
        std: DimensionStandard,
        result: TransformationResult,
    ) -> int:
        """
        Update dimension entity properties.

        Returns count of dimensions updated.
        """
        updated_count = 0

        for entity in entities:
            changed = False

            # Update arrow size
            if self._set_entity_property(entity, "arrow_size", std.arrow_size):
                changed = True

            # Update text height
            if self._set_entity_property(entity, "text_height", std.text_height):
                changed = True

            # Update text offset
            if self._set_entity_property(entity, "text_offset", std.text_offset):
                changed = True

            # Update extension line offset
            if self._set_entity_property(
                entity, "extension_line_offset", std.extension_line_offset
            ):
                changed = True

            # Update precision
            if self._set_entity_property(entity, "precision", std.precision):
                changed = True

            # Update units
            if self._set_entity_property(entity, "units", std.units):
                changed = True

            # Update arrow style
            if self._set_entity_property(entity, "arrow_style", std.arrow_style):
                changed = True

            # Update text alignment
            if self._set_entity_property(entity, "text_alignment", std.text_alignment):
                changed = True

            if changed:
                updated_count += 1

        return updated_count

    def _move_to_correct_layer(
        self,
        drawing: ParsedDrawing,
        entities: List[Any],
        std: DimensionStandard,
        result: TransformationResult,
    ) -> int:
        """
        Move dimensions to the correct layer.

        Returns count of dimensions moved.
        """
        moved_count = 0

        for entity in entities:
            current_layer = self._get_entity_layer(entity)

            if current_layer == std.layer:
                continue  # Already on correct layer

            # Remove from current layer
            if current_layer in drawing.layers:
                drawing.layers[current_layer]["entities"].remove(entity)

            # Add to target layer (create if needed)
            if std.layer not in drawing.layers:
                drawing.layers[std.layer] = self._create_layer(std.layer)
                result.add_warning(f"Created dimension layer '{std.layer}'")

            drawing.layers[std.layer]["entities"].append(entity)
            moved_count += 1

        return moved_count

    def _create_layer(self, layer_name: str) -> Dict[str, Any]:
        """Create layer dict for dimensions."""
        # Check if layer standard exists
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
            # Default dimension layer properties
            return {
                "color": 3,  # Green
                "line_type": "CONTINUOUS",
                "line_weight": 18,
                "plot": True,
                "entities": [],
            }

    def _get_entity_type(self, entity: Any) -> str:
        """Get entity type string."""
        # For dict-based entities
        if isinstance(entity, dict):
            return entity.get("type", "UNKNOWN")
        else:
            # For ezdxf entities: entity.dxftype()
            return str(type(entity).__name__)

    def _get_entity_layer(self, entity: Any) -> str:
        """Get layer name for entity."""
        if isinstance(entity, dict):
            return entity.get("layer", "0")
        else:
            # For ezdxf entities: entity.dxf.layer
            return "0"

    def _set_entity_property(self, entity: Any, prop: str, value: Any) -> bool:
        """
        Set entity property. Returns True if changed.

        This is placeholder - actual implementation depends on ezdxf API.
        """
        if isinstance(entity, dict):
            if entity.get(prop) != value:
                entity[prop] = value
                return True
        # For ezdxf entities, would use: entity.dxf.prop = value
        return False

    def _check_dimension_properties(
        self, entity: Any, std: DimensionStandard
    ) -> Dict[str, tuple]:
        """
        Check dimension properties against standard.

        Returns dict of mismatches: {property: (current, expected)}
        """
        mismatches = {}

        if isinstance(entity, dict):
            if entity.get("arrow_size") != std.arrow_size:
                mismatches["arrow_size"] = (entity.get("arrow_size"), std.arrow_size)

            if entity.get("text_height") != std.text_height:
                mismatches["text_height"] = (entity.get("text_height"), std.text_height)

            if entity.get("precision") != std.precision:
                mismatches["precision"] = (entity.get("precision"), std.precision)

            if entity.get("units") != std.units:
                mismatches["units"] = (entity.get("units"), std.units)

        return mismatches
