# CAD Migration Automation Tool

Automated migration tool for 2D CAD files (DWG/DXF) to SolidWorks PDM vault with standards compliance, part card data extraction, and custom property population.

## Features

- ✅ **Batch Processing**: Migrate 50-500 drawings per batch with parallel processing
- ✅ **Standards Compliance**: Automatic layer migration, dimensioning correction, and title block standardization
- ✅ **Data Extraction**: Part card data extraction for PDM custom properties
- ✅ **Standards Learning**: Learn standards from sample files (old vs new)
- ✅ **Validation**: Pre and post-migration validation with rollback support
- ✅ **Mock PDM**: File-system based PDM simulation for development
- ✅ **CLI Interface**: Command-line interface for automation

## Installation

```bash
# Clone repository
git clone <repository-url>
cd CAD_migration

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

## Quick Start

```bash
# Learn standards from sample files
python -m src.cli.commands learn-standards old_samples/ new_samples/ --output config/standards/learned.yaml

# Migrate CAD files in batch
python -m src.cli.commands migrate input_files/ --profile electrical_profile --standards latest

# Validate a single file
python -m src.cli.commands validate drawing.dxf --standards latest

# Rollback a migration
python -m src.cli.commands rollback migration_20240108_120000
```

## Project Structure

```
CAD_migration/
├── src/                    # Source code
│   ├── cli/               # CLI commands
│   ├── orchestration/     # Batch & workflow coordination
│   ├── core/              # Processing logic
│   ├── integration/       # PDM & learning systems
│   ├── data/              # Models & repositories
│   └── utils/             # Utilities
├── config/                # YAML configurations
├── tests/                 # Test suite
├── data/                  # Runtime data (gitignored)
└── docs/                  # Documentation
```

## Configuration

Standards are defined in YAML files in `config/standards/`:

- `layer_standards.yaml` - Layer naming conventions
- `title_block_standards.yaml` - Title block requirements
- `dimension_standards.yaml` - Dimensioning rules
- `property_mappings.yaml` - PDM property mappings

Migration profiles in `config/migration_profiles/`:

- `electrical_profile.yaml` - Electrical drawing settings
- ` mechanical_profile.yaml` - Mechanical drawing settings

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Format code
black src/ tests/

# Type checking
mypy src/
```

## Documentation

- [Migration Guide](docs/migration_guide.md)
- [Standards Authoring](docs/standards_authoring.md)
- [API Documentation](docs/API.md)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please read our contributing guidelines.
