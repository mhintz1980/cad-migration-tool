"""
Migration CLI commands.

Commands for running batch migrations with parallel processing.
"""

from pathlib import Path
from datetime import datetime
import click

from ..orchestration.batch_processor import BatchProcessor, BatchConfig
from ..data.repositories.database import Database
from ..data.repositories.migration_repository import MigrationRepository
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


@click.group(name="migrate")
def migrate_group():
    """Migration commands for batch processing."""
    pass


@migrate_group.command(name="run")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--standards",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to standards configuration YAML",
)
@click.option(
    "--profile",
    "-p",
    default="default",
    help="Migration profile name",
)
@click.option(
    "--workers",
    "-w",
    default=4,
    type=int,
    help="Number of parallel workers",
)
@click.option(
    "--pattern",
    default="*.dxf",
    help="File pattern to match",
)
@click.option(
    "--no-validation",
    is_flag=True,
    help="Skip validation",
)
@click.option(
    "--no-rollback",
    is_flag=True,
    help="Disable rollback support",
)
@click.option(
    "--max-failures",
    default=50,
    type=int,
    help="Maximum failures before aborting",
)
@click.option(
    "--checkpoint-interval",
    default=10,
    type=int,
    help="Checkpoint every N files",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=Path("data/migrations.db"),
    help="Database path",
)
@click.option(
    "--backup-dir",
    type=click.Path(path_type=Path),
    default=Path("backups"),
    help="Backup directory",
)
def run_migration(
    input_path,
    standards,
    profile,
    workers,
    pattern,
    no_validation,
    no_rollback,
    max_failures,
    checkpoint_interval,
    db_path,
    backup_dir,
):
    """Run batch migration on CAD files."""
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

        echo_info(f"Found {len(files)} files to process")

        # Generate migration ID
        migration_id = f"migration-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Configure batch processor
        config = BatchConfig(
            standards_config_path=standards,
            profile=profile,
            migration_id=migration_id,
            parallel_workers=workers,
            enable_validation=not no_validation,
            enable_pre_validation=not no_validation,
            enable_post_validation=not no_validation,
            enable_rollback=not no_rollback,
            max_failures=max_failures,
            checkpoint_interval=checkpoint_interval,
            db_path=db_path,
            backup_dir=backup_dir,
        )

        # Confirm
        echo_info(f"Migration ID: {migration_id}")
        echo_info(f"Workers: {workers}")
        echo_info(f"Validation: {'disabled' if no_validation else 'enabled'}")
        echo_info(f"Rollback: {'disabled' if no_rollback else 'enabled'}")

        if not confirm_action("Start migration?", default=True):
            echo_warning("Migration cancelled")
            return

        # Run migration
        processor = BatchProcessor(config)
        stats = processor.process_batch(files, resume=False, live_progress=True)

        # Display results
        click.echo()
        if stats["failed"] == 0:
            echo_success(
                f"Migration complete: {stats['successful']}/{stats['total']} files successful"
            )
        elif stats["successful"] > 0:
            echo_warning(
                f"Migration completed with errors: {stats['successful']}/{stats['total']} successful, "
                f"{stats['failed']} failed"
            )
        else:
            echo_error(f"Migration failed: {stats['failed']}/{stats['total']} files failed")

        echo_info(f"Processing time: {stats['processing_time']:.1f}s")
        echo_info(f"Success rate: {stats['success_rate']:.1%}")

    except Exception as e:
        handle_error(e)


@migrate_group.command(name="resume")
@click.argument("migration_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=Path("data/migrations.db"),
    help="Database path",
)
def resume_migration(migration_id, db_path):
    """Resume interrupted migration."""
    try:
        # Load migration from database
        db = Database(db_path)
        repo = MigrationRepository(db)
        migration = repo.get(migration_id)

        if not migration:
            echo_error(f"Migration not found: {migration_id}")
            return

        echo_info(f"Resuming migration: {migration_id}")
        echo_info(f"Profile: {migration.profile}")

        stats = repo.get_migration_stats(migration_id)
        echo_info(
            f"Progress: {stats['successful']}/{stats['total']} completed, "
            f"{stats['pending']} pending"
        )

        if stats["pending"] == 0:
            echo_warning("No pending files to process")
            return

        if not confirm_action(f"Resume with {stats['pending']} pending files?"):
            echo_warning("Resume cancelled")
            return

        # Create processor config from migration
        config = BatchConfig(
            standards_config_path=Path("config/standards.yaml"),  # TODO: Store in migration
            profile=migration.profile,
            migration_id=migration_id,
            parallel_workers=migration.parallel_workers,
            enable_rollback=migration.enable_rollback,
            db_path=db_path,
        )

        # Resume
        processor = BatchProcessor(config)
        stats = processor.process_batch([], resume=True, live_progress=True)

        # Display results
        click.echo()
        echo_success(f"Resume complete: {stats['successful']} additional files processed")

    except Exception as e:
        handle_error(e)


