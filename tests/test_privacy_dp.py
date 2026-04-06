"""
Tests for differential privacy engine and privacy accounting.

Tests formal (ε, δ)-DP guarantees, noise calibration, privacy budget tracking,
and composition theorems.
"""

import pytest
import torch
import math
from privacy_security.dp_engine import (
    DPConfig,
    PrivacyAccountant,
    DPGradientClipper,
    DPNoiseGenerator,
    create_dp_components
)


class TestDPConfig:
    """Tests for DP configuration."""

    def test_default_config(self):
        """Test default DP configuration values."""
        config = DPConfig()
        assert config.epsilon == 1.0
        assert config.delta == 1e-5
        assert config.max_grad_norm == 1.0
        assert config.noise_mechanism == "gaussian"
        assert config.accounting_method == "rdp"

    def test_custom_config(self):
        """Test custom DP configuration."""
        config = DPConfig(
            epsilon=10.0,
            delta=1e-6,
            max_grad_norm=2.0,
            noise_mechanism="laplace",
            accounting_method="gdp"
        )
        assert config.epsilon == 10.0
        assert config.delta == 1e-6
        assert config.max_grad_norm == 2.0
        assert config.noise_mechanism == "laplace"


class TestPrivacyAccountant:
    """Tests for privacy accountant and budget tracking."""

    def test_initialization(self, sample_dp_config):
        """Test privacy accountant initialization."""
        accountant = PrivacyAccountant(sample_dp_config)
        assert accountant.config == sample_dp_config
        assert accountant.steps == 0

    def test_initial_privacy_is_zero(self, privacy_accountant):
        """Test that initial privacy expenditure is zero."""
        epsilon, delta = privacy_accountant.get_current_privacy()
        assert epsilon == 0.0
        assert delta == 0.0

    def test_record_step_increases_privacy(self, privacy_accountant):
        """Test that recording steps increases privacy loss."""
        # Record a single step
        privacy_accountant.record_step(noise_multiplier=1.0, sample_rate=0.01)

        epsilon, delta = privacy_accountant.get_current_privacy()
        assert epsilon > 0.0
        assert delta == privacy_accountant.config.delta
        assert privacy_accountant.steps == 1

    def test_multiple_steps_composition(self, privacy_accountant):
        """Test that multiple steps compose correctly."""
        # Record 10 steps
        for _ in range(10):
            privacy_accountant.record_step(noise_multiplier=1.0, sample_rate=0.01)

        epsilon_10, _ = privacy_accountant.get_current_privacy()

        # Record 10 more steps
        for _ in range(10):
            privacy_accountant.record_step(noise_multiplier=1.0, sample_rate=0.01)

        epsilon_20, _ = privacy_accountant.get_current_privacy()

        # Privacy should increase with more steps
        assert epsilon_20 > epsilon_10
        assert privacy_accountant.steps == 20

    def test_compute_privacy_spent(self, privacy_accountant):
        """Test computing privacy spent for given parameters."""
        epsilon, delta = privacy_accountant.compute_privacy_spent(
            num_steps=100,
            sampling_rate=0.01,
            noise_multiplier=1.0
        )

        assert epsilon > 0.0
        assert delta == privacy_accountant.config.delta

    def test_can_proceed_with_budget(self, privacy_accountant):
        """Test budget checking with sufficient budget."""
        # No steps yet, should be able to proceed
        assert privacy_accountant.can_proceed(epsilon_limit=1.0)

        # Record a few steps
        for _ in range(5):
            privacy_accountant.record_step(noise_multiplier=1.0, sample_rate=0.01)

        # Should still be under budget
        assert privacy_accountant.can_proceed(epsilon_limit=10.0)

    def test_cannot_proceed_budget_exhausted(self, privacy_accountant):
        """Test budget checking when budget is exhausted."""
        # Record many steps to exhaust budget
        for _ in range(1000):
            privacy_accountant.record_step(noise_multiplier=0.5, sample_rate=0.1)

        # Should exceed small budget
        assert not privacy_accountant.can_proceed(epsilon_limit=0.1)

    def test_get_noise_multiplier(self, privacy_accountant):
        """Test computing required noise multiplier."""
        noise_mult = privacy_accountant.get_noise_multiplier(
            target_epsilon=1.0,
            target_delta=1e-5,
            num_steps=100,
            sample_rate=0.01
        )

        assert noise_mult > 0.0
        assert isinstance(noise_mult, float)

    def test_higher_noise_for_lower_epsilon(self, privacy_accountant):
        """Test that lower epsilon requires higher noise."""
        # Use achievable epsilon values for the given parameters
        noise_low_eps = privacy_accountant.get_noise_multiplier(
            target_epsilon=1.0,
            target_delta=1e-5,
            num_steps=100,
            sample_rate=0.01
        )

        noise_high_eps = privacy_accountant.get_noise_multiplier(
            target_epsilon=10.0,
            target_delta=1e-5,
            num_steps=100,
            sample_rate=0.01
        )

        # Lower epsilon should require more noise
        assert noise_low_eps > noise_high_eps


