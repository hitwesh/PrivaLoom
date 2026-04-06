import threading
import time
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from model.load_model import generate_response, model
from utils import (
    setup_logger, log_info, log_error, log_warning,
    log_update_received, log_aggregation_start, log_aggregation_complete,
    config, get_round_tracker
)

# Import Phase 2 security components
from privacy_security import (
    AggregatorFactory, AggregationMethod, AggregationConfig,
    OutlierDetector, OutlierDetectionMethod,
    get_reputation_manager, calculate_quality_score,
    get_security_monitor, create_malicious_update_event, create_outlier_event,
    create_update_validator, ValidationError
)

app = FastAPI()

# Initialize logger for server
logger = setup_logger("privaloom.server")

# Thread-safe update buffer and configuration
global_updates: list[dict[str, any]] = []  # Now stores update dict with metadata
update_buffer_lock = threading.Lock()

# Configurable threshold (defaults to 20, backward compatible)
UPDATE_THRESHOLD = config.get_int("UPDATE_THRESHOLD", 20)

# Global round tracker for persistent state
round_tracker = get_round_tracker()

# Phase 2: Byzantine-robust aggregation configuration
AGGREGATION_METHOD = config.get_str("AGGREGATION_METHOD", "trimmed_mean")
BYZANTINE_TOLERANCE = config.get_float("BYZANTINE_TOLERANCE", 0.2)
OUTLIER_DETECTION_ENABLED = config.get_bool("OUTLIER_DETECTION_ENABLED", True)
REPUTATION_ENABLED = config.get_bool("REPUTATION_ENABLED", True)
VALIDATION_ENABLED = config.get_bool("VALIDATION_ENABLED", True)

# Simulation mode configuration
SIMULATION_MODE = config.get_bool("SIMULATION_MODE", False)
SIMULATION_LOGGING_VERBOSE = config.get_bool("SIMULATION_LOGGING_VERBOSE", False)

# Initialize security components
try:
    aggregation_config = AggregationConfig(
        method=AggregationMethod(AGGREGATION_METHOD),
        byzantine_tolerance=BYZANTINE_TOLERANCE,
        min_updates_required=max(3, int(UPDATE_THRESHOLD * 0.1))
    )
    aggregator_factory = AggregatorFactory()

    outlier_detector = OutlierDetector() if OUTLIER_DETECTION_ENABLED else None
    reputation_manager = get_reputation_manager() if REPUTATION_ENABLED else None
    security_monitor = get_security_monitor()
    update_validator = create_update_validator(
        enable_all_features=VALIDATION_ENABLED
    ) if VALIDATION_ENABLED else None

    log_info(logger, "Phase 2 security components initialized", extra={
        "aggregation_method": AGGREGATION_METHOD,
        "byzantine_tolerance": BYZANTINE_TOLERANCE,
        "outlier_detection": OUTLIER_DETECTION_ENABLED,
        "reputation_enabled": REPUTATION_ENABLED,
        "validation_enabled": VALIDATION_ENABLED
    })

    # Enhanced logging for simulation mode
    if SIMULATION_MODE:
        log_info(logger, "Simulation mode active", extra={
            "simulation_mode": True,
            "verbose_logging": SIMULATION_LOGGING_VERBOSE,
            "aggregation_method": AGGREGATION_METHOD,
            "byzantine_tolerance": BYZANTINE_TOLERANCE,
            "update_threshold": UPDATE_THRESHOLD
        })

except Exception as e:
    log_error(logger, f"Failed to initialize security components: {e}")
    # Fallback to Phase 1 behavior
    aggregator_factory = None
    outlier_detector = None
    reputation_manager = None
    security_monitor = None
    update_validator = None

class ChatRequest(BaseModel):
    prompt: str


class UpdateRequest(BaseModel):
    weights: list[list[float]]
    client_id: str  # NEW: Required client identification
    timestamp: Optional[int] = None  # For replay protection (future)

@app.get("/")
def home() -> dict[str, str]:
    return {"message": "PrivaLoom Server with Byzantine Robust Aggregation"}


