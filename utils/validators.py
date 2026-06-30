"""
utils/validators.py

Reusable input validation functions called by route handlers before any
business logic runs.

Design decision: Validation is separated from routing so that the same
rules can be reused across multiple endpoints and tested independently.
Each function returns a tuple of (error_message_or_None, field_name_or_None)
so the caller can produce a specific, actionable error message.
"""

from flask import Request

# Submission text limits
TEXT_MIN_LENGTH: int = 1
TEXT_MAX_LENGTH: int = 10_000


def validate_submit_payload(request: Request) -> tuple[dict | None, str | None, str | None]:
    """
    Validate the JSON body of a POST /submit request.

    Checks:
      1. The request body is valid JSON.
      2. The 'text' field is present and non-empty.
      3. The 'creator_id' field is present and non-empty.
      4. The 'text' field does not exceed TEXT_MAX_LENGTH characters.

    Args:
        request: The Flask request object for the current request.

    Returns:
        A tuple of three values:
          - payload (dict | None): The parsed JSON body if valid, else None.
          - field (str | None):    The name of the invalid field, or None if valid.
          - message (str | None):  A human-readable error message, or None if valid.

    Usage:
        payload, field, message = validate_submit_payload(request)
        if field:
            return error_response("missing_field", message, 400)
    """
    # --- Check 1: Body must be valid JSON ---
    payload = request.get_json(silent=True)
    if payload is None:
        return None, "body", (
            "Request body must be valid JSON with Content-Type: application/json."
        )

    # --- Check 2: 'text' must be present and non-empty ---
    text = payload.get("text")
    if not text or not isinstance(text, str) or not text.strip():
        return None, "text", (
            "The 'text' field is required and must be a non-empty string."
        )

    # --- Check 3: 'creator_id' must be present and non-empty ---
    creator_id = payload.get("creator_id")
    if not creator_id or not isinstance(creator_id, str) or not creator_id.strip():
        return None, "creator_id", (
            "The 'creator_id' field is required and must be a non-empty string."
        )

    # --- Check 4: 'text' must not exceed the maximum allowed length ---
    if len(text) > TEXT_MAX_LENGTH:
        return None, "text", (
            f"The 'text' field must not exceed {TEXT_MAX_LENGTH} characters. "
            f"Received {len(text)} characters."
        )

    return payload, None, None
