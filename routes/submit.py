"""
routes/submit.py

POST /submit — accept text, run the full detection pipeline, persist to
the database, write an audit log entry, and return the result.

Pipeline order:
  1. Validate request
  2. Run LLM signal       (DetectionService.run_llm_signal)
  3. Run stylometric signal (DetectionService.run_stylometric_signal)
  4. Combine + label      (ConfidenceService.combine)
  5. Persist submission   (submissions table)
  6. Write audit log      (audit_logs table)
  7. Return JSON

Rate limiting: 10 requests per minute and 100 per day, per IP address.
Applied via Flask-Limiter using the shared limiter from extensions.py.
"""

import uuid

from flask import Blueprint, current_app, request

from database.db import get_db
from extensions import limiter
from services.audit_service import log_submission
from services.confidence_service import ConfidenceService
from services.detection_service import DetectionService
from utils.helpers import error_response, success_response
from utils.validators import validate_submit_payload

submit_bp = Blueprint("submit", __name__)


@submit_bp.route("/submit", methods=["POST"])
@limiter.limit("10 per minute; 100 per day")
def submit():
    """
    POST /submit

    Rate limited: 10/minute, 100/day per IP.
    Returns 429 Too Many Requests when the limit is exceeded.

    Request body (JSON):
        {
            "text":       "The text to analyze.",
            "creator_id": "user-abc-123"
        }

    Success response (200):
        {
            "status": "success",
            "data": {
                "content_id":     "<uuid>",
                "creator_id":     "user-abc-123",
                "classification": "ai" | "human" | "uncertain",
                "confidence":     0.0–1.0,
                "label":          "<plain-language transparency label>",
                "status":         "classified",
                "signals": {
                    "llm_score":          0.0–1.0,
                    "stylometric_score":  0.0–1.0,
                    "llm_detail":         { ... },
                    "stylometric_detail": { ... }
                }
            }
        }

    Error responses:
        400 — missing/invalid fields or unparseable JSON
        429 — rate limit exceeded
    """
    # ------------------------------------------------------------------ #
    # Step 1 — Validate                                                   #
    # ------------------------------------------------------------------ #
    payload, field, message = validate_submit_payload(request)
    if field is not None:
        return error_response("missing_field", message, 400)

    text       = payload["text"].strip()
    creator_id = payload["creator_id"].strip()

    # ------------------------------------------------------------------ #
    # Steps 2 & 3 — Run detection signals                                 #
    # ------------------------------------------------------------------ #
    groq_api_key       = current_app.config.get("GROQ_API_KEY", "")
    detection          = DetectionService(groq_api_key=groq_api_key)
    llm_result         = detection.run_llm_signal(text)
    stylometric_result = detection.run_stylometric_signal(text)

    # ------------------------------------------------------------------ #
    # Step 4 — Combine signals and assign label                           #
    # ------------------------------------------------------------------ #
    confidence_svc = ConfidenceService()
    result         = confidence_svc.combine(llm_result, stylometric_result)

    classification    = result["classification"]
    confidence        = result["confidence"]
    label_text        = result["label"]
    llm_score         = result["signals"]["llm_score"]
    stylometric_score = result["signals"]["stylometric_score"]

    # ------------------------------------------------------------------ #
    # Step 5 — Persist submission to the database                         #
    # ------------------------------------------------------------------ #
    content_id = str(uuid.uuid4())
    db         = get_db()

    db.execute(
        """
        INSERT INTO submissions (
            id, creator_id, content, classification,
            confidence, label, llm_score, stylometric_score,
            status, submitted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'classified', datetime('now'))
        """,
        (
            content_id,
            creator_id,
            text,
            classification,
            confidence,
            label_text,
            llm_score,
            stylometric_score,
        ),
    )
    db.commit()

    # ------------------------------------------------------------------ #
    # Step 6 — Write audit log entry                                      #
    # ------------------------------------------------------------------ #
    log_submission(
        db=db,
        submission_id=content_id,
        classification=classification,
        confidence=confidence,
        llm_score=llm_score,
        stylometric_score=stylometric_score,
        status="classified",
    )

    # ------------------------------------------------------------------ #
    # Step 7 — Return response                                            #
    # ------------------------------------------------------------------ #
    return success_response(
        {
            "content_id":     content_id,
            "creator_id":     creator_id,
            "classification": classification,
            "confidence":     confidence,
            "label":          label_text,
            "status":         "classified",
            "signals":        result["signals"],
        },
        200,
    )