@app.get("/status")
def get_status() -> dict:
    """Get current aggregation status and statistics."""
    with update_buffer_lock:
        current_buffer_size = len(global_updates)

    stats = round_tracker.get_stats()

    # Add security statistics if available
    security_stats = {}
    if reputation_manager:
        security_stats["reputation"] = reputation_manager.get_system_statistics()
    if security_monitor:
        security_stats["security_events"] = security_monitor.get_attack_statistics(hours=24)
    if update_validator:
        security_stats["validation"] = update_validator.get_validation_statistics()

    return {
        "server_status": "running",
        "current_buffer_size": current_buffer_size,
        "threshold": UPDATE_THRESHOLD,
        "updates_until_aggregation": max(0, UPDATE_THRESHOLD - current_buffer_size),
        "aggregation_stats": stats,
        "security_config": {
            "aggregation_method": AGGREGATION_METHOD,
            "byzantine_tolerance": BYZANTINE_TOLERANCE,
            "outlier_detection": OUTLIER_DETECTION_ENABLED,
            "reputation_enabled": REPUTATION_ENABLED
        },
        "security_stats": security_stats
    }


@app.get("/simulation/metrics")
def get_simulation_metrics() -> dict[str, any]:
    """Get real-time simulation metrics for monitoring."""
    from fastapi import HTTPException

    if not SIMULATION_MODE:
        raise HTTPException(status_code=404, detail="Simulation mode not active")

    # Get client count from reputation manager
    active_clients = 0
    if reputation_manager:
        try:
            active_clients = len(reputation_manager.get_all_client_ids())
        except AttributeError:
            # Fallback if method doesn't exist
            active_clients = 0

    # Get recent security events
    recent_security_events = 0
    if security_monitor:
        recent_events = security_monitor.get_recent_events(hours=1)
        recent_security_events = len(recent_events)

    # Get current round information
    current_round = round_tracker.get_current_round()

    # Get aggregation stats if available
    aggregation_stats = {}
    if hasattr(aggregator_factory, 'get_aggregation_stats'):
        try:
            aggregation_stats = aggregator_factory.get_aggregation_stats()
        except:
            pass

    return {
        "simulation_active": True,
        "active_clients": active_clients,
        "recent_security_events": recent_security_events,
        "current_round": current_round,
        "aggregation_method": AGGREGATION_METHOD,
        "byzantine_tolerance": BYZANTINE_TOLERANCE,
        "buffer_size": len(global_updates),
        "update_threshold": UPDATE_THRESHOLD,
        "aggregation_stats": aggregation_stats,
        "timestamp": time.time()
    }

@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    user_input = request.prompt
    response = generate_response(user_input)
    return {"input": user_input, "response": response}


