"""
Client factory for creating different types of simulated federated learning clients.

This module provides the ability to create honest clients, various types of
malicious clients (Byzantine attacks), and unreliable clients for comprehensive
federated learning simulation scenarios.
"""

import uuid
import time
import random
import math
import numpy as np
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from utils.logging import setup_logger, log_info, log_warning
from utils.types import GradientUpdate

# Initialize logger
logger = setup_logger("privaloom.simulation.client_factory")


class ClientType(Enum):
    """Types of simulated clients with different behaviors."""
    HONEST = "honest"
    GRADIENT_SCALING = "gradient_scaling"  # Byzantine attack with scaling
    SIGN_FLIPPING = "sign_flipping"        # Byzantine attack with sign flip
    GRADIENT_NOISE = "gradient_noise"      # Byzantine attack with random noise
    FREE_RIDER = "free_rider"              # Receives updates but doesn't contribute
    DROPOUT_PRONE = "dropout_prone"        # Intermittent connectivity
    COORDINATED_MALICIOUS = "coordinated_malicious"  # Coordinated attack


@dataclass
class ClientConfig:
    """Configuration for individual simulated clients."""
    client_id: str
    client_type: ClientType
    participation_rate: float = 0.8
    dropout_probability: float = 0.05
    malicious_intensity: float = 1.0  # Intensity of malicious behavior
    data_samples: int = 1000
    data_quality: float = 1.0  # 0.0-1.0, for simulating noisy data
    coordination_group: Optional[str] = None  # For coordinated attacks


@dataclass
class PopulationConfig:
    """Configuration for the entire client population."""
    total_clients: int = 50
    honest_fraction: float = 0.7
    malicious_types: Dict[str, float] = None  # malicious_type -> fraction
    participation_rate: float = 0.8
    dropout_probability: float = 0.05
    coordination_enabled: bool = False
    coordination_groups: int = 2  # Number of coordination groups


