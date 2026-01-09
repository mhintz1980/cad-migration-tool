"""
Integration tests for Phase 2A - Repository and Transformation layers.

Tests:
- Database initialization and schema
- Standards repository (YAML)
- Migration repository (SQLite)
- Layer transformer
- Dimension transformer
"""

import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.repositories.database import Database
from src.data.repositories.standards_repository import StandardsRepository
from src.data.repositories.migration_repository import MigrationRepository
from src.data.models.standards import (
    StandardConfig,
    LayerStandard,
    DimensionStandard,
)
from src.data.models.migration import Migration, MigrationItem, MigrationStatus
from src.core.parsers.base_parser import ParsedDrawing
from src.core.transformers.layer_transformer import LayerTransformer
from src.core.transformers.dimension_transformer import DimensionTransformer


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def test_database():
    """Test database initialization and operations."""
    print_section("Testing Database Layer")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        print(f"Creating database at: {db_path}")

        # Initialize database
        db = Database(db_path)

        # Check WAL mode
        with db.connection() as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()
            print(f"✓ Journal mode: {result[0]}")
            assert result[0] == "wal", "WAL mode not enabled"

        # Check foreign keys
        with db.connection() as conn:
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            print(f"✓ Foreign keys: {result[0]}")
            assert result[0] == 1, "Foreign keys not enabled"

        # Test checkpoint
        db.checkpoint()
        print("✓ Checkpoint successful")

        # Test schema version
        version = db.get_schema_version()
        print(f"✓ Schema version: {version}")

        print("\n✅ Database tests passed")


def test_standards_repository():
    """Test standards repository YAML operations."""
    print_section("Testing Standards Repository")

    with tempfile.TemporaryDirectory() as tmpdir:
        standards_dir = Path(tmpdir) / "standards"
        print(f"Standards directory: {standards_dir}")

        repo = StandardsRepository(standards_dir)

        # Create a sample standard
        config = StandardConfig(
            name="test_standard",
            version="1.0.0",
            description="Test standard for Phase 2A",
            drawing_type="electrical",
        )

        # Add layer standards
        config.layer_standards["CONSTRUCTION"] = LayerStandard(
            name="CONSTRUCTION",
            color=8,
            line_type="CONTINUOUS",
            line_weight=13,
            plot=False,
        )

        config.layer_standards["DIMENSIONS"] = LayerStandard(
            name="DIMENSIONS",
            color=3,
            line_type="CONTINUOUS",
            line_weight=18,
            plot=True,
        )

        # Add layer mapping
        config.layer_mapping = {"0": "CONSTRUCTION", "DIMS": "DIMENSIONS"}

        # Add dimension standard
        config.dimension_standards["default"] = DimensionStandard(
            arrow_size=2.5,
            text_height=2.5,
            text_offset=1.0,
            extension_line_offset=1.5,
            precision=2,
            units="mm",
            layer="DIMENSIONS",
        )

        print("\nCreated StandardConfig:")
        print(f"  Name: {config.name}")
        print(f"  Version: {config.version}")
        print(f"  Layers: {len(config.layer_standards)}")
        print(f"  Mappings: {len(config.layer_mapping)}")

        # Save to YAML
        repo.save(config)
        print(f"✓ Saved to YAML: {standards_dir / 'test_standard.yaml'}")

        # Verify file exists
        assert repo.exists("test_standard"), "Standard file not created"
        print("✓ File exists check passed")

        # Load back
        loaded = repo.get("test_standard")
        assert loaded is not None, "Failed to load standard"
        print("✓ Loaded from YAML")

        # Verify data integrity
        assert loaded.name == config.name
        assert loaded.version == config.version
        assert len(loaded.layer_standards) == len(config.layer_standards)
        assert len(loaded.layer_mapping) == len(config.layer_mapping)
        print("✓ Data integrity verified")

        # List standards
        standards = repo.list()
        print(f"✓ Listed {len(standards)} standards")

        # List by drawing type
        electrical = repo.list(drawing_type="electrical")
        assert len(electrical) == 1
        print("✓ Filter by drawing type works")

        # Get latest version
        latest = repo.get_latest("electrical")
        assert latest is not None
        assert latest.version == "1.0.0"
        print(f"✓ Get latest version: {latest.version}")

        # Create second version
        config2 = StandardConfig(
            name="test_standard_v2",
            version="2.0.0",
            description="Version 2",
            drawing_type="electrical",
        )
        repo.save(config2)

        latest = repo.get_latest("electrical")
        assert latest.version == "2.0.0"
        print(f"✓ Latest version updated: {latest.version}")

        print("\n✅ Standards repository tests passed")


