"""
Client reputation system for tracking and weighting federated learning participants.

This module provides persistent reputation tracking for clients, allowing the
system to weight updates based on historical behavior and exclude clients
with consistently malicious behavior:
- Persistent reputation scoring (0.0-1.0)
- Quality-based score updates with decay over time
- Reputation-weighted aggregation support
- Client blacklisting for low-reputation participants
- Audit trail of reputation changes

Follows the same persistence patterns as PrivacyTracker for reliability.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from utils.logging import setup_logger, log_info, log_warning, log_error
from utils.types import ClientID, ReputationScore

# Initialize logger
logger = setup_logger("privaloom.reputation")


@dataclass
class ReputationHistoryEntry:
    """Single entry in client reputation history."""
    timestamp: str
    old_score: float
    new_score: float
    quality_score: float
    reason: str
    update_count: int


@dataclass
class ClientReputation:
    """Reputation information for a single client."""
    client_id: str
    score: float  # Current reputation score (0.0-1.0)
    total_updates: int  # Total updates submitted by this client
    last_update_time: str  # ISO timestamp of last update
    created_time: str  # ISO timestamp when client was first seen
    score_history: List[ReputationHistoryEntry]  # History of score changes

    def __post_init__(self):
        """Ensure score is within valid range."""
        self.score = max(0.0, min(1.0, self.score))

    def add_history_entry(self, old_score: float, new_score: float,
                         quality_score: float, reason: str) -> None:
        """Add entry to reputation history.

        Args:
            old_score: Previous reputation score
            new_score: New reputation score
            quality_score: Quality score that triggered the update
            reason: Reason for reputation change
        """
        entry = ReputationHistoryEntry(
            timestamp=datetime.now().isoformat(),
            old_score=old_score,
            new_score=new_score,
            quality_score=quality_score,
            reason=reason,
            update_count=self.total_updates
        )
        self.score_history.append(entry)

        # Keep only last 100 entries to prevent unbounded growth
        if len(self.score_history) > 100:
            self.score_history = self.score_history[-100:]

    def get_recent_quality_scores(self, hours: int = 24) -> List[float]:
        """Get quality scores from recent history.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent quality scores
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()

        return [entry.quality_score for entry in self.score_history
                if entry.timestamp >= cutoff_iso]

    def get_score_trend(self) -> str:
        """Get general trend of reputation score.

        Returns:
            "improving", "declining", or "stable"
        """
        if len(self.score_history) < 2:
            return "stable"

        recent_entries = self.score_history[-10:]  # Last 10 entries
        if len(recent_entries) < 2:
            return "stable"

        first_score = recent_entries[0].new_score
        last_score = recent_entries[-1].new_score

        if last_score > first_score + 0.05:
            return "improving"
        elif last_score < first_score - 0.05:
            return "declining"
        else:
            return "stable"


@dataclass
class ReputationState:
    """Overall reputation system state."""
    clients: Dict[str, ClientReputation]
    system_created_time: str
    last_decay_time: str
    total_updates_processed: int
    reputation_config: Dict[str, Any]

    @classmethod
    def create_default(cls) -> 'ReputationState':
        """Create default reputation state."""
        return cls(
            clients={},
            system_created_time=datetime.now().isoformat(),
            last_decay_time=datetime.now().isoformat(),
            total_updates_processed=0,
            reputation_config={}
        )