class TestDPGradientClipper:
    """Tests for gradient clipping."""

    def test_initialization(self):
        """Test gradient clipper initialization."""
        clipper = DPGradientClipper(max_grad_norm=2.0)
        assert clipper.max_grad_norm == 2.0
        assert len(clipper.clipping_history) == 0

    def test_clip_gradients_within_norm(self, gradient_clipper, mock_model):
        """Test clipping when gradients are within norm."""
        # Create small gradients
        x = torch.randn(2, 10) * 0.01
        y = torch.randn(2, 5) * 0.01
        output = mock_model(x)
        loss = torch.nn.functional.mse_loss(output, y)
        loss.backward()

        params = list(mock_model.parameters())
        total_norm = gradient_clipper.clip_gradients(params)

        # Small gradients should not be clipped much
        assert total_norm < gradient_clipper.max_grad_norm * 2

    def test_clip_gradients_exceeds_norm(self, gradient_clipper, mock_model):
        """Test clipping when gradients exceed max norm."""
        # Create large gradients
        x = torch.randn(2, 10) * 100.0
        y = torch.randn(2, 5) * 100.0
        output = mock_model(x)
        loss = torch.nn.functional.mse_loss(output, y)
        loss.backward()

        params = list(mock_model.parameters())
        total_norm_before = gradient_clipper.clip_gradients(params)

        # Check that gradients are now clipped
        total_norm_after = torch.nn.utils.clip_grad_norm_(
            params,
            max_norm=float('inf'),
            norm_type=2
        )

        # After clipping, norm should be at most max_grad_norm
        assert total_norm_after <= gradient_clipper.max_grad_norm + 1e-5

    def test_clipping_history_tracking(self, gradient_clipper, mock_model):
        """Test that clipping history is tracked correctly."""
        # Clip gradients multiple times
        for i in range(5):
            mock_model.zero_grad()
            x = torch.randn(2, 10)
            y = torch.randn(2, 5)
            output = mock_model(x)
            loss = torch.nn.functional.mse_loss(output, y)
            loss.backward()

            gradient_clipper.clip_gradients(list(mock_model.parameters()))

        assert len(gradient_clipper.clipping_history) == 5

    def test_get_clipping_stats(self, gradient_clipper, mock_model):
        """Test clipping statistics computation."""
        # Clip gradients a few times
        for _ in range(10):
            mock_model.zero_grad()
            x = torch.randn(2, 10)
            y = torch.randn(2, 5)
            output = mock_model(x)
            loss = torch.nn.functional.mse_loss(output, y)
            loss.backward()

            gradient_clipper.clip_gradients(list(mock_model.parameters()))

        stats = gradient_clipper.get_clipping_stats()
        assert "mean" in stats
        assert "max" in stats
        assert "min" in stats
        assert "count" in stats
        assert stats["count"] == 10
        assert stats["mean"] > 0.0

    def test_update_max_norm(self, gradient_clipper):
        """Test updating clipping threshold."""
        gradient_clipper.update_max_norm(5.0)
        assert gradient_clipper.max_grad_norm == 5.0


