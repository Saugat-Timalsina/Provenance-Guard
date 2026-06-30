"""
utils/helpers.py

Reusable response-building utilities used by every route.

Design decision: All API responses — success and error — go through these
two functions. This guarantees a consistent envelope shape so clients never
have to guess the structure of an error vs. a success response.

Success envelope:
  { "status": "success", "data": { ... } }

Error envelope:
  { "status": "error", "error": { "code": "...", "message": "..." } }
"""

from flask import jsonify


def success_response(data: dict, http_status: int = 200):
    """
    Wrap a result dictionary in a standard success envelope and return
    a Flask JSON response.

    Args:
        data:        The payload to include under the "data" key.
        http_status: The HTTP status code. Defaults to 200.

    Returns:
        A Flask Response object with Content-Type: application/json.
    """
    return jsonify({"status": "success", "data": data}), http_status


def error_response(code: str, message: str, http_status: int):
    """
    Wrap an error description in a standard error envelope and return
    a Flask JSON response.

    Args:
        code:        A short machine-readable string identifying the error
                     (e.g. "missing_field", "invalid_json").
        message:     A human-readable description of what went wrong.
        http_status: The HTTP status code (e.g. 400, 404, 429).

    Returns:
        A Flask Response object with Content-Type: application/json.
    """
    return jsonify({
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        }
    }), http_status
