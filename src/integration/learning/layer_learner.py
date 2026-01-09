"""
Layer mapping learner.

Learns layer name mappings from old/new sample pairs by comparing
entity content and layer properties.
"""

from pathlib import Path
from typing import List, Dict, Set
import logging

from ...core.parsers.base_parser import ParsedDrawing
from .base_learner import BaseLearner
from .models import Observation, LearnedRule

logger = logging.getLogger(__name__)


class LayerLearner(BaseLearner):
    """Learns layer name mappings from sample pairs."""

    def get_rule_type(self) -> str:
        """Rule type for layer mappings."""
        return "layer_mapping"

    def extract_observations(
        self, old_drawing: ParsedDrawing, new_drawing: ParsedDrawing, file_pair: tuple[Path, Path]
    ) -> List[Observation]:
        """
        Extract layer mapping observations by comparing entity content.

        Strategy:
        1. For each old layer, find new layer with most similar entity content
        2. Use entity type distribution as similarity metric
        3. Record observation of (old_layer_name, new_layer_name)

        Args:
            old_drawing: Parsed old drawing
            new_drawing: Parsed new drawing
            file_pair: (old_file, new_file)

        Returns:
            List of observations
        """
        observations = []

        # Build entity type signatures for each layer
        old_signatures = self._build_layer_signatures(old_drawing)
        new_signatures = self._build_layer_signatures(new_drawing)

        # For each old layer, find best matching new layer
        for old_layer_name, old_signature in old_signatures.items():
            best_match = self._find_best_match(old_signature, new_signatures)

            if best_match:
                new_layer_name, similarity = best_match

                # Only create observation if similarity is reasonable
                if similarity > 0.3:  # At least 30% similarity
                    obs = Observation(
                        source=old_layer_name,
                        target=new_layer_name,
                        file_pair=file_pair,
                        context={
                            "similarity": similarity,
                            "old_entity_count": old_signature["entity_count"],
                            "new_entity_count": new_signatures[new_layer_name]["entity_count"],
                        },
                    )
                    observations.append(obs)

                    logger.debug(
                        f"Layer mapping: '{old_layer_name}' -> '{new_layer_name}' "
                        f"(similarity: {similarity:.2f})"
                    )

        return observations

    def create_rules(self, observations: List[Observation]) -> List[LearnedRule]:
        """
        Create layer mapping rules from observations.

        Groups observations by source layer and calculates confidence.

        Args:
            observations: All layer mapping observations

        Returns:
            List of learned layer mapping rules
        """
        if not observations:
            return []

        # Group by source layer
        grouped = self._group_observations_by_source(observations)

        rules = []
        for source_layer, obs_list in grouped.items():
            rule = self.scorer.create_rule_from_observations(
                rule_type=self.get_rule_type(),
                source_pattern=source_layer,
                observations=obs_list,
                min_confidence=self.min_confidence,
            )

            if rule:
                rules.append(rule)

        return rules

    def _build_layer_signatures(self, drawing: ParsedDrawing) -> Dict[str, Dict]:
        """
        Build entity type signature for each layer.

        Args:
            drawing: Parsed drawing

        Returns:
            Dictionary mapping layer_name to signature dict with:
            - entity_types: Set of entity types
            - entity_count: Total entity count
            - type_counts: Dict of entity_type -> count
        """
        signatures = {}

        for layer_name, layer_data in drawing.layers.items():
            entities = layer_data.get("entities", [])

            # Extract entity types
            type_counts: Dict[str, int] = {}
            for entity in entities:
                entity_type = self._get_entity_type(entity)
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

            signatures[layer_name] = {
                "entity_types": set(type_counts.keys()),
                "entity_count": len(entities),
                "type_counts": type_counts,
            }

        return signatures

    def _find_best_match(
        self, old_signature: Dict, new_signatures: Dict[str, Dict]
    ) -> tuple[str, float] | None:
        """
        Find new layer with best matching signature.

        Uses Jaccard similarity on entity types:
        similarity = |intersection| / |union|

        Args:
            old_signature: Signature of old layer
            new_signatures: All new layer signatures

        Returns:
            (best_layer_name, similarity_score) or None
        """
        best_match = None
        best_similarity = 0.0

        old_types = old_signature["entity_types"]

        for new_layer_name, new_signature in new_signatures.items():
            new_types = new_signature["entity_types"]

            # Calculate Jaccard similarity
            if not old_types and not new_types:
                # Both empty
                similarity = 1.0
            elif not old_types or not new_types:
                # One empty
                similarity = 0.0
            else:
                intersection = old_types & new_types
                union = old_types | new_types
                similarity = len(intersection) / len(union) if union else 0.0

            # Penalize large entity count differences
            count_ratio = min(
                old_signature["entity_count"], new_signature["entity_count"]
            ) / max(old_signature["entity_count"], new_signature["entity_count"])
            if old_signature["entity_count"] > 0 and new_signature["entity_count"] > 0:
                similarity *= (0.5 + 0.5 * count_ratio)  # Weighted by count similarity

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = (new_layer_name, similarity)

        return best_match

    def _get_entity_type(self, entity) -> str:
        """
        Extract entity type string.

        Args:
            entity: Entity (dict or object)

        Returns:
            Entity type string
        """
        if isinstance(entity, dict):
            return entity.get("type", "UNKNOWN")
        return str(type(entity).__name__)
