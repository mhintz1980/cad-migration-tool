"""
Test suite for Phase 2D: CLI Implementation.

Tests CLI commands and integration.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import shutil

from src.cli.main import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


# ============================================================================
# Main CLI Tests
# ============================================================================


def test_cli_help(runner):
    """Test main CLI help command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "CAD Migration Automation Tool" in result.output
    assert "migrate" in result.output
    assert "learn" in result.output
    assert "pdm" in result.output
    assert "validate" in result.output


def test_cli_version(runner):
    """Test CLI version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


# ============================================================================
# Migrate Command Tests
# ============================================================================


def test_migrate_help(runner):
    """Test migrate command group help."""
    result = runner.invoke(cli, ["migrate", "--help"])
    assert result.exit_code == 0
    assert "Migration commands" in result.output
    assert "run" in result.output
    assert "resume" in result.output
    assert "status" in result.output
    assert "rollback" in result.output
    assert "list" in result.output


def test_migrate_run_missing_args(runner):
    """Test migrate run with missing required arguments."""
    result = runner.invoke(cli, ["migrate", "run"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "Error" in result.output


def test_migrate_list_help(runner):
    """Test migrate list help."""
    result = runner.invoke(cli, ["migrate", "list", "--help"])
    assert result.exit_code == 0
    assert "recent migrations" in result.output


# ============================================================================
# Learn Command Tests
# ============================================================================


def test_learn_help(runner):
    """Test learn command group help."""
    result = runner.invoke(cli, ["learn", "--help"])
    assert result.exit_code == 0
    assert "Standards learning" in result.output
    assert "run" in result.output
    assert "report" in result.output
    assert "validate" in result.output


def test_learn_run_missing_args(runner):
    """Test learn run with missing arguments."""
    result = runner.invoke(cli, ["learn", "run"])
    assert result.exit_code != 0


# ============================================================================
# PDM Command Tests
# ============================================================================


def test_pdm_help(runner):
    """Test PDM command group help."""
    result = runner.invoke(cli, ["pdm", "--help"])
    assert result.exit_code == 0
    assert "PDM vault" in result.output
    assert "connect" in result.output
    assert "checkout" in result.output
    assert "checkin" in result.output
    assert "status" in result.output


def test_pdm_connect_missing_vault(runner):
    """Test PDM connect with missing vault name."""
    result = runner.invoke(cli, ["pdm", "connect"])
    assert result.exit_code != 0
    assert "--vault-name" in result.output or "Missing option" in result.output


# ============================================================================
# Validate Command Tests
# ============================================================================


def test_validate_help(runner):
    """Test validate command group help."""
    result = runner.invoke(cli, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Validation commands" in result.output
    assert "pre" in result.output
    assert "post" in result.output
    assert "file" in result.output


def test_validate_pre_missing_args(runner):
    """Test validate pre with missing arguments."""
    result = runner.invoke(cli, ["validate", "pre"])
    assert result.exit_code != 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_migrate_list_with_nonexistent_db(runner, temp_dir):
    """Test migrate list with non-existent database."""
    db_path = temp_dir / "nonexistent.db"
    result = runner.invoke(cli, ["migrate", "list", "--db-path", str(db_path)])
    # Should handle gracefully
    assert result.exit_code in [0, 1]  # Either succeeds with empty list or fails gracefully


def test_learn_validate_missing_file(runner, temp_dir):
    """Test learn validate with non-existent file."""
    missing_file = temp_dir / "missing.yaml"
    result = runner.invoke(cli, ["learn", "validate", str(missing_file)])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "does not exist" in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
