"""
Validation pipeline for comprehensive input validation and sanitization.

This module provides multi-layered validation for client updates before aggregation:
- Schema validation for update structure
- Range and bounds checking
- DP bounds integration
- Outlier detection integration
- Reputation-based filtering
- Input sanitization and normalization

The pipeline coordinates multiple validation components to ensure only
valid, safe updates are processed by the aggregation system.
"""

import math
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logging import setup_logger, log_info, log_warning, log_error
from utils.validation import validate_gradient_update, sanitize_gradient_update

# Initialize logger
logger = setup_logger("privaloom.validation_pipeline")
from privacy_security.outlier_detection import OutlierDetector, OutlierDetectionMethod
from privacy_security.reputation import ReputationManager
from privacy_security.security_monitor import SecurityMonitor, create_malicious_update_event


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class ValidationErrorType(Enum):
    """Types of validation errors."""
    SCHEMA_VALIDATION = "schema_validation"
    BOUNDS_VIOLATION = "bounds_violation"
    DP_VIOLATION = "dp_violation"
    OUTLIER_DETECTED = "outlier_detected"
    REPUTATION_TOO_LOW = "reputation_too_low"
    RATE_LIMITED = "rate_limited"
    MALFORMED_DATA = "malformed_data"


@dataclass
class ValidationResult:
    """Result of update validation process."""
    is_valid: bool
    errors: List[str]
    error_types: List[ValidationErrorType]
    sanitized_update: Optional[List[List[float]]]
    confidence: float  # Confidence in validation result (0.0-1.0)
    metadata: Dict[str, Any]  # Additional validation metadata

    @property
    def has_critical_errors(self) -> bool:
        """Check if result has critical errors that require immediate action."""
        critical_types = {
            ValidationErrorType.DP_VIOLATION,
            ValidationErrorType.MALFORMED_DATA
        }
        return any(error_type in critical_types for error_type in self.error_types)


@dataclass
class ValidationConfig:
    """Configuration for update validation pipeline."""
    # Schema validation
    enable_schema_validation: bool = True
    max_param_count: int = 10
    max_slice_size: int = 1000

    # Bounds checking
    enable_bounds_checking: bool = True
    max_gradient_magnitude: float = 100.0
    max_gradient_norm: float = 10.0
    allow_inf_nan: bool = False

    # DP integration
    enable_dp_bounds_checking: bool = True
    dp_noise_threshold: float = 0.001  # Minimum noise level expected

    # Outlier detection
    enable_outlier_detection: bool = True
    outlier_confidence_threshold: float = 0.7

    # Reputation filtering
    enable_reputation_filtering: bool = True
    min_reputation_threshold: float = 0.3

    # Rate limiting
    enable_rate_limiting: bool = True
    max_updates_per_minute: int = 10
    max_updates_per_hour: int = 100

    # Sanitization
    enable_sanitization: bool = True
    clamp_extreme_values: bool = True
    normalize_gradients: bool = False


