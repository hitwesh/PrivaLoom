import threading
import time
import secrets
import json
from datetime import datetime
from pathlib import Path
import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional

from model.load_model import generate_response, model
from utils import (
    setup_logger, log_info, log_error, log_warning,
    log_update_received, log_aggregation_start, log_aggregation_complete,
    config, reset_round_tracker
)

# Import Phase 2 security components
from privacy_security import (
    AggregatorFactory, AggregationMethod, AggregationConfig,
    OutlierDetector, OutlierDetectionMethod,
    reset_reputation_manager, calculate_quality_score, ClientReputation,
    reset_security_monitor, create_malicious_update_event, create_outlier_event,
    create_update_validator, ValidationError, reset_privacy_tracker
)
from server.auth_db import (
    ROLE_ADMIN,
    ROLE_USER,
    authenticate_user,
    create_session,
    create_user,
    delete_user,
    get_session_context,
    get_user_by_id,
    get_user_by_username,
    get_user_count,
    init_auth_db,
    list_users,
    revoke_session,
)

app = FastAPI()

frontend_origins = [
    origin.strip()
    for origin in config.get_str(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger for server
logger = setup_logger("privaloom.server")

# Thread-safe update buffer and configuration
global_updates: list[dict[str, Any]] = []  # Now stores update dict with metadata
update_buffer_lock = threading.Lock()

# Configurable threshold (defaults to 20, backward compatible)
UPDATE_THRESHOLD = config.get_int("UPDATE_THRESHOLD", 20)

# Persistent state file configuration
AGGREGATION_STATE_PATH = config.get_str("AGGREGATION_STATE_PATH", "data/aggregation_state.json")
PRIVACY_STATE_PATH = config.get_str("PRIVACY_STATE_PATH", "data/privacy_state.json")
REPUTATION_STATE_PATH = config.get_str("REPUTATION_STATE_PATH", "data/reputation_state.json")
SECURITY_EVENTS_PATH = config.get_str("SECURITY_EVENTS_PATH", "data/security_events.jsonl")
MODEL_PERSIST_ENABLED = config.get_bool("MODEL_PERSIST_ENABLED", True)
MODEL_STATE_PATH = config.get_str("MODEL_STATE_PATH", "data/model_state.pt")

# Phase 2: Byzantine-robust aggregation configuration
AGGREGATION_METHOD = config.get_str("AGGREGATION_METHOD", "trimmed_mean")
BYZANTINE_TOLERANCE = config.get_float("BYZANTINE_TOLERANCE", 0.2)
OUTLIER_DETECTION_ENABLED = config.get_bool("OUTLIER_DETECTION_ENABLED", True)
REPUTATION_ENABLED = config.get_bool("REPUTATION_ENABLED", True)
VALIDATION_ENABLED = config.get_bool("VALIDATION_ENABLED", True)

# Simulation mode configuration
SIMULATION_MODE = config.get_bool("SIMULATION_MODE", False)
SIMULATION_LOGGING_VERBOSE = config.get_bool("SIMULATION_LOGGING_VERBOSE", False)

# Authentication / RBAC configuration
AUTH_ENABLED = config.get_bool("AUTH_ENABLED", True)
AUTH_DB_PATH = config.get_str("AUTH_DB_PATH", "data/auth.db")
AUTH_BOOTSTRAP_ADMIN = config.get_str("AUTH_BOOTSTRAP_ADMIN", "admin")
AUTH_BOOTSTRAP_PASSWORD = config.get_str("AUTH_BOOTSTRAP_PASSWORD", "admin123")
AUTH_SEED_FILE = config.get_str("AUTH_SEED_FILE", "")

# Global persistent trackers
round_tracker = reset_round_tracker(AGGREGATION_STATE_PATH)
privacy_tracker = reset_privacy_tracker(PRIVACY_STATE_PATH)

try:
    init_auth_db(
        AUTH_DB_PATH,
        bootstrap_admin_username=AUTH_BOOTSTRAP_ADMIN,
        bootstrap_admin_password=AUTH_BOOTSTRAP_PASSWORD,
    )
except Exception as e:
    log_error(logger, f"Failed to initialize auth database: {e}")

# Initialize security components
try:
    aggregation_config = AggregationConfig(
        method=AggregationMethod(AGGREGATION_METHOD),
        byzantine_tolerance=BYZANTINE_TOLERANCE,
        min_updates_required=max(3, int(UPDATE_THRESHOLD * 0.1))
    )
    aggregator_factory = AggregatorFactory()

    outlier_detector = OutlierDetector() if OUTLIER_DETECTION_ENABLED else None
    reputation_manager = reset_reputation_manager(REPUTATION_STATE_PATH) if REPUTATION_ENABLED else None
    security_monitor = reset_security_monitor(log_file_path=SECURITY_EVENTS_PATH)
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


class AdminUserRequest(BaseModel):
    client_id: str


class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthUserRequest(BaseModel):
    username: str
    password: Optional[str] = None
    role: str = ROLE_USER


SIMULATION_CLIENT_PREFIXES = (
    "honest_",
    "gradient_scaling_",
    "sign_flipping_",
    "gradient_noise_",
    "free_rider_",
    "dropout_prone_",
    "coordinated_malicious_",
)


def _is_simulation_client_id(client_id: str) -> bool:
    return any(client_id.startswith(prefix) for prefix in SIMULATION_CLIENT_PREFIXES)


def _register_reputation_client(client_id: str) -> tuple[str, Optional[dict[str, Any]]]:
    """Create a reputation client if it does not already exist."""
    if not reputation_manager:
        return "reputation_disabled", None

    normalized = client_id.strip()
    if not normalized:
        raise ValueError("client_id cannot be empty")

    state = getattr(reputation_manager, "_state", None)
    lock = getattr(reputation_manager, "_lock", None)
    if state is None or not hasattr(state, "clients"):
        return "unavailable", None

    def _create_or_get() -> tuple[bool, dict[str, Any]]:
        tracked_clients = state.clients
        reputation = tracked_clients.get(normalized)
        created = False

        if reputation is None:
            now = datetime.now().isoformat()
            reputation = ClientReputation(
                client_id=normalized,
                score=float(getattr(reputation_manager, "initial_reputation", 0.8)),
                total_updates=0,
                last_update_time=now,
                created_time=now,
                score_history=[],
            )
            tracked_clients[normalized] = reputation
            created = True

        if hasattr(reputation_manager, "_save_state"):
            reputation_manager._save_state()

        return created, {
            "client_id": normalized,
            "current_score": float(getattr(reputation, "score", 0.0)),
            "total_updates": int(getattr(reputation, "total_updates", 0)),
            "last_update": getattr(reputation, "last_update_time", None),
            "created_time": getattr(reputation, "created_time", None),
            "is_simulated": _is_simulation_client_id(normalized),
        }

    if lock:
        with lock:
            created, payload = _create_or_get()
    else:
        created, payload = _create_or_get()

    return ("created" if created else "exists"), payload


def _remove_reputation_client(client_id: str) -> bool:
    """Remove client from reputation state."""
    if not reputation_manager:
        return False

    normalized = client_id.strip()
    if not normalized:
        return False

    state = getattr(reputation_manager, "_state", None)
    lock = getattr(reputation_manager, "_lock", None)
    if state is None or not hasattr(state, "clients"):
        return False

    def _remove() -> bool:
        tracked_clients = state.clients
        if normalized not in tracked_clients:
            return False

        del tracked_clients[normalized]
        if hasattr(reputation_manager, "_save_state"):
            reputation_manager._save_state()
        return True

    if lock:
        with lock:
            return _remove()

    return _remove()


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2:
        return None

    if parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    return token or None


def _require_auth(authorization: Optional[str]) -> dict[str, Any]:
    if not AUTH_ENABLED:
        return {
            "token": "auth-disabled",
            "session_user_id": 0,
            "session_username": "auth-disabled",
            "session_role": ROLE_ADMIN,
            "effective_user_id": 0,
            "effective_username": "auth-disabled",
            "effective_role": ROLE_ADMIN,
            "is_simulating": False,
            "expires_at": "",
            "created_at": "",
        }

    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    context = get_session_context(token)
    if not context:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return context


def _require_admin(
    authorization: Optional[str],
    *,
    allow_simulated_admin: bool = False,
) -> dict[str, Any]:
    context = _require_auth(authorization)
    if context.get("session_role") != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    if context.get("is_simulating") and not allow_simulated_admin:
        raise HTTPException(status_code=403, detail="Stop simulation to access admin controls")

    return context


def _serialize_auth_context(context: dict[str, Any], token: str) -> dict[str, Any]:
    return {
        "token": token,
        "user": {
            "id": context["effective_user_id"],
            "username": context["effective_username"],
            "role": context["effective_role"],
            "is_simulating": bool(context.get("is_simulating", False)),
            "actor_role": context.get("session_role"),
            "actor_username": context.get("session_username"),
            "expires_at": context.get("expires_at"),
        },
    }


def _create_temp_password() -> str:
    return f"Tmp-{secrets.token_urlsafe(9)}"


def _load_model_state_if_available() -> None:
    """Restore previously aggregated model state, if configured and present."""
    if not MODEL_PERSIST_ENABLED:
        return

    state_path = Path(MODEL_STATE_PATH)
    if not state_path.is_file():
        return

    try:
        state_dict = torch.load(state_path, map_location="cpu")
        model.load_state_dict(state_dict)
        log_info(logger, "Loaded persisted model state", extra={"path": str(state_path)})
    except Exception as e:
        log_warning(logger, f"Failed to load persisted model state: {e}")


def _save_model_state(round_num: int) -> None:
    """Persist current model weights so subsequent runs and teammates can reuse training progress."""
    if not MODEL_PERSIST_ENABLED:
        return

    state_path = Path(MODEL_STATE_PATH)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = Path(f"{state_path}.tmp")
        torch.save(model.state_dict(), temp_path)
        temp_path.replace(state_path)
        log_info(
            logger,
            "Persisted model state",
            extra={"path": str(state_path), "round": round_num},
        )
    except Exception as e:
        log_error(logger, f"Failed to persist model state: {e}")


def _seed_users_from_file() -> None:
    """Optionally create users from a JSON seed file for teammate onboarding."""
    if not AUTH_ENABLED:
        return
    if not AUTH_SEED_FILE:
        return

    seed_path = Path(AUTH_SEED_FILE)
    if not seed_path.is_file():
        log_warning(logger, f"Auth seed file not found: {seed_path}")
        return

    try:
        with seed_path.open("r", encoding="utf-8") as handle:
            seed_entries = json.load(handle)
    except Exception as e:
        log_error(logger, f"Failed to read auth seed file: {e}")
        return

    if not isinstance(seed_entries, list):
        log_warning(logger, "Auth seed file must contain a list of users")
        return

    created_count = 0
    skipped_count = 0
    invalid_count = 0

    for entry in seed_entries:
        if not isinstance(entry, dict):
            invalid_count += 1
            continue

        username = str(entry.get("username", "")).strip()
        password = str(entry.get("password", ""))
        role = str(entry.get("role", ROLE_USER)).strip().lower()

        if not username or not password or role not in {ROLE_ADMIN, ROLE_USER}:
            invalid_count += 1
            continue

        if get_user_by_username(username):
            skipped_count += 1
            continue

        try:
            create_user(username, password, role)
            created_count += 1
        except Exception:
            invalid_count += 1

    log_info(
        logger,
        "Processed auth user seed file",
        extra={
            "path": str(seed_path),
            "created": created_count,
            "skipped": skipped_count,
            "invalid": invalid_count,
        },
    )


_load_model_state_if_available()
_seed_users_from_file()


def _get_reputation_clients(limit: int = 50) -> list[dict[str, Any]]:
    """Get sorted client reputation stats for dashboards."""
    if not reputation_manager:
        return []

    try:
        clients = []
        state = getattr(reputation_manager, "_state", None)
        tracked_clients = getattr(state, "clients", {}) if state else {}

        for client_id, reputation in tracked_clients.items():
            score = float(getattr(reputation, "score", 0.0))
            total_updates = int(getattr(reputation, "total_updates", 0))
            threshold = getattr(reputation_manager, "min_reputation_threshold", 0.3)

            clients.append(
                {
                    "client_id": client_id,
                    "current_score": score,
                    "total_updates": total_updates,
                    "last_update": getattr(reputation, "last_update_time", None),
                    "created_time": getattr(reputation, "created_time", None),
                    "is_simulated": _is_simulation_client_id(client_id),
                    "is_accepted": score >= threshold,
                    "aggregation_weight": score if score >= threshold else 0.0,
                }
            )

        clients.sort(key=lambda client: client.get("total_updates", 0), reverse=True)
        return clients[:limit]
    except Exception as e:
        log_error(logger, f"Failed to read reputation client stats: {e}")
        return []


def _get_recent_security_events(hours: int = 24, limit: int = 50) -> list[dict[str, Any]]:
    """Get recent security events for dashboard display."""
    if not security_monitor:
        return []

    try:
        events = security_monitor.get_recent_events(hours=hours)
        return [event.to_dict() for event in events[:limit]]
    except Exception as e:
        log_error(logger, f"Failed to read recent security events: {e}")
        return []


def _get_simulation_scenario_names() -> list[str]:
    """Get available simulation scenarios from scenario library."""
    try:
        from simulation.scenarios import get_scenario_library

        return sorted(get_scenario_library().list_scenarios())
    except Exception as e:
        log_warning(logger, f"Failed to list simulation scenarios: {e}")
        return []


def _get_simulation_metrics_payload() -> Optional[dict[str, Any]]:
    """Return simulation metrics payload or None when unavailable."""
    if not SIMULATION_MODE:
        return None

    # Get client count from reputation manager
    active_clients = 0
    if reputation_manager:
        try:
            active_clients = len(reputation_manager.get_all_client_ids())
        except AttributeError:
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
    if hasattr(aggregator_factory, "get_aggregation_stats"):
        try:
            aggregation_stats = aggregator_factory.get_aggregation_stats()
        except Exception:
            aggregation_stats = {}

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
        "timestamp": time.time(),
    }

@app.get("/")
def home() -> dict[str, str]:
    return {"message": "PrivaLoom Server with Byzantine Robust Aggregation"}


@app.post("/auth/register")
def auth_register(
    request: AuthRegisterRequest,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Create a new authenticated user account."""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication is disabled")

    requested_role = (request.role or ROLE_USER).strip().lower()
    if requested_role not in {ROLE_USER, ROLE_ADMIN}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_count = get_user_count()
    if requested_role == ROLE_ADMIN and user_count > 0:
        _require_admin(authorization)

    if user_count == 0 and request.role is None:
        requested_role = ROLE_ADMIN

    try:
        user = create_user(request.username, request.password, requested_role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "status": "created",
        "user": user,
    }


@app.post("/auth/login")
def auth_login(request: AuthLoginRequest) -> dict[str, Any]:
    """Authenticate username/password and issue a session token."""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Authentication is disabled")

    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_session(user["id"])
    context = get_session_context(token)
    if not context:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return _serialize_auth_context(context, token)


@app.post("/auth/logout")
def auth_logout(authorization: Optional[str] = Header(default=None)) -> dict[str, str]:
    """Revoke current session token."""
    context = _require_auth(authorization)
    revoke_session(context["token"])
    return {"status": "logged_out"}


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Return current authenticated user context."""
    context = _require_auth(authorization)
    return _serialize_auth_context(context, context["token"])


@app.get("/auth/users")
def auth_list_users(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Admin-only user account listing."""
    _require_admin(authorization)
    users = list_users()
    return {
        "count": len(users),
        "users": users,
    }


@app.post("/auth/users")
def auth_create_user(
    request: AuthUserRequest,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Admin-only account creation."""
    _require_admin(authorization)

    role = request.role.strip().lower()
    if role not in {ROLE_ADMIN, ROLE_USER}:
        raise HTTPException(status_code=400, detail="Invalid role")

    generated_password = None
    password = request.password
    if not password:
        generated_password = _create_temp_password()
        password = generated_password

    try:
        user = create_user(request.username, password, role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    response: dict[str, Any] = {
        "status": "created",
        "user": user,
    }
    if generated_password:
        response["temporary_password"] = generated_password
    return response


@app.delete("/auth/users/{user_id}")
def auth_delete_user(
    user_id: int,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Admin-only account deletion."""
    context = _require_admin(authorization)

    if context["session_user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete currently authenticated admin")

    user = get_user_by_id(user_id)
    if not user:
        return {"status": "not_found", "user_id": user_id}

    removed = delete_user(user_id)
    if user.get("username"):
        _remove_reputation_client(user["username"])

    return {
        "status": "removed" if removed else "not_found",
        "user_id": user_id,
    }


@app.post("/auth/simulate/user/{user_id}")
def auth_simulate_user(
    user_id: int,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Admin-only impersonation: issue a token acting as selected user."""
    context = _require_admin(authorization)

    target_user = get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if target_user.get("role") != ROLE_USER:
        raise HTTPException(status_code=400, detail="Only user accounts can be simulated")

    if target_user.get("id") == context.get("session_user_id"):
        raise HTTPException(status_code=400, detail="Cannot simulate the current admin account")

    simulated_token = create_session(
        context["session_user_id"],
        acting_as_user_id=user_id,
    )
    simulated_context = get_session_context(simulated_token)
    if not simulated_context:
        raise HTTPException(status_code=500, detail="Failed to create simulation session")

    return _serialize_auth_context(simulated_context, simulated_token)


@app.post("/auth/simulate/stop")
def auth_stop_simulation(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Stop impersonation and return a token for the admin identity."""
    context = _require_admin(authorization, allow_simulated_admin=True)
    if not context.get("is_simulating"):
        raise HTTPException(status_code=400, detail="No active simulation session")

    restore_token = create_session(context["session_user_id"])
    restored_context = get_session_context(restore_token)
    revoke_session(context["token"])

    if not restored_context:
        raise HTTPException(status_code=500, detail="Failed to restore admin session")

    return _serialize_auth_context(restored_context, restore_token)


@app.get("/status")
def get_status(authorization: Optional[str] = Header(default=None)) -> dict:
    """Get current aggregation status and statistics."""
    _require_auth(authorization)

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
def get_simulation_metrics(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Get real-time simulation metrics for monitoring."""
    _require_auth(authorization)

    metrics = _get_simulation_metrics_payload()
    if metrics is None:
        raise HTTPException(status_code=404, detail="Simulation mode not active")
    return metrics


@app.get("/reputation/clients")
def get_reputation_clients(
    limit: int = 50,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Get client-level reputation details for frontend admin views."""
    _require_admin(authorization)

    safe_limit = max(1, min(limit, 200))
    clients = _get_reputation_clients(limit=safe_limit)
    return {
        "count": len(clients),
        "clients": clients,
    }


@app.post("/admin/users")
def admin_add_user(
    request: AdminUserRequest,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Register a reputation client for admin management."""
    _require_admin(authorization)

    normalized = request.client_id.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="client_id cannot be empty")
    if len(normalized) > 128:
        raise HTTPException(status_code=400, detail="client_id too long")

    status, payload = _register_reputation_client(normalized)
    if status == "reputation_disabled":
        raise HTTPException(status_code=503, detail="reputation manager disabled")
    if status == "unavailable" or payload is None:
        raise HTTPException(status_code=500, detail="unable to manage clients")

    return {
        "status": status,
        "client": payload,
    }


@app.delete("/admin/users/{client_id}")
def admin_remove_user(
    client_id: str,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Remove a reputation client from admin-managed list."""
    _require_admin(authorization)

    normalized = client_id.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="client_id cannot be empty")

    if not reputation_manager:
        raise HTTPException(status_code=503, detail="reputation manager disabled")

    was_removed = _remove_reputation_client(normalized)
    return {
        "status": "removed" if was_removed else "not_found",
        "client_id": normalized,
    }


@app.get("/security/events")
def get_security_events(
    hours: int = 24,
    limit: int = 50,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Get recent security events with optional window and result limit."""
    _require_admin(authorization)

    safe_hours = max(1, min(hours, 168))
    safe_limit = max(1, min(limit, 200))
    events = _get_recent_security_events(hours=safe_hours, limit=safe_limit)
    return {
        "count": len(events),
        "hours": safe_hours,
        "events": events,
    }


@app.get("/simulation/scenarios")
def list_simulation_scenarios(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """List available simulation scenarios for frontend controls."""
    _require_auth(authorization)
    return {"scenarios": _get_simulation_scenario_names()}


@app.get("/frontend/overview")
def get_frontend_overview(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    """Consolidated dashboard payload for frontend integration."""
    context = _require_auth(authorization)
    has_admin_access = context.get("session_role") == ROLE_ADMIN and not context.get("is_simulating")
    status_payload = get_status(authorization)
    simulation_payload = _get_simulation_metrics_payload()

    privacy_payload: dict[str, Any] = {}
    try:
        privacy_payload = privacy_tracker.get_cumulative_privacy()
    except Exception as e:
        log_warning(logger, f"Failed to fetch privacy summary: {e}")

    return {
        "status": status_payload,
        "reputation_clients": _get_reputation_clients(limit=100) if has_admin_access else [],
        "recent_security_events": _get_recent_security_events(hours=24, limit=50) if has_admin_access else [],
        "simulation": {
            "enabled": SIMULATION_MODE,
            "metrics": simulation_payload,
            "scenarios": _get_simulation_scenario_names(),
        },
        "privacy": privacy_payload,
        "frontend_origins": frontend_origins,
        "timestamp": time.time(),
    }

@app.post("/chat")
def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, str]:
    _require_auth(authorization)

    user_input = request.prompt
    response = generate_response(user_input)
    return {"input": user_input, "response": response}


@app.post("/send-update")
def receive_update(
    update: UpdateRequest,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Enhanced update endpoint with Byzantine-robust aggregation and security."""
    context = _require_auth(authorization)
    client_id = context.get("effective_username") or update.client_id
    validation_confidence = 1.0

    try:
        # Step 1: Input validation and sanitization
        if update_validator:
            canonical_update = update.dict()
            # Enforce authenticated identity as source-of-truth for validation.
            canonical_update["client_id"] = client_id
            validation_result = update_validator.validate_update(canonical_update, client_id)

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
            validation_confidence = getattr(validation_result, "confidence", 1.0)
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
                "validation_confidence": validation_confidence,
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
                _save_model_state(round_num)

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