def test_migration_repository():
    """Test migration repository SQLite operations."""
    print_section("Testing Migration Repository")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "migrations.db"
        print(f"Database path: {db_path}")

        db = Database(db_path)
        repo = MigrationRepository(db)

        # Check schema initialized
        assert db.table_exists("migrations")
        assert db.table_exists("migration_items")
        print("✓ Schema tables created")

        # Create a migration
        migration = Migration(
            migration_id="test_migration_001",
            profile="electrical_profile",
            standards_version="1.0.0",
            enable_rollback=True,
            parallel_workers=4,
        )

        print("\nCreated Migration:")
        print(f"  ID: {migration.migration_id}")
        print(f"  Profile: {migration.profile}")
        print(f"  Workers: {migration.parallel_workers}")

        # Add some items
        for i in range(5):
            item = MigrationItem(
                file_path=Path(f"/test/drawing_{i}.dxf"),
                migration_id=migration.migration_id,
                status=MigrationStatus.PENDING,
            )
            migration.add_item(item)

        print(f"✓ Added {len(migration.items)} items")

        # Save to database
        repo.save(migration)
        print("✓ Saved to SQLite")

        # Verify exists
        assert repo.exists(migration.migration_id)
        print("✓ Exists check passed")

        # Load back
        loaded = repo.get(migration.migration_id)
        assert loaded is not None
        assert len(loaded.items) == 5
        print(f"✓ Loaded migration with {len(loaded.items)} items")

        # Update status
        repo.update_status(migration.migration_id, MigrationStatus.COMPLETED)
        loaded = repo.get(migration.migration_id)
        assert loaded.status == MigrationStatus.COMPLETED
        print("✓ Status update works")

        # Update item status
        repo.update_item_status(
            migration.migration_id,
            Path("/test/drawing_0.dxf"),
            MigrationStatus.COMPLETED,
        )
        loaded = repo.get(migration.migration_id)
        assert loaded.items[0].status == MigrationStatus.COMPLETED
        print("✓ Item status update works")

        # Get pending files
        pending = repo.get_pending_files(migration.migration_id)
        assert len(pending) == 4  # 1 completed, 4 pending
        print(f"✓ Get pending files: {len(pending)}")

        # List migrations
        migrations = repo.list()
        assert len(migrations) == 1
        print(f"✓ List migrations: {len(migrations)}")

        # Filter by profile
        electrical = repo.list(profile="electrical_profile")
        assert len(electrical) == 1
        print("✓ Filter by profile works")

        # Get stats
        stats = repo.get_stats()
        print(f"✓ Stats retrieved: {stats}")

        # Test checkpoint
        db.checkpoint()
        print("✓ Database checkpoint successful")

        print("\n✅ Migration repository tests passed")


def test_transformers():
    """Test layer and dimension transformers."""
    print_section("Testing Transformation Pipeline")

    # Create sample standard
    config = StandardConfig(
        name="test_transform",
        version="1.0.0",
        description="Transform test",
    )

    # Layer standards
    config.layer_standards["CONSTRUCTION"] = LayerStandard(
        name="CONSTRUCTION", color=8, line_type="CONTINUOUS", line_weight=13
    )
    config.layer_standards["DIMENSIONS"] = LayerStandard(
        name="DIMENSIONS", color=3, line_type="CONTINUOUS", line_weight=18
    )

    # Layer mapping
    config.layer_mapping = {"0": "CONSTRUCTION", "DIMS": "DIMENSIONS"}

    # Dimension standard
    config.dimension_standards["default"] = DimensionStandard(
        arrow_size=2.5,
        text_height=2.5,
        text_offset=1.0,
        extension_line_offset=1.5,
        layer="DIMENSIONS",
    )

    print("\nCreated StandardConfig for transformation")
    print(f"  Layer standards: {len(config.layer_standards)}")
    print(f"  Layer mappings: {len(config.layer_mapping)}")

    # Create sample drawing with entities
    dummy_entity_1 = {"type": "LINE", "layer": "0"}
    dummy_entity_2 = {"type": "DIMENSION", "layer": "DIMS"}

    drawing = ParsedDrawing(
        file_path=Path("/test/sample.dxf"),
        file_type="DXF",
        layers={
            "0": {
                "color": 7,
                "line_type": "CONTINUOUS",
                "entities": [dummy_entity_1],
            },
            "DIMS": {
                "color": 1,
                "line_type": "CONTINUOUS",
                "entities": [dummy_entity_2],
            },
        },
        entities=[],
        blocks={},
        title_block={},
        attributes={},
        metadata={},
        raw_data=None,
    )

    print("\nCreated ParsedDrawing:")
    print(f"  Layers: {list(drawing.layers.keys())}")

    # Test Layer Transformer
    print("\n--- Testing Layer Transformer ---")
    layer_transformer = LayerTransformer(config)

    assert layer_transformer.can_transform(drawing)
    print("✓ Can transform check passed")

    # Validate before transform
    validation = layer_transformer.validate(drawing)
    print(f"✓ Validation completed: {len(validation.warnings)} warnings")
    for warning in validation.warnings:
        print(f"  Warning: {warning}")

    # Transform
    result = layer_transformer.transform(drawing)
    print(f"\n✓ Transformation completed")
    print(f"  Success: {result.success}")
    print(f"  Changes: {result.changes}")
    print(f"  Warnings: {len(result.warnings)}")
    print(f"  Errors: {len(result.errors)}")

    # Verify layer mapping applied
    assert "CONSTRUCTION" in drawing.layers
    assert "DIMENSIONS" in drawing.layers
    assert "0" not in drawing.layers or len(drawing.layers["0"]["entities"]) == 0
    print("✓ Layer mapping applied successfully")
    print(f"  Final layers: {list(drawing.layers.keys())}")

    # Test Dimension Transformer
    print("\n--- Testing Dimension Transformer ---")
    dim_transformer = DimensionTransformer(config)

    assert dim_transformer.can_transform(drawing)
    print("✓ Can transform check passed")

    # Transform (no dimensions in sample, but should not error)
    result = dim_transformer.transform(drawing)
    print(f"✓ Transformation completed")
    print(f"  Success: {result.success}")
    print(f"  Changes: {result.changes}")

    print("\n✅ Transformation pipeline tests passed")


