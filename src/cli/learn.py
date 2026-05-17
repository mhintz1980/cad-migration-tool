"""
Learning CLI commands.

Commands for standards learning from sample CAD file pairs.
"""

from pathlib import Path
from datetime import datetime
import click
import yaml

from ..integration.learning.learning_engine import LearningEngine
from ..data.models.standards import StandardConfig
from .utils import (
    validate_file_exists,
    validate_directory_exists,
    collect_files,
    echo_success,
    echo_error,
    echo_warning,
    echo_info,
    handle_error,
    confirm_action,
)


@click.group(name="learn")
def learn_group():
    """Standards learning commands."""
    pass


@learn_group.command(name="run")
@click.argument("old_samples", type=click.Path(exists=True, path_type=Path))
@click.argument("new_samples", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("config/learned-standards.yaml"),
    help="Output YAML file for learned standards",
)
@click.option(
    "--min-confidence",
    default=0.7,
    type=float,
    help="Minimum confidence threshold (0.0-1.0)",
)
@click.option(
    "--pattern",
    default="*.dxf",
    help="File pattern to match",
)
@click.option(
    "--name",
    default="learned-standards",
    help="Name for learned standards configuration",
)
def run_learning(old_samples, new_samples, output, min_confidence, pattern, name):
    """Learn standards from old/new sample CAD file pairs."""
    try:
        # Validate paths
        old_samples = validate_directory_exists(old_samples)
        new_samples = validate_directory_exists(new_samples)

        # Collect files
        echo_info(f"Collecting old samples from {old_samples}...")
        old_files = collect_files(old_samples, pattern)

        echo_info(f"Collecting new samples from {new_samples}...")
        new_files = collect_files(new_samples, pattern)

        if not old_files:
            echo_error(f"No old sample files found matching '{pattern}'")
            return

        if not new_files:
            echo_error(f"No new sample files found matching '{pattern}'")
            return

        echo_info(f"Found {len(old_files)} old samples and {len(new_files)} new samples")

        # Validate sample counts match
        if len(old_files) != len(new_files):
            echo_warning(
                f"Sample count mismatch: {len(old_files)} old vs {len(new_files)} new"
            )
            if not confirm_action("Continue with unmatched samples?", default=False):
                echo_warning("Learning cancelled")
                return

        # Confirm
        echo_info(f"Standards name: {name}")
        echo_info(f"Min confidence: {min_confidence}")
        echo_info(f"Output: {output}")

        if not confirm_action("Start learning?", default=True):
            echo_warning("Learning cancelled")
            return

        # Run learning
        echo_info("Learning standards from samples...")
        engine = LearningEngine(min_confidence=min_confidence)
        standards_config, learning_result = engine.learn(
            old_files, new_files, standards_name=name
        )

        # Display results
        click.echo()
        echo_success(f"Learning complete!")
        echo_info(f"Total rules learned: {learning_result.total_rules}")
        echo_info(f"High confidence rules: {learning_result.get_high_confidence_count()}")
        echo_info(f"Low confidence rules: {learning_result.get_low_confidence_count()}")

        if learning_result.layer_rules:
            echo_info(f"Layer mappings: {len(learning_result.layer_rules)}")
        if learning_result.dimension_rules:
            echo_info(f"Dimension properties: {len(learning_result.dimension_rules)}")
        if learning_result.title_block_rules:
            echo_info(f"Title block mappings: {len(learning_result.title_block_rules)}")

        # Export to YAML
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            yaml.dump(standards_config.to_dict(), f, default_flow_style=False, indent=2)

        echo_success(f"Standards exported to {output}")

        # Show warnings
        if learning_result.warnings:
            click.echo()
            echo_warning(f"Warnings ({len(learning_result.warnings)}):")
            for warning in learning_result.warnings[:5]:  # Show first 5
                click.echo(f"  • {warning}")
            if len(learning_result.warnings) > 5:
                echo_info(f"  ... and {len(learning_result.warnings) - 5} more")

    except Exception as e:
        handle_error(e)