class ReputationManager:
    """Manages client reputation tracking and persistence."""

    def __init__(self, state_file_path: Optional[str] = None,
                 learning_rate: float = 0.05,
                 decay_rate: float = 0.01,
                 min_reputation_threshold: float = 0.3,
                 initial_reputation: float = 0.8):
        """Initialize reputation manager.

        Args:
            state_file_path: Path to persistent state file (defaults to ~/.privaloom/reputation_state.json)
            learning_rate: Rate of reputation score updates (0.0-1.0)
            decay_rate: Daily decay rate for inactive clients (0.0-1.0)
            min_reputation_threshold: Minimum score to accept updates
            initial_reputation: Initial reputation for new clients
        """
        if state_file_path is None:
            default_dir = Path.home() / ".privaloom"
            default_dir.mkdir(parents=True, exist_ok=True)
            state_file_path = str(default_dir / "reputation_state.json")

        self.state_file = Path(state_file_path)
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.min_reputation_threshold = min_reputation_threshold
        self.initial_reputation = initial_reputation
        self._state = self._load_state()
        self._lock = threading.Lock()

        # Update config in state
        self._state.reputation_config = {
            "learning_rate": learning_rate,
            "decay_rate": decay_rate,
            "min_reputation_threshold": min_reputation_threshold,
            "initial_reputation": initial_reputation
        }

        log_info(logger, "Reputation manager initialized", extra={
            "state_file": str(self.state_file),
            "tracked_clients": len(self._state.clients),
            "config": self._state.reputation_config
        })

    def _load_state(self) -> ReputationState:
        """Load reputation state from persistent storage."""
        if not self.state_file.exists():
            return ReputationState.create_default()

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert client data back to ClientReputation objects
            clients = {}
            for client_id, client_data in data.get("clients", {}).items():
                # Convert history entries back to objects
                history = []
                for entry_data in client_data.get("score_history", []):
                    history.append(ReputationHistoryEntry(**entry_data))

                clients[client_id] = ClientReputation(
                    client_id=client_data["client_id"],
                    score=client_data["score"],
                    total_updates=client_data["total_updates"],
                    last_update_time=client_data["last_update_time"],
                    created_time=client_data["created_time"],
                    score_history=history
                )

            return ReputationState(
                clients=clients,
                system_created_time=data.get("system_created_time", datetime.now().isoformat()),
                last_decay_time=data.get("last_decay_time", datetime.now().isoformat()),
                total_updates_processed=data.get("total_updates_processed", 0),
                reputation_config=data.get("reputation_config", {})
            )

        except Exception as e:
            log_error(logger, f"Failed to load reputation state from {self.state_file}: {e}")
            return ReputationState.create_default()

    def _save_state(self) -> None:
        """Save reputation state to persistent storage atomically."""
        try:
            # Convert to JSON-serializable format
            data = {
                "clients": {},
                "system_created_time": self._state.system_created_time,
                "last_decay_time": self._state.last_decay_time,
                "total_updates_processed": self._state.total_updates_processed,
                "reputation_config": self._state.reputation_config
            }

            for client_id, reputation in self._state.clients.items():
                data["clients"][client_id] = {
                    "client_id": reputation.client_id,
                    "score": reputation.score,
                    "total_updates": reputation.total_updates,
                    "last_update_time": reputation.last_update_time,
                    "created_time": reputation.created_time,
                    "score_history": [asdict(entry) for entry in reputation.score_history]
                }

            # Atomic write using temporary file
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Atomic move
            temp_file.replace(self.state_file)

        except Exception as e:
            log_error(logger, f"Failed to save reputation state: {e}")

    def get_reputation(self, client_id: str) -> ClientReputation:
        """Get reputation for a client, creating new entry if needed.

        Args:
            client_id: Client identifier

        Returns:
            Client reputation object
        """
        with self._lock:
            if client_id not in self._state.clients:
                # Create new client with initial reputation
                now = datetime.now().isoformat()
                self._state.clients[client_id] = ClientReputation(
                    client_id=client_id,
                    score=self.initial_reputation,
                    total_updates=0,
                    last_update_time=now,
                    created_time=now,
                    score_history=[]
                )
                self._save_state()

                log_info(logger, "New client registered", extra={
                    "client_id": client_id,
                    "initial_reputation": self.initial_reputation
                })

            return self._state.clients[client_id]

    def update_reputation(self, client_id: str, quality_score: float, reason: str = "quality_update") -> None:
        """Update client reputation based on quality score.

        Args:
            client_id: Client identifier
            quality_score: Quality score for recent update (0.0-1.0)
            reason: Reason for reputation update
        """
        with self._lock:
            reputation = self.get_reputation(client_id)
            old_score = reputation.score

            # Exponential moving average update
            # new_score = (1 - α) * old_score + α * quality_score
            new_score = (1 - self.learning_rate) * old_score + self.learning_rate * quality_score
            new_score = max(0.0, min(1.0, new_score))  # Clamp to valid range

            # Update reputation
            reputation.score = new_score
            reputation.total_updates += 1
            reputation.last_update_time = datetime.now().isoformat()
            reputation.add_history_entry(old_score, new_score, quality_score, reason)

            self._state.total_updates_processed += 1
            self._save_state()

            log_info(logger, "Reputation updated", extra={
                "client_id": client_id,
                "old_score": old_score,
                "new_score": new_score,
                "quality_score": quality_score,
                "reason": reason,
                "total_updates": reputation.total_updates
            })

    def get_update_weight(self, client_id: str) -> float:
        """Get aggregation weight for client based on reputation.

        Args:
            client_id: Client identifier

        Returns:
            Weight for aggregation (0.0-1.0)
        """
        reputation = self.get_reputation(client_id)

        # Use sigmoid function to convert reputation score to weight
        # This gives higher weights to high-reputation clients
        weight = reputation.score

        # Apply minimum threshold - clients below threshold get zero weight
        if weight < self.min_reputation_threshold:
            weight = 0.0

        return weight

    def should_accept_update(self, client_id: str) -> bool:
        """Check if client's update should be accepted.

        Args:
            client_id: Client identifier

        Returns:
            True if update should be accepted
        """
        reputation = self.get_reputation(client_id)
        return reputation.score >= self.min_reputation_threshold

    def get_client_statistics(self, client_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a client.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary with client statistics
        """
        reputation = self.get_reputation(client_id)

        recent_quality_scores = reputation.get_recent_quality_scores(hours=24)

        return {
            "client_id": client_id,
            "current_score": reputation.score,
            "total_updates": reputation.total_updates,
            "last_update": reputation.last_update_time,
            "created_time": reputation.created_time,
            "score_trend": reputation.get_score_trend(),
            "recent_quality_average": sum(recent_quality_scores) / len(recent_quality_scores)
                                    if recent_quality_scores else 0.0,
            "recent_update_count": len(recent_quality_scores),
            "is_accepted": self.should_accept_update(client_id),
            "aggregation_weight": self.get_update_weight(client_id)
        }

    def get_all_client_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tracked clients.

        Returns:
            List of client statistics
        """
        with self._lock:
            return [self.get_client_statistics(client_id)
                   for client_id in self._state.clients.keys()]

    def decay_inactive_scores(self) -> None:
        """Apply decay to scores of inactive clients."""
        with self._lock:
            current_time = datetime.now()

            # Check if enough time has passed since last decay
            last_decay = datetime.fromisoformat(self._state.last_decay_time)
            if current_time - last_decay < timedelta(hours=24):
                return  # Don't decay more than once per day

            decayed_count = 0

            for client_id, reputation in self._state.clients.items():
                last_update = datetime.fromisoformat(reputation.last_update_time)
                inactive_days = (current_time - last_update).days

                if inactive_days > 1:  # Apply decay to clients inactive for >1 day
                    # Exponential decay: new_score = old_score * (1 - decay_rate)^days
                    decay_factor = (1 - self.decay_rate) ** inactive_days
                    old_score = reputation.score
                    new_score = old_score * decay_factor

                    if abs(new_score - old_score) > 0.001:  # Only update if significant change
                        reputation.score = new_score
                        reputation.add_history_entry(
                            old_score, new_score, 0.0,
                            f"inactivity_decay_{inactive_days}d"
                        )
                        decayed_count += 1

            self._state.last_decay_time = current_time.isoformat()

            if decayed_count > 0:
                self._save_state()
                log_info(logger, "Reputation decay applied", extra={
                    "decayed_clients": decayed_count,
                    "total_clients": len(self._state.clients)
                })

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get overall system statistics.

        Returns:
            Dictionary with system statistics
        """
        with self._lock:
            if not self._state.clients:
                return {
                    "total_clients": 0,
                    "total_updates_processed": self._state.total_updates_processed,
                    "system_uptime_days": 0
                }

            scores = [rep.score for rep in self._state.clients.values()]
            accepted_clients = sum(1 for rep in self._state.clients.values()
                                 if rep.score >= self.min_reputation_threshold)

            system_created = datetime.fromisoformat(self._state.system_created_time)
            uptime_days = (datetime.now() - system_created).days

            return {
                "total_clients": len(self._state.clients),
                "accepted_clients": accepted_clients,
                "rejected_clients": len(self._state.clients) - accepted_clients,
                "average_reputation": sum(scores) / len(scores),
                "min_reputation": min(scores),
                "max_reputation": max(scores),
                "total_updates_processed": self._state.total_updates_processed,
                "system_uptime_days": uptime_days,
                "last_decay_time": self._state.last_decay_time,
                "config": self._state.reputation_config
            }

    def reset_client_reputation(self, client_id: str) -> None:
        """Reset a client's reputation to initial value.

        Args:
            client_id: Client identifier
        """
        with self._lock:
            if client_id in self._state.clients:
                reputation = self._state.clients[client_id]
                old_score = reputation.score
                reputation.score = self.initial_reputation
                reputation.add_history_entry(
                    old_score, self.initial_reputation, 0.0, "manual_reset"
                )
                self._save_state()

                log_info(logger, "Client reputation reset", extra={
                    "client_id": client_id,
                    "old_score": old_score,
                    "new_score": self.initial_reputation
                })

    def blacklist_client(self, client_id: str, reason: str = "manual_blacklist") -> None:
        """Set client reputation to zero (effectively blacklist).

        Args:
            client_id: Client identifier
            reason: Reason for blacklisting
        """
        with self._lock:
            reputation = self.get_reputation(client_id)
            old_score = reputation.score
            reputation.score = 0.0
            reputation.add_history_entry(old_score, 0.0, 0.0, reason)
            self._save_state()

            log_warning(logger, "Client blacklisted", extra={
                "client_id": client_id,
                "reason": reason,
                "old_score": old_score
            })

    def export_reputation_data(self) -> Dict[str, Any]:
        """Export all reputation data for analysis or backup.

        Returns:
            Complete reputation state data
        """
        with self._lock:
            return {
                "clients": {client_id: asdict(rep) for client_id, rep in self._state.clients.items()},
                "system_statistics": self.get_system_statistics(),
                "export_timestamp": datetime.now().isoformat()
            }


def calculate_quality_score(update: List[List[float]],
                          aggregated_update: List[List[float]],
                          method: str = "cosine_similarity") -> float:
    """Calculate quality score for an update based on aggregated result.

    Args:
        update: Client's gradient update
        aggregated_update: Aggregated update from all clients
        method: Quality scoring method ("cosine_similarity" or "l2_distance")

    Returns:
        Quality score (0.0-1.0)
    """
    try:
        import numpy as np

        # Flatten both updates for comparison
        update_flat = []
        aggregated_flat = []

        for param_slice, agg_slice in zip(update, aggregated_update):
            update_flat.extend(param_slice)
            aggregated_flat.extend(agg_slice)

        update_vec = np.array(update_flat)
        aggregated_vec = np.array(aggregated_flat)

        if len(update_vec) != len(aggregated_vec):
            log_warning(logger, "Update and aggregated update have different lengths")
            return 0.5  # Neutral score

        if method == "cosine_similarity":
            # Cosine similarity between update and aggregated update
            dot_product = np.dot(update_vec, aggregated_vec)
            norm_update = np.linalg.norm(update_vec)
            norm_aggregated = np.linalg.norm(aggregated_vec)

            if norm_update == 0 or norm_aggregated == 0:
                return 0.5

            cosine_sim = dot_product / (norm_update * norm_aggregated)
            # Convert from [-1, 1] to [0, 1]
            quality_score = (cosine_sim + 1) / 2

        elif method == "l2_distance":
            # Inverse of normalized L2 distance
            l2_dist = np.linalg.norm(update_vec - aggregated_vec)
            max_possible_dist = np.linalg.norm(update_vec) + np.linalg.norm(aggregated_vec)

            if max_possible_dist == 0:
                return 1.0

            normalized_dist = l2_dist / max_possible_dist
            quality_score = 1.0 - normalized_dist

        else:
            log_error(logger, f"Unknown quality scoring method: {method}")
            return 0.5

        return max(0.0, min(1.0, quality_score))

    except Exception as e:
        log_error(logger, f"Failed to calculate quality score: {e}")
        return 0.5  # Neutral score on error


# Global reputation manager instance
_global_reputation_manager: Optional[ReputationManager] = None


def get_reputation_manager(state_file_path: Optional[str] = None, **kwargs) -> ReputationManager:
    """Get global reputation manager instance.

    Args:
        state_file_path: Path to state file (only used on first call)
        **kwargs: Configuration parameters (only used on first call)

    Returns:
        Global reputation manager instance
    """
    global _global_reputation_manager

    if _global_reputation_manager is None:
        _global_reputation_manager = ReputationManager(state_file_path, **kwargs)

    return _global_reputation_manager


def reset_reputation_manager(state_file_path: Optional[str] = None, **kwargs) -> ReputationManager:
    """Reset global reputation manager with new configuration.

    Args:
        state_file_path: Path to state file
        **kwargs: Configuration parameters

    Returns:
        New reputation manager instance
    """
    global _global_reputation_manager
    _global_reputation_manager = ReputationManager(state_file_path, **kwargs)
    return _global_reputation_manager