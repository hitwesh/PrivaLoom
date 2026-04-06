"""
Privacy and Security module for PrivaLoom federated learning.

Unified module containing differential privacy mechanisms, Byzantine-robust
aggregation, security monitoring, and attack detection capabilities.
"""

# Differential Privacy components
from privacy_security.dp_engine import (
    DPConfig,
    PrivacyAccountant,
    DPGradientClipper,
    DPNoiseGenerator,
    create_dp_components,
)

from privacy_security.privacy_tracker import (
    PrivacyTracker,
    PrivacyState,
    get_privacy_tracker,
    reset_privacy_tracker,
)

# Byzantine-Robust Aggregation components
from privacy_security.robust_aggregation import (
    AggregationMethod,
    AggregationConfig,
    RobustAggregator,
    AggregatorFactory,
    FedAvgAggregator,
    TrimmedMeanAggregator,
    MedianAggregator,
    KrumAggregator,
    BulyanAggregator,
    benchmark_aggregation_methods,
)

# Outlier Detection components
from privacy_security.outlier_detection import (
    OutlierDetectionMethod,
    OutlierDetectionConfig,
    DetectionResult,
    OutlierDetector,
    create_outlier_detector,
)

# Reputation Management components
from privacy_security.reputation import (
    ClientReputation,
    ReputationManager,
    calculate_quality_score,
    get_reputation_manager,
    reset_reputation_manager,
)

# Security Monitoring components
from privacy_security.security_monitor import (
    SecurityEventType,
    SecuritySeverity,
    SecurityEvent,
    SecurityMonitor,
    create_outlier_event,
    create_malicious_update_event,
    create_reputation_event,
    get_security_monitor,
    reset_security_monitor,
)

# Validation Pipeline components
from privacy_security.validation_pipeline import (
    ValidationError,
    ValidationErrorType,
    ValidationResult,
    ValidationConfig,
    UpdateValidator,
    create_update_validator,
)

__all__ = [
    # Differential Privacy
    "DPConfig",
    "PrivacyAccountant",
    "DPGradientClipper",
    "DPNoiseGenerator",
    "create_dp_components",

    # Privacy Tracking
    "PrivacyTracker",
    "PrivacyState",
    "get_privacy_tracker",
    "reset_privacy_tracker",

    # Byzantine-Robust Aggregation
    "AggregationMethod",
    "AggregationConfig",
    "RobustAggregator",
    "AggregatorFactory",
    "FedAvgAggregator",
    "TrimmedMeanAggregator",
    "MedianAggregator",
    "KrumAggregator",
    "BulyanAggregator",
    "benchmark_aggregation_methods",

    # Outlier Detection
    "OutlierDetectionMethod",
    "OutlierDetectionConfig",
    "DetectionResult",
    "OutlierDetector",
    "create_outlier_detector",

    # Reputation Management
    "ClientReputation",
    "ReputationManager",
    "calculate_quality_score",
    "get_reputation_manager",
    "reset_reputation_manager",

    # Security Monitoring
    "SecurityEventType",
    "SecuritySeverity",
    "SecurityEvent",
    "SecurityMonitor",
    "create_outlier_event",
    "create_malicious_update_event",
    "create_reputation_event",
    "get_security_monitor",
    "reset_security_monitor",

    # Validation Pipeline
    "ValidationError",
    "ValidationErrorType",
    "ValidationResult",
    "ValidationConfig",
    "UpdateValidator",
    "create_update_validator",
]