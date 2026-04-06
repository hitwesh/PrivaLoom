"""
Robust aggregation algorithms for Byzantine-fault-tolerant federated learning.

This module implements various robust aggregation methods that can handle
malicious client updates while maintaining model convergence:
- Krum: Select update closest to majority using pairwise L2 distances
- Trimmed Mean: Remove top/bottom β% of values per coordinate, average remaining
- Median: Coordinate-wise median (most robust against outliers)
- Bulyan: Multi-round Krum + trimmed mean combination
- FedAvg: Standard averaging for comparison/fallback

All algorithms are designed to be thread-safe and compatible with the existing
differential privacy guarantees from dp_engine.py.
"""

import math
import torch
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from utils.logging import setup_logger, log_info, log_error
from utils.types import GradientUpdate, UpdateBatch

# Initialize logger
logger = setup_logger("privaloom.robust_aggregation")


class AggregationMethod(Enum):
    """Supported robust aggregation methods."""
    FEDAVG = "fedavg"
    KRUM = "krum"
    TRIMMED_MEAN = "trimmed_mean"
    MEDIAN = "median"
    BULYAN = "bulyan"


@dataclass
class AggregationConfig:
    """Configuration for robust aggregation algorithms."""
    method: AggregationMethod = AggregationMethod.TRIMMED_MEAN
    byzantine_tolerance: float = 0.2  # Expected fraction of malicious clients
    trim_fraction: float = 0.2  # Fraction to trim for trimmed_mean
    krum_k: int = 5  # Nearest neighbors for Krum
    min_updates_required: int = 3  # Minimum updates needed for robust aggregation
    enable_weighted_aggregation: bool = True  # Use reputation weights


