"""
routes/appeal.py

POST /appeal — file an appeal against an existing submission's label.

The route layer is intentionally thin:
  - Parse and validate the JSON body.
  - Call AppealService.create_appeal() for all business logic.
  - Return the result or the appropriate error response.

No rate limiting is applied to this endpoint. A creator can only file
one appeal per submission (enforced by the service layer), so the
natural constraint is already in place.
"""

from flask import Blueprint, request

from database.db import get_db
from services.appeal_service import AppealError, create_appeal
from utils.helpers import error_response, success_response

appeal_bp = Blueprint("appeal", __name__)


@appeal_bp.route("/appeal", methods=["POST"])
def appeal():
    """
    POST /appeal

    Request body (JSON):
        {
            "submission_id":    "<uuid>",
            "creator_reasoning": "<string, minimum 10 characters>"
        }

    Success response (201 Created):
        {
            "status": "success",
            "data": {
                "appeal_id":    "<uuid>",
                "submission_id": "<uuid>",
                "status":       "pending",
                "filed_at":     "2026-06-29T14:45:11Z"
            }
        }

    Error responses:
        400 — missing fields or reasoning too short
        404 — submission_id does not exist
        409 — appeal already exists for this submission
    """
    # ------------------------------------------------------------------ #
    # Parse the request body                                              #
    # ------------------------------------------------------------------ #
    payload = request.get_json(silent=True)
    if payload is None:
        return error_response(
            "invalid_json",
            "Request body must be valid JSON with Content-Type: application/json.",
            400,
        )

    submission_id      = payload.get("submission_id", "")
    creator_reasoning  = payload.get("creator_reasoning", "")

    if not submission_id or not isinstance(submission_id, str) or not submission_id.strip():
        return error_response(
            "missing_field",
            "The 'submission_id' field is required and must be a non-empty string.",
            400,
        )

    if not creator_reasoning or not isinstance(creator_reasoning, str):
        return error_response(
            "missing_field",
            "The 'creator_reasoning' field is required.",
            400,
        )

    # ------------------------------------------------------------------ #
    # Delegate to the service layer                                       #
    # ------------------------------------------------------------------ #
    db = get_db()

    try:
        result = create_appeal(
            db=db,
            submission_id=submission_id.strip(),
            creator_reasoning=creator_reasoning,
        )
    except AppealError as exc:
        return error_response(exc.code, exc.message, exc.http_status)

    return success_response(result, 201)
