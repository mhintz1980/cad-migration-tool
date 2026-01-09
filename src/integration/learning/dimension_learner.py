"""
Dimension style learner.

Learns dimension style properties (arrow size, text height, etc.)
by comparing dimension entities across sample pairs.
"""

from pathlib import Path
from typing import List, Dict, Any
import logging

from ...core.parsers.base_parser import ParsedDrawing
from .base_learner import BaseLearner
from .models import Observation, LearnedRule

logger = logging.getLogger(__name__)


class DimensionLearner(BaseLearner):
    """Learns dimension style properties from sample pairs."""

    # Properties to learn
    DIMENSION_PROPERTIES = [
        "arrow_size",
        "text_height",
        "text_offset",
        "extension_line_offset",
        "precision",
        "units",
    ]

    def get_rule_type(self) -> str:
        """Rule type for dimension styles."""
        return "dimension_style"

    def extract_observations(
        self, old_drawing: ParsedDrawing, new_drawing: ParsedDrawing, file_pair: tuple[Path, Path]
    ) -> List[Observation]:
        """
        Extract dimension style observations.

        Strategy:
        1. Find all dimension entities in both drawings
        2. Extract common properties (arrow size, text height, etc.)
        3. Record property changes as observations

        Args:
            old_drawing: Parsed old drawing
            new_drawing: Parsed new drawing
            file_pair: (old_file, new_file)

        Returns:
            List of observations
        """
        observations = []

        # Extract dimension properties from both drawings
        old_dim_props = self._extract_dimension_properties(old_drawing)
        new_dim_props = self._extract_dimension_properties(new_drawing)

        # Compare each property
        for prop_name in self.DIMENSION_PROPERTIES:
            old_value = old_dim_props.get(prop_name)
            new_value = new_dim_props.get(prop_name)

            if old_value is not None and new_value is not None and old_value != new_value:
                # Property changed
                obs = Observation(
                    source=f"{prop_name}:{old_value}",
                    target=f"{prop_name}:{new_value}",
                    file_pair=file_pair,
                    context={
                        "property": prop_name,
                        "old_value": old_value,
                        "new_value": new_value,
                    },
                )
                observations.append(obs)

                logger.debug(
                    f"Dimension property change: {prop_name} "
                    f"{old_value} -> {new_value}"
                )

        return observations

    def create_rules(self, observations: List[Observation]) -> List[LearnedRule]:
        """
        Create dimension style rules from observations.

        Args:
            observations: All dimension style observations

        Returns:
            List of learned dimension style rules
        """
        if not observations:
            return []

        # Group by source (property:old_value)
        grouped = self._group_observations_by_source(observations)

        rules = []
        for source_pattern, obs_list in grouped.items():
            rule = self.scorer.create_rule_from_observations(
                rule_type=self.get_rule_type(),
                source_pattern=source_pattern,
                observations=obs_list,
                min_confidence=self.min_confidence,
            )

            if rule:
                rules.append(rule)

        return rules

    def _extract_dimension_properties(self, drawing: ParsedDrawing) -> Dict[str, Any]:
        """
        Extract common dimension properties from drawing.

        Args:
            drawing: Parsed drawing

        Returns:
            Dictionary of property -> most_common_value
        """
        property_values: Dict[str, List[Any]] = {prop: [] for prop in self.DIMENSION_PROPERTIES}

        # Search all layers for dimension entities
        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])

            for entity in entities:
                entity_type = self._get_entity_type(entity)

                if entity_type.startswith("DIM") or entity_type == "DIMENSION":
                    # Extract properties from this dimension
                    for prop_name in self.DIMENSION_PROPERTIES:
                        value = self._get_entity_property(entity, prop_name)
                        if value is not None:
                            property_values[prop_name].append(value)

        # Find most common value for each property
        result = {}
        for prop_name, values in property_values.items():
            if values:
                # Use most common value
                from collections import Counter
                most_common = Counter(values).most_common(1)[0][0]
                result[prop_name] = most_common

        return result

    def _get_entity_type(self, entity) -> str:
        """Extract entity type."""
        if isinstance(entity, dict):
            return entity.get("type", "UNKNOWN")
        return str(type(entity).__name__)

    def _get_entity_property(self, entity, property_name: str) -> Any:
        """Extract property value from entity."""
        if isinstance(entity, dict):
            return entity.get(property_name)

        # For ezdxf objects
        return getattr(entity, property_name, None)
