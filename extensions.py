"""
extensions.py

Holds Flask extension instances that are created before the application
factory runs and then initialised inside create_app().

Why this file exists:
  Flask-Limiter (and many other Flask extensions) must be created as a
  module-level object so that route decorators like @limiter.limit(...)
  can reference it at import time. But the Flask app itself doesn't exist
  yet when blueprints are imported — that is the whole point of the
  application factory pattern.

  The solution is a two-step initialisation:
    1. Create the extension here with no app attached.
    2. Call limiter.init_app(app) inside create_app() once the app exists.

  Any module (e.g. routes/submit.py) can then do:
      from extensions import limiter
  and use @limiter.limit(...) safely.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,   # rate-limit by caller IP address
    storage_uri="memory://",       # in-process memory store (dev/single-instance)
    default_limits=[],             # no global default — limits are applied per-route
)