class SimulatedClient:
    """Represents a single simulated federated learning client."""

    def __init__(self, config: ClientConfig):
        """Initialize simulated client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.client_id = config.client_id
        self.client_type = config.client_type
        self.round_history: List[int] = []
        self.last_participation_round = 0
        self.consecutive_dropouts = 0

        # For coordinated attacks
        self.coordination_state = {}
        if config.coordination_group:
            self.coordination_state["group"] = config.coordination_group
            self.coordination_state["attack_phase"] = "dormant"

        log_info(logger, f"Created simulated client",
                 client_id=self.client_id,
                 client_type=self.client_type.value,
                 coordination_group=config.coordination_group)

    def should_participate(self, round_number: int) -> bool:
        """Determine if client should participate in given round.

        Args:
            round_number: Current federated learning round

        Returns:
            True if client should participate, False otherwise
        """
        # Base participation based on participation rate
        if random.random() > self.config.participation_rate:
            return False

        # Dropout-prone clients have additional dropout probability
        if self.client_type == ClientType.DROPOUT_PRONE:
            if random.random() < self.config.dropout_probability * (1 + self.consecutive_dropouts * 0.1):
                self.consecutive_dropouts += 1
                return False
            else:
                self.consecutive_dropouts = 0

        # Free riders participate less frequently
        if self.client_type == ClientType.FREE_RIDER:
            return random.random() < 0.3  # Low participation rate

        # Coordinated attacks may have specific participation patterns
        if self.coordination_state.get("group"):
            return self._should_participate_coordinated(round_number)

        return True

    def _should_participate_coordinated(self, round_number: int) -> bool:
        """Determine participation for coordinated attack clients."""
        # Simple coordination: attack every 10 rounds, dormant otherwise
        if round_number % 10 in [7, 8, 9]:
            self.coordination_state["attack_phase"] = "active"
            return True
        else:
            self.coordination_state["attack_phase"] = "dormant"
            return random.random() < 0.2  # Low participation when dormant

    def generate_update(self, round_number: int, base_gradients: Optional[GradientUpdate] = None) -> Optional[Dict[str, Any]]:
        """Generate client update for federated learning round.

        Args:
            round_number: Current federated learning round
            base_gradients: Base honest gradients to modify (optional)

        Returns:
            Update dictionary or None if not participating
        """
        if not self.should_participate(round_number):
            return None

        # Generate base honest gradients if not provided
        if base_gradients is None:
            base_gradients = self._generate_base_gradients()

        # Apply client-specific behavior
        if self.client_type == ClientType.HONEST:
            weights = self._apply_honest_behavior(base_gradients)
        elif self.client_type == ClientType.GRADIENT_SCALING:
            weights = self._apply_scaling_attack(base_gradients)
        elif self.client_type == ClientType.SIGN_FLIPPING:
            weights = self._apply_sign_flipping_attack(base_gradients)
        elif self.client_type == ClientType.GRADIENT_NOISE:
            weights = self._apply_noise_attack(base_gradients)
        elif self.client_type == ClientType.FREE_RIDER:
            weights = self._apply_free_rider_behavior(base_gradients)
        elif self.client_type == ClientType.COORDINATED_MALICIOUS:
            weights = self._apply_coordinated_attack(base_gradients, round_number)
        else:
            weights = base_gradients  # Default to honest

        # Record participation
        self.round_history.append(round_number)
        self.last_participation_round = round_number

        return {
            "weights": weights,
            "client_id": self.client_id,
            "timestamp": int(time.time())
        }

    def _generate_base_gradients(self) -> GradientUpdate:
        """Generate base honest gradients for simulation."""
        # Generate realistic gradient shapes (5 parameter groups)
        gradients = []
        for param_idx in range(5):
            # Parameter size varies (simulating different layer sizes)
            if param_idx == 0:  # Large layer
                param_size = 100
            elif param_idx < 3:  # Medium layers
                param_size = 50
            else:  # Small layers
                param_size = 20

            # Generate gradients with realistic scale and some noise
            base_values = np.random.normal(0, 0.01, param_size)

            # Add some structure (not purely random)
            base_values += np.sin(np.linspace(0, 2*np.pi, param_size)) * 0.001

            gradients.append(base_values.tolist())

        return gradients

    def _apply_honest_behavior(self, gradients: GradientUpdate) -> GradientUpdate:
        """Apply honest client behavior (minimal modifications)."""
        # Add small amount of noise to simulate real training variations
        honest_gradients = []
        for param_slice in gradients:
            noise_scale = 0.001
            noisy_slice = [val + random.gauss(0, noise_scale) for val in param_slice]
            honest_gradients.append(noisy_slice)
        return honest_gradients

    def _apply_scaling_attack(self, gradients: GradientUpdate) -> GradientUpdate:
        """Apply gradient scaling Byzantine attack."""
        scale_factor = self.config.malicious_intensity * 10.0  # Scale gradients by large factor
        scaled_gradients = []
        for param_slice in gradients:
            scaled_slice = [val * scale_factor for val in param_slice]
            scaled_gradients.append(scaled_slice)
        return scaled_gradients

    def _apply_sign_flipping_attack(self, gradients: GradientUpdate) -> GradientUpdate:
        """Apply sign flipping Byzantine attack."""
        flipped_gradients = []
        for param_slice in gradients:
            # Flip signs of all gradients
            flipped_slice = [-val * self.config.malicious_intensity for val in param_slice]
            flipped_gradients.append(flipped_slice)
        return flipped_gradients

    def _apply_noise_attack(self, gradients: GradientUpdate) -> GradientUpdate:
        """Apply random noise Byzantine attack."""
        noise_scale = self.config.malicious_intensity * 0.1
        noisy_gradients = []
        for param_slice in gradients:
            # Replace gradients with random noise
            noisy_slice = [random.gauss(0, noise_scale) for _ in param_slice]
            noisy_gradients.append(noisy_slice)
        return noisy_gradients

    def _apply_free_rider_behavior(self, gradients: GradientUpdate) -> GradientUpdate:
        """Apply free rider behavior (send minimal/zero updates)."""
        zero_gradients = []
        for param_slice in gradients:
            # Send near-zero gradients (small noise to avoid detection)
            zero_slice = [random.gauss(0, 0.0001) for _ in param_slice]
            zero_gradients.append(zero_slice)
        return zero_gradients

    def _apply_coordinated_attack(self, gradients: GradientUpdate, round_number: int) -> GradientUpdate:
        """Apply coordinated attack behavior."""
        if self.coordination_state.get("attack_phase") == "active":
            # During active phase, apply strong scaling attack
            return self._apply_scaling_attack(gradients)
        else:
            # During dormant phase, behave honestly
            return self._apply_honest_behavior(gradients)

    def get_client_stats(self) -> Dict[str, Any]:
        """Get client participation and behavior statistics."""
        return {
            "client_id": self.client_id,
            "client_type": self.client_type.value,
            "total_rounds_participated": len(self.round_history),
            "last_participation_round": self.last_participation_round,
            "consecutive_dropouts": self.consecutive_dropouts,
            "coordination_group": self.config.coordination_group,
            "participation_rate": len(self.round_history) / max(1, self.last_participation_round)
        }


class ClientFactory:
    """Factory for creating populations of simulated clients."""

    @staticmethod
    def create_population(population_config: PopulationConfig) -> List[SimulatedClient]:
        """Create a population of simulated clients.

        Args:
            population_config: Configuration for client population

        Returns:
            List of simulated clients with specified distribution
        """
        clients = []

        # Calculate client type distribution
        num_honest = int(population_config.total_clients * population_config.honest_fraction)
        num_malicious = population_config.total_clients - num_honest

        # Default malicious distribution if not specified
        if population_config.malicious_types is None:
            malicious_types = {
                "gradient_scaling": 0.4,
                "sign_flipping": 0.3,
                "gradient_noise": 0.2,
                "dropout_prone": 0.1
            }
        else:
            malicious_types = population_config.malicious_types

        # Create honest clients
        for i in range(num_honest):
            client_id = f"honest_{i}_{uuid.uuid4().hex[:8]}"
            config = ClientConfig(
                client_id=client_id,
                client_type=ClientType.HONEST,
                participation_rate=population_config.participation_rate,
                dropout_probability=population_config.dropout_probability
            )
            clients.append(SimulatedClient(config))

        # Create malicious clients
        remaining_malicious = num_malicious
        for malicious_type, fraction in malicious_types.items():
            num_type = int(num_malicious * fraction)
            if remaining_malicious > 0:
                num_type = min(num_type, remaining_malicious)
                remaining_malicious -= num_type

                # Determine coordination group if enabled
                coordination_group = None
                if (population_config.coordination_enabled and
                    malicious_type in ["gradient_scaling", "sign_flipping", "coordinated_malicious"]):
                    coordination_group = f"group_{i % population_config.coordination_groups}"

                for i in range(num_type):
                    client_id = f"{malicious_type}_{i}_{uuid.uuid4().hex[:8]}"
                    try:
                        client_type = ClientType(malicious_type)
                    except ValueError:
                        log_warning(logger, f"Unknown client type: {malicious_type}, defaulting to gradient_noise")
                        client_type = ClientType.GRADIENT_NOISE

                    config = ClientConfig(
                        client_id=client_id,
                        client_type=client_type,
                        participation_rate=population_config.participation_rate * 0.8,  # Slightly lower for malicious
                        dropout_probability=population_config.dropout_probability,
                        malicious_intensity=random.uniform(0.8, 1.5),  # Vary intensity
                        coordination_group=coordination_group
                    )
                    clients.append(SimulatedClient(config))

        log_info(logger, f"Created client population",
                 total_clients=len(clients),
                 honest_clients=num_honest,
                 malicious_clients=num_malicious,
                 coordination_enabled=population_config.coordination_enabled)

        return clients

    @staticmethod
    def create_single_client(client_type: ClientType, client_id: Optional[str] = None, **kwargs) -> SimulatedClient:
        """Create a single simulated client for testing.

        Args:
            client_type: Type of client to create
            client_id: Optional specific client ID
            **kwargs: Additional configuration parameters

        Returns:
            Single simulated client
        """
        if client_id is None:
            client_id = f"{client_type.value}_{uuid.uuid4().hex[:8]}"

        config = ClientConfig(client_id=client_id, client_type=client_type, **kwargs)
        return SimulatedClient(config)

    @staticmethod
    def analyze_population(clients: List[SimulatedClient]) -> Dict[str, Any]:
        """Analyze the composition and behavior of a client population.

        Args:
            clients: List of simulated clients

        Returns:
            Population analysis statistics
        """
        type_counts = {}
        coordination_groups = set()
        total_clients = len(clients)

        for client in clients:
            client_type = client.client_type.value
            type_counts[client_type] = type_counts.get(client_type, 0) + 1

            if client.config.coordination_group:
                coordination_groups.add(client.config.coordination_group)

        return {
            "total_clients": total_clients,
            "client_type_distribution": type_counts,
            "coordination_groups": len(coordination_groups),
            "honest_fraction": type_counts.get("honest", 0) / total_clients,
            "malicious_fraction": 1 - (type_counts.get("honest", 0) / total_clients)
        }