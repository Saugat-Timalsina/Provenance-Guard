"""
services/audit_service.py

Writes structured entries to the audit_logs table.

Every significant event in the system produces one audit log entry.
This file defines one function per event type so the calling code
(routes) never builds raw SQL or constructs log dicts manually.

Current event types:
  "submission_analyzed" — written after POST /submit completes
  "appeal_filed"        — written after POST /appeal completes

All entries include the full analysis context (label, confidence, scores)
so a reviewer can read the log without querying other tables.
"""

import uuid
from datetime import datetime, timezone

import sqlite3


def log_submission(
    db: sqlite3.Connection,
    submission_id: str,
    classification: str,
    confidence: float,
    llm_score: float,
    stylometric_score: float,
    status: str = "classified",
) -> str:
    """
    Write a 'submission_analyzed' entry to audit_logs.

    Args:
        db:               Active SQLite connection from get_db().
        submission_id:    UUID of the submission (matches submissions.id).
        classification:   "ai" | "human" | "uncertain"
        confidence:       Combined confidence score 0.0–1.0.
        llm_score:        Raw LLM signal score.
        stylometric_score: Raw stylometric signal score.
        status:           Submission status at time of logging ("classified").

    Returns:
        The UUID string assigned to the new audit log entry.
    """
    log_id     = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    db.execute(
        """
        INSERT INTO audit_logs (
            id, event, submission_id, label, confidence,
            llm_score, stylometric_score, status,
            appeal_reasoning, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            "submission_analyzed",
            submission_id,
            classification,     # stored as "ai" | "human" | "uncertain"
            confidence,
            llm_score,
            stylometric_score,
            status,
            None,               # appeal_reasoning: null for submissions
            created_at,
        ),
    )
    db.commit()
    return log_id


def log_appeal(
    db: sqlite3.Connection,
    submission_id: str,
    creator_reasoning: str,
    original_classification: str,
    original_confidence: float,
    original_llm_score: float,
    original_stylometric_score: float,
) -> str:
    """
    Write an 'appeal_filed' entry to audit_logs.

    Stores the original classification context alongside the appeal
    reasoning so a reviewer sees both in a single log entry — they
    do not need to cross-reference the submissions table.

    Args:
        db:                         Active SQLite connection.
        submission_id:              UUID of the submission being appealed.
        creator_reasoning:          The creator's appeal text.
        original_classification:    Classification at time of appeal.
        original_confidence:        Confidence score at time of appeal.
        original_llm_score:         LLM signal score at time of appeal.
        original_stylometric_score: Stylometric score at time of appeal.

    Returns:
        The UUID string assigned to the new audit log entry.
    """
    log_id     = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    db.execute(
        """
        INSERT INTO audit_logs (
            id, event, submission_id, label, confidence,
            llm_score, stylometric_score, status,
            appeal_reasoning, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            "appeal_filed",
            submission_id,
            original_classification,
            original_confidence,
            original_llm_score,
            original_stylometric_score,
            "under_review",          # the status after an appeal is filed
            creator_reasoning,
            created_at,
        ),
    )
    db.commit()
    return log_id
