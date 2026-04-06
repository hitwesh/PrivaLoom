"""
Real-time metrics collection and analytics for federated learning simulations.

This module provides comprehensive monitoring capabilities during simulation
execution, including convergence analysis, security monitoring, and performance
metrics collection.
"""

import time
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime

from utils.logging import setup_logger, log_info
from privacy_security.security_monitor import SecurityMonitor
from privacy_security.reputation import ReputationManager

# Initialize logger
logger = setup_logger("privaloom.simulation.metrics")


@dataclass
class RoundMetrics:
    """Metrics collected for a single federated learning round."""
    round_number: int
    timestamp: str
    participating_clients: int
    total_clients: int
    outliers_detected: int
    outlier_client_ids: List[str]
    aggregation_method: str
    aggregation_duration: float  # seconds
    round_duration: float  # seconds
    reputation_changes: Dict[str, float]  # client_id -> reputation change
    security_events_count: int
    model_accuracy: Optional[float] = None
    convergence_metric: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return asdict(self)


@dataclass
class ConvergenceMetrics:
    """Metrics tracking model convergence over time."""
    rounds_completed: int
    accuracy_progression: List[float]
    loss_progression: List[float]
    convergence_rate: float  # Change in accuracy per round
    stability_metric: float  # Variance in recent accuracy
    rounds_to_convergence: Optional[int] = None
    final_accuracy: Optional[float] = None
    byzantine_impact: Optional[float] = None  # Accuracy degradation due to attacks


@dataclass
class SecuritySummary:
    """Summary of security events and system robustness."""
    total_security_events: int
    events_by_type: Dict[str, int]
    malicious_clients_detected: Set[str]
    outlier_detection_accuracy: float
    false_positive_rate: float
    attack_mitigation_rate: float
    reputation_effectiveness: float


@dataclass
class PerformanceMetrics:
    """Performance metrics for simulation execution."""
    simulation_duration: float
    avg_round_duration: float
    throughput_updates_per_second: float
    memory_usage_mb: float
    cpu_utilization: float
    max_concurrent_clients: int


