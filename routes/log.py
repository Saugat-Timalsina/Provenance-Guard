"""
routes/log.py

GET /log — retrieve structured audit log entries.

Supports optional filtering by submission_id via query parameter.
Returns entries in ascending created_at order (oldest first) so a
reviewer can read the history of a submission chronologically.

Not rate-limited: log retrieval is a read-only operation and is not
exposed to end users in a production scenario.
"""

from flask import Blueprint, request

from database.db import get_db
from utils.helpers import error_response, success_response

log_bp = Blueprint("log", __name__)


@log_bp.route("/log", methods=["GET"])
def get_log():
    """
    GET /log
    GET /log?submission_id=<uuid>
    GET /log?limit=<int>

    Query parameters (all optional):
        submission_id  — filter entries to a specific submission
        limit          — maximum number of entries to return (default 100)

    Success response (200):
        {
            "status": "success",
            "data": {
                "entries": [
                    {
                        "id":                 "<uuid>",
                        "event":              "submission_analyzed" | "appeal_filed",
                        "submission_id":      "<uuid>",
                        "label":              "ai" | "human" | "uncertain",
                        "confidence":         float,
                        "llm_score":          float,
                        "stylometric_score":  float,
                        "status":             "classified" | "under_review",
                        "appeal_reasoning":   str | null,
                        "created_at":         "ISO 8601 UTC"
                    },
                    ...
                ],
                "total": int
            }
        }

    Error responses:
        400 — limit parameter is not a valid positive integer
    """
    # ------------------------------------------------------------------ #
    # Parse query parameters                                              #
    # ------------------------------------------------------------------ #
    submission_id = request.args.get("submission_id", "").strip() or None

    raw_limit = request.args.get("limit", "100")
    try:
        limit = int(raw_limit)
        if limit <= 0:
            raise ValueError
    except ValueError:
        return error_response(
            "invalid_parameter",
            "'limit' must be a positive integer.",
            400,
        )

    # ------------------------------------------------------------------ #
    # Query audit_logs                                                    #
    # ------------------------------------------------------------------ #
    db = get_db()

    if submission_id:
        rows = db.execute(
            """
            SELECT id, event, submission_id, label, confidence,
                   llm_score, stylometric_score, status,
                   appeal_reasoning, created_at
            FROM audit_logs
            WHERE submission_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (submission_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, event, submission_id, label, confidence,
                   llm_score, stylometric_score, status,
                   appeal_reasoning, created_at
            FROM audit_logs
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    # ------------------------------------------------------------------ #
    # Serialize sqlite3.Row objects to plain dicts                        #
    # ------------------------------------------------------------------ #
    entries = [
        {
            "id":                str(row["id"]),
            "event":             row["event"],
            "submission_id":     row["submission_id"],
            "label":             row["label"],
            "confidence":        row["confidence"],
            "llm_score":         row["llm_score"],
            "stylometric_score": row["stylometric_score"],
            "status":            row["status"],
            "appeal_reasoning":  row["appeal_reasoning"],
            "created_at":        row["created_at"],
        }
        for row in rows
    ]

    return success_response({"entries": entries, "total": len(entries)}, 200)
