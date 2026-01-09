"""
Abstract base class for standards learners.

Defines the interface that all specific learners must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import logging

from ...core.parsers.base_parser import ParsedDrawing
from .models import Observation, LearnedRule, LearningResult
from .confidence import ConfidenceScorer

logger = logging.getLogger(__name__)


class BaseLearner(ABC):
    """Abstract base class for standards learners."""

    def __init__(self, min_confidence: float = 0.7, min_samples: int = 2):
        """
        Initialize learner.

        Args:
            min_confidence: Minimum confidence threshold for rules
            min_samples: Minimum number of samples required
        """
        self.min_confidence = min_confidence
        self.min_samples = min_samples
        self.scorer = ConfidenceScorer(min_samples=min_samples)

    @abstractmethod
    def extract_observations(
        self, old_drawing: ParsedDrawing, new_drawing: ParsedDrawing, file_pair: tuple[Path, Path]
    ) -> List[Observation]:
        """
        Extract observations from a pair of drawings.

        Args:
            old_drawing: Parsed old drawing
            new_drawing: Parsed new drawing
            file_pair: (old_file_path, new_file_path)

        Returns:
            List of observations extracted from this pair
        """
        pass

    @abstractmethod
    def create_rules(self, observations: List[Observation]) -> List[LearnedRule]:
        """
        Create learned rules from observations.

        Args:
            observations: All observations collected

        Returns:
            List of learned rules with confidence scores
        """
        pass

    @abstractmethod
    def get_rule_type(self) -> str:
        """
        Get the type of rules this learner produces.

        Returns:
            Rule type string (e.g., "layer_mapping", "dimension_style")
        """
        pass

    def learn(
        self,
        old_drawings: List[ParsedDrawing],
        new_drawings: List[ParsedDrawing],
        file_pairs: List[tuple[Path, Path]],
    ) -> LearningResult:
        """
        Learn rules from sample pairs.

        Args:
            old_drawings: List of parsed old drawings
            new_drawings: List of parsed new drawings
            file_pairs: List of (old_file, new_file) tuples

        Returns:
            LearningResult with extracted rules
        """
        if len(old_drawings) != len(new_drawings) != len(file_pairs):
            raise ValueError("Mismatched lengths for drawings and file pairs")

        logger.info(
            f"{self.__class__.__name__}: Learning from {len(file_pairs)} sample pairs "
            f"(min_confidence: {self.min_confidence})"
        )

        # Extract observations from all pairs
        all_observations = []
        failed_pairs = []

        for old_drawing, new_drawing, file_pair in zip(old_drawings, new_drawings, file_pairs):
            try:
                observations = self.extract_observations(old_drawing, new_drawing, file_pair)
                all_observations.extend(observations)
                logger.debug(
                    f"Extracted {len(observations)} observations from {file_pair[0].name}"
                )
            except Exception as e:
                logger.error(f"Failed to extract observations from {file_pair[0].name}: {e}")
                failed_pairs.append((file_pair[0], file_pair[1], str(e)))

        logger.info(f"Total observations: {len(all_observations)}")

        # Create rules from observations
        try:
            rules = self.create_rules(all_observations)
            logger.info(f"Created {len(rules)} rules")
        except Exception as e:
            logger.error(f"Failed to create rules: {e}")
            rules = []

        # Filter by confidence
        high_confidence = [r for r in rules if r.confidence >= self.min_confidence]
        low_confidence = [r for r in rules if r.confidence < self.min_confidence]

        warnings = []
        if low_confidence:
            warnings.append(
                f"{len(low_confidence)} rules rejected due to low confidence "
                f"(<{self.min_confidence})"
            )

        logger.info(
            f"{self.__class__.__name__}: {len(high_confidence)}/{len(rules)} rules "
            f"passed confidence threshold"
        )

        return LearningResult(
            rules=high_confidence,
            sample_count=len(file_pairs),
            successful_pairs=len(file_pairs) - len(failed_pairs),
            failed_pairs=failed_pairs,
            warnings=warnings,
            metadata={
                "learner_type": self.get_rule_type(),
                "min_confidence": self.min_confidence,
                "total_observations": len(all_observations),
                "rejected_rules": len(low_confidence),
            },
        )

    def _group_observations_by_source(
        self, observations: List[Observation]
    ) -> dict[str, List[Observation]]:
        """
        Helper to group observations by source pattern.

        Args:
            observations: List of observations

        Returns:
            Dictionary mapping source to list of observations
        """
        return self.scorer.group_observations_by_source(observations)
