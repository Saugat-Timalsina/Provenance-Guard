"""
services/appeal_service.py

Business logic for the appeals workflow.

Handles the three steps that must all succeed atomically:
  1. Validate the submission exists and has not already been appealed.
  2. Insert the appeal record and update the submission status.
  3. Write the audit log entry.

If any step fails, the caller (route handler) catches the exception and
returns the appropriate error response. The DB connection is passed in
from the route so the same request-scoped connection handles everything.
"""

import sqlite3
import uuid
from datetime import datetime, timezone

from services.audit_service import log_appeal


# Minimum length for creator_reasoning — must be meaningful, not a placeholder
REASONING_MIN_LENGTH = 10


class AppealError(Exception):
    """
    Raised when an appeal cannot be created due to a business rule violation.

    Attributes:
        code:        Machine-readable error code for the route to use.
        message:     Human-readable explanation.
        http_status: The appropriate HTTP response code.
    """
    def __init__(self, code: str, message: str, http_status: int):
        self.code        = code
        self.message     = message
        self.http_status = http_status
        super().__init__(message)


def create_appeal(
    db: sqlite3.Connection,
    submission_id: str,
    creator_reasoning: str,
) -> dict:
    """
    File an appeal against an existing submission.

    Validates, writes the appeal, updates submission status, writes
    the audit log, and returns the appeal record as a dict.

    Args:
        db:                Active SQLite connection from get_db().
        submission_id:     UUID of the submission being appealed.
        creator_reasoning: The creator's explanation of why the label is wrong.

    Returns:
        {
            "appeal_id":    str,  # UUID of the new appeal record
            "submission_id": str,
            "status":       "pending",
            "filed_at":     str,  # ISO 8601 UTC timestamp
        }

    Raises:
        AppealError: if validation fails (404, 409, or 400).
    """
    # ------------------------------------------------------------------ #
    # Validate: reasoning must be substantive                             #
    # ------------------------------------------------------------------ #
    if not creator_reasoning or len(creator_reasoning.strip()) < REASONING_MIN_LENGTH:
        raise AppealError(
            code="reasoning_too_short",
            message=(
                f"'creator_reasoning' must be at least {REASONING_MIN_LENGTH} "
                "characters. Please explain why you believe the label is incorrect."
            ),
            http_status=400,
        )

    # ------------------------------------------------------------------ #
    # Validate: submission must exist                                     #
    # ------------------------------------------------------------------ #
    row = db.execute(
        "SELECT id, classification, confidence, llm_score, stylometric_score, status "
        "FROM submissions WHERE id = ?",
        (submission_id,),
    ).fetchone()

    if row is None:
        raise AppealError(
            code="submission_not_found",
            message=f"No submission found with id '{submission_id}'.",
            http_status=404,
        )

    # ------------------------------------------------------------------ #
    # Validate: no existing appeal for this submission                    #
    # ------------------------------------------------------------------ #
    existing = db.execute(
        "SELECT id FROM appeals WHERE submission_id = ?",
        (submission_id,),
    ).fetchone()

    if existing is not None:
        raise AppealError(
            code="appeal_already_exists",
            message=(
                "An appeal has already been filed for this submission. "
                "Only one appeal is allowed per submission."
            ),
            http_status=409,
        )

    # ------------------------------------------------------------------ #
    # Insert the appeal record                                            #
    # ------------------------------------------------------------------ #
    appeal_id = str(uuid.uuid4())
    filed_at  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    db.execute(
        """
        INSERT INTO appeals (id, submission_id, creator_reasoning, status, filed_at)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (appeal_id, submission_id, creator_reasoning.strip(), filed_at),
    )

    # ------------------------------------------------------------------ #
    # Update submission status to "under_review"                         #
    # ------------------------------------------------------------------ #
    db.execute(
        "UPDATE submissions SET status = 'under_review' WHERE id = ?",
        (submission_id,),
    )

    db.commit()

    # ------------------------------------------------------------------ #
    # Write audit log entry                                               #
    # ------------------------------------------------------------------ #
    log_appeal(
        db=db,
        submission_id=submission_id,
        creator_reasoning=creator_reasoning.strip(),
        original_classification=row["classification"],
        original_confidence=row["confidence"],
        original_llm_score=row["llm_score"],
        original_stylometric_score=row["stylometric_score"],
    )

    return {
        "appeal_id":    appeal_id,
        "submission_id": submission_id,
        "status":       "pending",
        "filed_at":     filed_at,
    }
