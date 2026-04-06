#!/usr/bin/env python3
"""
Quick test script to verify Phase 2 components work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from privacy_security import (
    AggregatorFactory, AggregationMethod, OutlierDetector,
    get_reputation_manager, get_security_monitor
)


def test_robust_aggregation():
    """Test robust aggregation algorithms."""
    print("Testing Robust Aggregation...")

    # Create test updates (3 honest + 1 malicious)
    honest_updates = [
        [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],  # Client 1
        [[1.1, 2.1], [3.1, 4.1], [5.1, 6.1]],  # Client 2
        [[0.9, 1.9], [2.9, 3.9], [4.9, 5.9]],  # Client 3
    ]

    malicious_update = [
        [[100.0, 200.0], [300.0, 400.0], [500.0, 600.0]]  # Malicious client
    ]

    all_updates = honest_updates + malicious_update

    # Test each aggregation method
    methods = [AggregationMethod.FEDAVG, AggregationMethod.TRIMMED_MEAN,
               AggregationMethod.MEDIAN, AggregationMethod.KRUM]

    for method in methods:
        try:
            aggregator = AggregatorFactory.create(method)
            result = aggregator.aggregate(all_updates)
            print(f"[PASS] {method.value}: {result[0][:2]}")  # First param, first 2 elements
        except Exception as e:
            print(f"[FAIL] {method.value}: {e}")


def test_outlier_detection():
    """Test outlier detection."""
    print("\nTesting Outlier Detection...")

    # Normal updates
    normal_updates = [
        [[0.1, 0.2], [0.3, 0.4]],
        [[0.15, 0.25], [0.35, 0.45]],
        [[0.05, 0.15], [0.25, 0.35]]
    ]

    # Add malicious update
    outlier_update = [[10.0, 20.0], [30.0, 40.0]]
    test_updates = normal_updates + [outlier_update]

    try:
        detector = OutlierDetector()
        result = detector.detect_outliers(test_updates)
        print(f"[PASS] Detected {result.get_outlier_count()} outliers")
        print(f"  Outlier indices: {result.get_outlier_indices()}")
        print(f"  Scores: {[f'{s:.3f}' for s in result.outlier_scores]}")
    except Exception as e:
        print(f"[FAIL] Outlier detection failed: {e}")


def test_reputation_system():
    """Test reputation management."""
    print("\nTesting Reputation System...")

    try:
        reputation_manager = get_reputation_manager()

        # Test new client
        client_id = "test_client_123"
        initial_rep = reputation_manager.get_reputation(client_id)
        print(f"[PASS] New client reputation: {initial_rep.score}")

        # Update reputation
        reputation_manager.update_reputation(client_id, 0.9, "test_update")
        updated_rep = reputation_manager.get_reputation(client_id)
        print(f"[PASS] Updated reputation: {updated_rep.score}")

        # Test acceptance
        should_accept = reputation_manager.should_accept_update(client_id)
        print(f"[PASS] Should accept update: {should_accept}")

    except Exception as e:
        print(f"[FAIL] Reputation system failed: {e}")


def test_security_monitoring():
    """Test security event monitoring."""
    print("\nTesting Security Monitoring...")

    try:
        security_monitor = get_security_monitor()

        # Create test event
        from privacy_security import create_malicious_update_event
        event = create_malicious_update_event("test_client", "test_reason")

        # Log event
        security_monitor.log_event(event)
        print("[PASS] Security event logged")

        # Get statistics
        stats = security_monitor.get_attack_statistics(hours=1)
        print(f"[PASS] Events in last hour: {stats['total_events']}")

    except Exception as e:
        print(f"[FAIL] Security monitoring failed: {e}")


if __name__ == "__main__":
    print("Phase 2 Component Test")
    print("=" * 50)

    test_robust_aggregation()
    test_outlier_detection()
    test_reputation_system()
    test_security_monitoring()

    print("\nTest completed!")