@app.post("/send-update")
def receive_update(update: UpdateRequest) -> dict[str, str]:
    """Enhanced update endpoint with Byzantine-robust aggregation and security."""
    client_id = update.client_id

    try:
        # Step 1: Input validation and sanitization
        if update_validator:
            validation_result = update_validator.validate_update(update.dict(), client_id)

            if not validation_result.is_valid:
                log_warning(logger, f"Update validation failed for client {client_id}",
                          extra={"errors": validation_result.errors[:3]})  # First 3 errors
                return {
                    "status": "rejected",
                    "reason": "validation_failed",
                    "details": validation_result.errors[:3]
                }

            # Use sanitized update
            sanitized_weights = validation_result.sanitized_update
        else:
            sanitized_weights = update.weights

        # Step 2: Reputation check
        if reputation_manager and not reputation_manager.should_accept_update(client_id):
            reputation = reputation_manager.get_reputation(client_id)
            log_warning(logger, f"Update rejected due to low reputation",
                      extra={"client_id": client_id, "reputation": reputation.score})
            return {
                "status": "rejected",
                "reason": "low_reputation",
                "reputation": reputation.score
            }

        # Step 3: Thread-safe buffer management (FIX: don't hold lock during heavy computation)
        should_aggregate = False
        updates_to_aggregate = []

        with update_buffer_lock:
            global_updates.append({
                "weights": sanitized_weights,
                "client_id": client_id,
                "timestamp": update.timestamp or int(time.time()),
                "validation_confidence": getattr(validation_result, 'confidence', 1.0) if update_validator else 1.0
            })
            current_count = len(global_updates)

            log_update_received(logger, current_count, threshold=UPDATE_THRESHOLD,
                              extra={"client_id": client_id})

            # Check if we should trigger aggregation
            if current_count >= UPDATE_THRESHOLD:
                # Copy buffer and clear immediately (don't hold lock during aggregation)
                updates_to_aggregate = global_updates[:]
                global_updates.clear()
                should_aggregate = True

        # Step 4: Heavy computation OUTSIDE the lock
        if should_aggregate:
            try:
                # Get current round number before starting aggregation
                round_num = round_tracker.start_new_round()
                log_aggregation_start(logger, round_num, len(updates_to_aggregate))

                start_time = time.time()

                # Perform robust aggregation
                aggregated_update = perform_robust_aggregation(updates_to_aggregate)

                # Apply to model
                apply_robust_updates(aggregated_update)

                # Update client reputations based on participation
                if reputation_manager:
                    update_client_reputations(updates_to_aggregate, aggregated_update)

                # Calculate duration and complete round
                duration_ms = (time.time() - start_time) * 1000
                round_tracker.complete_round(len(updates_to_aggregate), duration_ms)

                log_aggregation_complete(logger, round_num, duration_ms,
                                       updates_processed=len(updates_to_aggregate),
                                       extra={"aggregation_method": AGGREGATION_METHOD})

            except Exception as e:
                log_error(logger, f"Robust aggregation failed for round {round_num}",
                        extra={"error": str(e), "updates_count": len(updates_to_aggregate)})
                # Don't re-add to buffer on aggregation failure
                raise

        return {
            "status": "accepted",
            "buffer_count": current_count if not should_aggregate else 0,
            "client_reputation": reputation_manager.get_reputation(client_id).score if reputation_manager else None
        }

    except Exception as e:
        log_error(logger, f"Error processing update from client {client_id}",
                extra={"error": str(e)})
        return {"status": "error", "reason": str(e)}


def perform_robust_aggregation(updates_to_aggregate: list[dict]) -> list[list[float]]:
    """Perform Byzantine-robust aggregation with outlier detection and security monitoring."""

    # Extract weights and metadata
    update_weights = [update_data["weights"] for update_data in updates_to_aggregate]
    client_ids = [update_data["client_id"] for update_data in updates_to_aggregate]

    # Step 1: Outlier detection
    outlier_indices = set()
    if outlier_detector and OUTLIER_DETECTION_ENABLED:
        try:
            detection_result = outlier_detector.detect_outliers(update_weights)
            outlier_indices = set(detection_result.get_outlier_indices())

            # Log security events for detected outliers
            if security_monitor:
                for outlier_idx in outlier_indices:
                    client_id = client_ids[outlier_idx]
                    event = create_outlier_event(
                        client_id=client_id,
                        detection_method=str(outlier_detector.config.method.value),
                        confidence=detection_result.outlier_scores[outlier_idx],
                        details={
                            "outlier_score": detection_result.outlier_scores[outlier_idx],
                            "detection_metadata": detection_result.detection_metadata
                        }
                    )
                    security_monitor.log_event(event)

            log_info(logger, "Outlier detection completed", extra={
                "total_updates": len(update_weights),
                "outliers_detected": len(outlier_indices),
                "outlier_clients": [client_ids[i] for i in outlier_indices]
            })

        except Exception as e:
            log_error(logger, f"Outlier detection failed: {e}")

    # Step 2: Filter out outliers
    if outlier_indices:
        filtered_updates = []
        filtered_client_ids = []

        for i, (weights, client_id) in enumerate(zip(update_weights, client_ids)):
            if i not in outlier_indices:
                filtered_updates.append(weights)
                filtered_client_ids.append(client_id)

        update_weights = filtered_updates
        client_ids = filtered_client_ids

        log_info(logger, f"Filtered out {len(outlier_indices)} outlier updates",
                extra={"remaining_updates": len(update_weights)})

    # Step 3: Get reputation weights for aggregation
    reputation_weights = None
    if reputation_manager and REPUTATION_ENABLED:
        try:
            reputation_weights = [reputation_manager.get_update_weight(client_id)
                                for client_id in client_ids]

            # Filter out zero-weight clients
            non_zero_indices = [i for i, weight in enumerate(reputation_weights) if weight > 0]
            if len(non_zero_indices) < len(reputation_weights):
                update_weights = [update_weights[i] for i in non_zero_indices]
                reputation_weights = [reputation_weights[i] for i in non_zero_indices]
                client_ids = [client_ids[i] for i in non_zero_indices]

                log_info(logger, f"Filtered out {len(reputation_weights) - len(non_zero_indices)} zero-reputation updates")

        except Exception as e:
            log_error(logger, f"Reputation weighting failed: {e}")
            reputation_weights = None

    # Step 4: Robust aggregation
    if not update_weights:
        raise ValueError("No valid updates remaining after filtering")

    try:
        aggregator = aggregator_factory.create(AggregationMethod(AGGREGATION_METHOD), aggregation_config)
        aggregated_update = aggregator.aggregate(update_weights, reputation_weights)

        log_info(logger, "Robust aggregation completed", extra={
            "method": AGGREGATION_METHOD,
            "input_updates": len(update_weights),
            "used_reputation_weights": reputation_weights is not None
        })

        return aggregated_update

    except Exception as e:
        log_error(logger, f"Robust aggregation failed: {e}")
        # Fallback to simple averaging
        log_warning(logger, "Falling back to simple averaging")
        return simple_average_aggregation(update_weights)


