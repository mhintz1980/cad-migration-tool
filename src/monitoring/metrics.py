"""
Metrics collection system.

Tracks counters, gauges, and timers for performance monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import time


@dataclass
class Metric:
    """Base metric data."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter(Metric):
    """Counter metric (monotonically increasing)."""

    pass


@dataclass
class Gauge(Metric):
    """Gauge metric (point-in-time value)."""

    pass


@dataclass
class Timer(Metric):
    """Timer metric (duration in seconds)."""

    pass


class MetricsCollector:
    """
    Collects and aggregates metrics.

    Thread-safe metrics collection with aggregation.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.metrics: List[Metric] = []

    def increment_counter(self, name: str, value: float = 1.0, **tags):
        """
        Increment counter metric.

        Args:
            name: Counter name
            value: Increment value
            **tags: Additional tags
        """
        key = self._make_key(name, tags)
        self.counters[key] += value
        self.metrics.append(Counter(name=name, value=self.counters[key], tags=tags))

    def set_gauge(self, name: str, value: float, **tags):
        """
        Set gauge metric.

        Args:
            name: Gauge name
            value: Gauge value
            **tags: Additional tags
        """
        key = self._make_key(name, tags)
        self.gauges[key] = value
        self.metrics.append(Gauge(name=name, value=value, tags=tags))

    def record_timer(self, name: str, duration: float, **tags):
        """
        Record timer metric.

        Args:
            name: Timer name
            duration: Duration in seconds
            **tags: Additional tags
        """
        key = self._make_key(name, tags)
        self.timers[key].append(duration)
        self.metrics.append(Timer(name=name, value=duration, tags=tags))

    def time(self, name: str, **tags):
        """
        Context manager for timing operations.

        Args:
            name: Timer name
            **tags: Additional tags

        Example:
            with metrics.time("parse_file", file_type="dxf"):
                parse_dxf_file()
        """
        return TimerContext(self, name, tags)

    def get_counter(self, name: str, **tags) -> float:
        """Get current counter value."""
        key = self._make_key(name, tags)
        return self.counters.get(key, 0.0)

    def get_gauge(self, name: str, **tags) -> float | None:
        """Get current gauge value."""
        key = self._make_key(name, tags)
        return self.gauges.get(key)

    def get_timer_stats(self, name: str, **tags) -> Dict[str, float]:
        """
        Get timer statistics.

        Returns:
            Dict with min, max, mean, count
        """
        key = self._make_key(name, tags)
        values = self.timers.get(key, [])

        if not values:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "total": 0}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "total": sum(values),
        }

    def get_all_metrics(self) -> List[Metric]:
        """Get all recorded metrics."""
        return self.metrics.copy()

    def get_summary(self) -> Dict[str, any]:
        """
        Get metrics summary.

        Returns:
            Summary with all metric types
        """
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {
                name: self.get_timer_stats(name) for name in self.timers.keys()
            },
            "total_metrics": len(self.metrics),
        }

    def reset(self):
        """Reset all metrics."""
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()
        self.metrics.clear()

    def _make_key(self, name: str, tags: Dict[str, str]) -> str:
        """Create unique key from name and tags."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str, tags: Dict[str, str]):
        """Initialize timer context."""
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        """Start timer."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record duration."""
        duration = time.perf_counter() - self.start_time
        self.collector.record_timer(self.name, duration, **self.tags)


# Global metrics collector
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics
