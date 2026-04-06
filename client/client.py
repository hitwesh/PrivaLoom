import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import requests
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from model.load_model import model, tokenizer
from utils import _get_env_bool, _get_env_float, _get_env_int, setup_logger, log_info, log_error, load_text_file
from privacy_security.dp_engine import DPConfig, PrivacyAccountant, DPGradientClipper, DPNoiseGenerator
from privacy_security.privacy_tracker import get_privacy_tracker

# Initialize logger for client
logger = setup_logger("privaloom.client")

CHAT_URL = "http://127.0.0.1:8000/chat"
UPDATE_URL = "http://127.0.0.1:8000/send-update"
DATA_PATH = os.path.join(ROOT_DIR, "data.txt")

# Client identification for Phase 2
def get_or_create_client_id() -> str:
    """Get or create persistent client ID."""
    client_id_file = Path.home() / ".privaloom" / "client_id.txt"
    client_id_file.parent.mkdir(parents=True, exist_ok=True)

    if client_id_file.exists():
        client_id = client_id_file.read_text().strip()
        if client_id:  # Ensure it's not empty
            return client_id

    # Generate new client ID
    client_id = str(uuid.uuid4())
    client_id_file.write_text(client_id)
    log_info(logger, "Generated new client ID", client_id=client_id)
    return client_id

# Initialize client ID
CLIENT_ID = get_or_create_client_id()

# Differential Privacy configuration with formal guarantees
DP_ENABLED = _get_env_bool("DP_ENABLED", True)
DP_EPSILON = _get_env_float("DP_EPSILON", 1.0)  # Target privacy budget
DP_DELTA = _get_env_float("DP_DELTA", 1e-5)  # Failure probability
DP_MAX_GRAD_NORM = _get_env_float("DP_MAX_GRAD_NORM", 1.0)  # Clipping threshold
DP_NOISE_STDDEV = _get_env_float("DP_NOISE_STDDEV", 0.001)  # Legacy: direct noise (deprecated)
DP_GRADIENT_SLICE_SIZE = _get_env_int("DP_GRADIENT_SLICE_SIZE", 2)  # Configurable slicing
DP_MAX_PARAMS = _get_env_int("DP_MAX_PARAMS", 5)  # Max parameters to send

# Initialize DP components if enabled
dp_config: Optional[DPConfig] = None
privacy_accountant: Optional[PrivacyAccountant] = None
gradient_clipper: Optional[DPGradientClipper] = None
noise_generator: Optional[DPNoiseGenerator] = None

if DP_ENABLED:
    dp_config = DPConfig(
        epsilon=DP_EPSILON,
        delta=DP_DELTA,
        max_grad_norm=DP_MAX_GRAD_NORM,
        noise_mechanism="gaussian"
    )
    privacy_accountant = PrivacyAccountant(dp_config)
    gradient_clipper = DPGradientClipper(max_grad_norm=DP_MAX_GRAD_NORM)
    noise_generator = DPNoiseGenerator(noise_mechanism="gaussian", noise_multiplier=1.0)

    # Calibrate noise for target privacy
    # Assume single sample per update, so sample_rate = 1.0
    try:
        noise_generator.calibrate_noise(
            epsilon=DP_EPSILON,
            delta=DP_DELTA,
            sensitivity=DP_MAX_GRAD_NORM,
            num_steps=100,  # Expected number of updates
            sample_rate=1.0  # Single sample per update
        )
        log_info(logger, "DP components initialized",
                client_id=CLIENT_ID,
                epsilon=DP_EPSILON, delta=DP_DELTA,
                noise_multiplier=noise_generator.noise_multiplier)
    except ValueError as e:
        # Fallback to manual noise if calibration fails
        log_error(logger, "DP calibration failed, using manual noise", error=str(e))
        noise_generator.noise_multiplier = DP_NOISE_STDDEV / DP_MAX_GRAD_NORM


def load_dataset() -> list[str]:
    """Load dataset from file using enhanced utilities."""
    return load_text_file(DATA_PATH)


