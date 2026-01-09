"""
Title block field learner.

Learns title block field mappings by comparing attribute tags
and field names across sample pairs.
"""

from pathlib import Path
from typing import List, Dict, Set
import logging

from ...core.parsers.base_parser import ParsedDrawing
from .base_learner import BaseLearner
from .models import Observation, LearnedRule

logger = logging.getLogger(__name__)


class TitleBlockLearner(BaseLearner):
    """Learns title block field mappings from sample pairs."""

    def get_rule_type(self) -> str:
        """Rule type for title block mappings."""
        return "title_block_mapping"

    def extract_observations(
        self, old_drawing: ParsedDrawing, new_drawing: ParsedDrawing, file_pair: tuple[Path, Path]
    ) -> List[Observation]:
        """
        Extract title block field mapping observations.

        Strategy:
        1. Compare title_block field names
        2. Use field similarity (edit distance, common words) to match
        3. Record field name mappings as observations

        Args:
            old_drawing: Parsed old drawing
            new_drawing: Parsed new drawing
            file_pair: (old_file, new_file)

        Returns:
            List of observations
        """
        observations = []

        old_fields = set(old_drawing.title_block.keys())
        new_fields = set(new_drawing.title_block.keys())

        # First check exact matches
        common_fields = old_fields & new_fields
        for field_name in common_fields:
            # Exact match - high confidence mapping
            obs = Observation(
                source=field_name,
                target=field_name,
                file_pair=file_pair,
                context={
                    "match_type": "exact",
                    "old_value": old_drawing.title_block.get(field_name),
                    "new_value": new_drawing.title_block.get(field_name),
                },
            )
            observations.append(obs)

        # Then find fuzzy matches for unmatched fields
        unmatched_old = old_fields - common_fields
        unmatched_new = new_fields - common_fields

        for old_field in unmatched_old:
            best_match = self._find_similar_field(old_field, unmatched_new)

            if best_match:
                new_field, similarity = best_match

                if similarity > 0.5:  # At least 50% similarity
                    obs = Observation(
                        source=old_field,
                        target=new_field,
                        file_pair=file_pair,
                        context={
                            "match_type": "fuzzy",
                            "similarity": similarity,
                            "old_value": old_drawing.title_block.get(old_field),
                            "new_value": new_drawing.title_block.get(new_field),
                        },
                    )
                    observations.append(obs)

                    logger.debug(
                        f"Title block mapping: '{old_field}' -> '{new_field}' "
                        f"(similarity: {similarity:.2f})"
                    )

        return observations

    def create_rules(self, observations: List[Observation]) -> List[LearnedRule]:
        """
        Create title block mapping rules from observations.

        Args:
            observations: All title block observations

        Returns:
            List of learned title block mapping rules
        """
        if not observations:
            return []

        # Group by source field
        grouped = self._group_observations_by_source(observations)

        rules = []
        for source_field, obs_list in grouped.items():
            rule = self.scorer.create_rule_from_observations(
                rule_type=self.get_rule_type(),
                source_pattern=source_field,
                observations=obs_list,
                min_confidence=self.min_confidence,
            )

            if rule:
                rules.append(rule)

        return rules

    def _find_similar_field(
        self, old_field: str, new_fields: Set[str]
    ) -> tuple[str, float] | None:
        """
        Find most similar new field name using string similarity.

        Uses combination of:
        - Levenshtein distance (edit distance)
        - Common words
        - Common prefixes/suffixes

        Args:
            old_field: Old field name
            new_fields: Set of new field names

        Returns:
            (best_match, similarity_score) or None
        """
        if not new_fields:
            return None

        best_match = None
        best_similarity = 0.0

        for new_field in new_fields:
            similarity = self._calculate_field_similarity(old_field, new_field)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = (new_field, similarity)

        return best_match

    def _calculate_field_similarity(self, field1: str, field2: str) -> float:
        """
        Calculate similarity between two field names.

        Uses simple normalized Levenshtein distance.

        Args:
            field1: First field name
            field2: Second field name

        Returns:
            Similarity score (0.0-1.0)
        """
        # Normalize to lowercase
        s1 = field1.lower()
        s2 = field2.lower()

        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(s1, s2)

        # Normalize to 0-1 range
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0

        similarity = 1.0 - (distance / max_len)

        # Bonus for exact word matches
        words1 = set(s1.replace("_", " ").split())
        words2 = set(s2.replace("_", " ").split())
        if words1 & words2:
            # Common words boost similarity
            word_overlap = len(words1 & words2) / max(len(words1), len(words2))
            similarity = similarity * 0.7 + word_overlap * 0.3

        return similarity

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein (edit) distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]

            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)

                current_row.append(min(insertions, deletions, substitutions))

            previous_row = current_row

        return previous_row[-1]
