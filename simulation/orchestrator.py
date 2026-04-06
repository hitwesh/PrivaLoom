"""
Central orchestrator for multi-client federated learning simulations.

This module coordinates all aspects of simulation execution including client
management, round coordination, metrics collection, and scenario execution.
"""

import time
import os
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import threading
from fastapi.testclient import TestClient

from utils.logging import setup_logger, log_info, log_warning, log_error
from privacy_security.security_monitor import get_security_monitor, reset_security_monitor
from privacy_security.reputation import get_reputation_manager, reset_reputation_manager
from privacy_security.validation_pipeline import create_update_validator
from utils.aggregation import reset_round_tracker

from .scenarios import SimulationScenario, get_scenario_library
from .client_factory import ClientFactory, SimulatedClient, PopulationConfig
from .data_distribution import DataDistributor, create_data_distributor
from .metrics import MetricsCollector, create_metrics_collector

# Initialize logger
logger = setup_logger("privaloom.simulation.orchestrator")


@dataclass
class SimulationConfig:
    """Configuration for simulation orchestration."""
    total_clients: int = 50
    malicious_fraction: float = 0.2
    total_rounds: int = 100
    participation_rate: float = 0.8
    max_concurrent_clients: int = 50
    round_timeout: int = 60  # seconds
    environment_overrides: Dict[str, str] = None

    def __post_init__(self):
        if self.environment_overrides is None:
            self.environment_overrides = {}


@dataclass
class SimulationResult:
    """Results from a completed simulation."""
    scenario_name: str
    total_rounds: int
    completed_rounds: int
    final_model_accuracy: Optional[float]
    convergence_round: Optional[int]
    byzantine_detection_stats: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    security_events: List[Dict[str, Any]]
    client_participation_stats: Dict[str, Any]
    simulation_duration: float
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return asdict(self)


