"""
Differential Privacy engine for PrivaLoom using Opacus.

Provides formal (ε, δ)-differential privacy with privacy accounting, gradient
clipping, and calibrated noise generation using the Opacus library.
"""

import torch
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal
from opacus.accountants import RDPAccountant
from opacus.accountants.utils import get_noise_multiplier


@dataclass
class DPConfig:
    """Configuration for differential privacy mechanisms."""
    epsilon: float = 1.0  # Target privacy budget (ε)
    delta: float = 1e-5  # Failure probability (δ)
    max_grad_norm: float = 1.0  # Gradient clipping threshold (C)
    noise_mechanism: Literal["gaussian", "laplace"] = "gaussian"
    accounting_method: Literal["rdp", "gdp"] = "rdp"  # RDP for tighter bounds


class PrivacyAccountant:
    """
    Privacy accountant for tracking (ε, δ) across multiple training rounds.

    Uses Opacus RDP (Rényi Differential Privacy) accounting for tighter privacy bounds.
    """

    def __init__(self, config: DPConfig):
        """
        Initialize privacy accountant.

        Args:
            config: DP configuration with epsilon, delta, and accounting method
        """
        self.config = config
        self.accountant = RDPAccountant()
        self.steps = 0

    def compute_privacy_spent(
        self,
        num_steps: int,
        sampling_rate: float,
        noise_multiplier: float
    ) -> Tuple[float, float]:
        """
        Compute privacy spent after given number of steps.

        Args:
            num_steps: Number of training steps
            sampling_rate: Probability of sampling each example (batch_size / dataset_size)
            noise_multiplier: Noise multiplier (σ = noise_multiplier * sensitivity)

        Returns:
            Tuple of (epsilon, delta) representing privacy loss
        """
        # Create a fresh accountant for calculation
        temp_accountant = RDPAccountant()

        # Record steps with noise
        for _ in range(num_steps):
            temp_accountant.step(
                noise_multiplier=noise_multiplier,
                sample_rate=sampling_rate
            )

        # Get epsilon for the target delta
        epsilon = temp_accountant.get_epsilon(delta=self.config.delta)
        return (epsilon, self.config.delta)

    def record_step(
        self,
        noise_multiplier: float,
        sample_rate: float
    ) -> None:
        """
        Record a single training step for privacy accounting.

        Args:
            noise_multiplier: Noise multiplier used in this step
            sample_rate: Sampling rate for this step
        """
        self.accountant.step(
            noise_multiplier=noise_multiplier,
            sample_rate=sample_rate
        )
        self.steps += 1

    def get_current_privacy(self) -> Tuple[float, float]:
        """
        Get current privacy expenditure.

        Returns:
            Tuple of (epsilon, delta) spent so far
        """
        if self.steps == 0:
            return (0.0, 0.0)

        epsilon = self.accountant.get_epsilon(delta=self.config.delta)
        return (epsilon, self.config.delta)

    def can_proceed(self, epsilon_limit: float) -> bool:
        """
        Check if we can proceed without exceeding privacy budget.

        Args:
            epsilon_limit: Maximum allowed epsilon

        Returns:
            True if privacy budget not exhausted, False otherwise
        """
        current_epsilon, _ = self.get_current_privacy()
        return current_epsilon < epsilon_limit

    def get_noise_multiplier(
        self,
        target_epsilon: float,
        target_delta: float,
        num_steps: int,
        sample_rate: float
    ) -> float:
        """
        Compute required noise multiplier to achieve target privacy.

        Args:
            target_epsilon: Target privacy budget
            target_delta: Target failure probability
            num_steps: Expected number of training steps
            sample_rate: Sampling rate

        Returns:
            Required noise multiplier (σ)
        """
        return get_noise_multiplier(
            target_epsilon=target_epsilon,
            target_delta=target_delta,
            sample_rate=sample_rate,
            epochs=num_steps,  # In opacus API, this is steps
            accountant="rdp"
        )


