"""
config/settings.py

Centralizes all configuration for the application.

We use a class-based approach so settings are grouped, easy to read,
and simple to extend (e.g. adding a TestingConfig later).

python-dotenv loads values from the .env file into os.environ before
this module reads them, so no .env values are hard-coded here.
"""

import os
from dotenv import load_dotenv

# Load the .env file into environment variables as early as possible.
# override=False means existing shell variables take priority over .env values,
# which is the safe default for production deployments.
load_dotenv(override=False)


class Config:
    """Base configuration shared by all environments."""

    # Flask uses this key to cryptographically sign session cookies.
    # Must be set to a long random string in production.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-unsafe")

    # Absolute or relative path to the SQLite database file.
    # The 'instance' folder is the Flask convention for runtime data.
    DATABASE_PATH: str = os.environ.get("DATABASE_PATH", "instance/provenance_guard.db")

    # Groq API key — required for AI detection (Milestone 3).
    # Stored in .env, never committed to version control.
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")

    # When True, Flask shows detailed error pages and auto-reloads on code changes.
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "0") == "1"


class DevelopmentConfig(Config):
    """Settings used during local development."""
    DEBUG = True


class ProductionConfig(Config):
    """Settings used in production — debug must be off."""
    DEBUG = False


# Maps the FLASK_ENV string to the matching config class.
# app.py uses this dict to select the right config at startup.
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
