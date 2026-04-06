"""
Common type definitions for PrivaLoom utilities.

Provides type aliases for gradient updates, configuration values, and other
commonly used types throughout the codebase.
"""

from typing import TypeAlias, Literal

# Core type definitions for gradient and update handling
GradientSlice: TypeAlias = list[float]
GradientUpdate: TypeAlias = list[GradientSlice]
UpdateBatch: TypeAlias = list[GradientUpdate]

# Configuration value types
ConfigValue: TypeAlias = str | int | float | bool

# Data processing types
TextSample: TypeAlias = str
TextDataset: TypeAlias = list[TextSample]

# Privacy and security types (Phase 1)
PrivacyBudget: TypeAlias = tuple[float, float]  # (epsilon, delta)
DPParams: TypeAlias = dict[str, float | str]  # DP configuration parameters
ClientID: TypeAlias = str
ReputationScore: TypeAlias = float
AnomalyScore: TypeAlias = float

# Security-related type aliases (Phase 2)
SecurityEventType: TypeAlias = Literal[
    "outlier_detected", "malicious_update", "reputation_decreased",
    "aggregation_failed", "client_blacklisted", "validation_failed",
    "suspicious_pattern", "attack_campaign", "system_compromise"
]
AggregationMethodType: TypeAlias = Literal[
    "fedavg", "krum", "trimmed_mean", "median", "bulyan"
]
OutlierDetectionMethodType: TypeAlias = Literal[
    "zscore", "iqr", "isolation_forest", "combined"
]
OutlierScores: TypeAlias = list[float]  # Anomaly scores 0-1
ClientWeights: TypeAlias = dict[str, float]  # client_id -> reputation weight
ValidationErrors: TypeAlias = list[str]  # Validation error messages