"""
Validation CLI commands.

Commands for pre/post migration validation.
"""

from pathlib import Path
import click
import yaml

from ..core.validators.pre_migration_validator import PreMigrationValidator
from ..core.validators.post_migration_validator import PostMigrationValidator
from ..data.models.standards import StandardConfig
from ..core.parsers.dxf_parser import DXFParser
from .utils import (
    validate_file_exists,
    validate_directory_exists,
    collect_files,
    echo_success,
    echo_error,
    echo_warning,
    echo_info,
    handle_error,
)


@click.group(name="validate")
def validate_group():
    """Validation commands."""
    pass


@validate_group.command(name="pre")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--standards",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to standards configuration YAML",
)
@click.option(
    "--pattern",
    default="*.dxf",
    help="File pattern to match",
)
@click.option(
    "--stop-on-error",
    is_flag=True,
    help="Stop on first error",
)
def pre_validate(input_path, standards, pattern, stop_on_error):
    """Run pre-migration validation on CAD files."""
    try:
        # Validate paths
        input_path = Path(input_path)
        standards = validate_file_exists(standards)

        # Collect files
        echo_info(f"Collecting files matching '{pattern}'...")
        files = collect_files(input_path, pattern)

        if not files:
            echo_error(f"No files found matching '{pattern}' in {input_path}")
            return

        echo_info(f"Found {len(files)} files to validate")

        # Load standards
        with open(standards) as f:
            standards_data = yaml.safe_load(f)
        standards_config = StandardConfig.from_dict(standards_data)

        # Create validator
        validator = PreMigrationValidator(standards_config)
        parser = DXFParser()

        # Validate files
        total_errors = 0
        total_warnings = 0
        failed_files = []

        click.echo()
        for file_path in files:
            try:
                # Parse
                drawing = parser.parse(file_path)

                # Validate
                result = validator.validate(drawing)

                # Display result
                if result.is_valid:
                    echo_success(f"{file_path.name}: PASS")
                else:
                    echo_error(f"{file_path.name}: FAIL")
                    failed_files.append(file_path)

                if result.errors:
                    for error in result.errors:
                        click.secho(f"  ✗ {error.message}", fg="red")
                    total_errors += len(result.errors)

                if result.warnings:
                    for warning in result.warnings:
                        click.secho(f"  ⚠ {warning.message}", fg="yellow")
                    total_warnings += len(result.warnings)

                if not result.is_valid and stop_on_error:
                    echo_warning("Stopping due to --stop-on-error")
                    break

            except Exception as e:
                echo_error(f"{file_path.name}: ERROR - {e}")
                failed_files.append(file_path)
                if stop_on_error:
                    break

        # Summary
        click.echo()
        click.echo("=" * 60)
        click.echo("Pre-Migration Validation Summary")
        click.echo("=" * 60)
        click.echo(f"Total files: {len(files)}")
        click.echo(f"Passed: {len(files) - len(failed_files)}")
        click.echo(f"Failed: {len(failed_files)}")
        click.echo(f"Total errors: {total_errors}")
        click.echo(f"Total warnings: {total_warnings}")

        if failed_files:
            click.echo()
            echo_warning("Failed files:")
            for file_path in failed_files:
                click.echo(f"  • {file_path}")

    except Exception as e:
        handle_error(e)


