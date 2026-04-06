"""
Outlier detection for identifying malicious or anomalous client updates.

This module provides statistical and machine learning-based outlier detection
methods to identify potentially malicious client updates before aggregation:
- Z-score detection: Statistical outliers based on standard deviations
- IQR detection: Interquartile range-based outlier identification
- Isolation Forest: ML-based anomaly detection
- Combined detection: Ensemble of multiple methods

All methods support both slice-based updates (current format) and full gradients.
"""

import numpy as np
import scipy.stats as stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Set
from dataclasses import dataclass
import threading

from utils.logging import setup_logger, log_info, log_warning, log_error
from utils.types import UpdateBatch
from utils.validation import validate_gradient_update

# Initialize logger
logger = setup_logger("privaloom.outlier_detection")


class OutlierDetectionMethod(Enum):
    """Supported outlier detection methods."""
    ZSCORE = "zscore"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    COMBINED = "combined"


@dataclass
class OutlierDetectionConfig:
    """Configuration for outlier detection algorithms."""
    method: OutlierDetectionMethod = OutlierDetectionMethod.COMBINED
    zscore_threshold: float = 3.0  # Standard deviations for Z-score detection
    iqr_multiplier: float = 1.5  # IQR multiplier for outlier detection
    isolation_contamination: float = 0.1  # Expected outlier fraction for Isolation Forest
    min_updates_for_ml: int = 5  # Minimum updates needed for ML-based detection
    ensemble_threshold: float = 0.5  # Fraction of methods that must agree for combined detection
    enable_adaptive_thresholds: bool = True  # Adapt thresholds based on history


class DetectionResult:
    """Result of outlier detection analysis."""

    def __init__(self, update_count: int):
        """Initialize detection result.

        Args:
            update_count: Total number of updates analyzed
        """
        self.update_count = update_count
        self.outlier_indices: Set[int] = set()
        self.outlier_scores: List[float] = [0.0] * update_count  # 0-1 anomaly scores
        self.method_results: Dict[str, Set[int]] = {}  # Results per method
        self.detection_metadata: Dict[str, Any] = {}

    def add_method_result(self, method: str, outliers: Set[int], scores: Optional[List[float]] = None) -> None:
        """Add outlier detection result from specific method.

        Args:
            method: Detection method name
            outliers: Set of outlier indices
            scores: Optional anomaly scores for each update
        """
        self.method_results[method] = outliers
        if scores is not None:
            # Combine scores (take maximum)
            for i, score in enumerate(scores):
                self.outlier_scores[i] = max(self.outlier_scores[i], score)

    def get_outlier_indices(self) -> List[int]:
        """Get list of outlier indices.

        Returns:
            Sorted list of outlier indices
        """
        return sorted(list(self.outlier_indices))

    def get_outlier_count(self) -> int:
        """Get total number of outliers detected.

        Returns:
            Number of outliers
        """
        return len(self.outlier_indices)

    def get_outlier_fraction(self) -> float:
        """Get fraction of updates that are outliers.

        Returns:
            Outlier fraction (0.0-1.0)
        """
        if self.update_count == 0:
            return 0.0
        return len(self.outlier_indices) / self.update_count

    def is_outlier(self, index: int) -> bool:
        """Check if specific update is an outlier.

        Args:
            index: Update index to check

        Returns:
            True if update is outlier
        """
        return index in self.outlier_indices


