"""
SQLite database module for OCT Smart Tutor.
Handles user management, session tracking, and attempt history.
"""
import sqlite3
import os
import time
import uuid
import bcrypt
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "oct_tutor.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                image_id TEXT NOT NULL,
                true_class TEXT NOT NULL,
                ai_prediction TEXT NOT NULL,
                ai_confidence REAL NOT NULL,
                user_prediction TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # Migration: add password_hash column if missing (for existing DBs)
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        ]
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            print("[DB] Migrated users table: added password_hash column")


# ------------------------------------------------------------------
# Password Helpers
# ------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ------------------------------------------------------------------
# User Management
# ------------------------------------------------------------------

def create_user(username: str, password: str) -> dict:
    """Create a new user with a hashed password."""
    user_id = str(uuid.uuid4())
    now = time.time()
    pw_hash = hash_password(password)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, pw_hash, now)
        )
    return {"id": user_id, "username": username, "created_at": now}


def get_user_by_username(username: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row:
            return dict(row)
    return None


def get_user_by_id(user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            return dict(row)
    return None


def set_user_password(user_id: str, password: str):
    """Set/update the password for an existing user (migration helper)."""
    pw_hash = hash_password(password)
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (pw_hash, user_id)
        )


# ------------------------------------------------------------------
# Session Management
# ------------------------------------------------------------------

def create_session(user_id: str) -> dict:
    session_id = str(uuid.uuid4())
    now = time.time()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (id, user_id, started_at) VALUES (?, ?, ?)",
            (session_id, user_id, now)
        )
    return {"id": session_id, "user_id": user_id, "started_at": now}


# ------------------------------------------------------------------
# Attempt Tracking
# ------------------------------------------------------------------

def record_attempt(session_id: str, user_id: str, image_id: str,
                   true_class: str, ai_prediction: str, ai_confidence: float,
                   user_prediction: str, is_correct: bool) -> dict:
    attempt_id = str(uuid.uuid4())
    now = time.time()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO attempts 
               (id, session_id, user_id, image_id, true_class, ai_prediction, 
                ai_confidence, user_prediction, is_correct, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (attempt_id, session_id, user_id, image_id, true_class,
             ai_prediction, ai_confidence, user_prediction,
             1 if is_correct else 0, now)
        )
    return {
        "id": attempt_id, "session_id": session_id, "user_id": user_id,
        "image_id": image_id, "true_class": true_class,
        "ai_prediction": ai_prediction, "ai_confidence": ai_confidence,
        "user_prediction": user_prediction, "is_correct": is_correct,
        "created_at": now
    }


def get_user_stats(user_id: str) -> dict:
    """Get per-class accuracy stats for a user."""
    classes = ["CNV", "DME", "DRUSEN", "NORMAL"]
    stats = {}
    with get_db() as conn:
        for cls in classes:
            total = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE user_id = ? AND true_class = ?",
                (user_id, cls)
            ).fetchone()[0]
            correct = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE user_id = ? AND true_class = ? AND is_correct = 1",
                (user_id, cls)
            ).fetchone()[0]
            stats[cls] = {
                "total": total,
                "correct": correct,
                "accuracy": correct / total if total > 0 else 0.0
            }
    return stats


def get_user_history(user_id: str, limit: int = 20) -> list:
    """Get recent attempt history for a user."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM attempts WHERE user_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
