"""
Aggregation state management for PrivaLoom federated learning.

Provides persistent round tracking, aggregation metadata, and state management
for multi-round federated learning with automatic retraining.
"""

import json
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.logging import setup_logger, log_info, log_error

# Initialize logger for aggregation module
logger = setup_logger("privaloom.aggregation")

# Global lock for thread-safe state operations
_state_lock = threading.Lock()


@dataclass
class AggregationState:
    """Persistent state for federated learning aggregation rounds."""
    current_round: int = 1
    total_updates_processed: int = 0
    last_aggregation_timestamp: Optional[str] = None
    last_aggregation_duration_ms: Optional[float] = None
    total_aggregation_rounds: int = 0


class RoundTracker:
    """Manages persistent round tracking and aggregation state."""

    def __init__(self, state_file_path: Optional[str] = None):
        """
        Initialize round tracker with persistent state file.

        Args:
            state_file_path: Path to state file, defaults to ~/.privaloom/aggregation_state.json
        """
        if state_file_path is None:
            # Use user home directory for persistent state
            home_dir = Path.home()
            privaloom_dir = home_dir / ".privaloom"
            privaloom_dir.mkdir(exist_ok=True)
            self.state_file = privaloom_dir / "aggregation_state.json"
        else:
            self.state_file = Path(state_file_path)

        self._state = self._load_state()

    def _load_state(self) -> AggregationState:
        """Load aggregation state from persistent storage."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return AggregationState(**data)
        except (json.JSONDecodeError, TypeError, FileNotFoundError) as e:
            log_error(logger, "Failed to load aggregation state, using defaults", error=e)

        # Return default state if loading fails
        return AggregationState()

    def _save_state(self) -> None:
        """Save aggregation state to persistent storage."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(exist_ok=True, parents=True)

            # Atomic write using temporary file
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(asdict(self._state), f, indent=2)

            # Atomic move to final location
            temp_file.replace(self.state_file)

        except (IOError, OSError) as e:
            log_error(logger, "Failed to save aggregation state", error=e)

    def get_current_round(self) -> int:
        """Get current round number."""
        with _state_lock:
            return self._state.current_round

    def start_new_round(self) -> int:
        """
        Start a new aggregation round.

        Returns:
            New round number
        """
        with _state_lock:
            round_num = self._state.current_round
            log_info(logger, f"Starting aggregation round {round_num}",
                    round=round_num, timestamp=datetime.utcnow().isoformat())
            return round_num

    def complete_round(self, num_updates: int, duration_ms: float) -> None:
        """
        Complete the current round and update persistent state.

        Args:
            num_updates: Number of updates processed in this round
            duration_ms: Aggregation duration in milliseconds
        """
        with _state_lock:
            # Update state
            self._state.current_round += 1
            self._state.total_updates_processed += num_updates
            self._state.last_aggregation_timestamp = datetime.utcnow().isoformat()
            self._state.last_aggregation_duration_ms = duration_ms
            self._state.total_aggregation_rounds += 1

            # Save to persistent storage
            self._save_state()

            log_info(logger, "Aggregation round completed",
                    round=self._state.current_round - 1,
                    total_rounds=self._state.total_aggregation_rounds,
                    updates_processed=num_updates,
                    duration_ms=duration_ms,
                    total_updates=self._state.total_updates_processed)

    def get_stats(self) -> dict:
        """Get current aggregation statistics."""
        with _state_lock:
            return {
                "current_round": self._state.current_round,
                "total_rounds_completed": self._state.total_aggregation_rounds,
                "total_updates_processed": self._state.total_updates_processed,
                "last_aggregation_timestamp": self._state.last_aggregation_timestamp,
                "last_duration_ms": self._state.last_aggregation_duration_ms
            }

    def get_privacy_stats(self) -> Optional[dict]:
        """
        Get privacy statistics (epsilon, delta) from privacy tracker if available.

        Returns:
            Privacy stats dict or None if privacy tracking not available
        """
        try:
            # Import here to avoid circular dependency
            from privacy_security.privacy_tracker import get_privacy_tracker
            privacy_tracker = get_privacy_tracker()
            return privacy_tracker.get_cumulative_privacy()
        except (ImportError, AttributeError):
            # Privacy module not available or not initialized
            return None


# Global round tracker instance
_global_tracker: Optional[RoundTracker] = None


def get_round_tracker() -> RoundTracker:
    """Get global round tracker instance (singleton)."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = RoundTracker()
    return _global_tracker


def reset_round_tracker(state_file_path: Optional[str] = None) -> RoundTracker:
    """Reset global round tracker with new state file (mainly for testing)."""
    global _global_tracker
    _global_tracker = RoundTracker(state_file_path)
    return _global_tracker