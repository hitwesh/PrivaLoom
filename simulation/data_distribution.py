"""
Data distribution management for realistic federated learning simulation.

This module handles distribution of data across simulated clients with support
for IID, non-IID, and pathological data distributions that reflect real-world
federated learning scenarios.
"""

import random
import numpy as np
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from utils.logging import setup_logger, log_info
from utils.types import GradientUpdate

# Initialize logger
logger = setup_logger("privaloom.simulation.data_distribution")


class DataDistributionType(Enum):
    """Types of data distribution patterns across clients."""
    IID = "iid"                    # Independent and identically distributed
    NON_IID = "non_iid"           # Heterogeneous distribution
    PATHOLOGICAL = "pathological"  # Extreme heterogeneity


@dataclass
class ClientDataConfig:
    """Configuration for data assigned to a specific client."""
    client_id: str
    data_samples: int
    data_quality: float  # 0.0-1.0, affects gradient quality
    class_distribution: Optional[Dict[int, float]] = None  # For non-IID scenarios
    noise_level: float = 0.0  # Additional noise in gradients
    bias_direction: Optional[List[float]] = None  # Systematic bias in gradients


@dataclass
class DataDistributionConfig:
    """Configuration for overall data distribution strategy."""
    distribution_type: DataDistributionType = DataDistributionType.NON_IID
    heterogeneity_alpha: float = 0.5  # Dirichlet parameter for non-IID (lower = more heterogeneous)
    samples_per_client: int = 1000
    min_samples_per_client: int = 100
    max_samples_per_client: int = 2000
    quality_variation: bool = True  # Whether to vary data quality across clients
    num_classes: int = 10  # Number of classes in the dataset (for classification)
    noise_clients_fraction: float = 0.1  # Fraction of clients with noisy data


