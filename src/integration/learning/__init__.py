"""
Standards learning system.

Learns CAD standards from old/new sample pairs using rule-based extraction
with statistical confidence scoring.
"""

from .models import (
    Observation,
    LearnedRule,
    LearningResult,
    LayerMapping,
    DimensionStyleMapping,
    PropertyMapping,
)
from .confidence import ConfidenceScorer
from .base_learner import BaseLearner
from .layer_learner import LayerLearner
from .dimension_learner import DimensionLearner
from .title_block_learner import TitleBlockLearner
from .learning_engine import LearningEngine

__all__ = [
    "Observation",
    "LearnedRule",
    "LearningResult",
    "LayerMapping",
    "DimensionStyleMapping",
    "PropertyMapping",
    "ConfidenceScorer",
    "BaseLearner",
    "LayerLearner",
    "DimensionLearner",
    "TitleBlockLearner",
    "LearningEngine",
]