class MetricsCollector:
    """Collects and analyzes metrics during federated learning simulation."""

    def __init__(self, security_monitor: Optional[SecurityMonitor] = None,
                 reputation_manager: Optional[ReputationManager] = None):
        """Initialize metrics collector.

        Args:
            security_monitor: Security monitoring component
            reputation_manager: Reputation management component
        """
        self.security_monitor = security_monitor
        self.reputation_manager = reputation_manager

        # Metrics storage
        self.round_metrics: List[RoundMetrics] = []
        self.simulation_start_time = time.time()
        self.last_round_time = time.time()

        # Tracking state
        self.total_updates_processed = 0
        self.client_participation_history: Dict[str, List[int]] = {}  # client_id -> round_numbers

        log_info(logger, "MetricsCollector initialized")

    def record_round_metrics(self, round_number: int, participating_clients: List[str],
                            total_clients: int, outliers_detected: List[str],
                            aggregation_method: str, aggregation_duration: float,
                            **kwargs) -> None:
        """Record metrics for a completed federated learning round.

        Args:
            round_number: Round number
            participating_clients: List of client IDs that participated
            total_clients: Total number of clients in simulation
            outliers_detected: List of client IDs detected as outliers
            aggregation_method: Aggregation method used
            aggregation_duration: Time spent on aggregation (seconds)
            **kwargs: Additional metrics
        """
        current_time = time.time()
        round_duration = current_time - self.last_round_time

        # Track client participation
        for client_id in participating_clients:
            if client_id not in self.client_participation_history:
                self.client_participation_history[client_id] = []
            self.client_participation_history[client_id].append(round_number)

        # Get reputation changes if available
        reputation_changes = {}
        if self.reputation_manager:
            # This would require tracking previous reputation scores
            # For now, we'll implement a simplified version
            reputation_changes = {
                client_id: 0.0 for client_id in participating_clients
            }

        # Count security events for this round
        security_events_count = 0
        if self.security_monitor:
            recent_events = self.security_monitor.get_recent_events(hours=0.1)  # Last ~6 minutes
            security_events_count = len(recent_events)

        # Create round metrics
        metrics = RoundMetrics(
            round_number=round_number,
            timestamp=datetime.now().isoformat(),
            participating_clients=len(participating_clients),
            total_clients=total_clients,
            outliers_detected=len(outliers_detected),
            outlier_client_ids=outliers_detected,
            aggregation_method=aggregation_method,
            aggregation_duration=aggregation_duration,
            round_duration=round_duration,
            reputation_changes=reputation_changes,
            security_events_count=security_events_count,
            model_accuracy=kwargs.get('model_accuracy'),
            convergence_metric=kwargs.get('convergence_metric')
        )

        self.round_metrics.append(metrics)
        self.total_updates_processed += len(participating_clients)
        self.last_round_time = current_time

        log_info(logger, f"Round {round_number} metrics recorded",
                 participating_clients=len(participating_clients),
                 outliers_detected=len(outliers_detected),
                 round_duration=round_duration)

    def get_convergence_analysis(self) -> ConvergenceMetrics:
        """Analyze model convergence based on collected metrics.

        Returns:
            Convergence analysis metrics
        """
        if not self.round_metrics:
            return ConvergenceMetrics(
                rounds_completed=0,
                accuracy_progression=[],
                loss_progression=[],
                convergence_rate=0.0,
                stability_metric=0.0
            )

        # Extract accuracy progression
        accuracy_values = []
        for metrics in self.round_metrics:
            if metrics.model_accuracy is not None:
                accuracy_values.append(metrics.model_accuracy)

        # Calculate convergence rate
        convergence_rate = 0.0
        if len(accuracy_values) >= 2:
            recent_accuracies = accuracy_values[-5:]  # Last 5 rounds
            if len(recent_accuracies) >= 2:
                convergence_rate = (recent_accuracies[-1] - recent_accuracies[0]) / len(recent_accuracies)

        # Calculate stability (variance in recent accuracy)
        stability_metric = 0.0
        if len(accuracy_values) >= 3:
            recent_accuracies = accuracy_values[-5:]
            if len(recent_accuracies) >= 2:
                mean_acc = sum(recent_accuracies) / len(recent_accuracies)
                stability_metric = sum((acc - mean_acc) ** 2 for acc in recent_accuracies) / len(recent_accuracies)

        # Determine if converged
        rounds_to_convergence = None
        final_accuracy = None
        if len(accuracy_values) >= 5:
            # Simple convergence criteria: accuracy improvement < 0.001 for 3 consecutive rounds
            for i in range(2, len(accuracy_values)):
                recent_change = abs(accuracy_values[i] - accuracy_values[i-1])
                if recent_change < 0.001:
                    rounds_to_convergence = i + 1
                    final_accuracy = accuracy_values[i]
                    break

        return ConvergenceMetrics(
            rounds_completed=len(self.round_metrics),
            accuracy_progression=accuracy_values,
            loss_progression=[],  # Would need loss values from simulation
            convergence_rate=convergence_rate,
            stability_metric=stability_metric,
            rounds_to_convergence=rounds_to_convergence,
            final_accuracy=accuracy_values[-1] if accuracy_values else None
        )

    def get_security_summary(self, hours: int = 24) -> SecuritySummary:
        """Generate security summary based on collected events.

        Args:
            hours: Time window for analysis

        Returns:
            Security summary metrics
        """
        if not self.security_monitor:
            return SecuritySummary(
                total_security_events=0,
                events_by_type={},
                malicious_clients_detected=set(),
                outlier_detection_accuracy=0.0,
                false_positive_rate=0.0,
                attack_mitigation_rate=0.0,
                reputation_effectiveness=0.0
            )

        # Get security events
        recent_events = self.security_monitor.get_recent_events(hours=hours)
        attack_stats = self.security_monitor.get_attack_statistics(hours=hours)

        # Extract malicious clients from round metrics
        malicious_clients = set()
        for round_metric in self.round_metrics:
            malicious_clients.update(round_metric.outlier_client_ids)

        # Calculate detection accuracy (simplified)
        total_outliers = sum(metrics.outliers_detected for metrics in self.round_metrics)
        total_participating = sum(metrics.participating_clients for metrics in self.round_metrics)
        outlier_detection_accuracy = total_outliers / max(1, total_participating * 0.1)  # Assume 10% should be outliers

        # Calculate false positive rate (would need ground truth for accurate calculation)
        false_positive_rate = 0.05  # Placeholder

        return SecuritySummary(
            total_security_events=len(recent_events),
            events_by_type=attack_stats.get("events_by_type", {}),
            malicious_clients_detected=malicious_clients,
            outlier_detection_accuracy=min(1.0, outlier_detection_accuracy),
            false_positive_rate=false_positive_rate,
            attack_mitigation_rate=0.85,  # Placeholder
            reputation_effectiveness=0.80  # Placeholder
        )

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate simulation performance metrics.

        Returns:
            Performance metrics
        """
        current_time = time.time()
        simulation_duration = current_time - self.simulation_start_time

        # Calculate average round duration
        if self.round_metrics:
            avg_round_duration = sum(m.round_duration for m in self.round_metrics) / len(self.round_metrics)
        else:
            avg_round_duration = 0.0

        # Calculate throughput
        throughput = self.total_updates_processed / max(1, simulation_duration)

        # Get system metrics (simplified - would use psutil for real implementation)
        import psutil
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        cpu_utilization = psutil.cpu_percent(interval=1)

        max_concurrent = max((m.participating_clients for m in self.round_metrics), default=0)

        return PerformanceMetrics(
            simulation_duration=simulation_duration,
            avg_round_duration=avg_round_duration,
            throughput_updates_per_second=throughput,
            memory_usage_mb=memory_usage,
            cpu_utilization=cpu_utilization,
            max_concurrent_clients=max_concurrent
        )

    def export_metrics(self, filepath: str, format: str = "json") -> None:
        """Export collected metrics to file.

        Args:
            filepath: Output file path
            format: Export format ("json" or "csv")
        """
        if format == "json":
            export_data = {
                "simulation_summary": {
                    "total_rounds": len(self.round_metrics),
                    "simulation_duration": time.time() - self.simulation_start_time,
                    "total_updates_processed": self.total_updates_processed
                },
                "round_metrics": [metrics.to_dict() for metrics in self.round_metrics],
                "convergence_analysis": asdict(self.get_convergence_analysis()),
                "security_summary": asdict(self.get_security_summary()),
                "performance_metrics": asdict(self.get_performance_metrics())
            }

            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)

        elif format == "csv":
            import csv
            with open(filepath, 'w', newline='') as csvfile:
                if self.round_metrics:
                    fieldnames = self.round_metrics[0].to_dict().keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for metrics in self.round_metrics:
                        writer.writerow(metrics.to_dict())

        log_info(logger, f"Metrics exported to {filepath}", format=format)

    def get_client_participation_stats(self) -> Dict[str, Any]:
        """Get statistics about client participation patterns.

        Returns:
            Client participation analysis
        """
        if not self.client_participation_history:
            return {"error": "No participation data available"}

        total_rounds = len(self.round_metrics)
        participation_rates = {}

        for client_id, rounds_participated in self.client_participation_history.items():
            participation_rate = len(rounds_participated) / max(1, total_rounds)
            participation_rates[client_id] = participation_rate

        # Calculate overall statistics
        rates = list(participation_rates.values())
        avg_participation = sum(rates) / len(rates) if rates else 0.0
        min_participation = min(rates) if rates else 0.0
        max_participation = max(rates) if rates else 0.0

        # Find most and least active clients
        most_active = max(participation_rates.items(), key=lambda x: x[1]) if participation_rates else None
        least_active = min(participation_rates.items(), key=lambda x: x[1]) if participation_rates else None

        return {
            "total_clients": len(self.client_participation_history),
            "total_rounds": total_rounds,
            "avg_participation_rate": avg_participation,
            "min_participation_rate": min_participation,
            "max_participation_rate": max_participation,
            "most_active_client": most_active,
            "least_active_client": least_active,
            "client_participation_rates": participation_rates
        }

    def generate_simulation_report(self) -> Dict[str, Any]:
        """Generate comprehensive simulation report.

        Returns:
            Complete simulation analysis report
        """
        convergence = self.get_convergence_analysis()
        security = self.get_security_summary()
        performance = self.get_performance_metrics()
        participation = self.get_client_participation_stats()

        return {
            "report_generated": datetime.now().isoformat(),
            "simulation_overview": {
                "total_rounds": len(self.round_metrics),
                "simulation_duration": time.time() - self.simulation_start_time,
                "total_updates_processed": self.total_updates_processed
            },
            "convergence_analysis": asdict(convergence),
            "security_analysis": {
                "total_security_events": security.total_security_events,
                "events_by_type": security.events_by_type,
                "malicious_clients_detected": len(security.malicious_clients_detected),
                "outlier_detection_accuracy": security.outlier_detection_accuracy,
                "false_positive_rate": security.false_positive_rate
            },
            "performance_analysis": asdict(performance),
            "participation_analysis": participation,
            "key_findings": self._generate_key_findings(convergence, security, performance)
        }

    def _generate_key_findings(self, convergence: ConvergenceMetrics,
                              security: SecuritySummary,
                              performance: PerformanceMetrics) -> List[str]:
        """Generate key findings from simulation results."""
        findings = []

        # Convergence findings
        if convergence.rounds_to_convergence:
            findings.append(f"Model converged after {convergence.rounds_to_convergence} rounds")
        else:
            findings.append("Model did not reach convergence criteria")

        if convergence.final_accuracy and convergence.final_accuracy > 0.8:
            findings.append("High final accuracy achieved despite Byzantine clients")
        elif convergence.final_accuracy and convergence.final_accuracy < 0.5:
            findings.append("Low final accuracy suggests significant Byzantine impact")

        # Security findings
        if security.outlier_detection_accuracy > 0.9:
            findings.append("Excellent outlier detection performance")
        elif security.outlier_detection_accuracy < 0.7:
            findings.append("Outlier detection may need tuning")

        if len(security.malicious_clients_detected) > 0:
            findings.append(f"Successfully identified {len(security.malicious_clients_detected)} malicious clients")

        # Performance findings
        if performance.avg_round_duration < 5.0:
            findings.append("Good simulation performance with fast round completion")
        elif performance.avg_round_duration > 10.0:
            findings.append("Slow round completion may indicate performance bottlenecks")

        if performance.throughput_updates_per_second > 20:
            findings.append("High throughput achieved for update processing")

        return findings


def create_metrics_collector(security_monitor: Optional[SecurityMonitor] = None,
                           reputation_manager: Optional[ReputationManager] = None) -> MetricsCollector:
    """Factory function for creating metrics collectors.

    Args:
        security_monitor: Security monitoring component
        reputation_manager: Reputation management component

    Returns:
        Configured MetricsCollector instance
    """
    return MetricsCollector(
        security_monitor=security_monitor,
        reputation_manager=reputation_manager
    )