class StatisticalOutlierDetector:
    """Statistical outlier detection using Z-score and IQR methods."""

    def __init__(self, config: OutlierDetectionConfig):
        """Initialize statistical outlier detector.

        Args:
            config: Detection configuration
        """
        self.config = config
        self.detection_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def zscore_detection(self, updates: List[List[List[float]]], threshold: Optional[float] = None) -> Tuple[Set[int], List[float]]:
        """Detect outliers using Z-score method.

        Args:
            updates: Client gradient updates
            threshold: Z-score threshold (uses config default if None)

        Returns:
            Tuple of (outlier_indices, anomaly_scores)
        """
        if threshold is None:
            threshold = self.config.zscore_threshold

        num_clients = len(updates)
        if num_clients < 3:
            return set(), [0.0] * num_clients

        # Convert updates to feature vectors (flatten each client's update)
        feature_vectors = []
        for update in updates:
            flattened = []
            for param_slice in update:
                flattened.extend(param_slice)
            feature_vectors.append(flattened)

        feature_matrix = np.array(feature_vectors)

        # Compute Z-scores for each client across all coordinates
        outliers = set()
        anomaly_scores = []

        for client_idx in range(num_clients):
            client_vector = feature_matrix[client_idx]

            # For each coordinate, compute Z-score of this client vs others
            z_scores = []
            for coord_idx in range(feature_matrix.shape[1]):
                coord_values = feature_matrix[:, coord_idx]
                mean_val = np.mean(coord_values)
                std_val = np.std(coord_values)

                if std_val > 1e-10:  # Avoid division by zero
                    z_score = abs(client_vector[coord_idx] - mean_val) / std_val
                    z_scores.append(z_score)

            # Aggregate Z-scores (use maximum as overall anomaly score)
            if z_scores:
                max_z_score = max(z_scores)
                anomaly_score = min(1.0, max_z_score / (threshold + 1e-10))  # Normalize to 0-1
                anomaly_scores.append(anomaly_score)

                if max_z_score > threshold:
                    outliers.add(client_idx)
            else:
                anomaly_scores.append(0.0)

        return outliers, anomaly_scores

    def iqr_detection(self, updates: List[List[List[float]]],
                     q1: float = 0.25, q3: float = 0.75) -> Tuple[Set[int], List[float]]:
        """Detect outliers using Interquartile Range (IQR) method.

        Args:
            updates: Client gradient updates
            q1: First quartile
            q3: Third quartile

        Returns:
            Tuple of (outlier_indices, anomaly_scores)
        """
        num_clients = len(updates)
        if num_clients < 4:  # Need at least 4 for meaningful quartiles
            return set(), [0.0] * num_clients

        # Convert updates to feature vectors
        feature_vectors = []
        for update in updates:
            flattened = []
            for param_slice in update:
                flattened.extend(param_slice)
            feature_vectors.append(flattened)

        feature_matrix = np.array(feature_vectors)

        outliers = set()
        anomaly_scores = []

        for client_idx in range(num_clients):
            client_vector = feature_matrix[client_idx]

            # For each coordinate, check if client is outlier using IQR
            outlier_flags = []
            for coord_idx in range(feature_matrix.shape[1]):
                coord_values = feature_matrix[:, coord_idx]
                q1_val = np.percentile(coord_values, q1 * 100)
                q3_val = np.percentile(coord_values, q3 * 100)
                iqr = q3_val - q1_val

                if iqr > 1e-10:  # Avoid issues with zero IQR
                    lower_bound = q1_val - self.config.iqr_multiplier * iqr
                    upper_bound = q3_val + self.config.iqr_multiplier * iqr

                    value = client_vector[coord_idx]
                    is_outlier = value < lower_bound or value > upper_bound

                    # Distance from bounds as anomaly score component
                    if is_outlier:
                        dist_from_bounds = min(abs(value - lower_bound), abs(value - upper_bound))
                        score_component = min(1.0, dist_from_bounds / (iqr + 1e-10))
                    else:
                        score_component = 0.0

                    outlier_flags.append((is_outlier, score_component))

            # Aggregate results
            outlier_count = sum(1 for is_outlier, _ in outlier_flags if is_outlier)
            max_score = max((score for _, score in outlier_flags), default=0.0)

            anomaly_scores.append(max_score)

            # Mark as outlier if significant fraction of coordinates are outliers
            outlier_threshold = 0.1  # 10% of coordinates
            if outlier_count > len(outlier_flags) * outlier_threshold:
                outliers.add(client_idx)

        return outliers, anomaly_scores

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get statistics about recent detections.

        Returns:
            Dictionary with detection statistics
        """
        with self._lock:
            if not self.detection_history:
                return {"total_detections": 0}

            return {
                "total_detections": len(self.detection_history),
                "average_outliers_detected": np.mean([h["outliers_detected"] for h in self.detection_history]),
                "average_anomaly_score": np.mean([h.get("average_score", 0.0) for h in self.detection_history])
            }


class MLOutlierDetector:
    """Machine learning-based outlier detection using scikit-learn."""

    def __init__(self, config: OutlierDetectionConfig):
        """Initialize ML outlier detector.

        Args:
            config: Detection configuration
        """
        self.config = config
        self.detection_history: List[Dict[str, Any]] = []
        self._scaler = StandardScaler()
        self._lock = threading.Lock()

    def isolation_forest_detection(self, updates: List[List[List[float]]]) -> Tuple[Set[int], List[float]]:
        """Detect outliers using Isolation Forest algorithm.

        Args:
            updates: Client gradient updates

        Returns:
            Tuple of (outlier_indices, anomaly_scores)
        """
        num_clients = len(updates)
        if num_clients < self.config.min_updates_for_ml:
            return set(), [0.0] * num_clients

        try:
            # Convert updates to feature vectors
            feature_vectors = []
            for update in updates:
                flattened = []
                for param_slice in update:
                    flattened.extend(param_slice)
                feature_vectors.append(flattened)

            feature_matrix = np.array(feature_vectors)

            # Standardize features
            feature_matrix_scaled = self._scaler.fit_transform(feature_matrix)

            # Apply Isolation Forest
            isolation_forest = IsolationForest(
                contamination=self.config.isolation_contamination,
                random_state=42,
                n_estimators=100
            )

            outlier_predictions = isolation_forest.fit_predict(feature_matrix_scaled)
            anomaly_scores = -isolation_forest.score_samples(feature_matrix_scaled)

            # Normalize anomaly scores to 0-1 range
            if len(anomaly_scores) > 1:
                min_score, max_score = np.min(anomaly_scores), np.max(anomaly_scores)
                if max_score > min_score:
                    anomaly_scores = (anomaly_scores - min_score) / (max_score - min_score)
                else:
                    anomaly_scores = np.zeros_like(anomaly_scores)

            # Convert predictions to outlier indices (-1 = outlier, 1 = normal)
            outliers = {i for i, pred in enumerate(outlier_predictions) if pred == -1}

            return outliers, anomaly_scores.tolist()

        except Exception as e:
            log_error(logger, f"Isolation Forest detection failed: {e}")
            return set(), [0.0] * num_clients

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get statistics about recent ML detections.

        Returns:
            Dictionary with detection statistics
        """
        with self._lock:
            if not self.detection_history:
                return {"total_detections": 0}

            return {
                "total_detections": len(self.detection_history),
                "average_outliers_detected": np.mean([h["outliers_detected"] for h in self.detection_history]),
                "average_anomaly_score": np.mean([h.get("average_score", 0.0) for h in self.detection_history])
            }