def aggregate_updates(updates: list[list[list[float]]]) -> list[list[float]]:
    if not updates:
        return []

    num_updates = len(updates)
    aggregated: list[list[float]] = []
    for i in range(len(updates[0])):
        slice_sum = [0.0] * len(updates[0][i])
        for update in updates:
            for j in range(len(update[i])):
                slice_sum[j] += update[i][j]
        slice_avg = [value / num_updates for value in slice_sum]
        aggregated.append(slice_avg)
    return aggregated


def train_and_get_update(text: str) -> Optional[list[list[float]]]:
    """
    Train on text and return gradient update with formal DP guarantees.

    Returns:
        Gradient update or None if privacy budget exhausted
    """
    # Check privacy budget before training
    if DP_ENABLED and privacy_accountant:
        if not privacy_accountant.can_proceed(epsilon_limit=DP_EPSILON):
            cumulative_eps, cumulative_delta = privacy_accountant.get_current_privacy()
            log_error(logger, "Privacy budget exhausted",
                     client_id=CLIENT_ID,
                     cumulative_epsilon=cumulative_eps,
                     cumulative_delta=cumulative_delta,
                     limit=DP_EPSILON)
            return None

    model.train()
    model.zero_grad()
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs, labels=inputs["input_ids"])
    loss = outputs.loss
    loss.backward()

    if DP_ENABLED and gradient_clipper and noise_generator:
        # Formal DP: Clip gradients
        params = list(model.parameters())
        total_norm = gradient_clipper.clip_gradients(params)

        # Add calibrated noise
        gradients_tensors = [p.grad for p in params if p.grad is not None]
        noise_generator.add_noise(gradients_tensors, sensitivity=DP_MAX_GRAD_NORM)

        # Record privacy loss
        if privacy_accountant:
            privacy_accountant.record_step(
                noise_multiplier=noise_generator.noise_multiplier,
                sample_rate=1.0  # Single sample
            )

            # Get current privacy and log
            cumulative_eps, cumulative_delta = privacy_accountant.get_current_privacy()
            log_info(logger, "Privacy spent after update",
                    client_id=CLIENT_ID,
                    cumulative_epsilon=cumulative_eps,
                    cumulative_delta=cumulative_delta,
                    gradient_norm=total_norm)

            # Also record in persistent tracker
            privacy_tracker = get_privacy_tracker()
            privacy_tracker.record_privacy_loss(
                epsilon=cumulative_eps - (privacy_accountant.steps - 1) * (cumulative_eps / privacy_accountant.steps) if privacy_accountant.steps > 1 else cumulative_eps,
                delta=DP_DELTA,
                round_num=privacy_accountant.steps
            )
    elif DP_ENABLED:
        # Legacy DP: Manual clipping and noise (deprecated)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=DP_MAX_GRAD_NORM)
        if DP_NOISE_STDDEV > 0:
            for param in model.parameters():
                if param.grad is not None:
                    param.grad.add_(torch.randn_like(param.grad) * DP_NOISE_STDDEV)

    # Extract gradients with configurable slicing
    gradients: list[list[float]] = []
    for param in model.parameters():
        if param.grad is not None:
            # Configurable slice size (default 2, can be 10, 50, 100, or full)
            slice_size = DP_GRADIENT_SLICE_SIZE if DP_GRADIENT_SLICE_SIZE > 0 else param.grad.numel()
            gradients.append(param.grad.view(-1)[:slice_size].tolist())

    # Return configurable number of parameters (default 5)
    max_params = DP_MAX_PARAMS if DP_MAX_PARAMS > 0 else len(gradients)
    return gradients[:max_params]


def train_on_dataset(fallback_text: str) -> Optional[list[list[float]]]:
    """Train on dataset with DP guarantees."""
    samples = load_dataset()
    if not samples:
        return train_and_get_update(fallback_text)

    updates = []
    for sample in samples:
        update = train_and_get_update(sample)
        if update is None:
            # Privacy budget exhausted
            log_error(logger, "Privacy budget exhausted during dataset training", client_id=CLIENT_ID)
            break
        updates.append(update)

    if not updates:
        return None

    return aggregate_updates(updates)


