"""
Scenario configuration system for federated learning simulations.

This module provides YAML-based scenario management with predefined scenarios
for common federated learning testing patterns and the ability to create
custom scenarios.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from utils.logging import setup_logger, log_info, log_warning
from .client_factory import ClientType, PopulationConfig
from .data_distribution import DataDistributionType, DataDistributionConfig

# Initialize logger
logger = setup_logger("privaloom.simulation.scenarios")


@dataclass
class AttackConfig:
    """Configuration for attack patterns in simulation."""
    enabled: bool = False
    coordination_rate: float = 0.0  # Fraction of attacks that are coordinated
    adaptive_attacks: bool = False  # Enable adaptive attack patterns
    attack_intensity: str = "medium"  # low, medium, high
    attack_schedule: Optional[Dict[int, str]] = None  # round -> attack_type


@dataclass
class SimulationScenario:
    """Complete configuration for a federated learning simulation scenario."""
    name: str
    description: str
    total_rounds: int
    client_population: PopulationConfig
    data_distribution: DataDistributionConfig
    attack_config: AttackConfig
    environment_overrides: Dict[str, str]
    expected_outcomes: Optional[Dict[str, float]] = None  # For validation

    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "total_rounds": self.total_rounds,
            "client_population": asdict(self.client_population),
            "data_distribution": asdict(self.data_distribution),
            "attack_config": asdict(self.attack_config),
            "environment_overrides": self.environment_overrides,
            "expected_outcomes": self.expected_outcomes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationScenario':
        """Create scenario from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            total_rounds=data["total_rounds"],
            client_population=PopulationConfig(**data["client_population"]),
            data_distribution=DataDistributionConfig(**data["data_distribution"]),
            attack_config=AttackConfig(**data["attack_config"]),
            environment_overrides=data["environment_overrides"],
            expected_outcomes=data.get("expected_outcomes")
        )