class OutlierDetector:
    """Main outlier detector with support for multiple detection methods."""

    def __init__(self, config: Optional[OutlierDetectionConfig] = None):
        """Initialize outlier detector.

        Args:
            config: Detection configuration (uses defaults if None)
        """
        self.config = config or OutlierDetectionConfig()
        self.statistical_detector = StatisticalOutlierDetector(self.config)
        self.ml_detector = MLOutlierDetector(self.config)
        self.detection_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def detect_outliers(self, updates: List[List[List[float]]],
                       method: Optional[OutlierDetectionMethod] = None) -> DetectionResult:
        """Detect outliers in client updates using specified method.

        Args:
            updates: Client gradient updates
            method: Detection method (uses config default if None)

        Returns:
            Detection result with outlier indices and scores
        """
        if method is None:
            method = self.config.method

        # Validate inputs
        if not updates:
            return DetectionResult(0)

        num_clients = len(updates)
        result = DetectionResult(num_clients)

        # Validate each update
        for i, update in enumerate(updates):
            try:
                validate_gradient_update(update)
            except Exception as e:
                log_warning(logger, f"Invalid update from client {i}: {e}")
                result.outlier_indices.add(i)
                result.outlier_scores[i] = 1.0  # Maximum anomaly score for invalid updates

        if method == OutlierDetectionMethod.ZSCORE:
            outliers, scores = self.statistical_detector.zscore_detection(updates)
            result.add_method_result("zscore", outliers, scores)
            result.outlier_indices.update(outliers)

        elif method == OutlierDetectionMethod.IQR:
            outliers, scores = self.statistical_detector.iqr_detection(updates)
            result.add_method_result("iqr", outliers, scores)
            result.outlier_indices.update(outliers)

        elif method == OutlierDetectionMethod.ISOLATION_FOREST:
            outliers, scores = self.ml_detector.isolation_forest_detection(updates)
            result.add_method_result("isolation_forest", outliers, scores)
            result.outlier_indices.update(outliers)

        elif method == OutlierDetectionMethod.COMBINED:
            # Run all methods and combine results
            all_outliers = {}
            all_scores = {}

            # Z-score detection
            try:
                outliers, scores = self.statistical_detector.zscore_detection(updates)
                all_outliers["zscore"] = outliers
                all_scores["zscore"] = scores
                result.add_method_result("zscore", outliers, scores)
            except Exception as e:
                log_warning(logger, f"Z-score detection failed: {e}")

            # IQR detection
            try:
                outliers, scores = self.statistical_detector.iqr_detection(updates)
                all_outliers["iqr"] = outliers
                all_scores["iqr"] = scores
                result.add_method_result("iqr", outliers, scores)
            except Exception as e:
                log_warning(logger, f"IQR detection failed: {e}")

            # Isolation Forest (if enough data)
            if num_clients >= self.config.min_updates_for_ml:
                try:
                    outliers, scores = self.ml_detector.isolation_forest_detection(updates)
                    all_outliers["isolation_forest"] = outliers
                    all_scores["isolation_forest"] = scores
                    result.add_method_result("isolation_forest", outliers, scores)
                except Exception as e:
                    log_warning(logger, f"Isolation Forest detection failed: {e}")

            # Ensemble voting: require multiple methods to agree
            if all_outliers:
                vote_counts = {}
                for client_idx in range(num_clients):
                    vote_counts[client_idx] = sum(1 for outliers in all_outliers.values()
                                                if client_idx in outliers)

                # Apply ensemble threshold
                threshold_votes = max(1, int(self.config.ensemble_threshold * len(all_outliers)))
                ensemble_outliers = {idx for idx, votes in vote_counts.items()
                                   if votes >= threshold_votes}

                result.outlier_indices.update(ensemble_outliers)

        # Record detection metadata
        result.detection_metadata = {
            "method": method.value,
            "total_updates": num_clients,
            "outliers_detected": len(result.outlier_indices),
            "outlier_fraction": result.get_outlier_fraction(),
            "config": {
                "zscore_threshold": self.config.zscore_threshold,
                "iqr_multiplier": self.config.iqr_multiplier,
                "isolation_contamination": self.config.isolation_contamination
            }
        }

        # Update history
        with self._lock:
            self.detection_history.append({
                "method": method.value,
                "outliers_detected": len(result.outlier_indices),
                "total_updates": num_clients,
                "average_score": np.mean(result.outlier_scores) if result.outlier_scores else 0.0
            })

        log_info(logger, "Outlier detection completed", extra=result.detection_metadata)

        return result

    def score_updates(self, updates: List[List[List[float]]]) -> List[float]:
        """Get anomaly scores for updates without binary outlier classification.

        Args:
            updates: Client gradient updates

        Returns:
            List of anomaly scores (0-1) for each update
        """
        result = self.detect_outliers(updates, OutlierDetectionMethod.COMBINED)
        return result.outlier_scores

    def update_adaptive_thresholds(self, false_positive_rate: float, false_negative_rate: float) -> None:
        """Update detection thresholds based on feedback.

        Args:
            false_positive_rate: Rate of honest clients flagged as outliers
            false_negative_rate: Rate of malicious clients not detected
        """
        if not self.config.enable_adaptive_thresholds:
            return

        # Adjust Z-score threshold
        if false_positive_rate > 0.05:  # Too many false positives
            self.config.zscore_threshold *= 1.1  # Increase threshold
        elif false_negative_rate > 0.1:  # Too many false negatives
            self.config.zscore_threshold *= 0.9  # Decrease threshold

        # Adjust IQR multiplier
        if false_positive_rate > 0.05:
            self.config.iqr_multiplier *= 1.1
        elif false_negative_rate > 0.1:
            self.config.iqr_multiplier *= 0.9

        # Clamp thresholds to reasonable ranges
        self.config.zscore_threshold = max(1.5, min(5.0, self.config.zscore_threshold))
        self.config.iqr_multiplier = max(1.0, min(3.0, self.config.iqr_multiplier))

        log_info(logger, "Adaptive thresholds updated", extra={
            "new_zscore_threshold": self.config.zscore_threshold,
            "new_iqr_multiplier": self.config.iqr_multiplier,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate
        })

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get comprehensive detection statistics.

        Returns:
            Dictionary with detection statistics
        """
        with self._lock:
            stats = {
                "total_detections": len(self.detection_history),
                "config": {
                    "method": self.config.method.value,
                    "zscore_threshold": self.config.zscore_threshold,
                    "iqr_multiplier": self.config.iqr_multiplier,
                    "isolation_contamination": self.config.isolation_contamination
                }
            }

            if self.detection_history:
                stats.update({
                    "average_outliers_detected": np.mean([h["outliers_detected"] for h in self.detection_history]),
                    "average_outlier_fraction": np.mean([h["outliers_detected"] / h["total_updates"]
                                                       for h in self.detection_history]),
                    "average_anomaly_score": np.mean([h.get("average_score", 0.0) for h in self.detection_history])
                })

            # Add component stats
            stats["statistical_detector"] = self.statistical_detector.get_detection_stats()
            stats["ml_detector"] = self.ml_detector.get_detection_stats()

            return stats


def create_outlier_detector(method: OutlierDetectionMethod = OutlierDetectionMethod.COMBINED,
                          **kwargs) -> OutlierDetector:
    """Factory function for creating outlier detector.

    Args:
        method: Detection method to use
        **kwargs: Additional configuration parameters

    Returns:
        Configured outlier detector
    """
    config = OutlierDetectionConfig(method=method, **kwargs)
    return OutlierDetector(config)