def simple_average_aggregation(updates: list[list[list[float]]]) -> list[list[float]]:
    """Fallback simple averaging aggregation."""
    if not updates:
        raise ValueError("No updates to aggregate")

    num_updates = len(updates)
    aggregated = []

    for i in range(len(updates[0])):
        slice_sum = [0.0] * len(updates[0][i])
        for update in updates:
            for j in range(len(update[i])):
                slice_sum[j] += update[i][j]
        slice_avg = [value / num_updates for value in slice_sum]
        aggregated.append(slice_avg)

    return aggregated


def update_client_reputations(updates_to_aggregate: list[dict], aggregated_update: list[list[float]]) -> None:
    """Update client reputations based on update quality."""
    if not reputation_manager:
        return

    try:
        for update_data in updates_to_aggregate:
            client_id = update_data["client_id"]
            client_update = update_data["weights"]

            # Calculate quality score based on similarity to aggregated result
            quality_score = calculate_quality_score(client_update, aggregated_update)

            # Update reputation
            reputation_manager.update_reputation(
                client_id=client_id,
                quality_score=quality_score,
                reason="aggregation_participation"
            )

        log_info(logger, "Client reputations updated", extra={
            "clients_updated": len(updates_to_aggregate)
        })

    except Exception as e:
        log_error(logger, f"Failed to update client reputations: {e}")


def apply_robust_updates(aggregated_update: list[list[float]]) -> None:
    """Apply robustly aggregated updates to model."""
    log_info(logger, "Applying robust aggregated updates to last layers")

    try:
        with torch.no_grad():
            params = list(model.parameters())
            num_layers_to_update = 5
            last_layers = params[-num_layers_to_update:]

            for index, param in enumerate(last_layers):
                if index < len(aggregated_update):
                    update_tensor = torch.tensor(aggregated_update[index])
                    flat_param = param.view(-1)
                    flat_param[: len(update_tensor)] += update_tensor

        log_info(logger, "Robust updates applied successfully", extra={
            "layers_updated": num_layers_to_update,
            "aggregation_method": AGGREGATION_METHOD
        })

    except Exception as e:
        log_error(logger, f"Failed to apply robust updates: {e}")
        raise


# Legacy function for backward compatibility
def apply_updates(updates: list[list[list[float]]]) -> None:
    """Legacy update application (kept for backward compatibility)."""
    aggregated = simple_average_aggregation(updates)
    apply_robust_updates(aggregated)
