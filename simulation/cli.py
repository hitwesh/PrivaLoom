"""
Command-line interface for multi-client federated learning simulations.

This module provides a user-friendly CLI for running simulation scenarios,
managing configurations, and analyzing results.
"""

import click
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from server.api import app
from simulation.orchestrator import SimulationOrchestrator, SimulationConfig
from simulation.scenarios import get_scenario_library, create_custom_scenario
from simulation.client_factory import ClientFactory, PopulationConfig
from utils.logging import setup_logger, log_info

# Initialize logger
logger = setup_logger("privaloom.simulation.cli")


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-file', '-c', help='Configuration file path')
@click.pass_context
def simulation(ctx, verbose, config_file):
    """Multi-client federated learning simulation toolkit."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file

    if verbose:
        click.echo("Verbose mode enabled")


@simulation.command()
@click.argument('scenario_name')
@click.option('--clients', '-c', default=None, type=int, help='Number of clients (overrides scenario)')
@click.option('--rounds', '-r', default=None, type=int, help='Training rounds (overrides scenario)')
@click.option('--malicious-fraction', '-m', default=None, type=float,
              help='Fraction of malicious clients (overrides scenario)')
@click.option('--output', '-o', help='Output file for results (JSON)')
@click.option('--aggregation-method', default=None,
              type=click.Choice(['fedavg', 'trimmed_mean', 'median', 'krum', 'bulyan']),
              help='Aggregation method (overrides scenario)')
@click.option('--data-distribution', default=None,
              type=click.Choice(['iid', 'non_iid', 'pathological']),
              help='Data distribution type (overrides scenario)')
@click.option('--isolated/--no-isolated', default=True,
              help='Use isolated simulation state (default: True)')
@click.option('--max-concurrent', default=50, type=int,
              help='Maximum concurrent clients')
@click.pass_context
def run(ctx, scenario_name, clients, rounds, malicious_fraction, output,
        aggregation_method, data_distribution, isolated, max_concurrent):
    """Run a simulation scenario.

    SCENARIO_NAME can be a predefined scenario or path to a custom scenario file.

    Examples:
        simulation run basic_federated_learning
        simulation run byzantine_robustness_test --clients 100 --rounds 50
        simulation run custom_scenario.yaml --output results.json
    """
    try:
        # Load scenario
        scenario_library = get_scenario_library()

        if scenario_name.endswith('.yaml') or scenario_name.endswith('.yml'):
            # Custom scenario file
            if not os.path.exists(scenario_name):
                click.echo(f"Error: Scenario file '{scenario_name}' not found", err=True)
                return
            scenario = scenario_library.load_scenario(Path(scenario_name).stem)
        else:
            # Predefined scenario
            try:
                scenario = scenario_library.load_scenario(scenario_name)
            except FileNotFoundError:
                click.echo(f"Error: Scenario '{scenario_name}' not found", err=True)
                click.echo(f"Available scenarios: {', '.join(scenario_library.list_scenarios())}")
                return

        # Apply CLI overrides
        if clients is not None:
            scenario.client_population.total_clients = clients

        if rounds is not None:
            scenario.total_rounds = rounds

        if malicious_fraction is not None:
            scenario.client_population.honest_fraction = 1.0 - malicious_fraction

        if aggregation_method is not None:
            scenario.environment_overrides["AGGREGATION_METHOD"] = aggregation_method

        if data_distribution is not None:
            scenario.data_distribution.distribution_type = data_distribution

        # Validate scenario
        warnings = scenario_library.validate_scenario(scenario)
        if warnings:
            click.echo("Warning: Scenario validation issues found:")
            for warning in warnings:
                click.echo(f"  - {warning}")
            if not click.confirm("Continue anyway?"):
                return

        # Display scenario summary
        click.echo(f"\n=== Running Simulation Scenario: {scenario.name} ===")
        click.echo(f"Description: {scenario.description}")
        click.echo(f"Total clients: {scenario.client_population.total_clients}")
        click.echo(f"Honest fraction: {scenario.client_population.honest_fraction:.2f}")
        click.echo(f"Total rounds: {scenario.total_rounds}")
        click.echo(f"Data distribution: {scenario.data_distribution.distribution_type.value}")
        click.echo(f"Aggregation method: {scenario.environment_overrides.get('AGGREGATION_METHOD', 'default')}")

        if scenario.attack_config.enabled:
            click.echo(f"Attacks enabled: {scenario.attack_config.attack_intensity} intensity")

        click.echo("")

        # Create test client and orchestrator
        test_client = TestClient(app)

        config = SimulationConfig(
            total_clients=scenario.client_population.total_clients,
            malicious_fraction=1.0 - scenario.client_population.honest_fraction,
            total_rounds=scenario.total_rounds,
            max_concurrent_clients=max_concurrent
        )

        orchestrator = SimulationOrchestrator(
            test_client=test_client,
            config=config,
            isolated_state=isolated
        )

        # Run simulation
        click.echo("Starting simulation...")
        start_time = click.get_current_context().meta.get('start_time', 0)

        with click.progressbar(length=scenario.total_rounds, label='Simulation progress') as bar:
            # This is a simplified progress bar - in reality we'd need to hook into the orchestrator
            # For now, run the simulation and update progress
            result = orchestrator.run_scenario(scenario)
            bar.update(result.completed_rounds)

        # Display results
        click.echo(f"\n=== Simulation Complete ===")
        click.echo(f"Scenario: {result.scenario_name}")
        click.echo(f"Success: {result.success}")
        click.echo(f"Completed rounds: {result.completed_rounds}/{result.total_rounds}")
        click.echo(f"Duration: {result.simulation_duration:.2f} seconds")

        if result.final_model_accuracy is not None:
            click.echo(f"Final accuracy: {result.final_model_accuracy:.3f}")

        if result.convergence_round is not None:
            click.echo(f"Converged at round: {result.convergence_round}")

        # Byzantine detection stats
        if result.byzantine_detection_stats:
            stats = result.byzantine_detection_stats
            click.echo(f"Outlier detection accuracy: {stats.get('outlier_detection_accuracy', 0):.3f}")
            click.echo(f"Malicious clients detected: {stats.get('malicious_clients_detected', 0)}")
            click.echo(f"Security events: {stats.get('total_security_events', 0)}")

        # Performance stats
        if result.performance_metrics:
            perf = result.performance_metrics
            click.echo(f"Average round duration: {perf.get('avg_round_duration', 0):.2f} seconds")
            click.echo(f"Throughput: {perf.get('throughput', 0):.1f} updates/sec")
            click.echo(f"Memory usage: {perf.get('memory_usage_mb', 0):.1f} MB")

        if not result.success:
            click.echo(f"Error: {result.error_message}", err=True)

        # Save results if output file specified
        if output:
            with open(output, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            click.echo(f"\nResults saved to {output}")

    except Exception as e:
        click.echo(f"Error running simulation: {e}", err=True)
        if ctx.obj.get('verbose'):
            import traceback
            traceback.print_exc()


@simulation.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed scenario information')
def list_scenarios(detailed):
    """List all available simulation scenarios."""
    scenario_library = get_scenario_library()
    scenarios = scenario_library.list_scenarios()

    if not scenarios:
        click.echo("No scenarios found.")
        return

    click.echo(f"Available simulation scenarios ({len(scenarios)}):")
    click.echo("")

    for scenario_name in sorted(scenarios):
        if detailed:
            try:
                scenario = scenario_library.load_scenario(scenario_name)
                click.echo(f"📋 {scenario_name}")
                click.echo(f"   {scenario.description}")
                click.echo(f"   Clients: {scenario.client_population.total_clients}, "
                          f"Rounds: {scenario.total_rounds}, "
                          f"Attacks: {'Yes' if scenario.attack_config.enabled else 'No'}")
                click.echo("")
            except Exception as e:
                click.echo(f"❌ {scenario_name} (failed to load: {e})")
        else:
            click.echo(f"  • {scenario_name}")


@simulation.command()
@click.argument('scenario_name')
def describe(scenario_name):
    """Show detailed information about a scenario."""
    try:
        scenario_library = get_scenario_library()
        scenario = scenario_library.load_scenario(scenario_name)

        click.echo(f"=== Scenario: {scenario.name} ===")
        click.echo(f"Description: {scenario.description}")
        click.echo("")

        click.echo("📊 Client Population:")
        click.echo(f"  Total clients: {scenario.client_population.total_clients}")
        click.echo(f"  Honest fraction: {scenario.client_population.honest_fraction:.2%}")
        click.echo(f"  Participation rate: {scenario.client_population.participation_rate:.2%}")
        click.echo(f"  Dropout probability: {scenario.client_population.dropout_probability:.2%}")

        if scenario.client_population.malicious_types:
            click.echo("  Malicious types:")
            for mtype, fraction in scenario.client_population.malicious_types.items():
                click.echo(f"    - {mtype}: {fraction:.2%}")

        click.echo("")

        click.echo("📈 Training Configuration:")
        click.echo(f"  Total rounds: {scenario.total_rounds}")
        click.echo(f"  Data distribution: {scenario.data_distribution.distribution_type.value}")
        click.echo(f"  Samples per client: {scenario.data_distribution.samples_per_client}")
        click.echo(f"  Heterogeneity alpha: {scenario.data_distribution.heterogeneity_alpha}")

        click.echo("")

        click.echo("⚡ Environment Settings:")
        for key, value in scenario.environment_overrides.items():
            click.echo(f"  {key}: {value}")

        click.echo("")

        if scenario.attack_config.enabled:
            click.echo("🚨 Attack Configuration:")
            click.echo(f"  Attack intensity: {scenario.attack_config.attack_intensity}")
            click.echo(f"  Coordination rate: {scenario.attack_config.coordination_rate:.2%}")
            click.echo(f"  Adaptive attacks: {scenario.attack_config.adaptive_attacks}")
        else:
            click.echo("✅ No attacks configured (honest scenario)")

        if scenario.expected_outcomes:
            click.echo("")
            click.echo("🎯 Expected Outcomes:")
            for metric, value in scenario.expected_outcomes.items():
                click.echo(f"  {metric}: {value}")

    except FileNotFoundError:
        click.echo(f"Error: Scenario '{scenario_name}' not found", err=True)
        click.echo(f"Available scenarios: {', '.join(scenario_library.list_scenarios())}")
    except Exception as e:
        click.echo(f"Error describing scenario: {e}", err=True)


@simulation.command()
@click.argument('name')
@click.option('--description', '-d', required=True, help='Scenario description')
@click.option('--clients', '-c', default=50, help='Number of clients')
@click.option('--rounds', '-r', default=100, help='Number of rounds')
@click.option('--malicious-fraction', '-m', default=0.2, help='Fraction of malicious clients')
@click.option('--distribution', default='non_iid',
              type=click.Choice(['iid', 'non_iid', 'pathological']),
              help='Data distribution type')
@click.option('--attacks/--no-attacks', default=True, help='Enable attacks')
@click.option('--save', '-s', is_flag=True, help='Save scenario to library')
def create(name, description, clients, rounds, malicious_fraction, distribution, attacks, save):
    """Create a custom simulation scenario."""
    try:
        scenario = create_custom_scenario(
            name=name,
            description=description,
            total_clients=clients,
            total_rounds=rounds,
            honest_fraction=1.0 - malicious_fraction,
            distribution_type=distribution,
            attacks_enabled=attacks
        )

        click.echo(f"Created custom scenario: {name}")
        click.echo(f"Description: {description}")
        click.echo(f"Clients: {clients} ({malicious_fraction:.1%} malicious)")
        click.echo(f"Rounds: {rounds}")
        click.echo(f"Distribution: {distribution}")
        click.echo(f"Attacks: {'Enabled' if attacks else 'Disabled'}")

        if save:
            scenario_library = get_scenario_library()
            scenario_library.save_scenario(scenario, overwrite=True)
            click.echo(f"✅ Scenario saved to library")
        else:
            click.echo("ℹ️  Use --save flag to add scenario to library")

    except Exception as e:
        click.echo(f"Error creating scenario: {e}", err=True)


@simulation.command()
@click.option('--clients', '-c', multiple=True, type=int,
              help='Test with different client counts (can specify multiple)')
@click.option('--aggregation-methods', '-a', multiple=True,
              type=click.Choice(['fedavg', 'trimmed_mean', 'median', 'krum', 'bulyan']),
              help='Test different aggregation methods')
@click.option('--output', '-o', help='Output file for benchmark results')
@click.option('--rounds', default=20, help='Rounds per benchmark (default: 20)')
def benchmark(clients, aggregation_methods, output, rounds):
    """Run performance benchmarks with different configurations."""
    if not clients:
        clients = [10, 25, 50, 100]

    if not aggregation_methods:
        aggregation_methods = ['fedavg', 'trimmed_mean', 'median']

    click.echo("🚀 Running simulation benchmarks...")
    click.echo(f"Client counts: {list(clients)}")
    click.echo(f"Aggregation methods: {list(aggregation_methods)}")
    click.echo(f"Rounds per test: {rounds}")
    click.echo("")

    results = []
    test_client = TestClient(app)

    total_tests = len(clients) * len(aggregation_methods)
    current_test = 0

    with click.progressbar(length=total_tests, label='Running benchmarks') as bar:
        for client_count in clients:
            for method in aggregation_methods:
                current_test += 1

                # Create benchmark scenario
                scenario = create_custom_scenario(
                    name=f"benchmark_{client_count}_{method}",
                    description=f"Benchmark with {client_count} clients using {method}",
                    total_clients=client_count,
                    total_rounds=rounds,
                    honest_fraction=1.0,  # All honest for pure performance test
                    distribution_type="iid",
                    attacks_enabled=False
                )

                scenario.environment_overrides["AGGREGATION_METHOD"] = method

                # Run benchmark
                orchestrator = SimulationOrchestrator(test_client, isolated_state=True)
                result = orchestrator.run_scenario(scenario)

                # Record results
                benchmark_result = {
                    "client_count": client_count,
                    "aggregation_method": method,
                    "rounds": rounds,
                    "duration": result.simulation_duration,
                    "avg_round_duration": result.performance_metrics.get("avg_round_duration", 0),
                    "throughput": result.performance_metrics.get("throughput", 0),
                    "memory_usage": result.performance_metrics.get("memory_usage_mb", 0),
                    "success": result.success
                }
                results.append(benchmark_result)

                bar.update(1)

    # Display results summary
    click.echo("\n📈 Benchmark Results:")
    click.echo("-" * 80)
    click.echo(f"{'Clients':<8} {'Method':<12} {'Duration':<10} {'Round Avg':<10} {'Throughput':<12} {'Memory':<10}")
    click.echo("-" * 80)

    for result in results:
        click.echo(f"{result['client_count']:<8} "
                  f"{result['aggregation_method']:<12} "
                  f"{result['duration']:<10.2f} "
                  f"{result['avg_round_duration']:<10.2f} "
                  f"{result['throughput']:<12.1f} "
                  f"{result['memory_usage']:<10.1f}")

    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"\n💾 Detailed results saved to {output}")


@simulation.command()
@click.argument('results_file', type=click.Path(exists=True))
@click.option('--format', default='summary',
              type=click.Choice(['summary', 'detailed', 'csv']),
              help='Output format')
def analyze(results_file, format):
    """Analyze simulation results from a JSON file."""
    try:
        with open(results_file, 'r') as f:
            data = json.load(f)

        if format == 'summary':
            click.echo(f"📊 Simulation Results Analysis")
            click.echo(f"Scenario: {data.get('scenario_name', 'Unknown')}")
            click.echo(f"Success: {data.get('success', False)}")
            click.echo(f"Completed rounds: {data.get('completed_rounds', 0)}")
            click.echo(f"Duration: {data.get('simulation_duration', 0):.2f} seconds")

            if data.get('final_model_accuracy'):
                click.echo(f"Final accuracy: {data['final_model_accuracy']:.3f}")

            byzantine_stats = data.get('byzantine_detection_stats', {})
            if byzantine_stats:
                click.echo(f"Outlier detection accuracy: {byzantine_stats.get('outlier_detection_accuracy', 0):.3f}")
                click.echo(f"Security events: {byzantine_stats.get('total_security_events', 0)}")

        elif format == 'detailed':
            click.echo(json.dumps(data, indent=2))

        elif format == 'csv':
            # Convert key metrics to CSV format
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers and data
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Scenario', data.get('scenario_name', '')])
            writer.writerow(['Success', data.get('success', False)])
            writer.writerow(['Completed Rounds', data.get('completed_rounds', 0)])
            writer.writerow(['Duration', data.get('simulation_duration', 0)])
            writer.writerow(['Final Accuracy', data.get('final_model_accuracy', '')])

            click.echo(output.getvalue())

    except Exception as e:
        click.echo(f"Error analyzing results: {e}", err=True)


if __name__ == '__main__':
    simulation()