"""
Tests for client-side differential privacy integration.
"""

import pytest
import torch
from unittest.mock import Mock, patch, MagicMock


class TestClientDPIntegration:
    """Tests for client.py DP integration."""

    @patch('client.client.model')
    @patch('client.client.tokenizer')
    @patch('client.client.privacy_accountant')
    @patch('client.client.gradient_clipper')
    @patch('client.client.noise_generator')
    def test_train_and_get_update_with_dp(
        self,
        mock_noise_gen,
        mock_clipper,
        mock_accountant,
        mock_tokenizer,
        mock_model
    ):
        """Test training with DP produces valid update."""
        # Setup mocks
        mock_model.train = Mock()
        mock_model.zero_grad = Mock()
        mock_model.parameters = Mock(return_value=[
            torch.nn.Parameter(torch.randn(10, 10))
            for _ in range(3)
        ])

        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

        mock_output = Mock()
        mock_output.loss = torch.tensor(1.0, requires_grad=True)
        mock_model.return_value = mock_output

        mock_accountant.can_proceed.return_value = True
        mock_accountant.get_current_privacy.return_value = (0.5, 1e-5)
        mock_accountant.steps = 1
        mock_clipper.clip_gradients.return_value = 0.8
        mock_noise_gen.noise_multiplier = 1.0

        # Import after patching
        from client.client import train_and_get_update

        # Execute
        update = train_and_get_update("test text")

        # Verify
        assert update is not None
        assert isinstance(update, list)
        mock_model.train.assert_called_once()
        mock_clipper.clip_gradients.assert_called_once()
        mock_noise_gen.add_noise.assert_called_once()
        mock_accountant.record_step.assert_called_once()

    @patch('client.client.model')
    @patch('client.client.tokenizer')
    @patch('client.client.privacy_accountant')
    def test_train_and_get_update_budget_exhausted(
        self,
        mock_accountant,
        mock_tokenizer,
        mock_model
    ):
        """Test that training stops when privacy budget exhausted."""
        # Mock budget exhausted
        mock_accountant.can_proceed.return_value = False
        mock_accountant.get_current_privacy.return_value = (1.5, 1e-5)

        from client.client import train_and_get_update

        # Execute
        update = train_and_get_update("test text")

        # Should return None when budget exhausted
        assert update is None
        mock_model.train.assert_not_called()

    @patch('client.client.DP_ENABLED', False)
    @patch('client.client.model')
    @patch('client.client.tokenizer')
    def test_train_without_dp(self, mock_tokenizer, mock_model):
        """Test training without DP enabled."""
        # Setup mocks
        mock_model.train = Mock()
        mock_model.zero_grad = Mock()

        # Create mock parameters with gradients
        params = []
        for _ in range(3):
            param = torch.nn.Parameter(torch.randn(10, 10))
            param.grad = torch.randn(10, 10)
            params.append(param)

        mock_model.parameters = Mock(return_value=params)
        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

        mock_output = Mock()
        mock_output.loss = torch.tensor(1.0, requires_grad=True)
        mock_model.return_value = mock_output

        from client.client import train_and_get_update

        # Execute
        update = train_and_get_update("test text")

        # Should still produce update
        assert update is not None
        assert isinstance(update, list)

    @patch('client.client.DP_GRADIENT_SLICE_SIZE', 10)
    @patch('client.client.DP_MAX_PARAMS', 3)
    @patch('client.client.model')
    @patch('client.client.tokenizer')
    @patch('client.client.privacy_accountant')
    @patch('client.client.gradient_clipper')
    @patch('client.client.noise_generator')
    def test_configurable_slicing(
        self,
        mock_noise_gen,
        mock_clipper,
        mock_accountant,
        mock_tokenizer,
        mock_model
    ):
        """Test configurable gradient slicing."""
        # Setup mocks
        mock_model.train = Mock()
        mock_model.zero_grad = Mock()

        # Create mock parameters with gradients
        params = []
        for _ in range(5):
            param = torch.nn.Parameter(torch.randn(20, 20))  # Large enough for slice of 10
            param.grad = torch.randn(20, 20)
            params.append(param)

        mock_model.parameters = Mock(return_value=params)
        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

        mock_output = Mock()
        mock_output.loss = torch.tensor(1.0, requires_grad=True)
        mock_model.return_value = mock_output

        mock_accountant.can_proceed.return_value = True
        mock_accountant.get_current_privacy.return_value = (0.5, 1e-5)
        mock_accountant.steps = 1
        mock_clipper.clip_gradients.return_value = 0.8
        mock_noise_gen.noise_multiplier = 1.0

        from client.client import train_and_get_update

        # Execute
        update = train_and_get_update("test text")

        # Verify slicing
        assert update is not None
        assert len(update) == 3  # DP_MAX_PARAMS = 3
        assert all(len(slice_data) == 10 for slice_data in update)  # DP_GRADIENT_SLICE_SIZE = 10


class TestPrivacyTrackerIntegration:
    """Tests for privacy tracker integration with client."""

    @patch('client.client.get_privacy_tracker')
    @patch('client.client.model')
    @patch('client.client.tokenizer')
    @patch('client.client.privacy_accountant')
    @patch('client.client.gradient_clipper')
    @patch('client.client.noise_generator')
    def test_privacy_tracker_records_loss(
        self,
        mock_noise_gen,
        mock_clipper,
        mock_accountant,
        mock_tokenizer,
        mock_model,
        mock_get_tracker
    ):
        """Test that privacy tracker records privacy loss."""
        # Setup mocks
        mock_tracker = Mock()
        mock_get_tracker.return_value = mock_tracker

        mock_model.train = Mock()
        mock_model.zero_grad = Mock()
        mock_model.parameters = Mock(return_value=[
            torch.nn.Parameter(torch.randn(10, 10))
        ])

        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

        mock_output = Mock()
        mock_output.loss = torch.tensor(1.0, requires_grad=True)
        mock_model.return_value = mock_output

        mock_accountant.can_proceed.return_value = True
        mock_accountant.get_current_privacy.return_value = (0.5, 1e-5)
        mock_accountant.steps = 1
        mock_clipper.clip_gradients.return_value = 0.8
        mock_noise_gen.noise_multiplier = 1.0

        from client.client import train_and_get_update

        # Execute
        train_and_get_update("test text")

        # Verify privacy tracker was called
        mock_get_tracker.assert_called_once()
        mock_tracker.record_privacy_loss.assert_called_once()
