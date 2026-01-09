"""
Learning engine orchestrator.

Coordinates all learners to extract a complete StandardConfig
from sample file pairs.
"""

from pathlib import Path
from typing import List, Optional
import logging

from ...core.parsers.dxf_parser import DXFParser
from ...data.models.standards import StandardConfig, LayerStandard, DimensionStandard
from .layer_learner import LayerLearner
from .dimension_learner import DimensionLearner
from .title_block_learner import TitleBlockLearner
from .models import LearningResult, LearnedRule

logger = logging.getLogger(__name__)


class LearningEngine:
    """Orchestrates standards learning from sample pairs."""

    def __init__(
        self,
        min_confidence: float = 0.7,
        min_samples: int = 2,
        parser: Optional[DXFParser] = None,
    ):
        """
        Initialize learning engine.

        Args:
            min_confidence: Minimum confidence threshold for rules
            min_samples: Minimum number of samples required
            parser: DXF parser (creates new if None)
        """
        self.min_confidence = min_confidence
        self.min_samples = min_samples
        self.parser = parser or DXFParser()

        # Initialize learners
        self.layer_learner = LayerLearner(min_confidence, min_samples)
        self.dimension_learner = DimensionLearner(min_confidence, min_samples)
        self.title_block_learner = TitleBlockLearner(min_confidence, min_samples)

    def learn(
        self,
        old_samples: List[Path],
        new_samples: List[Path],
        standards_name: str = "learned-standards",
        standards_version: str = "1.0",
    ) -> tuple[StandardConfig, LearningResult]:
        """
        Learn standards from sample file pairs.

        Args:
            old_samples: List of old sample files
            new_samples: List of new sample files
            standards_name: Name for generated standards
            standards_version: Version for generated standards

        Returns:
            Tuple of (StandardConfig, LearningResult with aggregated info)
        """
        if len(old_samples) != len(new_samples):
            raise ValueError(
                f"Mismatched sample counts: {len(old_samples)} old vs {len(new_samples)} new"
            )

        logger.info(
            f"Learning standards from {len(old_samples)} sample pairs "
            f"(min_confidence: {self.min_confidence})"
        )

        # Parse all samples
        old_drawings = []
        new_drawings = []
        file_pairs = []
        parse_errors = []

        for old_file, new_file in zip(old_samples, new_samples):
            try:
                # Parse old sample
                if not self.parser.can_parse(old_file):
                    raise ValueError(f"Cannot parse old file: {old_file}")
                old_drawing = self.parser.parse(old_file)

                # Parse new sample
                if not self.parser.can_parse(new_file):
                    raise ValueError(f"Cannot parse new file: {new_file}")
                new_drawing = self.parser.parse(new_file)

                old_drawings.append(old_drawing)
                new_drawings.append(new_drawing)
                file_pairs.append((old_file, new_file))

                logger.debug(f"Parsed pair: {old_file.name} + {new_file.name}")

            except Exception as e:
                logger.error(f"Failed to parse {old_file.name}: {e}")
                parse_errors.append((old_file, new_file, str(e)))

        if not old_drawings:
            raise ValueError("No sample pairs could be parsed successfully")

        logger.info(
            f"Successfully parsed {len(old_drawings)}/{len(old_samples)} sample pairs"
        )

        # Run all learners
        layer_result = self.layer_learner.learn(old_drawings, new_drawings, file_pairs)
        dimension_result = self.dimension_learner.learn(old_drawings, new_drawings, file_pairs)
        title_block_result = self.title_block_learner.learn(old_drawings, new_drawings, file_pairs)

        # Generate StandardConfig from learned rules
        standards = self._generate_standards(
            layer_result.rules,
            dimension_result.rules,
            title_block_result.rules,
            standards_name,
            standards_version,
        )

        # Aggregate learning results
        all_rules = layer_result.rules + dimension_result.rules + title_block_result.rules
        all_warnings = (
            layer_result.warnings + dimension_result.warnings + title_block_result.warnings
        )
        all_failed = layer_result.failed_pairs + dimension_result.failed_pairs + title_block_result.failed_pairs

        aggregated_result = LearningResult(
            rules=all_rules,
            sample_count=len(old_samples),
            successful_pairs=len(old_drawings),
            failed_pairs=all_failed,
            warnings=all_warnings,
            metadata={
                "standards_name": standards_name,
                "layer_rules": len(layer_result.rules),
                "dimension_rules": len(dimension_result.rules),
                "title_block_rules": len(title_block_result.rules),
            },
        )

        logger.info(
            f"Learning complete: {len(all_rules)} rules extracted, "
            f"{len(all_warnings)} warnings"
        )

        return standards, aggregated_result

    def _generate_standards(
        self,
        layer_rules: List[LearnedRule],
        dimension_rules: List[LearnedRule],
        title_block_rules: List[LearnedRule],
        name: str,
        version: str,
    ) -> StandardConfig:
        """
        Generate StandardConfig from learned rules.

        Args:
            layer_rules: Learned layer mapping rules
            dimension_rules: Learned dimension style rules
            title_block_rules: Learned title block mapping rules
            name: Standards name
            version: Standards version

        Returns:
            StandardConfig with learned standards
        """
        # Build layer mapping from rules
        layer_mapping = {}
        for rule in layer_rules:
            layer_mapping[rule.source_pattern] = rule.target_value

        # Build layer standards (placeholder - would need more logic)
        layer_standards = {}
        # Note: We'd need to extract layer properties (color, line_type, etc.)
        # from the new drawings. For now, just create standards for new layer names.
        unique_new_layers = set(rule.target_value for rule in layer_rules)
        for new_layer_name in unique_new_layers:
            layer_standards[new_layer_name] = LayerStandard(
                name=new_layer_name,
                color=7,  # Default values - would ideally learn from samples
                line_type="Continuous",
                line_weight=0.25,
                plot=True,
                description=f"Learned layer: {new_layer_name}",
            )

        # Build dimension standards from rules
        dimension_standards = {}
        dim_properties = {}
        for rule in dimension_rules:
            # Parse property:value from target
            if ":" in rule.target_value:
                prop_name, prop_value = rule.target_value.split(":", 1)
                try:
                    # Try to convert to appropriate type
                    if prop_name in ["arrow_size", "text_height", "text_offset", "extension_line_offset"]:
                        dim_properties[prop_name] = float(prop_value)
                    elif prop_name == "precision":
                        dim_properties[prop_name] = int(prop_value)
                    else:
                        dim_properties[prop_name] = prop_value
                except ValueError:
                    dim_properties[prop_name] = prop_value

        if dim_properties:
            dimension_standards["default"] = DimensionStandard(
                arrow_size=dim_properties.get("arrow_size", 0.18),
                text_height=dim_properties.get("text_height", 0.125),
                text_offset=dim_properties.get("text_offset", 0.09),
                extension_line_offset=dim_properties.get("extension_line_offset", 0.0625),
                precision=dim_properties.get("precision", 2),
                units=dim_properties.get("units", "mm"),
                layer="DIMENSIONS",  # Default
            )

        # Create StandardConfig
        standards = StandardConfig(
            name=name,
            version=version,
            description=f"Learned from {len(layer_rules)} sample pairs",
            layer_standards=layer_standards,
            layer_mapping=layer_mapping,
            dimension_standards=dimension_standards,
            # title_block and property_mappings would be populated similarly
        )

        logger.info(
            f"Generated StandardConfig: {len(layer_mapping)} layer mappings, "
            f"{len(layer_standards)} layer standards"
        )

        return standards
