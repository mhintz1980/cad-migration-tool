"""
Confidence scoring for learned rules.

Implements statistical confidence calculation based on sample agreement.
"""

from typing import List, Dict, Any
from collections import Counter
import logging

from .models import Observation, LearnedRule

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates confidence scores for learned rules."""

    def __init__(self, min_samples: int = 2):
        """
        Initialize confidence scorer.

        Args:
            min_samples: Minimum number of samples required for a rule
        """
        self.min_samples = min_samples

    def calculate_confidence(self, observations: List[Observation]) -> float:
        """
        Calculate confidence score for observations.

        Formula: confidence = (majority_count / total_count) * consistency_factor

        Where consistency_factor penalizes contradictory mappings:
        - All samples agree: 1.0
        - 80%+ agree: 0.9
        - 60-80% agree: 0.7
        - Below 60%: low confidence

        Args:
            observations: List of observations for the same source pattern

        Returns:
            Confidence score (0.0-1.0)
        """
        if not observations:
            return 0.0

        if len(observations) < self.min_samples:
            logger.warning(f"Only {len(observations)} samples, minimum {self.min_samples} required")
            return 0.0

        # Count target values
        target_counts = Counter(obs.target for obs in observations)
        most_common_target, majority_count = target_counts.most_common(1)[0]
        total_count = len(observations)

        # Base confidence = agreement ratio
        agreement_ratio = majority_count / total_count

        # Apply consistency factor
        if agreement_ratio == 1.0:
            # Perfect agreement
            consistency_factor = 1.0
        elif agreement_ratio >= 0.8:
            # Strong agreement (80%+)
            consistency_factor = 0.9
        elif agreement_ratio >= 0.6:
            # Moderate agreement (60-80%)
            consistency_factor = 0.7
        else:
            # Weak agreement (<60%)
            consistency_factor = 0.5

        confidence = agreement_ratio * consistency_factor

        logger.debug(
            f"Confidence: {confidence:.2f} (agreement: {majority_count}/{total_count}, "
            f"factor: {consistency_factor})"
        )

        return confidence

    def create_rule_from_observations(
        self,
        rule_type: str,
        source_pattern: str,
        observations: List[Observation],
        min_confidence: float = 0.0,
    ) -> LearnedRule | None:
        """
        Create a learned rule from observations.

        Args:
            rule_type: Type of rule
            source_pattern: Source pattern being mapped
            observations: Observations for this pattern
            min_confidence: Minimum confidence threshold

        Returns:
            LearnedRule if confidence >= threshold, None otherwise
        """
        if not observations:
            return None

        # Calculate confidence
        confidence = self.calculate_confidence(observations)

        if confidence < min_confidence:
            logger.debug(
                f"Rule rejected: confidence {confidence:.2f} < threshold {min_confidence}"
            )
            return None

        # Find majority target value
        target_counts = Counter(obs.target for obs in observations)
        target_value, _ = target_counts.most_common(1)[0]

        # Find exceptions (observations that disagree)
        exceptions = [
            str(obs.file_pair[0].name)
            for obs in observations
            if obs.target != target_value
        ]

        return LearnedRule(
            rule_type=rule_type,
            source_pattern=source_pattern,
            target_value=target_value,
            confidence=confidence,
            sample_count=len(observations),
            observations=observations,
            exceptions=exceptions,
        )

    def group_observations_by_source(
        self, observations: List[Observation]
    ) -> Dict[str, List[Observation]]:
        """
        Group observations by source pattern.

        Args:
            observations: List of all observations

        Returns:
            Dictionary mapping source pattern to list of observations
        """
        grouped: Dict[str, List[Observation]] = {}

        for obs in observations:
            if obs.source not in grouped:
                grouped[obs.source] = []
            grouped[obs.source].append(obs)

        return grouped

    def filter_high_confidence_rules(
        self, rules: List[LearnedRule], threshold: float = 0.8
    ) -> List[LearnedRule]:
        """
        Filter rules by confidence threshold.

        Args:
            rules: List of learned rules
            threshold: Minimum confidence threshold

        Returns:
            Rules with confidence >= threshold
        """
        return [rule for rule in rules if rule.confidence >= threshold]

    def detect_conflicts(self, rules: List[LearnedRule]) -> List[tuple[LearnedRule, LearnedRule]]:
        """
        Detect conflicting rules (same source, different targets).

        Args:
            rules: List of learned rules

        Returns:
            List of conflicting rule pairs
        """
        conflicts = []

        # Group by rule_type and source_pattern
        by_source: Dict[tuple[str, str], List[LearnedRule]] = {}

        for rule in rules:
            key = (rule.rule_type, rule.source_pattern)
            if key not in by_source:
                by_source[key] = []
            by_source[key].append(rule)

        # Find conflicts
        for key, rule_list in by_source.items():
            if len(rule_list) > 1:
                # Multiple rules for same source
                target_values = set(rule.target_value for rule in rule_list)
                if len(target_values) > 1:
                    # Different targets = conflict
                    for i in range(len(rule_list)):
                        for j in range(i + 1, len(rule_list)):
                            conflicts.append((rule_list[i], rule_list[j]))

        return conflicts