class RobustAggregator(ABC):
    """Abstract base class for robust aggregation algorithms."""

    def __init__(self, config: AggregationConfig):
        """Initialize robust aggregator with configuration.

        Args:
            config: Aggregation configuration parameters
        """
        self.config = config
        self.aggregation_history: List[Dict[str, Any]] = []

    @abstractmethod
    def aggregate(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> List[List[float]]:
        """Aggregate client updates using robust method.

        Args:
            updates: List of client gradient updates (each is list of parameter slices)
            weights: Optional client reputation weights (0.0-1.0)

        Returns:
            Aggregated update as list of parameter slices

        Raises:
            ValueError: If insufficient updates or invalid parameters
        """
        pass

    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get statistics about recent aggregations.

        Returns:
            Dictionary with aggregation statistics
        """
        if not self.aggregation_history:
            return {"total_aggregations": 0}

        return {
            "total_aggregations": len(self.aggregation_history),
            "average_clients_per_round": np.mean([h["num_clients"] for h in self.aggregation_history]),
            "average_outliers_removed": np.mean([h.get("outliers_removed", 0) for h in self.aggregation_history]),
            "method": self.config.method.value
        }

    def _validate_inputs(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> None:
        """Validate aggregation inputs.

        Args:
            updates: Client gradient updates
            weights: Optional reputation weights

        Raises:
            ValueError: If inputs are invalid
        """
        if not updates:
            raise ValueError("No updates provided for aggregation")

        if len(updates) < self.config.min_updates_required:
            raise ValueError(f"Insufficient updates: {len(updates)} < {self.config.min_updates_required}")

        # Check all updates have same structure
        first_update_shape = [len(param_slice) for param_slice in updates[0]]
        for i, update in enumerate(updates[1:], 1):
            update_shape = [len(param_slice) for param_slice in update]
            if update_shape != first_update_shape:
                raise ValueError(f"Update {i} has different shape: {update_shape} vs {first_update_shape}")

        # Validate weights if provided
        if weights is not None:
            if len(weights) != len(updates):
                raise ValueError(f"Number of weights ({len(weights)}) != number of updates ({len(updates)})")
            if any(w < 0 or w > 1 for w in weights):
                raise ValueError("All weights must be between 0 and 1")

    def _convert_to_tensors(self, updates: List[List[List[float]]]) -> List[torch.Tensor]:
        """Convert gradient updates to PyTorch tensors for computation.

        Args:
            updates: Client gradient updates

        Returns:
            List of concatenated tensor updates (one per client)
        """
        tensor_updates = []
        for update in updates:
            # Concatenate all parameter slices for this client into single tensor
            flattened = []
            for param_slice in update:
                flattened.extend(param_slice)
            tensor_updates.append(torch.tensor(flattened, dtype=torch.float32))
        return tensor_updates

    def _convert_from_tensor(self, tensor_update: torch.Tensor, reference_structure: List[List[float]]) -> List[List[float]]:
        """Convert aggregated tensor back to original gradient update structure.

        Args:
            tensor_update: Aggregated tensor
            reference_structure: Original structure to match

        Returns:
            Gradient update in original list-of-lists format
        """
        result = []
        offset = 0
        for param_slice in reference_structure:
            slice_length = len(param_slice)
            result.append(tensor_update[offset:offset+slice_length].tolist())
            offset += slice_length
        return result


class FedAvgAggregator(RobustAggregator):
    """Standard FedAvg aggregation (simple weighted averaging)."""

    def aggregate(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> List[List[float]]:
        """Aggregate updates using simple weighted averaging.

        Args:
            updates: Client gradient updates
            weights: Optional reputation weights

        Returns:
            Averaged gradient update
        """
        self._validate_inputs(updates, weights)

        num_clients = len(updates)

        # Use uniform weights if none provided
        if weights is None:
            weights = [1.0] * num_clients

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            raise ValueError("All weights are zero")
        weights = [w / total_weight for w in weights]

        # Weighted averaging
        aggregated = []
        for param_idx in range(len(updates[0])):
            param_slice = []
            for elem_idx in range(len(updates[0][param_idx])):
                weighted_sum = sum(updates[client_idx][param_idx][elem_idx] * weights[client_idx]
                                 for client_idx in range(num_clients))
                param_slice.append(weighted_sum)
            aggregated.append(param_slice)

        # Record aggregation history
        self.aggregation_history.append({
            "method": "fedavg",
            "num_clients": num_clients,
            "outliers_removed": 0,
            "effective_clients": num_clients
        })

        log_info(logger, "FedAvg aggregation completed",
                 num_clients=num_clients, weighted=weights is not None)

        return aggregated


class TrimmedMeanAggregator(RobustAggregator):
    """Trimmed mean aggregation - removes top and bottom β% of values per coordinate."""

    def aggregate(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> List[List[float]]:
        """Aggregate updates using trimmed mean.

        Args:
            updates: Client gradient updates
            weights: Optional reputation weights (currently ignored for trimmed mean)

        Returns:
            Trimmed mean aggregated update
        """
        self._validate_inputs(updates, weights)

        num_clients = len(updates)
        trim_count = max(1, int(self.config.trim_fraction * num_clients))

        if num_clients - 2 * trim_count < 1:
            log_error(logger, f"Too few clients ({num_clients}) for trim fraction {self.config.trim_fraction}")
            # Fallback to simple averaging
            fallback = FedAvgAggregator(self.config)
            return fallback.aggregate(updates, weights)

        aggregated = []
        total_trimmed = 0

        for param_idx in range(len(updates[0])):
            param_slice = []
            for elem_idx in range(len(updates[0][param_idx])):
                # Collect values for this coordinate across all clients
                values = [updates[client_idx][param_idx][elem_idx] for client_idx in range(num_clients)]

                # Sort and trim
                values.sort()
                trimmed_values = values[trim_count:-trim_count] if trim_count > 0 else values

                # Compute mean of remaining values
                mean_value = sum(trimmed_values) / len(trimmed_values)
                param_slice.append(mean_value)

                total_trimmed += 2 * trim_count

            aggregated.append(param_slice)

        outliers_removed = 2 * trim_count  # Total clients trimmed per coordinate

        # Record aggregation history
        self.aggregation_history.append({
            "method": "trimmed_mean",
            "num_clients": num_clients,
            "outliers_removed": outliers_removed,
            "effective_clients": num_clients - outliers_removed,
            "trim_fraction": self.config.trim_fraction
        })

        log_info(logger, "Trimmed mean aggregation completed",
                 num_clients=num_clients, trim_count=trim_count,
                 outliers_removed=outliers_removed)

        return aggregated


class MedianAggregator(RobustAggregator):
    """Coordinate-wise median aggregation - most robust against outliers."""

    def aggregate(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> List[List[float]]:
        """Aggregate updates using coordinate-wise median.

        Args:
            updates: Client gradient updates
            weights: Optional reputation weights (currently ignored for median)

        Returns:
            Median aggregated update
        """
        self._validate_inputs(updates, weights)

        num_clients = len(updates)

        aggregated = []

        for param_idx in range(len(updates[0])):
            param_slice = []
            for elem_idx in range(len(updates[0][param_idx])):
                # Collect values for this coordinate across all clients
                values = [updates[client_idx][param_idx][elem_idx] for client_idx in range(num_clients)]

                # Compute median
                values.sort()
                if len(values) % 2 == 1:
                    median_value = values[len(values) // 2]
                else:
                    mid_idx = len(values) // 2
                    median_value = (values[mid_idx - 1] + values[mid_idx]) / 2

                param_slice.append(median_value)

            aggregated.append(param_slice)

        # Record aggregation history
        self.aggregation_history.append({
            "method": "median",
            "num_clients": num_clients,
            "outliers_removed": 0,  # Median doesn't explicitly remove outliers
            "effective_clients": num_clients
        })

        log_info(logger, "Median aggregation completed",
                 num_clients=num_clients)

        return aggregated


class KrumAggregator(RobustAggregator):
    """Krum aggregation - selects update closest to majority using pairwise L2 distances."""

    def aggregate(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> List[List[float]]:
        """Aggregate updates using Krum algorithm.

        Args:
            updates: Client gradient updates
            weights: Optional reputation weights (used as tie-breaker)

        Returns:
            Selected update from honest majority
        """
        self._validate_inputs(updates, weights)

        num_clients = len(updates)

        # Need sufficient clients for Krum
        if num_clients < 3:
            log_error(logger, f"Too few clients ({num_clients}) for Krum aggregation")
            fallback = FedAvgAggregator(self.config)
            return fallback.aggregate(updates, weights)

        # Convert to tensors for efficient computation
        tensor_updates = self._convert_to_tensors(updates)

        # Compute pairwise L2 distances
        distances = torch.zeros(num_clients, num_clients)
        for i in range(num_clients):
            for j in range(i + 1, num_clients):
                dist = torch.norm(tensor_updates[i] - tensor_updates[j], p=2)
                distances[i, j] = distances[j, i] = dist

        # For each client, compute sum of distances to k-nearest neighbors
        k = min(self.config.krum_k, num_clients - 1)
        scores = []

        for i in range(num_clients):
            # Get distances from client i to all others, excluding self
            client_distances = distances[i, :].clone()
            client_distances[i] = float('inf')  # Exclude self-distance

            # Sum of k smallest distances
            k_nearest_distances, _ = torch.topk(client_distances, k, largest=False)
            score = k_nearest_distances.sum().item()
            scores.append(score)

        # Select client with minimum score (closest to majority)
        selected_idx = scores.index(min(scores))

        # Use weights as tie-breaker if provided
        if weights is not None:
            min_score = min(scores)
            candidates = [i for i, score in enumerate(scores) if abs(score - min_score) < 1e-6]
            if len(candidates) > 1:
                # Among tied candidates, select highest weighted client
                best_weight = max(weights[i] for i in candidates)
                selected_idx = next(i for i in candidates if weights[i] == best_weight)

        selected_update = updates[selected_idx]

        # Record aggregation history
        self.aggregation_history.append({
            "method": "krum",
            "num_clients": num_clients,
            "selected_client": selected_idx,
            "outliers_removed": num_clients - 1,  # All but selected are considered "removed"
            "effective_clients": 1,
            "krum_score": scores[selected_idx]
        })

        log_info(logger, "Krum aggregation completed",
                 num_clients=num_clients, selected_client=selected_idx,
                 krum_score=scores[selected_idx])

        return selected_update


class BulyanAggregator(RobustAggregator):
    """Bulyan aggregation - multi-round Krum + trimmed mean combination."""

    def aggregate(self, updates: List[List[List[float]]], weights: Optional[List[float]] = None) -> List[List[float]]:
        """Aggregate updates using Bulyan algorithm.

        Args:
            updates: Client gradient updates
            weights: Optional reputation weights

        Returns:
            Bulyan aggregated update
        """
        self._validate_inputs(updates, weights)

        num_clients = len(updates)

        # Bulyan requires sufficient clients
        if num_clients < 4:
            log_error(logger, f"Too few clients ({num_clients}) for Bulyan aggregation")
            fallback = TrimmedMeanAggregator(self.config)
            return fallback.aggregate(updates, weights)

        # Estimate number of Byzantine clients
        f = int(self.config.byzantine_tolerance * num_clients)
        theta = num_clients - f  # Number of honest clients

        # Step 1: Multi-round Krum to select θ closest updates
        if theta >= num_clients:
            # All clients are considered honest
            selected_updates = updates
            selected_weights = weights
        else:
            # Need to select subset using Krum
            tensor_updates = self._convert_to_tensors(updates)

            # Compute pairwise distances (reuse from Krum)
            distances = torch.zeros(num_clients, num_clients)
            for i in range(num_clients):
                for j in range(i + 1, num_clients):
                    dist = torch.norm(tensor_updates[i] - tensor_updates[j], p=2)
                    distances[i, j] = distances[j, i] = dist

            # Select θ updates with best Krum scores
            k = min(self.config.krum_k, num_clients - 1)
            scores = []

            for i in range(num_clients):
                client_distances = distances[i, :].clone()
                client_distances[i] = float('inf')
                k_nearest_distances, _ = torch.topk(client_distances, k, largest=False)
                score = k_nearest_distances.sum().item()
                scores.append((score, i))

            # Sort by score and select best θ clients
            scores.sort()
            selected_indices = [idx for _, idx in scores[:theta]]

            selected_updates = [updates[i] for i in selected_indices]
            selected_weights = [weights[i] for i in selected_indices] if weights else None

        # Step 2: Apply trimmed mean to selected updates
        trimmed_aggregator = TrimmedMeanAggregator(self.config)
        aggregated = trimmed_aggregator.aggregate(selected_updates, selected_weights)

        # Record aggregation history
        self.aggregation_history.append({
            "method": "bulyan",
            "num_clients": num_clients,
            "selected_clients": len(selected_updates),
            "outliers_removed": num_clients - len(selected_updates),
            "effective_clients": len(selected_updates),
            "byzantine_tolerance": f
        })

        log_info(logger, "Bulyan aggregation completed",
                 num_clients=num_clients, selected_clients=len(selected_updates),
                 byzantine_estimate=f)

        return aggregated


class AggregatorFactory:
    """Factory for creating robust aggregation instances."""

    @staticmethod
    def create(method: AggregationMethod, config: Optional[AggregationConfig] = None) -> RobustAggregator:
        """Create aggregator instance for specified method.

        Args:
            method: Aggregation method to use
            config: Optional configuration (uses defaults if not provided)

        Returns:
            Configured aggregator instance

        Raises:
            ValueError: If method is not supported
        """
        if config is None:
            config = AggregationConfig(method=method)
        else:
            config.method = method

        if method == AggregationMethod.FEDAVG:
            return FedAvgAggregator(config)
        elif method == AggregationMethod.KRUM:
            return KrumAggregator(config)
        elif method == AggregationMethod.TRIMMED_MEAN:
            return TrimmedMeanAggregator(config)
        elif method == AggregationMethod.MEDIAN:
            return MedianAggregator(config)
        elif method == AggregationMethod.BULYAN:
            return BulyanAggregator(config)
        else:
            raise ValueError(f"Unsupported aggregation method: {method}")

    @staticmethod
    def get_available_methods() -> List[AggregationMethod]:
        """Get list of all available aggregation methods.

        Returns:
            List of supported aggregation methods
        """
        return list(AggregationMethod)

    @staticmethod
    def get_method_info(method: AggregationMethod) -> Dict[str, Any]:
        """Get information about specific aggregation method.

        Args:
            method: Aggregation method

        Returns:
            Dictionary with method information
        """
        info = {
            AggregationMethod.FEDAVG: {
                "name": "FedAvg",
                "description": "Standard federated averaging",
                "byzantine_tolerance": 0.0,
                "computational_cost": "Low",
                "robustness": "None"
            },
            AggregationMethod.KRUM: {
                "name": "Krum",
                "description": "Selects update closest to majority",
                "byzantine_tolerance": 0.33,
                "computational_cost": "High",
                "robustness": "High"
            },
            AggregationMethod.TRIMMED_MEAN: {
                "name": "Trimmed Mean",
                "description": "Removes extreme values per coordinate",
                "byzantine_tolerance": 0.5,
                "computational_cost": "Medium",
                "robustness": "High"
            },
            AggregationMethod.MEDIAN: {
                "name": "Coordinate Median",
                "description": "Coordinate-wise median (most robust)",
                "byzantine_tolerance": 0.5,
                "computational_cost": "Low",
                "robustness": "Highest"
            },
            AggregationMethod.BULYAN: {
                "name": "Bulyan",
                "description": "Multi-round Krum + trimmed mean",
                "byzantine_tolerance": 0.33,
                "computational_cost": "Very High",
                "robustness": "Very High"
            }
        }

        return info.get(method, {"name": "Unknown", "description": "Unknown method"})


def benchmark_aggregation_methods(updates: List[List[List[float]]],
                                weights: Optional[List[float]] = None) -> Dict[str, Any]:
    """Benchmark all aggregation methods for performance comparison.

    Args:
        updates: Client gradient updates
        weights: Optional reputation weights

    Returns:
        Dictionary with benchmark results
    """
    import time

    results = {}
    config = AggregationConfig()

    for method in AggregationMethod:
        try:
            aggregator = AggregatorFactory.create(method, config)

            start_time = time.time()
            aggregated = aggregator.aggregate(updates, weights)
            end_time = time.time()

            results[method.value] = {
                "success": True,
                "duration_ms": (end_time - start_time) * 1000,
                "output_shape": [len(param_slice) for param_slice in aggregated]
            }

        except Exception as e:
            results[method.value] = {
                "success": False,
                "error": str(e),
                "duration_ms": None
            }

    return results