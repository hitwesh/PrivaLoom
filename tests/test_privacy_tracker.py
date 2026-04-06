"""
Tests for privacy tracker and persistent privacy budget management.
"""

import pytest
import json
from privacy_security.privacy_tracker import (
    PrivacyTracker,
    PrivacyState,
    get_privacy_tracker,
    reset_privacy_tracker
)


class TestPrivacyState:
    """Tests for PrivacyState dataclass."""

    def test_default_state(self):
        """Test default privacy state initialization."""
        state = PrivacyState()
        assert state.cumulative_epsilon == 0.0
        assert state.cumulative_delta == 0.0
        assert state.total_rounds == 0
        assert state.last_update_timestamp is None
        assert state.privacy_history == []


class TestPrivacyTracker:
    """Tests for privacy budget tracker."""

    def test_initialization_with_custom_file(self, temp_privacy_state_file):
        """Test tracker initialization with custom state file."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))
        assert tracker.state_file == temp_privacy_state_file

    def test_initial_privacy_is_zero(self, temp_privacy_state_file):
        """Test that initial privacy budget is zero."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))
        budget = tracker.get_privacy_budget()
        assert budget == (0.0, 0.0)

    def test_record_privacy_loss(self, temp_privacy_state_file):
        """Test recording privacy loss for a round."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        tracker.record_privacy_loss(epsilon=0.5, delta=1e-5, round_num=1)

        budget = tracker.get_privacy_budget()
        assert budget[0] == 0.5
        assert budget[1] == 1e-5

    def test_cumulative_privacy_loss(self, temp_privacy_state_file):
        """Test that privacy loss accumulates across rounds."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        # Record 5 rounds
        for i in range(1, 6):
            tracker.record_privacy_loss(epsilon=0.1, delta=1e-6, round_num=i)

        budget = tracker.get_privacy_budget()
        assert budget[0] == pytest.approx(0.5, rel=1e-6)
        assert budget[1] == pytest.approx(5e-6, rel=1e-9)

    def test_get_cumulative_privacy(self, temp_privacy_state_file):
        """Test getting cumulative privacy statistics."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        tracker.record_privacy_loss(epsilon=1.0, delta=1e-5, round_num=1)
        tracker.record_privacy_loss(epsilon=0.5, delta=1e-5, round_num=2)

        stats = tracker.get_cumulative_privacy()
        assert stats["cumulative_epsilon"] == 1.5
        assert stats["cumulative_delta"] == 2e-5
        assert stats["total_rounds"] == 2
        assert stats["last_update"] is not None

    def test_check_budget_not_exhausted(self, temp_privacy_state_file):
        """Test checking budget when not exhausted."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        tracker.record_privacy_loss(epsilon=0.5, delta=1e-5)

        # Should not be exhausted with limit of 10.0
        assert not tracker.check_budget_exhausted(epsilon_limit=10.0)

    def test_check_budget_exhausted(self, temp_privacy_state_file):
        """Test checking budget when exhausted."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        # Record enough to exhaust budget
        for _ in range(10):
            tracker.record_privacy_loss(epsilon=0.5, delta=1e-5)

        # Should be exhausted with limit of 1.0
        assert tracker.check_budget_exhausted(epsilon_limit=1.0)

    def test_check_budget_delta_limit(self, temp_privacy_state_file):
        """Test checking budget with delta limit."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        # Record 10 rounds
        for _ in range(10):
            tracker.record_privacy_loss(epsilon=0.01, delta=1e-5)

        # Should be exhausted on delta
        assert tracker.check_budget_exhausted(
            epsilon_limit=10.0,
            delta_limit=5e-5
        )

    def test_privacy_history(self, temp_privacy_state_file):
        """Test privacy history tracking."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        tracker.record_privacy_loss(epsilon=0.5, delta=1e-5, round_num=1)
        tracker.record_privacy_loss(epsilon=0.3, delta=1e-5, round_num=2)

        history = tracker.get_privacy_history()
        assert len(history) == 2
        assert history[0]["round"] == 1
        assert history[0]["epsilon"] == 0.5
        assert history[1]["round"] == 2
        assert history[1]["epsilon"] == 0.3
        assert history[1]["cumulative_epsilon"] == 0.8

    def test_persistence(self, temp_privacy_state_file):
        """Test that privacy state persists across tracker instances."""
        # Create tracker and record privacy
        tracker1 = PrivacyTracker(str(temp_privacy_state_file))
        tracker1.record_privacy_loss(epsilon=1.0, delta=1e-5, round_num=1)
        budget1 = tracker1.get_privacy_budget()

        # Create new tracker with same file
        tracker2 = PrivacyTracker(str(temp_privacy_state_file))
        budget2 = tracker2.get_privacy_budget()

        # Should have same budget
        assert budget1 == budget2
        assert budget2[0] == 1.0

    def test_persistence_across_restarts(self, temp_privacy_state_file):
        """Test state persistence with multiple rounds across restarts."""
        # First session
        tracker1 = PrivacyTracker(str(temp_privacy_state_file))
        for i in range(1, 4):
            tracker1.record_privacy_loss(epsilon=0.5, delta=1e-5, round_num=i)

        # Second session (simulated restart)
        tracker2 = PrivacyTracker(str(temp_privacy_state_file))
        for i in range(4, 7):
            tracker2.record_privacy_loss(epsilon=0.5, delta=1e-5, round_num=i)

        budget = tracker2.get_privacy_budget()
        assert budget[0] == pytest.approx(3.0, rel=1e-6)  # 6 rounds * 0.5
        assert tracker2._state.total_rounds == 6

    def test_reset_budget(self, temp_privacy_state_file):
        """Test resetting privacy budget."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        # Record some privacy loss
        tracker.record_privacy_loss(epsilon=5.0, delta=1e-4)
        assert tracker.get_privacy_budget()[0] == 5.0

        # Reset
        tracker.reset_budget()

        # Should be zero again
        budget = tracker.get_privacy_budget()
        assert budget == (0.0, 0.0)
        history = tracker.get_privacy_history()
        assert len(history) == 0

    def test_atomic_save(self, temp_privacy_state_file):
        """Test atomic save operation."""
        tracker = PrivacyTracker(str(temp_privacy_state_file))

        tracker.record_privacy_loss(epsilon=1.0, delta=1e-5)

        # State file should exist
        assert temp_privacy_state_file.exists()

        # Should be valid JSON
        with open(temp_privacy_state_file, 'r') as f:
            data = json.load(f)
            assert data["cumulative_epsilon"] == 1.0

        # Temp file should not exist after atomic move
        temp_file = temp_privacy_state_file.with_suffix('.tmp')
        assert not temp_file.exists()


