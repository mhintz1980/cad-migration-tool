"""
Configuration management system.

Handles environment variables, config files, and defaults.
"""

import os
from pathlib import Path
from typing import Any
import yaml
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """
    Application configuration.

    Manages all configuration settings with environment variable overrides.
    """

    # Logging
    log_level: str = "INFO"
    log_dir: Path = Path("logs")
    structured_logging: bool = False

    # Database
    db_path: Path = Path("data/migrations.db")
    db_echo: bool = False  # SQLAlchemy echo mode

    # Batch Processing
    default_workers: int = 4
    default_checkpoint_interval: int = 10
    max_failures_threshold: int = 50

    # Backup
    backup_dir: Path = Path("backups")
    backup_retention_days: int = 30

    # Standards
    default_standards_path: Path = Path("config/standards.yaml")

    # PDM
    pdm_timeout: int = 30  # seconds
    pdm_retry_attempts: int = 3

    # Learning
    min_learning_confidence: float = 0.7
    min_learning_samples: int = 5

    # Performance
    enable_profiling: bool = False
    enable_metrics: bool = False

    # Paths
    temp_dir: Path = Path("/tmp/cad_migration")

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Create configuration from environment variables.

        Environment variables override defaults.

        Returns:
            AppConfig instance
        """
        return cls(
            # Logging
            log_level=os.getenv("CAD_LOG_LEVEL", "INFO"),
            log_dir=Path(os.getenv("CAD_LOG_DIR", "logs")),
            structured_logging=os.getenv("CAD_STRUCTURED_LOGGING", "false").lower()
            == "true",
            # Database
            db_path=Path(os.getenv("CAD_DB_PATH", "data/migrations.db")),
            db_echo=os.getenv("CAD_DB_ECHO", "false").lower() == "true",
            # Batch Processing
            default_workers=int(os.getenv("CAD_DEFAULT_WORKERS", "4")),
            default_checkpoint_interval=int(
                os.getenv("CAD_CHECKPOINT_INTERVAL", "10")
            ),
            max_failures_threshold=int(os.getenv("CAD_MAX_FAILURES", "50")),
            # Backup
            backup_dir=Path(os.getenv("CAD_BACKUP_DIR", "backups")),
            backup_retention_days=int(os.getenv("CAD_BACKUP_RETENTION_DAYS", "30")),
            # Standards
            default_standards_path=Path(
                os.getenv("CAD_STANDARDS_PATH", "config/standards.yaml")
            ),
            # PDM
            pdm_timeout=int(os.getenv("CAD_PDM_TIMEOUT", "30")),
            pdm_retry_attempts=int(os.getenv("CAD_PDM_RETRY_ATTEMPTS", "3")),
            # Learning
            min_learning_confidence=float(
                os.getenv("CAD_MIN_LEARNING_CONFIDENCE", "0.7")
            ),
            min_learning_samples=int(os.getenv("CAD_MIN_LEARNING_SAMPLES", "5")),
            # Performance
            enable_profiling=os.getenv("CAD_ENABLE_PROFILING", "false").lower()
            == "true",
            enable_metrics=os.getenv("CAD_ENABLE_METRICS", "false").lower() == "true",
            # Paths
            temp_dir=Path(os.getenv("CAD_TEMP_DIR", "/tmp/cad_migration")),
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "AppConfig":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            AppConfig instance
        """
        with open(config_path) as f:
            data = yaml.safe_load(f)

        # Convert path strings to Path objects
        for key in [
            "log_dir",
            "db_path",
            "backup_dir",
            "default_standards_path",
            "temp_dir",
        ]:
            if key in data:
                data[key] = Path(data[key])

        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result

    def save(self, config_path: Path):
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to save config
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)


# Global configuration instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """
    Get global configuration instance.

    Creates from environment on first call.

    Returns:
        AppConfig instance
    """
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def set_config(config: AppConfig):
    """
    Set global configuration instance.

    Args:
        config: AppConfig instance
    """
    global _config
    _config = config


def load_config(config_path: Path):
    """
    Load configuration from file and set as global.

    Args:
        config_path: Path to config file
    """
    global _config
    _config = AppConfig.from_file(config_path)