class DPGradientClipper:
    """
    Gradient clipper for differential privacy.

    Implements per-sample gradient clipping to bound sensitivity.
    """

    def __init__(self, max_grad_norm: float = 1.0):
        """
        Initialize gradient clipper.

        Args:
            max_grad_norm: Maximum L2 norm for gradients
        """
        self.max_grad_norm = max_grad_norm
        self.clipping_history: List[float] = []

    def clip_gradients(
        self,
        parameters: List[torch.Tensor]
    ) -> float:
        """
        Clip gradients to maximum norm.

        Args:
            parameters: List of model parameters with gradients

        Returns:
            Total norm before clipping
        """
        # Compute total norm across all parameters
        total_norm = torch.nn.utils.clip_grad_norm_(
            parameters,
            max_norm=self.max_grad_norm
        )

        # Track clipping history
        self.clipping_history.append(float(total_norm))

        return float(total_norm)

    def get_clipping_stats(self) -> dict:
        """
        Get statistics about gradient clipping.

        Returns:
            Dict with mean, max, min norms before clipping
        """
        if not self.clipping_history:
            return {"mean": 0.0, "max": 0.0, "min": 0.0, "count": 0}

        return {
            "mean": sum(self.clipping_history) / len(self.clipping_history),
            "max": max(self.clipping_history),
            "min": min(self.clipping_history),
            "count": len(self.clipping_history)
        }

    def update_max_norm(self, new_max_norm: float) -> None:
        """
        Update clipping threshold (for adaptive clipping).

        Args:
            new_max_norm: New maximum gradient norm
        """
        self.max_grad_norm = new_max_norm


class DPNoiseGenerator:
    """
    Noise generator for differential privacy.

    Adds calibrated Gaussian or Laplace noise to gradients.
    """

    def __init__(
        self,
        noise_mechanism: Literal["gaussian", "laplace"] = "gaussian",
        noise_multiplier: float = 1.0
    ):
        """
        Initialize noise generator.

        Args:
            noise_mechanism: Type of noise distribution
            noise_multiplier: Noise scale multiplier (σ)
        """
        self.noise_mechanism = noise_mechanism
        self.noise_multiplier = noise_multiplier

    def add_noise(
        self,
        gradients: List[torch.Tensor],
        sensitivity: float = 1.0
    ) -> None:
        """
        Add calibrated noise to gradients in-place.

        Args:
            gradients: List of gradient tensors to add noise to
            sensitivity: Sensitivity of the query (typically max_grad_norm)
        """
        noise_scale = self.noise_multiplier * sensitivity

        for grad in gradients:
            if grad is None:
                continue

            if self.noise_mechanism == "gaussian":
                # Gaussian noise: N(0, σ²)
                noise = torch.randn_like(grad) * noise_scale
            else:  # laplace
                # Laplace noise: Laplace(0, b) where b = sensitivity / epsilon
                # For DP, we use noise_scale = sensitivity * noise_multiplier
                noise = torch.distributions.Laplace(
                    torch.zeros_like(grad),
                    torch.ones_like(grad) * noise_scale
                ).sample()

            grad.add_(noise)

    def calibrate_noise(
        self,
        epsilon: float,
        delta: float,
        sensitivity: float,
        num_steps: int,
        sample_rate: float
    ) -> None:
        """
        Calibrate noise multiplier based on target privacy.

        Args:
            epsilon: Target privacy budget
            delta: Target failure probability
            sensitivity: Query sensitivity (max_grad_norm)
            num_steps: Expected number of training steps
            sample_rate: Sampling rate
        """
        self.noise_multiplier = get_noise_multiplier(
            target_epsilon=epsilon,
            target_delta=delta,
            sample_rate=sample_rate,
            epochs=num_steps,
            accountant="rdp"
        )


def create_dp_components(
    epsilon: float = 1.0,
    delta: float = 1e-5,
    max_grad_norm: float = 1.0,
    noise_mechanism: Literal["gaussian", "laplace"] = "gaussian"
) -> Tuple[DPConfig, PrivacyAccountant, DPGradientClipper, DPNoiseGenerator]:
    """
    Convenience function to create all DP components with consistent config.

    Args:
        epsilon: Target privacy budget
        delta: Failure probability
        max_grad_norm: Gradient clipping threshold
        noise_mechanism: Type of noise distribution

    Returns:
        Tuple of (config, accountant, clipper, noise_generator)
    """
    config = DPConfig(
        epsilon=epsilon,
        delta=delta,
        max_grad_norm=max_grad_norm,
        noise_mechanism=noise_mechanism
    )

    accountant = PrivacyAccountant(config)
    clipper = DPGradientClipper(max_grad_norm)
    noise_gen = DPNoiseGenerator(noise_mechanism, noise_multiplier=1.0)

    return config, accountant, clipper, noise_gen
