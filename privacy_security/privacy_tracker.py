"""
Privacy budget tracker for PrivaLoom federated learning.

Provides persistent tracking of cumulative privacy loss (ε, δ) across multiple
training rounds with thread-safe state management.
"""

import json
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from utils.logging import setup_logger, log_info, log_error
from utils.types import PrivacyBudget

# Initialize logger
logger = setup_logger("privaloom.privacy")

# Global lock for thread-safe privacy state operations
_privacy_lock = threading.Lock()


@dataclass
class PrivacyState:
    """Persistent privacy state tracking cumulative privacy loss."""
    cumulative_epsilon: float = 0.0
    cumulative_delta: float = 0.0
    total_rounds: int = 0
    last_update_timestamp: Optional[str] = None
    privacy_history: list = None  # List of (round, epsilon, delta) tuples

    def __post_init__(self):
        if self.privacy_history is None:
            self.privacy_history = []


class PrivacyTracker:
    """
    Manages persistent privacy budget tracking across training rounds.

    Extends the RoundTracker pattern with privacy-specific state management.
    """

    def __init__(self, state_file_path: Optional[str] = None):
        """
        Initialize privacy tracker with persistent state file.

        Args:
            state_file_path: Path to state file, defaults to ~/.privaloom/privacy_state.json
        """
        if state_file_path is None:
            # Use user home directory for persistent state
            home_dir = Path.home()
            privaloom_dir = home_dir / ".privaloom"
            privaloom_dir.mkdir(exist_ok=True)
            self.state_file = privaloom_dir / "privacy_state.json"
        else:
            self.state_file = Path(state_file_path)

        self._state = self._load_state()

    def _load_state(self) -> PrivacyState:
        """Load privacy state from persistent storage."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return PrivacyState(**data)
        except (json.JSONDecodeError, TypeError, FileNotFoundError) as e:
            log_error(logger, "Failed to load privacy state, using defaults", error=str(e))

        # Return default state if loading fails
        return PrivacyState()

    def _save_state(self) -> None:
        """Save privacy state to persistent storage."""
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
            log_error(logger, "Failed to save privacy state", error=str(e))

    def record_privacy_loss(
        self,
        epsilon: float,
        delta: float,
        round_num: Optional[int] = None
    ) -> None:
        """
        Record privacy loss for a training round.

        Args:
            epsilon: Privacy loss (ε) for this round
            delta: Failure probability (δ) for this round
            round_num: Optional round number for tracking
        """
        with _privacy_lock:
            # Update cumulative privacy using advanced composition
            # For simplicity, we use basic composition: ε_total = Σ ε_i
            # Advanced composition would give tighter bounds
            self._state.cumulative_epsilon += epsilon
            self._state.cumulative_delta += delta
            self._state.total_rounds += 1
            self._state.last_update_timestamp = datetime.utcnow().isoformat()

            # Track history
            if round_num is None:
                round_num = self._state.total_rounds

            self._state.privacy_history.append({
                "round": round_num,
                "epsilon": epsilon,
                "delta": delta,
                "cumulative_epsilon": self._state.cumulative_epsilon,
                "cumulative_delta": self._state.cumulative_delta,
                "timestamp": self._state.last_update_timestamp
            })

            # Save to persistent storage
            self._save_state()

            log_info(
                logger,
                f"Privacy loss recorded for round {round_num}",
                round=round_num,
                epsilon=epsilon,
                delta=delta,
                cumulative_epsilon=self._state.cumulative_epsilon,
                cumulative_delta=self._state.cumulative_delta
            )

    def get_cumulative_privacy(self) -> dict:
        """
        Get cumulative privacy expenditure.

        Returns:
            Dict with cumulative epsilon, delta, and metadata
        """
        with _privacy_lock:
            return {
                "cumulative_epsilon": self._state.cumulative_epsilon,
                "cumulative_delta": self._state.cumulative_delta,
                "total_rounds": self._state.total_rounds,
                "last_update": self._state.last_update_timestamp
            }

    def get_privacy_budget(self) -> PrivacyBudget:
        """
        Get current privacy budget as (ε, δ) tuple.

        Returns:
            Tuple of (cumulative_epsilon, cumulative_delta)
        """
        with _privacy_lock:
            return (self._state.cumulative_epsilon, self._state.cumulative_delta)

    def check_budget_exhausted(
        self,
        epsilon_limit: float,
        delta_limit: Optional[float] = None
    ) -> bool:
        """
        Check if privacy budget is exhausted.

        Args:
            epsilon_limit: Maximum allowed cumulative epsilon
            delta_limit: Optional maximum allowed cumulative delta

        Returns:
            True if budget exhausted, False otherwise
        """
        with _privacy_lock:
            epsilon_exceeded = self._state.cumulative_epsilon >= epsilon_limit

            if delta_limit is not None:
                delta_exceeded = self._state.cumulative_delta >= delta_limit
                return epsilon_exceeded or delta_exceeded

            return epsilon_exceeded

    def get_privacy_history(self) -> list:
        """
        Get full privacy history across all rounds.

        Returns:
            List of privacy loss records for each round
        """
        with _privacy_lock:
            return self._state.privacy_history.copy()

    def reset_budget(self) -> None:
        """
        Reset privacy budget to zero (use with caution).

        This should only be used for testing or when starting a new privacy regime.
        """
        with _privacy_lock:
            self._state.cumulative_epsilon = 0.0
            self._state.cumulative_delta = 0.0
            self._state.total_rounds = 0
            self._state.privacy_history = []
            self._state.last_update_timestamp = datetime.utcnow().isoformat()

            self._save_state()

            log_info(logger, "Privacy budget reset to zero")


# Global privacy tracker instance
_global_privacy_tracker: Optional[PrivacyTracker] = None


def get_privacy_tracker() -> PrivacyTracker:
    """Get global privacy tracker instance (singleton)."""
    global _global_privacy_tracker
    if _global_privacy_tracker is None:
        _global_privacy_tracker = PrivacyTracker()
    return _global_privacy_tracker


def reset_privacy_tracker(state_file_path: Optional[str] = None) -> PrivacyTracker:
    """Reset global privacy tracker with new state file (mainly for testing)."""
    global _global_privacy_tracker
    _global_privacy_tracker = PrivacyTracker(state_file_path)
    return _global_privacy_tracker