class ScenarioLibrary:
    """Library of predefined simulation scenarios."""

    def __init__(self, scenarios_dir: Optional[str] = None):
        """Initialize scenario library.

        Args:
            scenarios_dir: Directory containing scenario YAML files
        """
        if scenarios_dir is None:
            scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")

        self.scenarios_dir = Path(scenarios_dir)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)

        # Create predefined scenarios if they don't exist
        self._create_predefined_scenarios()

        log_info(logger, "ScenarioLibrary initialized", scenarios_dir=str(self.scenarios_dir))

    def _create_predefined_scenarios(self) -> None:
        """Create predefined scenario files if they don't exist."""
        predefined_scenarios = {
            "basic_federated_learning": self._basic_federated_learning_scenario(),
            "byzantine_robustness_test": self._byzantine_robustness_scenario(),
            "large_scale_simulation": self._large_scale_scenario(),
            "coordinated_attack_simulation": self._coordinated_attack_scenario(),
            "dp_privacy_validation": self._dp_privacy_scenario(),
            "non_iid_heterogeneity": self._non_iid_scenario(),
            "pathological_non_iid": self._pathological_scenario(),
            "performance_benchmark": self._performance_benchmark_scenario(),
            "robustness_stress_test": self._robustness_stress_scenario(),
            "adaptive_attack_test": self._adaptive_attack_scenario()
        }

        for scenario_name, scenario in predefined_scenarios.items():
            scenario_file = self.scenarios_dir / f"{scenario_name}.yaml"
            if not scenario_file.exists():
                self._save_scenario_to_file(scenario, str(scenario_file))

    def _basic_federated_learning_scenario(self) -> SimulationScenario:
        """Basic federated learning with honest clients."""
        return SimulationScenario(
            name="basic_federated_learning",
            description="Basic federated learning with 20 honest clients and IID data distribution",
            total_rounds=50,
            client_population=PopulationConfig(
                total_clients=20,
                honest_fraction=1.0,
                participation_rate=0.8,
                dropout_probability=0.02
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.IID,
                samples_per_client=1000,
                quality_variation=False
            ),
            attack_config=AttackConfig(enabled=False),
            environment_overrides={
                "AGGREGATION_METHOD": "fedavg",
                "UPDATE_THRESHOLD": "10",
                "OUTLIER_DETECTION_ENABLED": "false"
            },
            expected_outcomes={
                "min_final_accuracy": 0.75,
                "max_convergence_rounds": 40,
                "max_security_events": 0
            }
        )

    def _byzantine_robustness_scenario(self) -> SimulationScenario:
        """Byzantine robustness testing with 30% malicious clients."""
        return SimulationScenario(
            name="byzantine_robustness_test",
            description="Test system resilience with 30% malicious clients using robust aggregation",
            total_rounds=100,
            client_population=PopulationConfig(
                total_clients=50,
                honest_fraction=0.7,
                malicious_types={
                    "gradient_scaling": 0.15,
                    "sign_flipping": 0.15
                },
                participation_rate=0.8,
                dropout_probability=0.05
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.NON_IID,
                heterogeneity_alpha=0.5,
                samples_per_client=1000,
                quality_variation=True
            ),
            attack_config=AttackConfig(
                enabled=True,
                coordination_rate=0.3,
                attack_intensity="high"
            ),
            environment_overrides={
                "AGGREGATION_METHOD": "trimmed_mean",
                "BYZANTINE_TOLERANCE": "0.3",
                "OUTLIER_DETECTION_ENABLED": "true",
                "REPUTATION_ENABLED": "true",
                "UPDATE_THRESHOLD": "15"
            },
            expected_outcomes={
                "min_final_accuracy": 0.5,
                "max_outlier_detection_rate": 0.95,
                "min_security_events": 10
            }
        )

    def _large_scale_scenario(self) -> SimulationScenario:
        """Large-scale simulation with 500+ clients."""
        return SimulationScenario(
            name="large_scale_simulation",
            description="Large-scale performance testing with 500+ clients",
            total_rounds=50,
            client_population=PopulationConfig(
                total_clients=500,
                honest_fraction=0.9,
                malicious_types={
                    "gradient_scaling": 0.05,
                    "dropout_prone": 0.05
                },
                participation_rate=0.6,  # Lower participation for scalability
                dropout_probability=0.1
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.NON_IID,
                heterogeneity_alpha=0.3,
                samples_per_client=500,  # Smaller per-client data
                quality_variation=True
            ),
            attack_config=AttackConfig(
                enabled=True,
                attack_intensity="low"
            ),
            environment_overrides={
                "AGGREGATION_METHOD": "median",
                "UPDATE_THRESHOLD": "50",
                "SIMULATION_MAX_CONCURRENT_CLIENTS": "100"
            },
            expected_outcomes={
                "max_avg_round_duration": 10.0,
                "min_throughput": 25.0,
                "max_memory_usage_mb": 2000
            }
        )

    def _coordinated_attack_scenario(self) -> SimulationScenario:
        """Sophisticated coordinated attack simulation."""
        return SimulationScenario(
            name="coordinated_attack_simulation",
            description="Test against sophisticated coordinated attacks",
            total_rounds=80,
            client_population=PopulationConfig(
                total_clients=40,
                honest_fraction=0.6,
                malicious_types={
                    "coordinated_malicious": 0.25,
                    "gradient_scaling": 0.15
                },
                coordination_enabled=True,
                coordination_groups=2,
                participation_rate=0.85
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.NON_IID,
                heterogeneity_alpha=0.4,
                samples_per_client=800
            ),
            attack_config=AttackConfig(
                enabled=True,
                coordination_rate=0.8,
                adaptive_attacks=True,
                attack_intensity="high",
                attack_schedule={
                    20: "scaling_burst",
                    40: "sign_flip_coordinated",
                    60: "adaptive_noise"
                }
            ),
            environment_overrides={
                "AGGREGATION_METHOD": "krum",
                "BYZANTINE_TOLERANCE": "0.4",
                "OUTLIER_DETECTION_ENABLED": "true",
                "REPUTATION_ENABLED": "true"
            },
            expected_outcomes={
                "min_final_accuracy": 0.4,
                "max_attack_success_rate": 0.3
            }
        )

    def _dp_privacy_scenario(self) -> SimulationScenario:
        """Differential privacy validation scenario."""
        return SimulationScenario(
            name="dp_privacy_validation",
            description="Test differential privacy mechanisms and budget consumption",
            total_rounds=100,
            client_population=PopulationConfig(
                total_clients=30,
                honest_fraction=0.9,
                malicious_types={"gradient_noise": 0.1},
                participation_rate=0.7
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.IID,
                samples_per_client=1200,
                quality_variation=False
            ),
            attack_config=AttackConfig(enabled=False),
            environment_overrides={
                "DP_ENABLED": "true",
                "DP_EPSILON": "8.0",
                "DP_DELTA": "1e-5",
                "DP_MAX_GRAD_NORM": "1.0",
                "AGGREGATION_METHOD": "fedavg"
            },
            expected_outcomes={
                "privacy_budget_consumed": 8.0,
                "min_final_accuracy": 0.6  # Lower due to DP noise
            }
        )

    def _non_iid_scenario(self) -> SimulationScenario:
        """Non-IID data heterogeneity testing."""
        return SimulationScenario(
            name="non_iid_heterogeneity",
            description="Test federated learning with realistic non-IID data distribution",
            total_rounds=75,
            client_population=PopulationConfig(
                total_clients=40,
                honest_fraction=0.85,
                malicious_types={"gradient_noise": 0.15},
                participation_rate=0.75
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.NON_IID,
                heterogeneity_alpha=0.1,  # High heterogeneity
                samples_per_client=800,
                quality_variation=True,
                noise_clients_fraction=0.2
            ),
            attack_config=AttackConfig(enabled=True, attack_intensity="low"),
            environment_overrides={
                "AGGREGATION_METHOD": "trimmed_mean",
                "OUTLIER_DETECTION_ENABLED": "true"
            },
            expected_outcomes={
                "min_final_accuracy": 0.55,
                "max_convergence_rounds": 70
            }
        )

    def _pathological_scenario(self) -> SimulationScenario:
        """Extreme pathological non-IID scenario."""
        return SimulationScenario(
            name="pathological_non_iid",
            description="Extreme heterogeneity with pathological data distribution",
            total_rounds=120,
            client_population=PopulationConfig(
                total_clients=30,
                honest_fraction=0.8,
                malicious_types={"sign_flipping": 0.2},
                participation_rate=0.6
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.PATHOLOGICAL,
                samples_per_client=600,
                quality_variation=True,
                noise_clients_fraction=0.3
            ),
            attack_config=AttackConfig(enabled=True, attack_intensity="medium"),
            environment_overrides={
                "AGGREGATION_METHOD": "median",
                "BYZANTINE_TOLERANCE": "0.2",
                "OUTLIER_DETECTION_ENABLED": "true"
            },
            expected_outcomes={
                "min_final_accuracy": 0.3,  # Very challenging scenario
                "max_convergence_rounds": 100
            }
        )

    def _performance_benchmark_scenario(self) -> SimulationScenario:
        """Performance benchmarking scenario."""
        return SimulationScenario(
            name="performance_benchmark",
            description="Benchmark simulation performance with various client counts",
            total_rounds=20,  # Short for benchmarking
            client_population=PopulationConfig(
                total_clients=100,
                honest_fraction=1.0,
                participation_rate=1.0  # All clients participate
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.IID,
                samples_per_client=500,
                quality_variation=False
            ),
            attack_config=AttackConfig(enabled=False),
            environment_overrides={
                "AGGREGATION_METHOD": "fedavg",
                "UPDATE_THRESHOLD": "100"  # Process all clients at once
            },
            expected_outcomes={
                "max_avg_round_duration": 5.0,
                "min_throughput": 50.0
            }
        )

    def _robustness_stress_scenario(self) -> SimulationScenario:
        """Stress test robustness with extreme conditions."""
        return SimulationScenario(
            name="robustness_stress_test",
            description="Stress test with maximum Byzantine fraction and attacks",
            total_rounds=60,
            client_population=PopulationConfig(
                total_clients=30,
                honest_fraction=0.5,  # 50% malicious (at theoretical limit)
                malicious_types={
                    "gradient_scaling": 0.2,
                    "sign_flipping": 0.2,
                    "gradient_noise": 0.1
                },
                coordination_enabled=True,
                participation_rate=0.9
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.PATHOLOGICAL,
                heterogeneity_alpha=0.05,  # Extreme heterogeneity
                samples_per_client=400,
                quality_variation=True,
                noise_clients_fraction=0.4
            ),
            attack_config=AttackConfig(
                enabled=True,
                coordination_rate=0.9,
                attack_intensity="high",
                adaptive_attacks=True
            ),
            environment_overrides={
                "AGGREGATION_METHOD": "bulyan",
                "BYZANTINE_TOLERANCE": "0.5",
                "OUTLIER_DETECTION_ENABLED": "true",
                "REPUTATION_ENABLED": "true"
            },
            expected_outcomes={
                "min_final_accuracy": 0.2  # System should survive but with low accuracy
            }
        )

    def _adaptive_attack_scenario(self) -> SimulationScenario:
        """Adaptive attack patterns that change over time."""
        return SimulationScenario(
            name="adaptive_attack_test",
            description="Test against adaptive attacks that change strategy",
            total_rounds=90,
            client_population=PopulationConfig(
                total_clients=35,
                honest_fraction=0.75,
                malicious_types={
                    "gradient_scaling": 0.15,
                    "coordinated_malicious": 0.1
                },
                coordination_enabled=True
            ),
            data_distribution=DataDistributionConfig(
                distribution_type=DataDistributionType.NON_IID,
                heterogeneity_alpha=0.3,
                samples_per_client=900
            ),
            attack_config=AttackConfig(
                enabled=True,
                coordination_rate=0.6,
                adaptive_attacks=True,
                attack_intensity="medium",
                attack_schedule={
                    0: "dormant",
                    20: "scaling_attack",
                    40: "sign_flip_attack",
                    60: "noise_attack",
                    80: "coordinated_burst"
                }
            ),
            environment_overrides={
                "AGGREGATION_METHOD": "trimmed_mean",
                "BYZANTINE_TOLERANCE": "0.25",
                "OUTLIER_DETECTION_ENABLED": "true",
                "REPUTATION_ENABLED": "true"
            },
            expected_outcomes={
                "min_final_accuracy": 0.45,
                "adaptation_detection_rate": 0.8
            }
        )

    def load_scenario(self, scenario_name: str) -> SimulationScenario:
        """Load a scenario by name.

        Args:
            scenario_name: Name of the scenario to load

        Returns:
            Loaded simulation scenario

        Raises:
            FileNotFoundError: If scenario file doesn't exist
            ValueError: If scenario file is invalid
        """
        scenario_file = self.scenarios_dir / f"{scenario_name}.yaml"

        if not scenario_file.exists():
            raise FileNotFoundError(f"Scenario '{scenario_name}' not found at {scenario_file}")

        try:
            with open(scenario_file, 'r') as f:
                scenario_data = yaml.safe_load(f)

            # Convert string enums back to enum objects
            if 'client_population' in scenario_data and 'malicious_types' in scenario_data['client_population']:
                # Malicious types are already strings, no conversion needed
                pass

            if 'data_distribution' in scenario_data:
                dist_type = scenario_data['data_distribution']['distribution_type']
                scenario_data['data_distribution']['distribution_type'] = DataDistributionType(dist_type)

            scenario = SimulationScenario.from_dict(scenario_data)
            log_info(logger, f"Loaded scenario '{scenario_name}'", file=str(scenario_file))
            return scenario

        except (yaml.YAMLError, KeyError, ValueError, TypeError) as e:
            log_warning(logger, f"Failed to load scenario '{scenario_name}': {e}")
            raise ValueError(f"Invalid scenario file '{scenario_name}': {e}")

    def list_scenarios(self) -> List[str]:
        """List all available scenarios.

        Returns:
            List of scenario names
        """
        scenario_files = self.scenarios_dir.glob("*.yaml")
        return [f.stem for f in scenario_files]

    def save_scenario(self, scenario: SimulationScenario, overwrite: bool = False) -> None:
        """Save a scenario to the library.

        Args:
            scenario: Scenario to save
            overwrite: Whether to overwrite existing scenario

        Raises:
            FileExistsError: If scenario exists and overwrite=False
        """
        scenario_file = self.scenarios_dir / f"{scenario.name}.yaml"

        if scenario_file.exists() and not overwrite:
            raise FileExistsError(f"Scenario '{scenario.name}' already exists. Use overwrite=True to replace.")

        self._save_scenario_to_file(scenario, str(scenario_file))

    def _save_scenario_to_file(self, scenario: SimulationScenario, filepath: str) -> None:
        """Save scenario to YAML file."""
        # Convert scenario to dictionary with proper enum serialization
        scenario_dict = scenario.to_dict()

        # Convert enum values to strings for YAML serialization
        if 'distribution_type' in scenario_dict['data_distribution']:
            scenario_dict['data_distribution']['distribution_type'] = scenario_dict['data_distribution']['distribution_type'].value

        with open(filepath, 'w') as f:
            yaml.dump(scenario_dict, f, indent=2, default_flow_style=False)

        log_info(logger, f"Scenario saved", name=scenario.name, file=filepath)

    def validate_scenario(self, scenario: SimulationScenario) -> List[str]:
        """Validate a scenario configuration.

        Args:
            scenario: Scenario to validate

        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []

        # Validate client population
        if scenario.client_population.total_clients < 1:
            warnings.append("Total clients must be at least 1")

        if not (0.0 <= scenario.client_population.honest_fraction <= 1.0):
            warnings.append("Honest fraction must be between 0.0 and 1.0")

        if scenario.client_population.malicious_types:
            malicious_sum = sum(scenario.client_population.malicious_types.values())
            expected_malicious = 1.0 - scenario.client_population.honest_fraction
            if abs(malicious_sum - expected_malicious) > 0.01:
                warnings.append(f"Malicious type fractions sum to {malicious_sum}, expected {expected_malicious}")

        # Validate rounds
        if scenario.total_rounds < 1:
            warnings.append("Total rounds must be at least 1")

        # Validate data distribution
        if scenario.data_distribution.samples_per_client < 10:
            warnings.append("Very low samples per client may cause instability")

        # Validate environment overrides
        aggregation_method = scenario.environment_overrides.get("AGGREGATION_METHOD", "")
        valid_methods = ["fedavg", "trimmed_mean", "median", "krum", "bulyan"]
        if aggregation_method and aggregation_method not in valid_methods:
            warnings.append(f"Unknown aggregation method: {aggregation_method}")

        return warnings


# Global scenario library instance
_scenario_library = None


def get_scenario_library() -> ScenarioLibrary:
    """Get the global scenario library instance."""
    global _scenario_library
    if _scenario_library is None:
        _scenario_library = ScenarioLibrary()
    return _scenario_library


def create_custom_scenario(name: str, description: str, **kwargs) -> SimulationScenario:
    """Create a custom scenario with specified parameters.

    Args:
        name: Scenario name
        description: Scenario description
        **kwargs: Additional scenario parameters

    Returns:
        Custom simulation scenario
    """
    defaults = {
        "total_rounds": 50,
        "total_clients": 20,
        "honest_fraction": 0.8,
        "distribution_type": "non_iid",
        "attacks_enabled": False
    }

    # Override defaults with provided kwargs
    config = {**defaults, **kwargs}

    return SimulationScenario(
        name=name,
        description=description,
        total_rounds=config["total_rounds"],
        client_population=PopulationConfig(
            total_clients=config["total_clients"],
            honest_fraction=config["honest_fraction"]
        ),
        data_distribution=DataDistributionConfig(
            distribution_type=DataDistributionType(config["distribution_type"])
        ),
        attack_config=AttackConfig(enabled=config["attacks_enabled"]),
        environment_overrides={}
    )