class SimulationOrchestrator:
    """Orchestrates multi-client federated learning simulations."""

    def __init__(self, test_client: TestClient, config: Optional[SimulationConfig] = None,
                 isolated_state: bool = True):
        """Initialize simulation orchestrator.

        Args:
            test_client: FastAPI test client for server communication
            config: Simulation configuration
            isolated_state: Whether to use isolated state for simulation
        """
        self.test_client = test_client
        self.config = config or SimulationConfig()
        self.isolated_state = isolated_state

        # Simulation state
        self.clients: List[SimulatedClient] = []
        self.data_distributor: Optional[DataDistributor] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.is_running = False
        self._stop_requested = False
        self._round_lock = threading.Lock()

        # Performance tracking
        self.simulation_start_time: Optional[float] = None

        log_info(logger, "SimulationOrchestrator initialized",
                 max_concurrent_clients=self.config.max_concurrent_clients,
                 isolated_state=isolated_state)

    def prepare_simulation(self, scenario: SimulationScenario) -> None:
        """Prepare simulation environment and components.

        Args:
            scenario: Simulation scenario to prepare for
        """
        log_info(logger, f"Preparing simulation: {scenario.name}")

        # Reset state if using isolated simulation
        if self.isolated_state:
            self._reset_simulation_state()

        # Apply environment overrides
        self._apply_environment_overrides(scenario.environment_overrides)

        # Create client population
        self.clients = ClientFactory.create_population(scenario.client_population)
        log_info(logger, f"Created {len(self.clients)} simulated clients")

        # Setup data distribution
        self.data_distributor = create_data_distributor(
            distribution_type=scenario.data_distribution.distribution_type.value,
            heterogeneity_alpha=scenario.data_distribution.heterogeneity_alpha,
            samples_per_client=scenario.data_distribution.samples_per_client,
            num_classes=scenario.data_distribution.num_classes,
            quality_variation=scenario.data_distribution.quality_variation,
            noise_clients_fraction=scenario.data_distribution.noise_clients_fraction
        )

        # Distribute data to clients
        client_ids = [client.client_id for client in self.clients]
        self.data_distributor.distribute_data(client_ids)
        log_info(logger, "Data distribution completed")

        # Initialize metrics collection
        security_monitor = get_security_monitor()
        reputation_manager = get_reputation_manager()
        self.metrics_collector = create_metrics_collector(
            security_monitor=security_monitor,
            reputation_manager=reputation_manager
        )

        log_info(logger, "Simulation preparation completed")

    def run_scenario(self, scenario: SimulationScenario) -> SimulationResult:
        """Run a complete simulation scenario.

        Args:
            scenario: Scenario to execute

        Returns:
            Simulation results
        """
        start_time = time.time()
        self.simulation_start_time = start_time
        self.is_running = True
        self._stop_requested = False

        try:
            log_info(logger, f"Starting simulation scenario: {scenario.name}")

            # Prepare simulation
            self.prepare_simulation(scenario)

            # Run simulation rounds
            completed_rounds = 0
            for round_number in range(1, scenario.total_rounds + 1):
                if self._stop_requested:
                    log_info(logger, "Simulation stopped by request")
                    break

                try:
                    self._execute_round(round_number, scenario)
                    completed_rounds = round_number
                    log_info(logger, f"Completed round {round_number}/{scenario.total_rounds}")

                except Exception as e:
                    log_error(logger, f"Error in round {round_number}: {e}")
                    break

            # Generate results
            simulation_duration = time.time() - start_time
            result = self._generate_simulation_result(
                scenario=scenario,
                completed_rounds=completed_rounds,
                simulation_duration=simulation_duration,
                success=True
            )

            log_info(logger, f"Simulation completed successfully",
                     scenario=scenario.name,
                     completed_rounds=completed_rounds,
                     duration=simulation_duration)

            return result

        except Exception as e:
            simulation_duration = time.time() - start_time
            log_error(logger, f"Simulation failed: {e}")

            # Generate error result
            result = self._generate_simulation_result(
                scenario=scenario,
                completed_rounds=0,
                simulation_duration=simulation_duration,
                success=False,
                error_message=str(e)
            )
            return result

        finally:
            self.is_running = False

    def _execute_round(self, round_number: int, scenario: SimulationScenario) -> None:
        """Execute a single federated learning round.

        Args:
            round_number: Current round number
            scenario: Simulation scenario
        """
        round_start_time = time.time()

        # Determine participating clients
        participating_clients = []
        for client in self.clients:
            if client.should_participate(round_number):
                participating_clients.append(client)

        if not participating_clients:
            log_warning(logger, f"No clients participating in round {round_number}")
            return

        log_info(logger, f"Round {round_number}: {len(participating_clients)} clients participating")

        # Generate base gradients for this round
        base_gradients = self._generate_base_gradients()

        # Generate client updates concurrently
        client_updates = self._generate_client_updates_concurrent(
            participating_clients, round_number, base_gradients
        )

        if not client_updates:
            log_warning(logger, f"No valid updates generated in round {round_number}")
            return

        # Send updates to server
        outliers_detected = self._send_updates_to_server(client_updates)

        # Calculate round metrics
        aggregation_duration = 0.5  # Placeholder - would measure actual aggregation time
        round_duration = time.time() - round_start_time

        # Record metrics
        if self.metrics_collector:
            participating_client_ids = [client.client_id for client in participating_clients]
            self.metrics_collector.record_round_metrics(
                round_number=round_number,
                participating_clients=participating_client_ids,
                total_clients=len(self.clients),
                outliers_detected=outliers_detected,
                aggregation_method=scenario.environment_overrides.get("AGGREGATION_METHOD", "fedavg"),
                aggregation_duration=aggregation_duration,
                round_duration=round_duration
            )

    def _generate_base_gradients(self) -> List[List[float]]:
        """Generate base honest gradients for the round."""
        # This would typically come from actual model training
        # For simulation, we generate synthetic but realistic gradients
        import random
        import math

        gradients = []
        for param_idx in range(5):  # 5 parameter groups
            if param_idx == 0:  # Large layer
                param_size = 100
            elif param_idx < 3:  # Medium layers
                param_size = 50
            else:  # Small layers
                param_size = 20

            # Generate gradients with realistic scale
            param_gradients = []
            for i in range(param_size):
                # Base gradient with some structure
                base_val = random.gauss(0, 0.01)
                # Add sinusoidal structure to make it more realistic
                base_val += math.sin(i * 0.1) * 0.001
                param_gradients.append(base_val)

            gradients.append(param_gradients)

        return gradients

    def _generate_client_updates_concurrent(self, clients: List[SimulatedClient],
                                          round_number: int,
                                          base_gradients: List[List[float]]) -> List[Dict[str, Any]]:
        """Generate client updates using concurrent execution.

        Args:
            clients: List of participating clients
            round_number: Current round number
            base_gradients: Base gradients to modify per client

        Returns:
            List of valid client updates
        """
        updates = []
        max_workers = min(self.config.max_concurrent_clients, len(clients))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit client update generation tasks
            future_to_client = {
                executor.submit(self._generate_single_client_update, client, round_number, base_gradients): client
                for client in clients
            }

            # Collect results as they complete
            for future in as_completed(future_to_client):
                client = future_to_client[future]
                try:
                    update = future.result(timeout=30)  # 30 second timeout per client
                    if update:
                        updates.append(update)
                except Exception as e:
                    log_warning(logger, f"Failed to generate update for client {client.client_id}: {e}")

        log_info(logger, f"Generated {len(updates)} client updates")
        return updates

    def _generate_single_client_update(self, client: SimulatedClient, round_number: int,
                                     base_gradients: List[List[float]]) -> Optional[Dict[str, Any]]:
        """Generate update for a single client.

        Args:
            client: Client to generate update for
            round_number: Current round number
            base_gradients: Base gradients

        Returns:
            Client update dictionary or None
        """
        # Apply data distribution effects to base gradients
        if self.data_distributor:
            client_gradients = self.data_distributor.generate_client_gradients(
                client.client_id, base_gradients, round_number
            )
        else:
            client_gradients = base_gradients

        # Generate client-specific update
        return client.generate_update(round_number, client_gradients)

    def _send_updates_to_server(self, updates: List[Dict[str, Any]]) -> List[str]:
        """Send client updates to the federated learning server.

        Args:
            updates: List of client updates to send

        Returns:
            List of client IDs detected as outliers
        """
        outliers_detected = []
        successful_updates = 0

        # Send updates concurrently
        max_workers = min(20, len(updates))  # Limit concurrent HTTP requests

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_update = {
                executor.submit(self._send_single_update, update): update
                for update in updates
            }

            for future in as_completed(future_to_update):
                update = future_to_update[future]
                try:
                    response = future.result(timeout=10)  # 10 second timeout per request

                    if response.status_code == 200:
                        successful_updates += 1
                        response_data = response.json()

                        # Check if client was rejected due to being outlier
                        if response_data.get("status") == "rejected":
                            reason = response_data.get("reason", "")
                            if "outlier" in reason.lower() or "validation" in reason.lower():
                                outliers_detected.append(update["client_id"])

                    else:
                        log_warning(logger, f"Update rejected for client {update['client_id']}: {response.status_code}")

                except Exception as e:
                    log_warning(logger, f"Failed to send update for client {update['client_id']}: {e}")

        log_info(logger, f"Sent updates: {successful_updates} successful, {len(outliers_detected)} outliers detected")
        return outliers_detected

    def _send_single_update(self, update: Dict[str, Any]):
        """Send a single update to the server.

        Args:
            update: Client update to send

        Returns:
            HTTP response
        """
        return self.test_client.post("/send-update", json=update)

    def _generate_simulation_result(self, scenario: SimulationScenario, completed_rounds: int,
                                   simulation_duration: float, success: bool,
                                   error_message: Optional[str] = None) -> SimulationResult:
        """Generate simulation result summary.

        Args:
            scenario: Executed scenario
            completed_rounds: Number of completed rounds
            simulation_duration: Total simulation time
            success: Whether simulation was successful
            error_message: Error message if failed

        Returns:
            Simulation result summary
        """
        # Get final metrics
        final_accuracy = None
        convergence_round = None
        byzantine_stats = {}
        performance_stats = {}
        security_events = []
        participation_stats = {}

        if self.metrics_collector and success:
            try:
                convergence = self.metrics_collector.get_convergence_analysis()
                final_accuracy = convergence.final_accuracy
                convergence_round = convergence.rounds_to_convergence

                security_summary = self.metrics_collector.get_security_summary()
                byzantine_stats = {
                    "outlier_detection_accuracy": security_summary.outlier_detection_accuracy,
                    "malicious_clients_detected": len(security_summary.malicious_clients_detected),
                    "total_security_events": security_summary.total_security_events
                }

                performance_metrics = self.metrics_collector.get_performance_metrics()
                performance_stats = {
                    "avg_round_duration": performance_metrics.avg_round_duration,
                    "throughput": performance_metrics.throughput_updates_per_second,
                    "memory_usage_mb": performance_metrics.memory_usage_mb,
                    "cpu_utilization": performance_metrics.cpu_utilization
                }

                # Get security events
                security_monitor = get_security_monitor()
                recent_events = security_monitor.get_recent_events(hours=24)
                security_events = [event.to_dict() for event in recent_events]

                participation_stats = self.metrics_collector.get_client_participation_stats()

            except Exception as e:
                log_warning(logger, f"Error generating final metrics: {e}")

        return SimulationResult(
            scenario_name=scenario.name,
            total_rounds=scenario.total_rounds,
            completed_rounds=completed_rounds,
            final_model_accuracy=final_accuracy,
            convergence_round=convergence_round,
            byzantine_detection_stats=byzantine_stats,
            performance_metrics=performance_stats,
            security_events=security_events,
            client_participation_stats=participation_stats,
            simulation_duration=simulation_duration,
            success=success,
            error_message=error_message
        )

    def _reset_simulation_state(self) -> None:
        """Reset simulation state for isolated execution."""
        log_info(logger, "Resetting simulation state")

        # Reset security and aggregation state
        reset_security_monitor()
        reset_reputation_manager()
        reset_round_tracker()

        # Clear client and distributor state
        self.clients = []
        self.data_distributor = None
        self.metrics_collector = None

    def _apply_environment_overrides(self, overrides: Dict[str, str]) -> None:
        """Apply environment variable overrides for simulation.

        Args:
            overrides: Dictionary of environment variables to set
        """
        if not overrides:
            return

        log_info(logger, f"Applying {len(overrides)} environment overrides")

        for key, value in overrides.items():
            os.environ[key] = str(value)
            log_info(logger, f"Set {key}={value}")

    def stop_simulation(self) -> None:
        """Request simulation to stop gracefully."""
        self._stop_requested = True
        log_info(logger, "Simulation stop requested")

    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status.

        Returns:
            Dictionary with simulation status information
        """
        status = {
            "is_running": self.is_running,
            "total_clients": len(self.clients),
            "simulation_duration": time.time() - self.simulation_start_time if self.simulation_start_time else 0
        }

        if self.metrics_collector:
            status["completed_rounds"] = len(self.metrics_collector.round_metrics)

            if self.metrics_collector.round_metrics:
                last_round = self.metrics_collector.round_metrics[-1]
                status["last_round_number"] = last_round.round_number
                status["last_round_participants"] = last_round.participating_clients

        return status

    @classmethod
    def from_scenario_name(cls, test_client: TestClient, scenario_name: str, **kwargs) -> 'SimulationOrchestrator':
        """Create orchestrator from scenario name.

        Args:
            test_client: FastAPI test client
            scenario_name: Name of scenario to load
            **kwargs: Additional configuration options

        Returns:
            Configured simulation orchestrator
        """
        orchestrator = cls(test_client, **kwargs)
        return orchestrator

    @classmethod
    def from_config(cls, test_client: TestClient, config: SimulationConfig, **kwargs) -> 'SimulationOrchestrator':
        """Create orchestrator from configuration.

        Args:
            test_client: FastAPI test client
            config: Simulation configuration
            **kwargs: Additional options

        Returns:
            Configured simulation orchestrator
        """
        return cls(test_client, config=config, **kwargs)


def create_simulation_orchestrator(test_client: TestClient, **kwargs) -> SimulationOrchestrator:
    """Factory function for creating simulation orchestrators.

    Args:
        test_client: FastAPI test client for server communication
        **kwargs: Additional configuration parameters

    Returns:
        Configured simulation orchestrator
    """
    return SimulationOrchestrator(test_client, **kwargs)