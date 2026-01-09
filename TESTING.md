# Testing the CAD Migration Tool

This guide will walk you through testing all features of the CAD migration tool.

## Prerequisites

```bash
# Install dependencies (if not already installed)
pip install ezdxf click rich pyyaml sqlalchemy

# Or create a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install ezdxf click rich pyyaml sqlalchemy
```

## Quick Start - 5 Minute Test

### 1. Create Sample Files

```bash
# Create sample DXF files for testing
python3 test_data/create_sample_dxf.py
```

This creates:
- 5 legacy drawings in `test_data/input/`
- 3 old/new sample pairs in `test_data/samples/`

### 2. Check CLI Help

```bash
# Main help
python3 cad_migration.py --help

# Command help
python3 cad_migration.py migrate --help
python3 cad_migration.py learn --help
python3 cad_migration.py validate --help
python3 cad_migration.py pdm --help
```

### 3. Validate Legacy Drawings

```bash
# Validate legacy drawings against modern standards
python3 cad_migration.py validate pre \
  test_data/input \
  --standards config/standards-example.yaml
```

You should see validation errors for old layer names.

### 4. Learn Standards from Samples

```bash
# Learn modern standards from old/new sample pairs
python3 cad_migration.py learn run \
  test_data/samples/old \
  test_data/samples/new \
  --output config/learned-standards.yaml \
  --min-confidence 0.6

# View the learned standards
cat config/learned-standards.yaml
```

### 5. Run Migration

```bash
# Migrate legacy drawings to modern standards
python3 cad_migration.py migrate run \
  test_data/input \
  --standards config/standards-example.yaml \
  --workers 2 \
  --pattern "*.dxf"

# You'll see live progress and results
```

### 6. Check Migration Status

```bash
# List recent migrations
python3 cad_migration.py migrate list

# Check specific migration status
python3 cad_migration.py migrate status <migration-id>
```

### 7. Validate Migrated Files

```bash
# Post-migration validation
python3 cad_migration.py validate post \
  test_data/input \
  --standards config/standards-example.yaml
```

## Detailed Testing Scenarios

### Scenario 1: Learn-Then-Migrate Workflow

```bash
# Step 1: Learn standards
python3 cad_migration.py learn run \
  test_data/samples/old \
  test_data/samples/new \
  --output config/my-learned-standards.yaml \
  --min-confidence 0.7

# Step 2: Generate confidence report
python3 cad_migration.py learn report \
  test_data/samples/old \
  test_data/samples/new \
  --detailed

# Step 3: Validate learned standards
python3 cad_migration.py learn validate \
  config/my-learned-standards.yaml

# Step 4: Migrate using learned standards
python3 cad_migration.py migrate run \
  test_data/input \
  --standards config/my-learned-standards.yaml \
  --workers 4
```

### Scenario 2: Validation Workflow

```bash
# Pre-migration validation
python3 cad_migration.py validate pre \
  test_data/input \
  --standards config/standards-example.yaml \
  --pattern "*.dxf"

# Validate a single file with details
python3 cad_migration.py validate file \
  test_data/input/legacy-drawing-01.dxf \
  --standards config/standards-example.yaml \
  --verbose

# Post-migration validation
python3 cad_migration.py validate post \
  test_data/input \
  --standards config/standards-example.yaml
```

### Scenario 3: Crash Recovery Test

```bash
# Start migration (then press Ctrl+C to interrupt)
python3 cad_migration.py migrate run \
  test_data/input \
  --standards config/standards-example.yaml

# Press Ctrl+C after a few files...

# List migrations to find the ID
python3 cad_migration.py migrate list

# Resume the interrupted migration
python3 cad_migration.py migrate resume <migration-id>
```

### Scenario 4: PDM Integration (Mock Mode)

```bash
# Test PDM connection
python3 cad_migration.py pdm connect \
  --vault-name "TestVault" \
  --mock \
  --vault-root test_data/.mock_vault

# Check out a file
python3 cad_migration.py pdm checkout \
  "drawings/test.dxf" \
  test_data/checked_out.dxf \
  --vault-name "TestVault" \
  --mock \
  --vault-root test_data/.mock_vault

# Check in a file
python3 cad_migration.py pdm checkin \
  test_data/input/legacy-drawing-01.dxf \
  "drawings/migrated-01.dxf" \
  --vault-name "TestVault" \
  --mock \
  --vault-root test_data/.mock_vault \
  --comment "Migrated to modern standards"

# Check file status
python3 cad_migration.py pdm status \
  "drawings/migrated-01.dxf" \
  --vault-name "TestVault" \
  --mock \
  --vault-root test_data/.mock_vault
```

