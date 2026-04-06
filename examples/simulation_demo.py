#!/usr/bin/env python3
"""
Example usage script for the multi-client simulation system.

This script demonstrates how to use the simulation system programmatically
and provides examples for different simulation scenarios.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from server.api import app
from simulation.orchestrator import SimulationOrchestrator, SimulationConfig
from simulation.scenarios import get_scenario_library, create_custom_scenario
from simulation.client_factory import ClientFactory, PopulationConfig
from simulation.data_distribution import create_data_distributor
from simulation.metrics import create_metrics_collector
from privacy_security.security_monitor import reset_security_monitor
from privacy_security.reputation import reset_reputation_manager
from utils.aggregation import reset_round_tracker


def run_basic_simulation():
    """Run a basic federated learning simulation."""
    print("🚀 Running Basic Federated Learning Simulation")
    print("=" * 60)

    # Setup
    test_client = TestClient(app)
    reset_simulation_state()

    # Load predefined scenario
    scenario_library = get_scenario_library()
    scenario = scenario_library.load_scenario("basic_federated_learning")

    # Reduce scale for demo
    scenario.total_rounds = 10
    scenario.client_population.total_clients = 15

    print(f"Scenario: {scenario.name}")
    print(f"Description: {scenario.description}")
    print(f"Clients: {scenario.client_population.total_clients}")
    print(f"Rounds: {scenario.total_rounds}")
    print(f"Aggregation: {scenario.environment_overrides.get('AGGREGATION_METHOD', 'default')}")
    print()

    # Run simulation
    orchestrator = SimulationOrchestrator(test_client=test_client, isolated_state=True)

    start_time = time.time()
    print("Starting simulation...")

    result = orchestrator.run_scenario(scenario)

    duration = time.time() - start_time
    print(f"✅ Simulation completed in {duration:.2f} seconds")
    print()

    # Display results
    print("📊 Results Summary:")
    print(f"  Success: {result.success}")
    print(f"  Completed rounds: {result.completed_rounds}/{result.total_rounds}")
    print(f"  Final accuracy: {result.final_model_accuracy or 'N/A'}")
    print(f"  Security events: {len(result.security_events)}")

    if result.performance_metrics:
        perf = result.performance_metrics
        print(f"  Avg round duration: {perf.get('avg_round_duration', 0):.2f}s")
        print(f"  Throughput: {perf.get('throughput', 0):.1f} updates/sec")

    return result


def run_byzantine_robustness_test():
    """Run a Byzantine robustness test."""
    print("\n🛡️ Running Byzantine Robustness Test")
    print("=" * 60)

    # Setup
    test_client = TestClient(app)
    reset_simulation_state()

    # Load Byzantine scenario
    scenario_library = get_scenario_library()
    scenario = scenario_library.load_scenario("byzantine_robustness_test")

    # Reduce scale for demo
    scenario.total_rounds = 15
    scenario.client_population.total_clients = 25

    print(f"Scenario: {scenario.name}")
    print(f"Honest fraction: {scenario.client_population.honest_fraction:.1%}")
    print(f"Malicious types: {scenario.client_population.malicious_types}")
    print(f"Attack intensity: {scenario.attack_config.attack_intensity}")
    print()

    # Run simulation
    orchestrator = SimulationOrchestrator(test_client=test_client, isolated_state=True)

    start_time = time.time()
    print("Starting Byzantine simulation...")

    result = orchestrator.run_scenario(scenario)

    duration = time.time() - start_time
    print(f"✅ Byzantine simulation completed in {duration:.2f} seconds")
    print()

    # Display results
    print("📊 Byzantine Robustness Results:")
    print(f"  System survived: {result.success}")
    print(f"  Completed rounds: {result.completed_rounds}/{result.total_rounds}")

    if result.byzantine_detection_stats:
        stats = result.byzantine_detection_stats
        print(f"  Outlier detection accuracy: {stats.get('outlier_detection_accuracy', 0):.3f}")
        print(f"  Malicious clients detected: {stats.get('malicious_clients_detected', 0)}")
        print(f"  Total security events: {stats.get('total_security_events', 0)}")

    print(f"  Final model accuracy: {result.final_model_accuracy or 'N/A'}")

    return result


def run_custom_simulation():
    """Run a custom simulation scenario."""
    print("\n⚙️ Running Custom Simulation Scenario")
    print("=" * 60)

    # Setup
    test_client = TestClient(app)
    reset_simulation_state()

    # Create custom scenario
    scenario = create_custom_scenario(
        name="custom_demo",
        description="Custom demonstration scenario",
        total_clients=20,
        total_rounds=8,
        honest_fraction=0.75,  # 25% malicious
        distribution_type="non_iid",
        attacks_enabled=True
    )

    # Customize environment
    scenario.environment_overrides.update({
        "AGGREGATION_METHOD": "median",
        "OUTLIER_DETECTION_ENABLED": "true",
        "REPUTATION_ENABLED": "true"
    })

    print(f"Custom Scenario Configuration:")
    print(f"  Total clients: {scenario.client_population.total_clients}")
    print(f"  Honest fraction: {scenario.client_population.honest_fraction:.1%}")
    print(f"  Data distribution: {scenario.data_distribution.distribution_type.value}")
    print(f"  Aggregation method: {scenario.environment_overrides['AGGREGATION_METHOD']}")
    print()

    # Run simulation
    orchestrator = SimulationOrchestrator(test_client=test_client, isolated_state=True)

    start_time = time.time()
    print("Starting custom simulation...")

    result = orchestrator.run_scenario(scenario)

    duration = time.time() - start_time
    print(f"✅ Custom simulation completed in {duration:.2f} seconds")
    print()

    # Display results
    print("📊 Custom Simulation Results:")
    print(f"  Success: {result.success}")
    print(f"  Rounds completed: {result.completed_rounds}")
    print(f"  Client participation: {result.client_participation_stats['total_clients']} clients")

    return result


def run_performance_benchmark():
    """Run a performance benchmark with different client counts."""
    print("\n⚡ Running Performance Benchmark")
    print("=" * 60)

    client_counts = [10, 25, 50]
    results = {}

    for client_count in client_counts:
        print(f"\nBenchmarking with {client_count} clients...")

        # Setup
        test_client = TestClient(app)
        reset_simulation_state()

        # Create benchmark scenario
        scenario = create_custom_scenario(
            name=f"benchmark_{client_count}",
            description=f"Benchmark with {client_count} clients",
            total_clients=client_count,
            total_rounds=5,  # Short rounds for benchmarking
            honest_fraction=1.0,  # All honest for pure performance
            distribution_type="iid",
            attacks_enabled=False
        )

        orchestrator = SimulationOrchestrator(test_client=test_client, isolated_state=True)

        start_time = time.time()
        result = orchestrator.run_scenario(scenario)
        duration = time.time() - start_time

        results[client_count] = {
            "duration": duration,
            "success": result.success,
            "avg_round_duration": result.performance_metrics.get("avg_round_duration", 0),
            "throughput": result.performance_metrics.get("throughput", 0)
        }

        print(f"  Duration: {duration:.2f}s")
        print(f"  Success: {result.success}")
        if result.performance_metrics:
            print(f"  Avg round time: {result.performance_metrics.get('avg_round_duration', 0):.2f}s")
            print(f"  Throughput: {result.performance_metrics.get('throughput', 0):.1f} updates/sec")

    # Summary
    print("\n📈 Performance Benchmark Summary:")
    print("Clients | Duration | Round Avg | Throughput")
    print("-" * 45)
    for client_count, data in results.items():
        print(f"{client_count:7} | {data['duration']:8.2f}s | {data['avg_round_duration']:9.2f}s | {data['throughput']:8.1f} ops/s")

    return results


def demonstrate_client_behaviors():
    """Demonstrate different client behavior types."""
    print("\n👥 Demonstrating Client Behavior Types")
    print("=" * 60)

    # Create population with various client types
    config = PopulationConfig(
        total_clients=15,
        honest_fraction=0.6,
        malicious_types={
            "gradient_scaling": 0.2,
            "sign_flipping": 0.1,
            "gradient_noise": 0.1
        },
        coordination_enabled=True,
        coordination_groups=2
    )

    clients = ClientFactory.create_population(config)

    print(f"Created {len(clients)} simulated clients:")
    client_type_counts = {}
    coordination_groups = set()

    for client in clients:
        client_type = client.client_type.value
        client_type_counts[client_type] = client_type_counts.get(client_type, 0) + 1

        if client.config.coordination_group:
            coordination_groups.add(client.config.coordination_group)

    for client_type, count in client_type_counts.items():
        percentage = (count / len(clients)) * 100
        print(f"  {client_type}: {count} clients ({percentage:.1f}%)")

    print(f"  Coordination groups: {len(coordination_groups)}")

    # Demonstrate data distribution
    print("\n📊 Data Distribution Demonstration:")

    # IID distribution
    iid_distributor = create_data_distributor("iid", samples_per_client=1000)
    client_ids = [client.client_id for client in clients[:5]]  # First 5 clients
    iid_configs = iid_distributor.distribute_data(client_ids)

    print("  IID Distribution:")
    for client_id, config in list(iid_configs.items())[:3]:
        print(f"    {client_id}: {config.data_samples} samples, quality={config.data_quality:.2f}")

    # Non-IID distribution
    non_iid_distributor = create_data_distributor("non_iid", heterogeneity_alpha=0.3)
    non_iid_configs = non_iid_distributor.distribute_data(client_ids)

    print("  Non-IID Distribution:")
    for client_id, config in list(non_iid_configs.items())[:3]:
        print(f"    {client_id}: {config.data_samples} samples, quality={config.data_quality:.2f}, noise={config.noise_level:.3f}")

    return clients


def reset_simulation_state():
    """Reset all simulation state for clean runs."""
    reset_security_monitor()
    reset_reputation_manager()
    reset_round_tracker()

    # Set simulation mode
    os.environ["SIMULATION_MODE"] = "true"
    os.environ["SIMULATION_LOGGING_VERBOSE"] = "false"


def main():
    """Run all demonstration examples."""
    print("🌟 PrivaLoom Multi-Client Simulation Demonstration")
    print("=" * 70)
    print("This script demonstrates the capabilities of the multi-client")
    print("simulation system for federated learning research and testing.")
    print("=" * 70)

    try:
        # 1. Basic federated learning
        result1 = run_basic_simulation()

        # 2. Byzantine robustness test
        result2 = run_byzantine_robustness_test()

        # 3. Custom scenario
        result3 = run_custom_simulation()

        # 4. Performance benchmark
        benchmark_results = run_performance_benchmark()

        # 5. Client behavior demonstration
        client_demo = demonstrate_client_behaviors()

        print("\n🎉 All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✅ Basic federated learning simulation")
        print("  ✅ Byzantine robustness testing")
        print("  ✅ Custom scenario creation")
        print("  ✅ Performance benchmarking")
        print("  ✅ Multiple client behavior types")
        print("  ✅ Data distribution patterns")
        print("  ✅ Security monitoring integration")
        print("  ✅ Real-time metrics collection")

        print(f"\nNext Steps:")
        print("  • Run 'python simulation/cli.py list-scenarios' to see all available scenarios")
        print("  • Use 'python simulation/cli.py run <scenario>' to run specific scenarios")
        print("  • Check tests/test_simulation_integration.py for comprehensive tests")
        print("  • Explore simulation/scenarios/ directory for scenario configurations")

    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())