@migrate_group.command(name="status")
@click.argument("migration_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=Path("data/migrations.db"),
    help="Database path",
)
def migration_status(migration_id, db_path):
    """Check migration status."""
    try:
        db = Database(db_path)
        repo = MigrationRepository(db)
        migration = repo.get(migration_id)

        if not migration:
            echo_error(f"Migration not found: {migration_id}")
            return

        # Display status
        click.echo()
        click.echo(f"Migration: {migration.migration_id}")
        click.echo(f"Profile: {migration.profile}")
        click.echo(f"Status: {migration.status.value}")
        click.echo(f"Started: {migration.started_at}")
        click.echo(f"Completed: {migration.completed_at or 'In progress'}")
        click.echo()

        stats = repo.get_migration_stats(migration_id)
        click.echo(f"Total files: {stats['total']}")
        click.echo(f"Successful: {stats['successful']}")
        click.echo(f"Failed: {stats['failed']}")
        click.echo(f"Pending: {stats['pending']}")
        click.echo(f"Success rate: {stats['success_rate']:.1%}")

    except Exception as e:
        handle_error(e)


@migrate_group.command(name="rollback")
@click.argument("migration_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=Path("data/migrations.db"),
    help="Database path",
)
@click.option(
    "--backup-dir",
    type=click.Path(path_type=Path),
    default=Path("backups"),
    help="Backup directory",
)
def rollback_migration(migration_id, db_path, backup_dir):
    """Rollback migration."""
    try:
        db = Database(db_path)
        repo = MigrationRepository(db)
        migration = repo.get(migration_id)

        if not migration:
            echo_error(f"Migration not found: {migration_id}")
            return

        if not migration.enable_rollback:
            echo_error("Rollback not enabled for this migration")
            return

        stats = repo.get_migration_stats(migration_id)
        echo_warning(
            f"This will restore {stats['successful']} files from backup"
        )

        if not confirm_action("Rollback migration?", default=False):
            echo_warning("Rollback cancelled")
            return

        # Rollback
        config = BatchConfig(
            standards_config_path=Path("config/standards.yaml"),
            profile=migration.profile,
            migration_id=migration_id,
            db_path=db_path,
            backup_dir=backup_dir,
        )

        processor = BatchProcessor(config)
        result = processor.rollback()

        # Display results
        click.echo()
        if result["failed_count"] == 0:
            echo_success(f"Rollback complete: {result['restored_count']} files restored")
        else:
            echo_warning(
                f"Rollback partial: {result['restored_count']} restored, "
                f"{result['failed_count']} failed"
            )

    except Exception as e:
        handle_error(e)


@migrate_group.command(name="list")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=Path("data/migrations.db"),
    help="Database path",
)
@click.option(
    "--limit",
    "-n",
    default=20,
    type=int,
    help="Maximum migrations to list",
)
def list_migrations(db_path, limit):
    """List recent migrations."""
    try:
        db = Database(db_path)
        repo = MigrationRepository(db)
        migrations = repo.list(limit=limit)

        if not migrations:
            echo_info("No migrations found")
            return

        click.echo()
        click.echo(f"{'ID':<30} {'Status':<12} {'Files':<15} {'Success Rate':<15} {'Started'}")
        click.echo("-" * 100)

        for migration in migrations:
            stats = repo.get_migration_stats(migration.migration_id)
            click.echo(
                f"{migration.migration_id:<30} "
                f"{migration.status.value:<12} "
                f"{stats['successful']}/{stats['total']:<12} "
                f"{stats['success_rate']:.1%}            "
                f"{migration.started_at}"
            )

    except Exception as e:
        handle_error(e)