def run_integration_test():
    """Full integration test combining all components."""
    print_section("Integration Test - Full Workflow")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print(f"Working directory: {tmpdir}")

        # Setup repositories
        db = Database(tmpdir / "migrations.db")
        standards_repo = StandardsRepository(tmpdir / "standards")
        migration_repo = MigrationRepository(db)
        print("✓ Repositories initialized")

        # Create and save standard
        config = StandardConfig(
            name="integration_test",
            version="1.0.0",
            description="Integration test standard",
        )
        config.layer_standards["CONSTRUCTION"] = LayerStandard(
            name="CONSTRUCTION", color=8, line_type="CONTINUOUS", line_weight=13
        )
        config.layer_mapping = {"0": "CONSTRUCTION"}

        standards_repo.save(config)
        print("✓ Standard saved to YAML")

        # Load standard back
        loaded_config = standards_repo.get("integration_test")
        assert loaded_config is not None
        print("✓ Standard loaded from YAML")

        # Create migration
        migration = Migration(
            migration_id="integration_001",
            profile="test_profile",
            standards_version="1.0.0",
        )

        item = MigrationItem(
            file_path=Path("/test/drawing.dxf"),
            migration_id=migration.migration_id,
        )
        migration.add_item(item)

        migration_repo.save(migration)
        print("✓ Migration saved to SQLite")

        # Load migration back
        loaded_migration = migration_repo.get("integration_001")
        assert loaded_migration is not None
        assert len(loaded_migration.items) == 1
        print("✓ Migration loaded from SQLite")

        # Create drawing and transform
        drawing = ParsedDrawing(
            file_path=Path("/test/drawing.dxf"),
            file_type="DXF",
            layers={"0": {"color": 7, "entities": []}},
            entities=[],
            blocks={},
            title_block={},
            attributes={},
            metadata={},
            raw_data=None,
        )

        transformer = LayerTransformer(loaded_config)
        result = transformer.transform(drawing)
        print(f"✓ Transformation applied: {result.changes}")

        # Update migration with results
        loaded_migration.items[0].status = MigrationStatus.COMPLETED
        loaded_migration.items[0].changes = result.changes
        migration_repo.save(loaded_migration)
        print("✓ Migration updated with transformation results")

        # Verify persistence
        final = migration_repo.get("integration_001")
        assert final.items[0].status == MigrationStatus.COMPLETED
        assert final.items[0].changes == result.changes
        print("✓ Results persisted correctly")

        print("\n✅ Integration test passed")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Phase 2A Integration Tests")
    print("  Repository Layer + Transformation Pipeline")
    print("=" * 60)

    try:
        test_database()
        test_standards_repository()
        test_migration_repository()
        test_transformers()
        run_integration_test()

        print("\n" + "=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 2A is working correctly!")
        print("\nComponents tested:")
        print("  ✓ Database (SQLite + WAL)")
        print("  ✓ Standards Repository (YAML)")
        print("  ✓ Migration Repository (SQLite)")
        print("  ✓ Layer Transformer")
        print("  ✓ Dimension Transformer")
        print("  ✓ Full integration workflow")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