class DataDistributor:
    """Manages realistic data distribution across simulated clients."""

    def __init__(self, config: DataDistributionConfig):
        """Initialize data distributor.

        Args:
            config: Data distribution configuration
        """
        self.config = config
        self.client_data_configs: Dict[str, ClientDataConfig] = {}

        log_info(logger, "DataDistributor initialized",
                 distribution_type=config.distribution_type.value,
                 heterogeneity_alpha=config.heterogeneity_alpha,
                 samples_per_client=config.samples_per_client)

    def distribute_data(self, client_ids: List[str]) -> Dict[str, ClientDataConfig]:
        """Distribute data configurations across clients.

        Args:
            client_ids: List of client identifiers

        Returns:
            Dictionary mapping client IDs to their data configurations
        """
        num_clients = len(client_ids)

        if self.config.distribution_type == DataDistributionType.IID:
            self.client_data_configs = self._distribute_iid(client_ids)
        elif self.config.distribution_type == DataDistributionType.NON_IID:
            self.client_data_configs = self._distribute_non_iid(client_ids)
        elif self.config.distribution_type == DataDistributionType.PATHOLOGICAL:
            self.client_data_configs = self._distribute_pathological(client_ids)

        log_info(logger, f"Data distributed to {num_clients} clients",
                 distribution_type=self.config.distribution_type.value)

        return self.client_data_configs

    def _distribute_iid(self, client_ids: List[str]) -> Dict[str, ClientDataConfig]:
        """Distribute data using IID (identical) distribution."""
        configs = {}

        for client_id in client_ids:
            # All clients get similar data distribution
            data_samples = random.randint(
                max(self.config.min_samples_per_client, int(self.config.samples_per_client * 0.8)),
                min(self.config.max_samples_per_client, int(self.config.samples_per_client * 1.2))
            )

            # Uniform class distribution
            class_distribution = {i: 1.0 / self.config.num_classes for i in range(self.config.num_classes)}

            # Slight quality variation even in IID
            data_quality = 1.0
            if self.config.quality_variation:
                data_quality = random.uniform(0.8, 1.0)

            configs[client_id] = ClientDataConfig(
                client_id=client_id,
                data_samples=data_samples,
                data_quality=data_quality,
                class_distribution=class_distribution,
                noise_level=0.0
            )

        return configs

    def _distribute_non_iid(self, client_ids: List[str]) -> Dict[str, ClientDataConfig]:
        """Distribute data using non-IID (heterogeneous) distribution."""
        configs = {}
        num_clients = len(client_ids)

        # Generate Dirichlet distribution for class allocation
        # Lower alpha = more heterogeneous
        alpha = [self.config.heterogeneity_alpha] * self.config.num_classes
        class_distributions = np.random.dirichlet(alpha, num_clients)

        for i, client_id in enumerate(client_ids):
            # Variable sample sizes
            data_samples = random.randint(
                self.config.min_samples_per_client,
                self.config.max_samples_per_client
            )

            # Heterogeneous class distribution from Dirichlet
            class_distribution = {
                j: float(class_distributions[i][j]) for j in range(self.config.num_classes)
            }

            # Variable data quality
            data_quality = 1.0
            if self.config.quality_variation:
                data_quality = random.uniform(0.6, 1.0)

            # Some clients get noisy data
            noise_level = 0.0
            if random.random() < self.config.noise_clients_fraction:
                noise_level = random.uniform(0.01, 0.05)

            configs[client_id] = ClientDataConfig(
                client_id=client_id,
                data_samples=data_samples,
                data_quality=data_quality,
                class_distribution=class_distribution,
                noise_level=noise_level
            )

        return configs

    def _distribute_pathological(self, client_ids: List[str]) -> Dict[str, ClientDataConfig]:
        """Distribute data using pathological (extreme) non-IID distribution."""
        configs = {}
        num_clients = len(client_ids)
        classes_per_client = max(1, self.config.num_classes // 4)  # Each client gets few classes

        # Assign classes to clients
        client_classes = {}
        for i, client_id in enumerate(client_ids):
            start_class = (i * classes_per_client) % self.config.num_classes
            assigned_classes = [
                (start_class + j) % self.config.num_classes
                for j in range(classes_per_client)
            ]
            client_classes[client_id] = assigned_classes

        for client_id in client_ids:
            # Highly variable sample sizes
            data_samples = random.randint(
                self.config.min_samples_per_client,
                self.config.max_samples_per_client
            )

            # Extreme class concentration
            assigned_classes = client_classes[client_id]
            class_distribution = {i: 0.0 for i in range(self.config.num_classes)}

            for cls in assigned_classes:
                class_distribution[cls] = 1.0 / len(assigned_classes)

            # High quality variation
            data_quality = random.uniform(0.4, 1.0) if self.config.quality_variation else 1.0

            # Higher noise for some clients
            noise_level = 0.0
            if random.random() < self.config.noise_clients_fraction * 2:  # Double the noise fraction
                noise_level = random.uniform(0.02, 0.1)

            # Add systematic bias for pathological cases
            bias_direction = None
            if random.random() < 0.3:  # 30% of clients have systematic bias
                bias_direction = [random.uniform(-0.01, 0.01) for _ in range(5)]  # 5 parameter groups

            configs[client_id] = ClientDataConfig(
                client_id=client_id,
                data_samples=data_samples,
                data_quality=data_quality,
                class_distribution=class_distribution,
                noise_level=noise_level,
                bias_direction=bias_direction
            )

        return configs

    def generate_client_gradients(self, client_id: str, base_gradients: GradientUpdate,
                                round_number: int) -> GradientUpdate:
        """Generate client-specific gradients based on data distribution.

        Args:
            client_id: Client identifier
            base_gradients: Base gradient template
            round_number: Current federated learning round

        Returns:
            Modified gradients reflecting client's data distribution
        """
        if client_id not in self.client_data_configs:
            log_info(logger, f"No data config for client {client_id}, using base gradients")
            return base_gradients

        config = self.client_data_configs[client_id]
        modified_gradients = []

        for param_idx, param_slice in enumerate(base_gradients):
            modified_slice = []

            for value in param_slice:
                # Apply data quality scaling
                modified_value = value * config.data_quality

                # Add noise if configured
                if config.noise_level > 0:
                    noise = random.gauss(0, config.noise_level)
                    modified_value += noise

                # Apply systematic bias if present
                if config.bias_direction and param_idx < len(config.bias_direction):
                    modified_value += config.bias_direction[param_idx]

                modified_slice.append(modified_value)

            modified_gradients.append(modified_slice)

        return modified_gradients

    def get_distribution_stats(self) -> Dict[str, Any]:
        """Get statistics about the current data distribution.

        Returns:
            Dictionary with distribution statistics
        """
        if not self.client_data_configs:
            return {"error": "No data distributed yet"}

        configs = list(self.client_data_configs.values())
        total_clients = len(configs)

        # Sample size statistics
        sample_sizes = [config.data_samples for config in configs]
        avg_samples = sum(sample_sizes) / total_clients
        min_samples = min(sample_sizes)
        max_samples = max(sample_sizes)

        # Quality statistics
        qualities = [config.data_quality for config in configs]
        avg_quality = sum(qualities) / total_clients
        min_quality = min(qualities)

        # Noise statistics
        noise_levels = [config.noise_level for config in configs if config.noise_level > 0]
        noisy_clients = len(noise_levels)

        # Class distribution analysis (for non-IID)
        class_entropy = 0.0
        if self.config.distribution_type != DataDistributionType.IID:
            entropies = []
            for config in configs:
                if config.class_distribution:
                    # Calculate entropy of class distribution
                    probs = list(config.class_distribution.values())
                    entropy = -sum(p * np.log2(p + 1e-10) for p in probs if p > 0)
                    entropies.append(entropy)
            class_entropy = sum(entropies) / len(entropies) if entropies else 0.0

        return {
            "distribution_type": self.config.distribution_type.value,
            "total_clients": total_clients,
            "sample_statistics": {
                "avg_samples_per_client": avg_samples,
                "min_samples": min_samples,
                "max_samples": max_samples,
                "total_samples": sum(sample_sizes)
            },
            "quality_statistics": {
                "avg_quality": avg_quality,
                "min_quality": min_quality,
                "quality_variation": max(qualities) - min(qualities)
            },
            "noise_statistics": {
                "noisy_clients": noisy_clients,
                "noise_fraction": noisy_clients / total_clients,
                "avg_noise_level": sum(noise_levels) / len(noise_levels) if noise_levels else 0.0
            },
            "heterogeneity": {
                "class_entropy_avg": class_entropy,
                "heterogeneity_alpha": self.config.heterogeneity_alpha
            }
        }

    def export_distribution(self, filepath: str) -> None:
        """Export data distribution configuration to file.

        Args:
            filepath: Path to save distribution configuration
        """
        import json

        export_data = {
            "config": {
                "distribution_type": self.config.distribution_type.value,
                "heterogeneity_alpha": self.config.heterogeneity_alpha,
                "samples_per_client": self.config.samples_per_client,
                "num_classes": self.config.num_classes,
                "quality_variation": self.config.quality_variation,
                "noise_clients_fraction": self.config.noise_clients_fraction
            },
            "client_configs": {
                client_id: {
                    "data_samples": config.data_samples,
                    "data_quality": config.data_quality,
                    "class_distribution": config.class_distribution,
                    "noise_level": config.noise_level,
                    "bias_direction": config.bias_direction
                }
                for client_id, config in self.client_data_configs.items()
            },
            "statistics": self.get_distribution_stats()
        }

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        log_info(logger, f"Data distribution exported to {filepath}")


def create_data_distributor(distribution_type: str = "non_iid", **kwargs) -> DataDistributor:
    """Factory function for creating data distributors.

    Args:
        distribution_type: Type of distribution ("iid", "non_iid", "pathological")
        **kwargs: Additional configuration parameters

    Returns:
        Configured DataDistributor instance
    """
    try:
        dist_type = DataDistributionType(distribution_type)
    except ValueError:
        log_info(logger, f"Unknown distribution type {distribution_type}, defaulting to non_iid")
        dist_type = DataDistributionType.NON_IID

    config = DataDistributionConfig(distribution_type=dist_type, **kwargs)
    return DataDistributor(config)