@validate_group.command(name="post")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--standards",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to standards configuration YAML",
)
@click.option(
    "--pattern",
    default="*.dxf",
    help="File pattern to match",
)
@click.option(
    "--stop-on-error",
    is_flag=True,
    help="Stop on first error",
)
def post_validate(input_path, standards, pattern, stop_on_error):
    """Run post-migration validation on CAD files."""
    try:
        # Validate paths
        input_path = Path(input_path)
        standards = validate_file_exists(standards)

        # Collect files
        echo_info(f"Collecting files matching '{pattern}'...")
        files = collect_files(input_path, pattern)

        if not files:
            echo_error(f"No files found matching '{pattern}' in {input_path}")
            return

        echo_info(f"Found {len(files)} files to validate")

        # Load standards
        with open(standards) as f:
            standards_data = yaml.safe_load(f)
        standards_config = StandardConfig.from_dict(standards_data)

        # Create validator
        validator = PostMigrationValidator(standards_config)
        parser = DXFParser()

        # Validate files
        total_errors = 0
        total_warnings = 0
        failed_files = []

        click.echo()
        for file_path in files:
            try:
                # Parse
                drawing = parser.parse(file_path)

                # Validate
                result = validator.validate(drawing)

                # Display result
                if result.is_valid:
                    echo_success(f"{file_path.name}: PASS")
                else:
                    echo_error(f"{file_path.name}: FAIL")
                    failed_files.append(file_path)

                if result.errors:
                    for error in result.errors:
                        click.secho(f"  ✗ {error.message}", fg="red")
                    total_errors += len(result.errors)

                if result.warnings:
                    for warning in result.warnings:
                        click.secho(f"  ⚠ {warning.message}", fg="yellow")
                    total_warnings += len(result.warnings)

                if not result.is_valid and stop_on_error:
                    echo_warning("Stopping due to --stop-on-error")
                    break

            except Exception as e:
                echo_error(f"{file_path.name}: ERROR - {e}")
                failed_files.append(file_path)
                if stop_on_error:
                    break

        # Summary
        click.echo()
        click.echo("=" * 60)
        click.echo("Post-Migration Validation Summary")
        click.echo("=" * 60)
        click.echo(f"Total files: {len(files)}")
        click.echo(f"Passed: {len(files) - len(failed_files)}")
        click.echo(f"Failed: {len(failed_files)}")
        click.echo(f"Total errors: {total_errors}")
        click.echo(f"Total warnings: {total_warnings}")

        if failed_files:
            click.echo()
            echo_warning("Failed files:")
            for file_path in failed_files:
                click.echo(f"  • {file_path}")

    except Exception as e:
        handle_error(e)


@validate_group.command(name="file")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--standards",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to standards configuration YAML",
)
@click.option(
    "--pre",
    "validation_type",
    flag_value="pre",
    default=True,
    help="Pre-migration validation (default)",
)
@click.option(
    "--post",
    "validation_type",
    flag_value="post",
    help="Post-migration validation",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information",
)
def validate_file(file_path, standards, validation_type, verbose):
    """Validate a single CAD file."""
    try:
        # Validate paths
        file_path = validate_file_exists(file_path)
        standards = validate_file_exists(standards)

        echo_info(f"Validating: {file_path}")
        echo_info(f"Type: {validation_type}-migration")

        # Load standards
        with open(standards) as f:
            standards_data = yaml.safe_load(f)
        standards_config = StandardConfig.from_dict(standards_data)

        # Create validator
        if validation_type == "pre":
            validator = PreMigrationValidator(standards_config)
        else:
            validator = PostMigrationValidator(standards_config)

        # Parse and validate
        parser = DXFParser()
        drawing = parser.parse(file_path)
        result = validator.validate(drawing)

        # Display result
        click.echo()
        if result.is_valid:
            echo_success("Validation PASSED")
        else:
            echo_error("Validation FAILED")

        click.echo()

        # Errors
        if result.errors:
            click.secho(f"Errors ({len(result.errors)}):", fg="red", bold=True)
            for i, error in enumerate(result.errors, 1):
                click.secho(f"  {i}. {error.message}", fg="red")
                if verbose and error.context:
                    for key, value in error.context.items():
                        click.echo(f"     {key}: {value}")
            click.echo()

        # Warnings
        if result.warnings:
            click.secho(f"Warnings ({len(result.warnings)}):", fg="yellow", bold=True)
            for i, warning in enumerate(result.warnings, 1):
                click.secho(f"  {i}. {warning.message}", fg="yellow")
                if verbose and warning.context:
                    for key, value in warning.context.items():
                        click.echo(f"     {key}: {value}")
            click.echo()

        # Info
        if result.info and verbose:
            click.secho(f"Info ({len(result.info)}):", fg="blue", bold=True)
            for i, info in enumerate(result.info, 1):
                click.secho(f"  {i}. {info.message}", fg="blue")
                if info.context:
                    for key, value in info.context.items():
                        click.echo(f"     {key}: {value}")

    except Exception as e:
        handle_error(e)
