"""
PrivaLoom Utilities Package

Centralized utilities for logging, configuration, data preprocessing, validation, and aggregation.
Provides backward compatibility with existing code patterns.
"""

# Core utilities and backward compatibility
from utils.config import config, _get_env_bool, _get_env_float, _get_env_int
from utils.logging import (
    setup_logger, log_info, log_error, log_training_step,
    log_update_received, log_aggregation_event, log_aggregation_start, log_aggregation_complete
)
from utils.data import (
    load_text_file, validate_text_samples, preprocess_text, get_dataset_stats
)
from utils.validation import (
    ValidationError, validate_gradient_update, validate_update_batch,
    sanitize_gradient_update, check_differential_privacy_bounds,
    validate_client_id, validate_json_payload
)
from utils.aggregation import (
    AggregationState, RoundTracker, get_round_tracker, reset_round_tracker
)
from utils.types import (
    GradientSlice, GradientUpdate, UpdateBatch, ConfigValue,
    TextSample, TextDataset
)

__all__ = [
    # Configuration
    'config', '_get_env_bool', '_get_env_float', '_get_env_int',

    # Logging
    'setup_logger', 'log_info', 'log_error', 'log_training_step',
    'log_update_received', 'log_aggregation_event', 'log_aggregation_start', 'log_aggregation_complete',

    # Data processing
    'load_text_file', 'validate_text_samples', 'preprocess_text', 'get_dataset_stats',

    # Validation
    'ValidationError', 'validate_gradient_update', 'validate_update_batch',
    'sanitize_gradient_update', 'check_differential_privacy_bounds',
    'validate_client_id', 'validate_json_payload',

    # Aggregation
    'AggregationState', 'RoundTracker', 'get_round_tracker', 'reset_round_tracker',

    # Types
    'GradientSlice', 'GradientUpdate', 'UpdateBatch', 'ConfigValue',
    'TextSample', 'TextDataset',
]