@learn_group.command(name="report")
@click.argument("old_samples", type=click.Path(exists=True, path_type=Path))
@click.argument("new_samples", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--min-confidence",
    default=0.7,
    type=float,
    help="Minimum confidence threshold",
)
@click.option(
    "--pattern",
    default="*.dxf",
    help="File pattern to match",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed rule information",
)
def learning_report(old_samples, new_samples, min_confidence, pattern, detailed):
    """Generate learning confidence report without saving."""
    try:
        # Validate paths
        old_samples = validate_directory_exists(old_samples)
        new_samples = validate_directory_exists(new_samples)

        # Collect files
        old_files = collect_files(old_samples, pattern)
        new_files = collect_files(new_samples, pattern)

        if not old_files or not new_files:
            echo_error("No sample files found")
            return

        # Run learning
        echo_info(f"Analyzing {len(old_files)} sample pairs...")
        engine = LearningEngine(min_confidence=min_confidence)
        _, learning_result = engine.learn(old_files, new_files)

        # Display report
        click.echo()
        click.echo("=" * 60)
        click.echo(f"Standards Learning Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo("=" * 60)
        click.echo()

        click.echo(f"Sample files analyzed: {len(old_files)}")
        click.echo(f"Minimum confidence threshold: {min_confidence}")
        click.echo()

        click.echo("Rule Summary:")
        click.echo(f"  Total rules: {learning_result.total_rules}")
        click.echo(f"  High confidence (≥{min_confidence}): {learning_result.get_high_confidence_count(min_confidence)}")
        click.echo(f"  Low confidence (<{min_confidence}): {learning_result.get_low_confidence_count(min_confidence)}")
        click.echo()

        # Layer rules
        if learning_result.layer_rules:
            click.echo(f"Layer Mapping Rules ({len(learning_result.layer_rules)}):")
            rules_to_show = learning_result.layer_rules if detailed else learning_result.layer_rules[:10]
            for rule in rules_to_show:
                confidence_color = "green" if rule.confidence >= min_confidence else "yellow"
                click.secho(
                    f"  {rule.source_pattern} → {rule.target_value} "
                    f"(confidence: {rule.confidence:.2f}, samples: {rule.sample_count})",
                    fg=confidence_color,
                )
            if len(learning_result.layer_rules) > 10 and not detailed:
                click.echo(f"  ... and {len(learning_result.layer_rules) - 10} more")
            click.echo()

        # Dimension rules
        if learning_result.dimension_rules:
            click.echo(f"Dimension Property Rules ({len(learning_result.dimension_rules)}):")
            rules_to_show = learning_result.dimension_rules if detailed else learning_result.dimension_rules[:10]
            for rule in rules_to_show:
                confidence_color = "green" if rule.confidence >= min_confidence else "yellow"
                click.secho(
                    f"  {rule.source_pattern} → {rule.target_value} "
                    f"(confidence: {rule.confidence:.2f})",
                    fg=confidence_color,
                )
            if len(learning_result.dimension_rules) > 10 and not detailed:
                click.echo(f"  ... and {len(learning_result.dimension_rules) - 10} more")
            click.echo()

        # Title block rules
        if learning_result.title_block_rules:
            click.echo(f"Title Block Field Rules ({len(learning_result.title_block_rules)}):")
            rules_to_show = learning_result.title_block_rules if detailed else learning_result.title_block_rules[:10]
            for rule in rules_to_show:
                confidence_color = "green" if rule.confidence >= min_confidence else "yellow"
                click.secho(
                    f"  {rule.source_pattern} → {rule.target_value} "
                    f"(confidence: {rule.confidence:.2f})",
                    fg=confidence_color,
                )
            if len(learning_result.title_block_rules) > 10 and not detailed:
                click.echo(f"  ... and {len(learning_result.title_block_rules) - 10} more")
            click.echo()

        # Warnings
        if learning_result.warnings:
            echo_warning(f"Warnings ({len(learning_result.warnings)}):")
            for warning in learning_result.warnings[:5]:
                click.echo(f"  • {warning}")
            if len(learning_result.warnings) > 5:
                click.echo(f"  ... and {len(learning_result.warnings) - 5} more")

    except Exception as e:
        handle_error(e)


@learn_group.command(name="validate")
@click.argument("standards_file", type=click.Path(exists=True, path_type=Path))
def validate_standards(standards_file):
    """Validate learned standards configuration file."""
    try:
        standards_file = validate_file_exists(standards_file)

        echo_info(f"Validating standards file: {standards_file}")

        # Load and parse YAML
        with open(standards_file) as f:
            data = yaml.safe_load(f)

        # Try to create StandardConfig
        config = StandardConfig.from_dict(data)

        # Display summary
        click.echo()
        echo_success("Standards file is valid!")
        click.echo()
        click.echo(f"Name: {config.name}")
        click.echo(f"Version: {config.version}")
        click.echo(f"Drawing type: {config.drawing_type}")
        click.echo()

        if config.layer_standards:
            click.echo(f"Layer standards: {len(config.layer_standards)} defined")
        if config.dimension_standards:
            click.echo(f"Dimension standards: {len(config.dimension_standards)} defined")
        if config.text_standards:
            click.echo(f"Text standards: {len(config.text_standards)} defined")

        echo_success("Validation passed")

    except yaml.YAMLError as e:
        echo_error(f"YAML syntax error: {e}")
    except Exception as e:
        handle_error(e)