### Scenario 5: Rollback Test

```bash
# Run migration with rollback enabled (default)
python3 cad_migration.py migrate run \
  test_data/input \
  --standards config/standards-example.yaml

# List migrations
python3 cad_migration.py migrate list

# Rollback the migration
python3 cad_migration.py migrate rollback <migration-id>
```

## Testing Advanced Features

### Test Logging

```bash
# Run with different log levels (set via environment)
CAD_LOG_LEVEL=DEBUG python3 cad_migration.py migrate run \
  test_data/input \
  --standards config/standards-example.yaml
```

### Test Configuration

```bash
# Override defaults via environment variables
CAD_DEFAULT_WORKERS=8 \
CAD_CHECKPOINT_INTERVAL=5 \
python3 cad_migration.py migrate run \
  test_data/input \
  --standards config/standards-example.yaml
```

### Test Different Workers

```bash
# Test with 1 worker (sequential)
python3 cad_migration.py migrate run test_data/input \
  --standards config/standards-example.yaml --workers 1

# Test with 4 workers (parallel)
python3 cad_migration.py migrate run test_data/input \
  --standards config/standards-example.yaml --workers 4
```

## Verifying Results

### Check Migration Database

```bash
# The migration database stores all state
sqlite3 data/migrations.db "SELECT * FROM migrations;"
sqlite3 data/migrations.db "SELECT * FROM file_records LIMIT 10;"
```

### Check Backups

```bash
# Backups are stored by migration ID
ls -lh backups/
```

### Compare Files

```bash
# Use Python to compare original vs migrated
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.utils.file_utils import compare_files

result = compare_files(
    Path('test_data/samples/old/sample-1.dxf'),
    Path('test_data/samples/new/sample-1.dxf')
)

print("Comparison Results:")
print(f"Identical: {result['identical']}")
print(f"Layers added: {result['layers']['added']}")
print(f"Layers removed: {result['layers']['removed']}")
print(f"Entities added: {result['entities']['added']}")
print(f"Entities removed: {result['entities']['removed']}")
EOF
```

## Troubleshooting

### Issue: "No module named 'ezdxf'"

```bash
pip install ezdxf click rich pyyaml sqlalchemy
```

### Issue: Permission denied

```bash
chmod +x cad_migration.py
```

### Issue: Database locked

```bash
# Close any open database connections
# Or delete and recreate: rm data/migrations.db
```

### Issue: No files found

```bash
# Make sure you created sample files
python3 test_data/create_sample_dxf.py
```

## Performance Testing

```bash
# Test with many files
for i in {1..20}; do
  cp test_data/input/legacy-drawing-01.dxf test_data/input/test-$i.dxf
done

# Benchmark with different worker counts
time python3 cad_migration.py migrate run test_data/input \
  --standards config/standards-example.yaml --workers 1

time python3 cad_migration.py migrate run test_data/input \
  --standards config/standards-example.yaml --workers 4
```

## Next Steps

After testing:

1. **Customize standards** - Edit `config/standards-example.yaml` for your needs
2. **Create real workflows** - Use learning to extract your standards
3. **Integrate with PDM** - Configure for SolidWorks PDM on Windows
4. **Automate** - Create scripts for batch operations
5. **Monitor** - Use logging and metrics for production

## Environment Variables

```bash
# Logging
export CAD_LOG_LEVEL=DEBUG
export CAD_STRUCTURED_LOGGING=true
export CAD_LOG_DIR=logs

# Performance
export CAD_DEFAULT_WORKERS=8
export CAD_CHECKPOINT_INTERVAL=5

# Storage
export CAD_DB_PATH=data/migrations.db
export CAD_BACKUP_DIR=backups
```

## Quick Commands Reference

```bash
# Help
python3 cad_migration.py --help

# Migrate
python3 cad_migration.py migrate run <path> -s <standards.yaml>

# Learn
python3 cad_migration.py learn run <old> <new> -o <output.yaml>

# Validate
python3 cad_migration.py validate pre <path> -s <standards.yaml>

# PDM
python3 cad_migration.py pdm connect --vault-name <name> --mock

# Status
python3 cad_migration.py migrate list
python3 cad_migration.py migrate status <id>
```

Happy testing! 🚀