class TestDPNoiseGenerator:
    """Tests for DP noise generation."""

    def test_initialization(self):
        """Test noise generator initialization."""
        noise_gen = DPNoiseGenerator(noise_mechanism="gaussian", noise_multiplier=1.5)
        assert noise_gen.noise_mechanism == "gaussian"
        assert noise_gen.noise_multiplier == 1.5

    def test_add_gaussian_noise(self, noise_generator):
        """Test adding Gaussian noise to gradients."""
        gradients = [torch.ones(10, 10) for _ in range(3)]
        original_sum = sum(g.sum().item() for g in gradients)

        noise_generator.add_noise(gradients, sensitivity=1.0)

        noisy_sum = sum(g.sum().item() for g in gradients)

        # Noise should change the sum
        assert abs(noisy_sum - original_sum) > 0.1

    def test_add_laplace_noise(self):
        """Test adding Laplace noise to gradients."""
        noise_gen = DPNoiseGenerator(noise_mechanism="laplace", noise_multiplier=1.0)
        gradients = [torch.ones(10, 10) for _ in range(3)]
        original_sum = sum(g.sum().item() for g in gradients)

        noise_gen.add_noise(gradients, sensitivity=1.0)

        noisy_sum = sum(g.sum().item() for g in gradients)

        # Noise should change the sum
        assert abs(noisy_sum - original_sum) > 0.1

    def test_noise_scale_affects_magnitude(self):
        """Test that higher noise multiplier adds more noise."""
        gradients_low = [torch.ones(100, 100) for _ in range(3)]
        gradients_high = [torch.ones(100, 100) for _ in range(3)]

        noise_gen_low = DPNoiseGenerator("gaussian", noise_multiplier=0.1)
        noise_gen_high = DPNoiseGenerator("gaussian", noise_multiplier=10.0)

        noise_gen_low.add_noise(gradients_low, sensitivity=1.0)
        noise_gen_high.add_noise(gradients_high, sensitivity=1.0)

        # Compute variance of noise (deviation from expected value of 1.0)
        var_low = sum(((g - 1.0) ** 2).mean().item() for g in gradients_low)
        var_high = sum(((g - 1.0) ** 2).mean().item() for g in gradients_high)

        # Higher noise multiplier should have higher variance
        assert var_high > var_low * 10  # Significantly more noise

    def test_none_gradients_skipped(self, noise_generator):
        """Test that None gradients are skipped."""
        gradients = [torch.ones(5, 5), None, torch.ones(5, 5)]

        # Should not raise an error
        noise_generator.add_noise(gradients, sensitivity=1.0)

        assert gradients[1] is None  # None unchanged
        assert gradients[0] is not None
        assert gradients[2] is not None

    def test_calibrate_noise(self, noise_generator):
        """Test noise calibration based on privacy parameters."""
        noise_generator.calibrate_noise(
            epsilon=1.0,
            delta=1e-5,
            sensitivity=1.0,
            num_steps=100,
            sample_rate=0.01
        )

        # Noise multiplier should be set
        assert noise_generator.noise_multiplier > 0.0


class TestCreateDPComponents:
    """Tests for DP components factory function."""

    def test_create_all_components(self):
        """Test creating all DP components with consistent config."""
        config, accountant, clipper, noise_gen = create_dp_components(
            epsilon=2.0,
            delta=1e-6,
            max_grad_norm=1.5,
            noise_mechanism="gaussian"
        )

        assert config.epsilon == 2.0
        assert config.delta == 1e-6
        assert config.max_grad_norm == 1.5
        assert config.noise_mechanism == "gaussian"

        assert accountant.config == config
        assert clipper.max_grad_norm == 1.5
        assert noise_gen.noise_mechanism == "gaussian"

    def test_default_components(self):
        """Test creating components with default values."""
        config, accountant, clipper, noise_gen = create_dp_components()

        assert config.epsilon == 1.0
        assert config.delta == 1e-5
        assert config.max_grad_norm == 1.0
        assert config.noise_mechanism == "gaussian"


class TestDPIntegration:
    """Integration tests for full DP workflow."""

    def test_full_dp_workflow(self, mock_model):
        """Test complete DP training workflow."""
        # Create DP components
        config, accountant, clipper, noise_gen = create_dp_components(
            epsilon=1.0,
            delta=1e-5,
            max_grad_norm=1.0
        )

        # Calibrate noise for 10 steps
        noise_gen.calibrate_noise(
            epsilon=config.epsilon,
            delta=config.delta,
            sensitivity=config.max_grad_norm,
            num_steps=10,
            sample_rate=0.1
        )

        # Simulate training for 10 steps
        for step in range(10):
            # Forward pass
            mock_model.zero_grad()
            x = torch.randn(4, 10)
            y = torch.randn(4, 5)
            output = mock_model(x)
            loss = torch.nn.functional.mse_loss(output, y)

            # Backward pass
            loss.backward()

            # Clip gradients
            params = list(mock_model.parameters())
            clipper.clip_gradients(params)

            # Add noise
            gradients = [p.grad for p in params if p.grad is not None]
            noise_gen.add_noise(gradients, sensitivity=config.max_grad_norm)

            # Record privacy
            accountant.record_step(
                noise_multiplier=noise_gen.noise_multiplier,
                sample_rate=0.1
            )

        # Check privacy spent
        epsilon, delta = accountant.get_current_privacy()
        assert epsilon > 0.0
        assert epsilon < config.epsilon * 2  # Should be reasonable
        assert delta == config.delta
        assert accountant.steps == 10

    def test_privacy_budget_enforcement(self):
        """Test that privacy budget can be enforced."""
        config, accountant, clipper, noise_gen = create_dp_components(
            epsilon=0.5,  # Very small budget
            delta=1e-5
        )

        # Simulate steps until budget exhausted
        steps_taken = 0
        max_steps = 1000

        for step in range(max_steps):
            if not accountant.can_proceed(epsilon_limit=config.epsilon):
                break

            accountant.record_step(noise_multiplier=1.0, sample_rate=0.1)
            steps_taken += 1

        # Should have stopped before max_steps due to budget
        assert steps_taken < max_steps
        assert not accountant.can_proceed(epsilon_limit=config.epsilon)
