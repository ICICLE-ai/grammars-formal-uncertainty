"""Metric type definitions."""

from enum import Enum


class MetricDirection(str, Enum):
    """Direction of metric correlation with correctness."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"
