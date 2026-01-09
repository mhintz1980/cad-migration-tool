"""
Worker function for parallel file processing.

This module contains the worker function that processes a single file.
Designed to be executed in a separate process via ProcessPoolExecutor.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for worker processing."""

    standards_config_path: Path
    profile: str
    enable_validation: bool = True
    enable_pre_validation: bool = True
    enable_post_validation: bool = True


@dataclass
class WorkerResult:
    """Result of processing a single file."""

    file_path: Path
    success: bool
    output_path: Path | None = None
    processing_time: float = 0.0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    changes: Dict[str, int] = field(default_factory=dict)
    validation_errors: int = 0
    validation_warnings: int = 0


def process_file(file_path: Path, config: WorkerConfig) -> WorkerResult:
    """
    Process a single CAD file.

    This function is designed to be called in a separate process.
    It should not share state with the parent process.

    Args:
        file_path: Path to CAD file
        config: Worker configuration

    Returns:
        WorkerResult with processing results
    """
    start_time = datetime.now()
    result = WorkerResult(file_path=file_path, success=False)

    try:
        # Import here to avoid issues with multiprocessing
        from ..core.parsers.dxf_parser import DXFParser
        from ..data.models.standards import StandardConfig
        from ..core.validators.pre_migration_validator import PreMigrationValidator
        from ..core.validators.post_migration_validator import PostMigrationValidator
        from ..core.transformers.layer_transformer import LayerTransformer
        from ..core.transformers.dimension_transformer import DimensionTransformer

        logger.info(f"Processing file: {file_path}")

        # Load standards
        standards = StandardConfig.load_from_file(config.standards_config_path)

        # Parse file
        parser = DXFParser()
        if not parser.can_parse(file_path):
            result.error = f"Parser cannot handle file type: {file_path.suffix}"
            return result

        drawing = parser.parse(file_path)
        logger.debug(f"Parsed {file_path}: {len(drawing.layers)} layers")

        # Pre-migration validation
        if config.enable_pre_validation:
            pre_validator = PreMigrationValidator(standards)
            pre_validation = pre_validator.validate(drawing)

            result.validation_errors += pre_validation.error_count
            result.validation_warnings += pre_validation.warning_count
            result.warnings.extend([str(issue) for issue in pre_validation.issues])

            if not pre_validation.is_valid:
                result.error = "Pre-migration validation failed"
                return result

        # Apply transformations
        layer_transformer = LayerTransformer(standards)
        layer_result = layer_transformer.transform(drawing)
        result.warnings.extend(layer_result.warnings)
        result.changes.update(layer_result.changes)

        if not layer_result.success:
            result.error = "Layer transformation failed"
            result.warnings.extend(layer_result.errors)
            return result

        dim_transformer = DimensionTransformer(standards)
        if dim_transformer.can_transform(drawing):
            dim_result = dim_transformer.transform(drawing)
            result.warnings.extend(dim_result.warnings)
            result.changes.update(dim_result.changes)

            if not dim_result.success:
                result.warnings.extend(dim_result.errors)

        # Post-migration validation
        if config.enable_post_validation:
            post_validator = PostMigrationValidator(standards)
            post_validation = post_validator.validate(drawing)

            result.validation_errors += post_validation.error_count
            result.validation_warnings += post_validation.warning_count
            result.warnings.extend([str(issue) for issue in post_validation.issues])

            if not post_validation.is_valid:
                result.error = "Post-migration validation failed"
                return result

        # Save transformed drawing
        output_path = file_path.parent / f"{file_path.stem}_migrated{file_path.suffix}"
        parser.save(drawing, output_path)
        result.output_path = output_path

        # Success!
        result.success = True
        logger.info(f"Successfully processed {file_path} -> {output_path}")

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        result.error = str(e)

    finally:
        # Calculate processing time
        end_time = datetime.now()
        result.processing_time = (end_time - start_time).total_seconds()

    return result
