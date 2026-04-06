"""
SQLite-backed authentication and RBAC helpers for PrivaLoom.

Provides:
- User storage with salted password hashing
- Session token issuance and validation
- Role checks (admin/user)
- Admin impersonation (simulate user)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES = {ROLE_ADMIN, ROLE_USER}

_lock = threading.Lock()
_db_path: Optional[Path] = None


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _to_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1]
    return datetime.fromisoformat(value)


def _connect() -> sqlite3.Connection:
    if _db_path is None:
        raise RuntimeError("Auth database not initialized")

    conn = sqlite3.connect(_db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _hash_password(password: str, *, iterations: int = 260000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def init_auth_db(db_path: str, *, bootstrap_admin_username: str, bootstrap_admin_password: str) -> None:
    """Initialize auth DB and ensure a bootstrap admin exists."""
    global _db_path

    _db_path = Path(db_path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    acting_as_user_id INTEGER,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(acting_as_user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            if user_count == 0 and bootstrap_admin_username and bootstrap_admin_password:
                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role, is_active, created_at)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (
                        bootstrap_admin_username.strip(),
                        _hash_password(bootstrap_admin_password),
                        ROLE_ADMIN,
                        _utc_now_iso(),
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def get_user_count() -> int:
    conn = _connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])
    finally:
        conn.close()


def _normalize_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, username, role, is_active, created_at, last_login_at FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        return _normalize_user(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, username, role, is_active, created_at, last_login_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return _normalize_user(row) if row else None
    finally:
        conn.close()


def list_users() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, username, role, is_active, created_at, last_login_at FROM users ORDER BY created_at ASC"
        ).fetchall()
        return [_normalize_user(row) for row in rows]
    finally:
        conn.close()


def create_user(username: str, password: str, role: str = ROLE_USER) -> dict[str, Any]:
    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("username cannot be empty")
    if len(normalized_username) > 128:
        raise ValueError("username too long")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")

    normalized_role = role.strip().lower()
    if normalized_role not in VALID_ROLES:
        raise ValueError("invalid role")

    with _lock:
        conn = _connect()
        try:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (normalized_username,),
            ).fetchone()
            if existing:
                raise ValueError("username already exists")

            conn.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    normalized_username,
                    _hash_password(password),
                    normalized_role,
                    _utc_now_iso(),
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT id, username, role, is_active, created_at, last_login_at FROM users WHERE username = ?",
                (normalized_username,),
            ).fetchone()
            if row is None:
                raise RuntimeError("failed to create user")
            return _normalize_user(row)
        finally:
            conn.close()


def delete_user(user_id: int) -> bool:
    with _lock:
        conn = _connect()
        try:
            result = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()


def authenticate_user(username: str, password: str) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, role, is_active, created_at, last_login_at FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()

        if row is None:
            return None
        if not bool(row["is_active"]):
            return None
        if not _verify_password(password, row["password_hash"]):
            return None

        now = _utc_now_iso()
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, int(row["id"])))
        conn.commit()

        return {
            "id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "last_login_at": now,
        }
    finally:
        conn.close()


def create_session(user_id: int, *, acting_as_user_id: Optional[int] = None, ttl_hours: int = 24) -> str:
    token = secrets.token_urlsafe(48)
    created_at = _utc_now_iso()
    expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat() + "Z"

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, acting_as_user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (token, user_id, acting_as_user_id, created_at, expires_at),
            )
            conn.commit()
            return token
        finally:
            conn.close()


def revoke_session(token: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()


def get_session_context(token: str) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT
                s.token,
                s.user_id AS session_user_id,
                s.acting_as_user_id,
                s.created_at,
                s.expires_at,
                su.username AS session_username,
                su.role AS session_role,
                su.is_active AS session_is_active,
                eu.id AS effective_user_id,
                eu.username AS effective_username,
                eu.role AS effective_role,
                eu.is_active AS effective_is_active
            FROM sessions s
            JOIN users su ON su.id = s.user_id
            LEFT JOIN users eu ON eu.id = COALESCE(s.acting_as_user_id, s.user_id)
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()

        if row is None:
            return None

        if _to_datetime(row["expires_at"]) <= datetime.utcnow():
            revoke_session(token)
            return None

        if not bool(row["session_is_active"]) or not bool(row["effective_is_active"]):
            revoke_session(token)
            return None

        return {
            "token": row["token"],
            "session_user_id": int(row["session_user_id"]),
            "session_username": row["session_username"],
            "session_role": row["session_role"],
            "effective_user_id": int(row["effective_user_id"]),
            "effective_username": row["effective_username"],
            "effective_role": row["effective_role"],
            "is_simulating": row["acting_as_user_id"] is not None,
            "expires_at": row["expires_at"],
            "created_at": row["created_at"],
        }
    finally:
        conn.close()
