"""
Test suite for Phase 3: Advanced Features.

Tests logging, configuration, monitoring, and reporting.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Logging tests
from src.utils.logging import StructuredLogger, LoggerFactory

# Configuration tests
from src.utils.config import AppConfig

# Exception tests
from src.utils.exceptions import (
    CADMigrationError,
    ParserError,
    ValidationError,
    BatchProcessingError,
)

# Metrics tests
from src.monitoring.metrics import MetricsCollector, Counter, Gauge, Timer

# Performance monitoring tests
from src.monitoring.performance import PerformanceMonitor, PerformanceReport


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


# ============================================================================
# Logging Tests
# ============================================================================


def test_structured_logger_creation():
    """Test creating structured logger."""
    logger = StructuredLogger("test_logger", level="INFO")

    assert logger.logger.name == "test_logger"
    assert logger.logger.level == 20  # INFO level


def test_structured_logger_file_output(temp_dir):
    """Test logging to file."""
    log_file = temp_dir / "test.log"
    logger = StructuredLogger("test", log_file=log_file)

    logger.info("Test message")

    assert log_file.exists()
    content = log_file.read_text()
    assert "Test message" in content


def test_logger_factory():
    """Test logger factory."""
    LoggerFactory.configure(level="DEBUG", structured=False)

    logger = LoggerFactory.get_logger("factory_test")

    assert logger.logger.level == 10  # DEBUG level


# ============================================================================
# Configuration Tests
# ============================================================================


def test_app_config_defaults():
    """Test AppConfig with default values."""
    config = AppConfig()

    assert config.log_level == "INFO"
    assert config.default_workers == 4
    assert config.min_learning_confidence == 0.7


def test_app_config_from_env(monkeypatch):
    """Test AppConfig from environment variables."""
    monkeypatch.setenv("CAD_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CAD_DEFAULT_WORKERS", "8")

    config = AppConfig.from_env()

    assert config.log_level == "DEBUG"
    assert config.default_workers == 8


def test_app_config_save_load(temp_dir):
    """Test saving and loading configuration."""
    config_path = temp_dir / "config.yaml"

    # Create and save
    config = AppConfig(log_level="DEBUG", default_workers=8)
    config.save(config_path)

    assert config_path.exists()

    # Load
    loaded = AppConfig.from_file(config_path)

    assert loaded.log_level == "DEBUG"
    assert loaded.default_workers == 8


# ============================================================================
# Exception Tests
# ============================================================================


def test_base_exception():
    """Test base CADMigrationError."""
    error = CADMigrationError("Test error", context={"key": "value"})

    assert str(error) == "Test error"
    assert error.context == {"key": "value"}


def test_exception_hierarchy():
    """Test exception inheritance."""
    assert issubclass(ParserError, CADMigrationError)
    assert issubclass(ValidationError, CADMigrationError)
    assert issubclass(BatchProcessingError, CADMigrationError)


def test_exception_with_context():
    """Test exception with context."""
    error = ParserError("Parse failed", context={"file": "test.dxf", "line": 42})

    assert error.message == "Parse failed"
    assert error.context["file"] == "test.dxf"
    assert error.context["line"] == 42


# ============================================================================
# Metrics Tests
# ============================================================================


def test_metrics_counter():
    """Test counter metrics."""
    collector = MetricsCollector()

    collector.increment_counter("files_processed")
    collector.increment_counter("files_processed")
    collector.increment_counter("files_processed", value=3)

    assert collector.get_counter("files_processed") == 5.0


def test_metrics_gauge():
    """Test gauge metrics."""
    collector = MetricsCollector()

    collector.set_gauge("queue_size", 10)
    collector.set_gauge("queue_size", 15)

    assert collector.get_gauge("queue_size") == 15.0


def test_metrics_timer():
    """Test timer metrics."""
    collector = MetricsCollector()

    collector.record_timer("parse_file", 0.5)
    collector.record_timer("parse_file", 1.0)
    collector.record_timer("parse_file", 0.75)

    stats = collector.get_timer_stats("parse_file")

    assert stats["count"] == 3
    assert stats["min"] == 0.5
    assert stats["max"] == 1.0
    assert stats["mean"] == 0.75


def test_metrics_timer_context():
    """Test timer context manager."""
    collector = MetricsCollector()

    with collector.time("operation"):
        pass  # Operation

    stats = collector.get_timer_stats("operation")
    assert stats["count"] == 1
    assert stats["min"] > 0


def test_metrics_with_tags():
    """Test metrics with tags."""
    collector = MetricsCollector()

    collector.increment_counter("requests", file_type="dxf")
    collector.increment_counter("requests", file_type="dwg")

    assert collector.get_counter("requests", file_type="dxf") == 1.0
    assert collector.get_counter("requests", file_type="dwg") == 1.0


def test_metrics_summary():
    """Test metrics summary."""
    collector = MetricsCollector()

    collector.increment_counter("counter1")
    collector.set_gauge("gauge1", 42)
    collector.record_timer("timer1", 1.5)

    summary = collector.get_summary()

    assert "counters" in summary
    assert "gauges" in summary
    assert "timers" in summary
    assert summary["total_metrics"] == 3


def test_metrics_reset():
    """Test metrics reset."""
    collector = MetricsCollector()

    collector.increment_counter("test")
    collector.set_gauge("test", 10)

    collector.reset()

    assert collector.get_counter("test") == 0.0
    assert collector.get_gauge("test") is None


# ============================================================================
# Performance Monitoring Tests
# ============================================================================


def test_performance_monitor_basic():
    """Test basic performance monitoring."""
    monitor = PerformanceMonitor()

    monitor.start()
    monitor.record_file_processed(Path("test.dxf"), success=True, processing_time=1.0)
    monitor.record_file_processed(Path("test2.dxf"), success=True, processing_time=0.5)
    monitor.stop()

    report = monitor.generate_report()

    assert report.files_processed == 2
    assert report.files_succeeded == 2
    assert report.files_failed == 0
    assert report.success_rate == 1.0


def test_performance_monitor_with_failures():
    """Test performance monitor with failed files."""
    monitor = PerformanceMonitor()

    monitor.start()
    monitor.record_file_processed(Path("good.dxf"), success=True, processing_time=1.0)
    monitor.record_file_processed(
        Path("bad.dxf"), success=False, processing_time=0.5, error="Parse error"
    )
    monitor.stop()

    report = monitor.generate_report()

    assert report.files_processed == 2
    assert report.files_succeeded == 1
    assert report.files_failed == 1
    assert report.success_rate == 0.5
    assert len(report.errors) == 1


def test_performance_monitor_metrics():
    """Test performance monitor custom metrics."""
    monitor = PerformanceMonitor()

    monitor.start()
    monitor.add_metric("workers", 4)
    monitor.add_warning("Test warning")
    monitor.stop()

    report = monitor.generate_report()

    assert report.metrics["workers"] == 4
    assert len(report.warnings) == 1


def test_performance_report_str():
    """Test performance report string representation."""
    monitor = PerformanceMonitor()

    monitor.start()
    monitor.record_file_processed(Path("test.dxf"), success=True, processing_time=1.0)
    monitor.stop()

    report = monitor.generate_report()
    report_str = str(report)

    assert "Performance Report" in report_str
    assert "Files Processed: 1" in report_str
    assert "Success Rate: 100.0%" in report_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
