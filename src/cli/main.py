"""
Main CLI entry point.

Combines all command groups into a single CLI application.
"""

import click
from pathlib import Path

from .migrate import migrate_group
from .learn import learn_group
from .pdm import pdm_group
from .validate import validate_group


@click.group()
@click.version_option(version="0.1.0", prog_name="cad-migration")
@click.pass_context
def cli(ctx):
    """
    CAD Migration Automation Tool.

    A comprehensive tool for automating CAD drawing migrations with:
    - Batch migration with parallel processing
    - Standards learning from sample files
    - PDM vault integration
    - Pre/post migration validation
    - Rollback support and crash recovery

    Examples:
        # Run batch migration
        cad-migration migrate run ./drawings -s config/standards.yaml

        # Learn standards from samples
        cad-migration learn run ./old_samples ./new_samples

        # Validate drawings
        cad-migration validate pre ./drawings -s config/standards.yaml

        # PDM operations
        cad-migration pdm connect --vault-name MyVault

    For command-specific help:
        cad-migration <command> --help
    """
    ctx.ensure_object(dict)


# Register command groups
cli.add_command(migrate_group)
cli.add_command(learn_group)
cli.add_command(pdm_group)
cli.add_command(validate_group)


if __name__ == "__main__":
    cli()