class SchemaValidator:
    """Validates update structure and schema."""

    def __init__(self, config: ValidationConfig):
        """Initialize schema validator.

        Args:
            config: Validation configuration
        """
        self.config = config

    def validate_update_schema(self, update: Any, client_id: str) -> Tuple[bool, List[str]]:
        """Validate update schema and structure.

        Args:
            update: Raw update data
            client_id: Client identifier

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Basic type checking
            if not isinstance(update, dict):
                errors.append("Update must be a dictionary")
                return False, errors

            if "weights" not in update:
                errors.append("Update missing required 'weights' field")
                return False, errors

            weights = update["weights"]
            if not isinstance(weights, list):
                errors.append("Weights must be a list")
                return False, errors

            # Validate gradient structure
            if len(weights) > self.config.max_param_count:
                errors.append(f"Too many parameters: {len(weights)} > {self.config.max_param_count}")

            for i, param_slice in enumerate(weights):
                if not isinstance(param_slice, list):
                    errors.append(f"Parameter slice {i} must be a list")
                    continue

                if len(param_slice) > self.config.max_slice_size:
                    errors.append(f"Parameter slice {i} too large: {len(param_slice)} > {self.config.max_slice_size}")

                # Check element types
                for j, value in enumerate(param_slice):
                    if not isinstance(value, (int, float)):
                        errors.append(f"Invalid value type at param {i}, element {j}: {type(value)}")

            # Validate client_id if present
            if "client_id" in update:
                if not isinstance(update["client_id"], str) or not update["client_id"].strip():
                    errors.append("Invalid client_id: must be non-empty string")
                elif update["client_id"] != client_id:
                    errors.append(f"Client ID mismatch: {update['client_id']} != {client_id}")

        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")

        return len(errors) == 0, errors

    def validate_client_metadata(self, update: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate optional client metadata.

        Args:
            update: Update dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate timestamp if present
        if "timestamp" in update:
            try:
                timestamp = update["timestamp"]
                if isinstance(timestamp, str):
                    from datetime import datetime
                    datetime.fromisoformat(timestamp)
                elif isinstance(timestamp, (int, float)):
                    if timestamp < 0 or timestamp > 2**32:  # Reasonable Unix timestamp range
                        errors.append("Invalid timestamp range")
            except (ValueError, OverflowError):
                errors.append("Invalid timestamp format")

        return len(errors) == 0, errors


class BoundsValidator:
    """Validates gradient bounds and ranges."""

    def __init__(self, config: ValidationConfig):
        """Initialize bounds validator.

        Args:
            config: Validation configuration
        """
        self.config = config

    def validate_gradient_bounds(self, gradients: List[List[float]]) -> Tuple[bool, List[str]]:
        """Validate gradient values are within acceptable bounds.

        Args:
            gradients: Gradient update

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Flatten gradients for analysis
            flat_gradients = []
            for param_slice in gradients:
                flat_gradients.extend(param_slice)

            if not flat_gradients:
                errors.append("Empty gradient update")
                return False, errors

            # Check for inf/nan values
            if not self.config.allow_inf_nan:
                for i, value in enumerate(flat_gradients):
                    if math.isnan(value):
                        errors.append(f"NaN value detected at index {i}")
                    elif math.isinf(value):
                        errors.append(f"Infinite value detected at index {i}")

            # Check magnitude bounds
            max_magnitude = max(abs(value) for value in flat_gradients)
            if max_magnitude > self.config.max_gradient_magnitude:
                errors.append(f"Gradient magnitude too large: {max_magnitude} > {self.config.max_gradient_magnitude}")

            # Check gradient norm
            gradient_norm = math.sqrt(sum(value**2 for value in flat_gradients))
            if gradient_norm > self.config.max_gradient_norm:
                errors.append(f"Gradient norm too large: {gradient_norm} > {self.config.max_gradient_norm}")

        except Exception as e:
            errors.append(f"Bounds validation error: {str(e)}")

        return len(errors) == 0, errors

    def check_differential_privacy_bounds(self, gradients: List[List[float]]) -> Tuple[bool, List[str]]:
        """Check if gradients are consistent with DP requirements.

        Args:
            gradients: Gradient update

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Flatten gradients
            flat_gradients = []
            for param_slice in gradients:
                flat_gradients.extend(param_slice)

            if not flat_gradients:
                return True, []

            # Check for suspiciously low noise (could indicate DP bypass)
            gradient_variance = np.var(flat_gradients) if len(flat_gradients) > 1 else 0.0
            if gradient_variance < self.config.dp_noise_threshold:
                errors.append(f"Gradient variance too low: {gradient_variance} < {self.config.dp_noise_threshold}")

            # Check for patterns that suggest tampering
            # (Real DP gradients should have some randomness)
            if len(flat_gradients) > 10:
                # Check for too many identical values (suspicious)
                from collections import Counter
                value_counts = Counter(flat_gradients)
                most_common_count = value_counts.most_common(1)[0][1]
                if most_common_count > len(flat_gradients) * 0.8:
                    errors.append("Too many identical gradient values (potential DP bypass)")

        except Exception as e:
            errors.append(f"DP bounds validation error: {str(e)}")

        return len(errors) == 0, errors


class RateLimiter:
    """Rate limiting for client updates."""

    def __init__(self, config: ValidationConfig):
        """Initialize rate limiter.

        Args:
            config: Validation configuration
        """
        self.config = config
        self.client_request_times: Dict[str, List[float]] = {}

    def check_rate_limit(self, client_id: str) -> Tuple[bool, Optional[str]]:
        """Check if client is within rate limits.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (is_allowed, error_message)
        """
        if not self.config.enable_rate_limiting:
            return True, None

        import time
        current_time = time.time()

        # Initialize client history if needed
        if client_id not in self.client_request_times:
            self.client_request_times[client_id] = []

        request_times = self.client_request_times[client_id]

        # Remove old requests
        minute_cutoff = current_time - 60
        hour_cutoff = current_time - 3600
        request_times[:] = [t for t in request_times if t >= hour_cutoff]

        # Count recent requests
        minute_count = sum(1 for t in request_times if t >= minute_cutoff)
        hour_count = len(request_times)

        # Check limits
        if minute_count >= self.config.max_updates_per_minute:
            return False, f"Rate limit exceeded: {minute_count} updates in last minute"

        if hour_count >= self.config.max_updates_per_hour:
            return False, f"Rate limit exceeded: {hour_count} updates in last hour"

        # Record this request
        request_times.append(current_time)

        return True, None


class UpdateValidator:
    """Main validation pipeline coordinator."""

    def __init__(self, outlier_detector: Optional[OutlierDetector] = None,
                 reputation_manager: Optional[ReputationManager] = None,
                 security_monitor: Optional[SecurityMonitor] = None,
                 config: Optional[ValidationConfig] = None):
        """Initialize update validator.

        Args:
            outlier_detector: Outlier detection component
            reputation_manager: Reputation management component
            security_monitor: Security monitoring component
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        self.outlier_detector = outlier_detector
        self.reputation_manager = reputation_manager
        self.security_monitor = security_monitor

        self.schema_validator = SchemaValidator(self.config)
        self.bounds_validator = BoundsValidator(self.config)
        self.rate_limiter = RateLimiter(self.config)

        self.validation_history: List[Dict[str, Any]] = []

    def validate_update(self, update: Dict[str, Any], client_id: str) -> ValidationResult:
        """Validate client update through complete pipeline.

        Args:
            update: Raw update data
            client_id: Client identifier

        Returns:
            Comprehensive validation result
        """
        errors = []
        error_types = []
        confidence = 1.0
        metadata = {"client_id": client_id, "validation_steps": []}

        try:
            # Step 1: Rate limiting
            if self.config.enable_rate_limiting:
                is_allowed, rate_error = self.rate_limiter.check_rate_limit(client_id)
                metadata["validation_steps"].append("rate_limiting")
                if not is_allowed:
                    errors.append(rate_error)
                    error_types.append(ValidationErrorType.RATE_LIMITED)

            # Step 2: Schema validation
            if self.config.enable_schema_validation:
                is_valid, schema_errors = self.schema_validator.validate_update_schema(update, client_id)
                metadata["validation_steps"].append("schema_validation")
                if not is_valid:
                    errors.extend(schema_errors)
                    error_types.extend([ValidationErrorType.SCHEMA_VALIDATION] * len(schema_errors))

                # Validate metadata
                is_meta_valid, meta_errors = self.schema_validator.validate_client_metadata(update)
                if not is_meta_valid:
                    errors.extend(meta_errors)
                    error_types.extend([ValidationErrorType.SCHEMA_VALIDATION] * len(meta_errors))

            # Early exit if schema validation fails
            if errors:
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    error_types=error_types,
                    sanitized_update=None,
                    confidence=confidence,
                    metadata=metadata
                )

            # Extract gradients for further validation
            gradients = update["weights"]

            # Step 3: Basic gradient validation (from utils)
            try:
                validate_gradient_update(gradients)
                metadata["validation_steps"].append("basic_gradient_validation")
            except Exception as e:
                errors.append(f"Basic gradient validation failed: {str(e)}")
                error_types.append(ValidationErrorType.MALFORMED_DATA)

            # Step 4: Bounds validation
            if self.config.enable_bounds_checking:
                is_bounds_valid, bounds_errors = self.bounds_validator.validate_gradient_bounds(gradients)
                metadata["validation_steps"].append("bounds_validation")
                if not is_bounds_valid:
                    errors.extend(bounds_errors)
                    error_types.extend([ValidationErrorType.BOUNDS_VIOLATION] * len(bounds_errors))

            # Step 5: DP bounds checking
            if self.config.enable_dp_bounds_checking:
                is_dp_valid, dp_errors = self.bounds_validator.check_differential_privacy_bounds(gradients)
                metadata["validation_steps"].append("dp_bounds_validation")
                if not is_dp_valid:
                    errors.extend(dp_errors)
                    error_types.extend([ValidationErrorType.DP_VIOLATION] * len(dp_errors))

            # Step 6: Reputation checking
            if self.config.enable_reputation_filtering and self.reputation_manager:
                is_rep_valid = self.reputation_manager.should_accept_update(client_id)
                metadata["validation_steps"].append("reputation_check")
                if not is_rep_valid:
                    reputation = self.reputation_manager.get_reputation(client_id)
                    errors.append(f"Client reputation too low: {reputation.score} < {self.config.min_reputation_threshold}")
                    error_types.append(ValidationErrorType.REPUTATION_TOO_LOW)

            # Step 7: Outlier detection (if no critical errors so far)
            if not errors and self.config.enable_outlier_detection and self.outlier_detector:
                detection_result = self.outlier_detector.detect_outliers([gradients])
                metadata["validation_steps"].append("outlier_detection")

                if detection_result.is_outlier(0):  # First (and only) update
                    outlier_score = detection_result.outlier_scores[0]
                    if outlier_score >= self.config.outlier_confidence_threshold:
                        errors.append(f"Update detected as outlier with score {outlier_score}")
                        error_types.append(ValidationErrorType.OUTLIER_DETECTED)
                        confidence *= (1.0 - outlier_score)

                metadata["outlier_score"] = detection_result.outlier_scores[0] if detection_result.outlier_scores else 0.0

            # Step 8: Sanitization
            sanitized_update = None
            if self.config.enable_sanitization:
                try:
                    sanitized_update = self.sanitize_update(gradients)
                    metadata["validation_steps"].append("sanitization")
                except Exception as e:
                    errors.append(f"Sanitization failed: {str(e)}")
                    error_types.append(ValidationErrorType.MALFORMED_DATA)

            # Determine final validation result
            is_valid = len(errors) == 0

            # Log security events for failed validations
            if not is_valid and self.security_monitor:
                event = create_malicious_update_event(
                    client_id=client_id,
                    reason=f"Validation failed: {'; '.join(errors[:3])}",  # First 3 errors
                    details={
                        "total_errors": len(errors),
                        "error_types": [et.value for et in error_types],
                        "confidence": confidence,
                        "metadata": metadata
                    }
                )
                self.security_monitor.log_event(event)

        except Exception as e:
            # Catch-all for unexpected validation errors
            errors.append(f"Validation pipeline error: {str(e)}")
            error_types.append(ValidationErrorType.MALFORMED_DATA)
            is_valid = False
            confidence = 0.0

        # Record validation history
        self.validation_history.append({
            "client_id": client_id,
            "is_valid": is_valid,
            "error_count": len(errors),
            "confidence": confidence,
            "timestamp": __import__("time").time()
        })

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            error_types=error_types,
            sanitized_update=sanitized_update if is_valid else None,
            confidence=confidence,
            metadata=metadata
        )

    def sanitize_update(self, gradients: List[List[float]]) -> List[List[float]]:
        """Sanitize gradient update.

        Args:
            gradients: Raw gradient update

        Returns:
            Sanitized gradient update
        """
        try:
            # Use existing sanitization from utils
            sanitized = sanitize_gradient_update(gradients)

            # Additional sanitization steps
            if self.config.clamp_extreme_values:
                sanitized = self._clamp_extreme_values(sanitized)

            if self.config.normalize_gradients:
                sanitized = self._normalize_gradients(sanitized)

            return sanitized

        except Exception as e:
            log_error(logger, f"Sanitization failed: {e}")
            raise

    def _clamp_extreme_values(self, gradients: List[List[float]]) -> List[List[float]]:
        """Clamp gradient values to reasonable range.

        Args:
            gradients: Gradient update

        Returns:
            Clamped gradient update
        """
        max_val = self.config.max_gradient_magnitude
        min_val = -max_val

        clamped = []
        for param_slice in gradients:
            clamped_slice = [max(min_val, min(max_val, value)) for value in param_slice]
            clamped.append(clamped_slice)

        return clamped

    def _normalize_gradients(self, gradients: List[List[float]]) -> List[List[float]]:
        """Normalize gradients by their L2 norm.

        Args:
            gradients: Gradient update

        Returns:
            Normalized gradient update
        """
        # Flatten for norm calculation
        flat_gradients = []
        for param_slice in gradients:
            flat_gradients.extend(param_slice)

        if not flat_gradients:
            return gradients

        # Compute L2 norm
        l2_norm = math.sqrt(sum(value**2 for value in flat_gradients))

        if l2_norm < 1e-10:  # Avoid division by zero
            return gradients

        # Normalize to unit norm
        normalization_factor = 1.0 / l2_norm
        normalized = []

        for param_slice in gradients:
            normalized_slice = [value * normalization_factor for value in param_slice]
            normalized.append(normalized_slice)

        return normalized

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation pipeline statistics.

        Returns:
            Dictionary with validation statistics
        """
        if not self.validation_history:
            return {"total_validations": 0}

        total = len(self.validation_history)
        valid_count = sum(1 for v in self.validation_history if v["is_valid"])
        invalid_count = total - valid_count

        recent_validations = self.validation_history[-100:]  # Last 100
        average_confidence = sum(v["confidence"] for v in recent_validations) / len(recent_validations)

        return {
            "total_validations": total,
            "valid_updates": valid_count,
            "invalid_updates": invalid_count,
            "validation_success_rate": valid_count / total,
            "average_confidence": average_confidence,
            "config": {
                "schema_validation": self.config.enable_schema_validation,
                "bounds_checking": self.config.enable_bounds_checking,
                "dp_bounds_checking": self.config.enable_dp_bounds_checking,
                "outlier_detection": self.config.enable_outlier_detection,
                "reputation_filtering": self.config.enable_reputation_filtering,
                "rate_limiting": self.config.enable_rate_limiting
            }
        }


def create_update_validator(enable_all_features: bool = True, **kwargs) -> UpdateValidator:
    """Factory function for creating update validator with components.

    Args:
        enable_all_features: Enable all validation features
        **kwargs: Additional configuration parameters

    Returns:
        Configured update validator
    """
    config = ValidationConfig(**kwargs)

    # Initialize components if features are enabled
    outlier_detector = None
    reputation_manager = None
    security_monitor = None

    if enable_all_features:
        try:
            from privacy_security.outlier_detection import OutlierDetector
            from privacy_security.reputation import get_reputation_manager
            from privacy_security.security_monitor import get_security_monitor

            outlier_detector = OutlierDetector()
            reputation_manager = get_reputation_manager()
            security_monitor = get_security_monitor()

        except ImportError as e:
            log_warning(logger, f"Could not import security components: {e}")

    return UpdateValidator(
        outlier_detector=outlier_detector,
        reputation_manager=reputation_manager,
        security_monitor=security_monitor,
        config=config
    )