class TestPrivacyTrackerSingleton:
    """Tests for global privacy tracker singleton."""

    def test_get_privacy_tracker(self):
        """Test getting global privacy tracker."""
        tracker = get_privacy_tracker()
        assert tracker is not None
        assert isinstance(tracker, PrivacyTracker)

    def test_singleton_same_instance(self):
        """Test that multiple calls return same instance."""
        tracker1 = get_privacy_tracker()
        tracker2 = get_privacy_tracker()
        assert tracker1 is tracker2

    def test_reset_privacy_tracker(self, temp_privacy_state_file):
        """Test resetting global privacy tracker."""
        # Get initial tracker
        tracker1 = get_privacy_tracker()

        # Reset with custom file
        tracker2 = reset_privacy_tracker(str(temp_privacy_state_file))

        # Should be different instance
        assert tracker1 is not tracker2
        assert tracker2.state_file == temp_privacy_state_file

        # Future calls should return new instance
        tracker3 = get_privacy_tracker()
        assert tracker3 is tracker2


class TestPrivacyTrackerThreadSafety:
    """Tests for thread-safe privacy tracking."""

    def test_concurrent_recording(self, temp_privacy_state_file):
        """Test concurrent privacy recording (simulated)."""
        import threading

        tracker = PrivacyTracker(str(temp_privacy_state_file))
        errors = []

        def record_rounds():
            try:
                for i in range(10):
                    tracker.record_privacy_loss(epsilon=0.1, delta=1e-5)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=record_rounds) for _ in range(5)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # Total privacy should be sum of all recordings
        budget = tracker.get_privacy_budget()
        assert budget[0] == pytest.approx(5.0, rel=1e-6)  # 50 rounds * 0.1
