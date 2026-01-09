# Contributing to CAD Migration Tool

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/yourusername/CAD_migration.git
cd CAD_migration
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black mypy
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_phase2b.py -v

# Run specific test
pytest tests/test_phase2b.py::test_batch_processor_basic -v
```

### Code Formatting

```bash
# Format code with black
black src/ tests/

# Check formatting
black --check src/ tests/
```

### Type Checking

```bash
# Run mypy
mypy src/
```

### Linting

```bash
# Run flake8 (if installed)
flake8 src/ tests/
```

## Project Structure

```
src/
├── core/           # Core parsers, transformers, validators
├── data/           # Data models and repositories
├── orchestration/  # Batch processing
├── integration/    # Learning, PDM integration
└── cli/            # Command-line interface

tests/              # Test suite
docs/               # Documentation
config/             # Example configurations
```

## Coding Standards

### Python Style
- Follow PEP 8
- Use Black for formatting (line length: 88)
- Use type hints for all functions
- Write docstrings for public APIs

### Example:

```python
"""Module docstring."""

from pathlib import Path
from typing import List, Optional


def process_files(
    file_paths: List[Path],
    output_dir: Optional[Path] = None,
) -> int:
    """
    Process CAD files.
    
    Args:
        file_paths: List of files to process
        output_dir: Optional output directory
        
    Returns:
        Number of files processed successfully
        
    Raises:
        ValueError: If file_paths is empty
    """
    if not file_paths:
        raise ValueError("file_paths cannot be empty")
        
    # Implementation...
    return len(file_paths)
```

### Naming Conventions
- **Classes:** PascalCase (e.g., `DXFParser`)
- **Functions:** snake_case (e.g., `parse_file`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_WORKERS`)
- **Private:** Leading underscore (e.g., `_internal_method`)

### File Organization
- Maximum 500 lines per file
- One class per file (generally)
- Related functions grouped in modules

## Testing Guidelines

### Test Structure

```python
"""Test module docstring."""

import pytest
from pathlib import Path

from src.core.parsers.dxf_parser import DXFParser


@pytest.fixture
def sample_file():
    """Create sample DXF file for testing."""
    # Setup
    yield Path("test.dxf")
    # Teardown


def test_parser_basic(sample_file):
    """Test basic parsing functionality."""
    parser = DXFParser()
    result = parser.parse(sample_file)
    
    assert result is not None
    assert result.file_type == "DXF"
```

### Test Coverage
- Aim for 70%+ coverage
- Focus on critical paths
- Test error conditions
- Test edge cases

### Test Naming
- Descriptive names: `test_parser_handles_empty_file`
- Use prefixes: `test_`, `when_`, `should_`
- Group related tests in classes

## Pull Request Process

### 1. Before Submitting

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Code formatted: `black src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

### 2. Commit Messages

Use conventional commits format:

```
feat: Add support for DWG file format
fix: Handle empty layer names correctly
docs: Update installation instructions
test: Add tests for dimension transformer
refactor: Simplify batch processor logic
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance

### 3. Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests pass locally
```

### 4. Review Process

1. Automated checks run (tests, linting)
2. Code review by maintainer
3. Address feedback
4. Approval and merge

## Areas for Contribution

### High Priority
- Windows COM PDM client implementation
- Additional file format parsers (STEP, IGES)
- Performance optimizations
- Documentation improvements

### Medium Priority
- Web UI for monitoring
- REST API
- Docker support
- Additional learners (block learners, style learners)

### Good First Issues
- Add CLI help text
- Improve error messages
- Add example configurations
- Write tutorials

## Documentation

### Code Comments
- Explain **why**, not **what**
- Document assumptions
- Note edge cases
- Reference issues/PRs where relevant

### Docstrings
- Required for public APIs
- Follow Google or NumPy style
- Include examples for complex functions

### User Documentation
- Update README.md for new features
- Add usage examples
- Document configuration options

## Questions?

- Open an issue for questions
- Join discussions
- Ask in pull request comments

## Recognition

Contributors will be acknowledged in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing! 🎉