def send_update_to_server(update_weights: list[list[float]]) -> dict:
    """Send update to server with client ID."""
    update_payload = {
        "weights": update_weights,
        "client_id": CLIENT_ID,
        "timestamp": int(__import__("time").time())
    }

    try:
        response = requests.post(UPDATE_URL, json=update_payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        log_info(logger, "Update sent to server",
                client_id=CLIENT_ID,
                status=result.get("status"),
                server_response=result)

        return result

    except requests.RequestException as e:
        log_error(logger, "Failed to send update to server",
                 client_id=CLIENT_ID, error=str(e))
        return {"status": "error", "error": str(e)}


def main() -> None:
    dataset_trained = False

    # Log initial client information
    log_info(logger, "PrivaLoom client started",
             client_id=CLIENT_ID,
             dp_enabled=DP_ENABLED,
             epsilon_budget=DP_EPSILON if DP_ENABLED else None,
             delta=DP_DELTA if DP_ENABLED else None)

    # Log initial privacy budget
    if DP_ENABLED and privacy_accountant:
        log_info(logger, "Client initialized with formal DP",
                client_id=CLIENT_ID,
                epsilon_budget=DP_EPSILON,
                delta=DP_DELTA,
                max_grad_norm=DP_MAX_GRAD_NORM,
                slice_size=DP_GRADIENT_SLICE_SIZE,
                max_params=DP_MAX_PARAMS)

    while True:
        try:
            user_input = input("You: ")

            # Get chat response
            chat_response = requests.post(CHAT_URL, json={"prompt": user_input}, timeout=30)
            chat_result = chat_response.json()
            print("Bot:", chat_result.get("response", ""))

            # Handle training and updates
            if not dataset_trained:
                log_info(logger, "Training on local dataset", client_id=CLIENT_ID)
                update_weights = train_on_dataset(user_input)
                dataset_trained = True
            else:
                update_weights = train_and_get_update(user_input)

            if update_weights is None:
                log_error(logger, "Cannot send update - privacy budget exhausted or training failed",
                         client_id=CLIENT_ID)
                print("Privacy budget exhausted. No more updates will be sent.")
                continue

            # Send update with enhanced error handling
            server_response = send_update_to_server(update_weights)

            # Handle server response
            if server_response.get("status") == "rejected":
                reason = server_response.get("reason", "unknown")
                log_warning(logger, f"Update rejected by server: {reason}",
                           client_id=CLIENT_ID, reason=reason)
                print(f"Update rejected: {reason}")

                if reason == "low_reputation":
                    print(f"Client reputation too low: {server_response.get('reputation', 'unknown')}")
                elif reason == "validation_failed":
                    print("Update failed validation checks")

            elif server_response.get("status") == "accepted":
                reputation = server_response.get("client_reputation")
                if reputation is not None:
                    log_info(logger, "Update accepted",
                            client_id=CLIENT_ID, reputation=reputation)

            # Log current privacy status every 10 updates
            if DP_ENABLED and privacy_accountant and privacy_accountant.steps % 10 == 0:
                cumulative_eps, cumulative_delta = privacy_accountant.get_current_privacy()
                remaining = DP_EPSILON - cumulative_eps
                log_info(logger, "Privacy budget status",
                        client_id=CLIENT_ID,
                        cumulative_epsilon=cumulative_eps,
                        cumulative_delta=cumulative_delta,
                        remaining_epsilon=remaining,
                        updates_sent=privacy_accountant.steps)

        except KeyboardInterrupt:
            log_info(logger, "Client shutdown requested", client_id=CLIENT_ID)
            print("\nShutting down client...")
            break
        except Exception as e:
            log_error(logger, "Unexpected error in main loop",
                     client_id=CLIENT_ID, error=str(e))
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
