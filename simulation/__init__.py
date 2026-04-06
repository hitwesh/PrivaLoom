"""
Multi-client simulation system for federated learning.

This package provides comprehensive simulation capabilities for testing
federated learning systems with multiple clients, various attack patterns,
and realistic data distributions.
"""

from .orchestrator import SimulationOrchestrator, SimulationConfig, SimulationResult
from .client_factory import ClientFactory, SimulatedClient, ClientType, ClientConfig
from .scenarios import SimulationScenario, ScenarioLibrary, PopulationConfig
from .metrics import MetricsCollector, RoundMetrics, ConvergenceMetrics
from .data_distribution import DataDistributor, DataDistributionType, ClientDataConfig

__all__ = [
    "SimulationOrchestrator",
    "SimulationConfig",
    "SimulationResult",
    "ClientFactory",
    "SimulatedClient",
    "ClientType",
    "ClientConfig",
    "SimulationScenario",
    "ScenarioLibrary",
    "PopulationConfig",
    "MetricsCollector",
    "RoundMetrics",
    "ConvergenceMetrics",
    "DataDistributor",
    "DataDistributionType",
    "ClientDataConfig"
]