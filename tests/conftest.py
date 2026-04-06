"""
Pytest configuration and fixtures for PrivaLoom tests.

Provides shared fixtures for testing privacy, security, and aggregation modules.
"""

import pytest
import tempfile
import torch
import torch.nn as nn
from pathlib import Path
from fastapi.testclient import TestClient
from typing import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test files.

    Yields:
        Path to temporary directory (cleaned up after test)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_model() -> nn.Module:
    """
    Create a small mock model for testing without loading DistilGPT2.

    Returns:
        Simple PyTorch model with a few parameters
    """
    class MockModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.layer1 = nn.Linear(10, 20)
            self.layer2 = nn.Linear(20, 10)
            self.layer3 = nn.Linear(10, 5)

        def forward(self, x):
            x = torch.relu(self.layer1(x))
            x = torch.relu(self.layer2(x))
            return self.layer3(x)

    return MockModel()


@pytest.fixture
def mock_gradients(mock_model: nn.Module) -> list:
    """
    Create mock gradients for testing DP mechanisms.

    Args:
        mock_model: Model fixture

    Returns:
        List of gradient tensors
    """
    # Create dummy loss and compute gradients
    x = torch.randn(4, 10)
    y = torch.randn(4, 5)
    output = mock_model(x)
    loss = torch.nn.functional.mse_loss(output, y)
    loss.backward()

    # Extract gradients
    gradients = [p.grad.clone() for p in mock_model.parameters() if p.grad is not None]
    return gradients


@pytest.fixture
def temp_privacy_state_file(temp_dir: Path) -> Path:
    """
    Create temporary privacy state file path.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to privacy state file
    """
    return temp_dir / "privacy_state.json"


@pytest.fixture
def temp_aggregation_state_file(temp_dir: Path) -> Path:
    """
    Create temporary aggregation state file path.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to aggregation state file
    """
    return temp_dir / "aggregation_state.json"


@pytest.fixture
def temp_reputation_state_file(temp_dir: Path) -> Path:
    """
    Create temporary reputation state file path.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to reputation state file
    """
    return temp_dir / "reputation_state.json"


@pytest.fixture
def mock_gradient_update() -> list:
    """
    Create a mock gradient update in the format expected by server.

    Returns:
        List of gradient slices (list of lists of floats)
    """
    return [
        [0.5, -0.3],
        [1.2, -0.8],
        [-0.1, 0.4],
        [0.9, -0.5],
        [0.2, 0.7]
    ]


@pytest.fixture
def mock_update_batch() -> list:
    """
    Create a batch of mock gradient updates.

    Returns:
        List of gradient updates (for testing aggregation)
    """
    return [
        [[0.5, -0.3], [1.2, -0.8], [-0.1, 0.4]],
        [[0.6, -0.4], [1.1, -0.7], [-0.2, 0.3]],
        [[0.4, -0.2], [1.3, -0.9], [0.0, 0.5]],
        [[0.7, -0.5], [1.0, -0.6], [-0.3, 0.2]],
    ]


@pytest.fixture
def malicious_update() -> list:
    """
    Create a malicious gradient update (scaled up significantly).

    Returns:
        Malicious gradient update for testing Byzantine robustness
    """
    return [
        [50.0, -30.0],  # 100x normal magnitude
        [120.0, -80.0],
        [-10.0, 40.0],
        [90.0, -50.0],
        [20.0, 70.0]
    ]


@pytest.fixture
def test_client() -> TestClient:
    """
    Create FastAPI test client.

    Returns:
        Test client for API endpoint testing
    """
    # Import here to avoid circular dependency issues during early development
    try:
        from server.api import app
        return TestClient(app)
    except ImportError:
        pytest.skip("Server API not available")


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Reset global singletons before each test.

    This ensures tests don't interfere with each other through shared state.
    """
    # Reset privacy tracker
    try:
        from privacy_security import privacy_tracker
        privacy_tracker._global_privacy_tracker = None
    except ImportError:
        pass

    # Reset round tracker
    try:
        from utils import aggregation
        aggregation._global_tracker = None
    except ImportError:
        pass

    yield

    # Cleanup after test
    # (singletons will be reset in next test's setup)


@pytest.fixture
def sample_dp_config():
    """
    Create sample DP configuration for testing.

    Returns:
        DPConfig with test-friendly values
    """
    from privacy_security.dp_engine import DPConfig
    return DPConfig(
        epsilon=1.0,
        delta=1e-5,
        max_grad_norm=1.0,
        noise_mechanism="gaussian",
        accounting_method="rdp"
    )


@pytest.fixture
def privacy_accountant(sample_dp_config):
    """
    Create privacy accountant for testing.

    Args:
        sample_dp_config: DP config fixture

    Returns:
        PrivacyAccountant instance
    """
    from privacy_security.dp_engine import PrivacyAccountant
    return PrivacyAccountant(sample_dp_config)


@pytest.fixture
def gradient_clipper():
    """
    Create gradient clipper for testing.

    Returns:
        DPGradientClipper instance
    """
    from privacy_security.dp_engine import DPGradientClipper
    return DPGradientClipper(max_grad_norm=1.0)


@pytest.fixture
def noise_generator():
    """
    Create noise generator for testing.

    Returns:
        DPNoiseGenerator instance
    """
    from privacy_security.dp_engine import DPNoiseGenerator
    return DPNoiseGenerator(noise_mechanism="gaussian", noise_multiplier=1.0)
