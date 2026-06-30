"""
database/db.py

Provides:
  get_db()   — SQLite connection scoped to the current Flask request.
  close_db() — Closes that connection at request teardown.
  init_db()  — Creates all tables if they don't exist.

Schema change from Milestone 1:
  All primary keys are now TEXT UUIDs generated in Python, not
  INTEGER AUTOINCREMENT. This lets us generate the content_id before
  the DB insert and return it in the API response without a round-trip.

  The submissions table also stores all analysis fields so the audit
  service and appeal service can read them without re-running detection.
"""

import os
import sqlite3

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """
    Return the SQLite connection for the current request, opening one if
    needed. Stored in Flask's g object so it is reused within a request
    and closed automatically at teardown.
    """
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None) -> None:
    """Close the connection at the end of a request (called by Flask)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app) -> None:
    """
    Create all tables using IF NOT EXISTS — safe to call on every restart.

    If the database file already exists with an old schema (from a previous
    milestone), delete instance/provenance_guard.db and restart the server
    so this function can build the correct schema from scratch.
    """
    with app.app_context():
        db = get_db()
        db.executescript("""
            -- ----------------------------------------------------------------
            -- submissions
            -- Primary key is a UUID string generated in routes/submit.py.
            -- status starts as "classified" and moves to "under_review" when
            -- an appeal is filed.
            -- ----------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS submissions (
                id                TEXT PRIMARY KEY,
                creator_id        TEXT NOT NULL,
                content           TEXT NOT NULL,
                classification    TEXT NOT NULL,
                confidence        REAL NOT NULL,
                label             TEXT NOT NULL,
                llm_score         REAL NOT NULL,
                stylometric_score REAL NOT NULL,
                status            TEXT NOT NULL DEFAULT 'classified',
                submitted_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            -- ----------------------------------------------------------------
            -- appeals
            -- Schema exactly matches the Milestone 5 specification.
            -- submission_id references submissions(id) as a foreign key.
            -- ----------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS appeals (
                id                TEXT PRIMARY KEY,
                submission_id     TEXT NOT NULL REFERENCES submissions(id),
                creator_reasoning TEXT NOT NULL,
                status            TEXT NOT NULL DEFAULT 'pending',
                filed_at          TEXT NOT NULL DEFAULT (datetime('now'))
            );

            -- ----------------------------------------------------------------
            -- audit_logs
            -- One row per significant event. All required fields are stored
            -- as explicit columns (not a JSON blob) so they can be queried
            -- and filtered efficiently.
            -- appeal_reasoning is NULL for submission_analyzed events.
            -- ----------------------------------------------------------------
            CREATE TABLE IF NOT EXISTS audit_logs (
                id                TEXT PRIMARY KEY,
                event             TEXT NOT NULL,
                submission_id     TEXT,
                label             TEXT,
                confidence        REAL,
                llm_score         REAL,
                stylometric_score REAL,
                status            TEXT,
                appeal_reasoning  TEXT,
                created_at        TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        db.commit()
