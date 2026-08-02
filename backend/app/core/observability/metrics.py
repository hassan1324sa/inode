from typing import Dict, List, Any, Optional
from collections import defaultdict
import time

class FluxaMetrics:
    """
    Prometheus-compatible metrics collector for Fluxa workflow and node executions.
    """
    _counters: Dict[str, int] = defaultdict(int)
    _gauges: Dict[str, float] = defaultdict(float)
    _histograms: Dict[str, List[float]] = defaultdict(list)
    _labels: Dict[str, Dict[str, str]] = {}

    @classmethod
    def inc_counter(cls, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        key = cls._make_key(name, labels)
        cls._counters[key] += value
        if labels:
            cls._labels[key] = labels

    @classmethod
    def set_gauge(cls, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        key = cls._make_key(name, labels)
        cls._gauges[key] = value
        if labels:
            cls._labels[key] = labels

    @classmethod
    def observe_histogram(cls, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        key = cls._make_key(name, labels)
        cls._histograms[key].append(value)
        if labels:
            cls._labels[key] = labels

    @classmethod
    def _make_key(cls, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    @classmethod
    def _format_metric_name(cls, key: str, suffix: str) -> str:
        if "{" in key:
            base, labels = key.split("{", 1)
            return f"{base}{suffix}{{{labels}"
        return f"{key}{suffix}"

    @classmethod
    def export_prometheus(cls) -> str:
        """
        Export metrics in standard Prometheus text format.
        """
        lines = []
        # Counters
        for key, val in sorted(cls._counters.items()):
            base_name = key.split("{")[0]
            lines.append(f"# TYPE {base_name} counter")
            lines.append(f"{key} {val}")
        # Gauges
        for key, val in sorted(cls._gauges.items()):
            base_name = key.split("{")[0]
            lines.append(f"# TYPE {base_name} gauge")
            lines.append(f"{key} {val}")
        # Histograms
        for key, values in sorted(cls._histograms.items()):
            base_name = key.split("{")[0]
            count = len(values)
            total = sum(values)
            lines.append(f"# TYPE {base_name} histogram")
            count_key = cls._format_metric_name(key, "_count")
            sum_key = cls._format_metric_name(key, "_sum")
            lines.append(f"{count_key} {count}")
            lines.append(f"{sum_key} {total}")
        return "\n".join(lines) + "\n"

    @classmethod
    def clear(cls):
        cls._counters.clear()
        cls._gauges.clear()
        cls._histograms.clear()
        cls._labels.clear()
