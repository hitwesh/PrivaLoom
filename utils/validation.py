"""
Validation utilities for PrivaLoom.

Provides validation functions for gradient updates, payloads, and model
parameters with optional strict validation modes.
"""

import math
from typing import Any
from utils.types import GradientSlice, GradientUpdate, UpdateBatch


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def is_finite_number(value: float) -> bool:
    """Check if a number is finite (not NaN or infinity)."""
    return math.isfinite(value)


def validate_gradient_slice(slice_data: Any, max_size: int = 1000) -> bool:
    """
    Validate a single gradient slice.

    Args:
        slice_data: Data to validate as gradient slice
        max_size: Maximum allowed slice size

    Returns:
        True if valid, False otherwise
    """
    # Check if it's a list
    if not isinstance(slice_data, list):
        return False

    # Check size bounds
    if len(slice_data) > max_size:
        return False

    # Check if all elements are finite numbers
    for value in slice_data:
        if not isinstance(value, (int, float)) or not is_finite_number(float(value)):
            return False

    return True


def validate_gradient_update(update: Any, max_layers: int = 10, max_slice_size: int = 1000) -> bool:
    """
    Validate gradient update structure and bounds.

    Args:
        update: Data to validate as gradient update
        max_layers: Maximum number of layers allowed
        max_slice_size: Maximum size per gradient slice

    Returns:
        True if valid, False otherwise
    """
    # Check if it's a list
    if not isinstance(update, list):
        return False

    # Check number of layers
    if len(update) > max_layers:
        return False

    # Validate each gradient slice
    for slice_data in update:
        if not validate_gradient_slice(slice_data, max_slice_size):
            return False

    return True


def validate_update_batch(batch: Any, min_updates: int = 1, max_updates: int = 100) -> bool:
    """
    Validate batch of gradient updates.

    Args:
        batch: Data to validate as update batch
        min_updates: Minimum number of updates required
        max_updates: Maximum number of updates allowed

    Returns:
        True if valid, False otherwise
    """
    # Check if it's a list
    if not isinstance(batch, list):
        return False

    # Check batch size
    if not (min_updates <= len(batch) <= max_updates):
        return False

    # Validate each update in the batch
    for update in batch:
        if not validate_gradient_update(update):
            return False

    return True


def sanitize_gradient_slice(slice_data: GradientSlice) -> GradientSlice:
    """
    Sanitize gradient slice by removing NaN/inf values.

    Args:
        slice_data: Gradient slice to sanitize

    Returns:
        Sanitized gradient slice with finite values only
    """
    sanitized = []
    for value in slice_data:
        if isinstance(value, (int, float)) and is_finite_number(float(value)):
            sanitized.append(float(value))
        else:
            # Replace invalid values with 0.0
            sanitized.append(0.0)
    return sanitized


def sanitize_gradient_update(update: GradientUpdate) -> GradientUpdate:
    """
    Sanitize gradient update by removing NaN/inf values.

    Args:
        update: Gradient update to sanitize

    Returns:
        Sanitized gradient update
    """
    return [sanitize_gradient_slice(slice_data) for slice_data in update]


def check_differential_privacy_bounds(update: GradientUpdate, max_norm: float = 1.0) -> bool:
    """
    Check if gradient update satisfies differential privacy bounds.

    Args:
        update: Gradient update to check
        max_norm: Maximum allowed L2 norm

    Returns:
        True if within bounds, False otherwise
    """
    # Calculate L2 norm across all gradient values
    total_norm_squared = 0.0

    for slice_data in update:
        for value in slice_data:
            if isinstance(value, (int, float)) and is_finite_number(float(value)):
                total_norm_squared += float(value) ** 2

    l2_norm = math.sqrt(total_norm_squared)
    return l2_norm <= max_norm


def validate_client_id(client_id: Any) -> bool:
    """
    Validate client ID format.

    Args:
        client_id: Client ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(client_id, str):
        return False

    # Check basic format requirements
    if len(client_id) < 1 or len(client_id) > 100:
        return False

    # Check for reasonable characters (alphanumeric, hyphens, underscores)
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
    return all(c in allowed_chars for c in client_id)


def validate_json_payload(payload: Any, required_fields: list[str]) -> bool:
    """
    Validate JSON payload structure.

    Args:
        payload: Payload to validate
        required_fields: List of required field names

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(payload, dict):
        return False

    # Check that all required fields are present
    for field in required_fields:
        if field not in payload:
            return False

    return True