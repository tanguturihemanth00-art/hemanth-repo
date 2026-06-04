"""
config/environment.py
=====================
Loads and validates all environment variables from .env.
Single source of truth for runtime secrets and env-overridable settings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Resolve the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


def _load_env() -> None:
    """Load .env file if it exists. Fail gracefully if absent."""
    if _ENV_FILE.exists():
        load_dotenv(dotenv_path=_ENV_FILE, override=True)
    else:
        print(
            f"[WARNING] .env file not found at {_ENV_FILE}. "
            "Using system environment variables only."
        )


_load_env()


class EnvironmentConfig:
    """
    Typed accessor for all environment variables.

    Reads from the process environment (populated by .env via load_dotenv).
    All sensitive values are read-only properties — never stored in instance vars
    longer than necessary to avoid accidental logging.
    """

    # ------------------------------------------------------------------ #
    # Application                                                          #
    # ------------------------------------------------------------------ #
    @property
    def app_url(self) -> str:
        value = os.environ.get("APP_URL", "").strip()
        if not value:
            raise EnvironmentError(
                "APP_URL is not set. Add it to your .env file."
            )
        return value

    @property
    def app_username(self) -> str:
        value = os.environ.get("APP_USERNAME", "").strip()
        if not value:
            raise EnvironmentError(
                "APP_USERNAME is not set. Add it to your .env file."
            )
        return value

    @property
    def app_password(self) -> str:
        value = os.environ.get("APP_PASSWORD", "").strip()
        if not value:
            raise EnvironmentError(
                "APP_PASSWORD is not set. Add it to your .env file."
            )
        return value

    # ------------------------------------------------------------------ #
    # Browser                                                              #
    # ------------------------------------------------------------------ #
    @property
    def browser_headless(self) -> bool:
        return os.environ.get("BROWSER_HEADLESS", "false").lower() == "true"

    @property
    def browser_slow_mo(self) -> int:
        return int(os.environ.get("BROWSER_SLOW_MO", "0"))

    @property
    def browser_timeout(self) -> int:
        return int(os.environ.get("BROWSER_TIMEOUT", "30000"))

    # ------------------------------------------------------------------ #
    # Session                                                              #
    # ------------------------------------------------------------------ #
    @property
    def session_reuse(self) -> bool:
        return os.environ.get("SESSION_REUSE", "true").lower() == "true"

    @property
    def session_file(self) -> Path:
        raw = os.environ.get("SESSION_FILE", "data/session/session_state.json")
        path = _PROJECT_ROOT / raw
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------ #
    # Runtime Environment                                                  #
    # ------------------------------------------------------------------ #
    @property
    def environment(self) -> str:
        return os.environ.get("ENVIRONMENT", "development").lower()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #
    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO").upper()

    @property
    def log_dir(self) -> Path:
        raw = os.environ.get("LOG_DIR", "data/logs")
        path = _PROJECT_ROOT / raw
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------ #
    # Data Directories                                                     #
    # ------------------------------------------------------------------ #
    @property
    def input_dir(self) -> Path:
        raw = os.environ.get("INPUT_DIR", "data/input")
        path = _PROJECT_ROOT / raw
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_dir(self) -> Path:
        raw = os.environ.get("OUTPUT_DIR", "data/output")
        path = _PROJECT_ROOT / raw
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def failed_dir(self) -> Path:
        raw = os.environ.get("FAILED_DIR", "data/failed")
        path = _PROJECT_ROOT / raw
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def screenshot_dir(self) -> Path:
        raw = os.environ.get("SCREENSHOT_DIR", "data/screenshots")
        path = _PROJECT_ROOT / raw
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def report_dir(self) -> Path:
        raw = os.environ.get("REPORT_DIR", "data/report")
        path = _PROJECT_ROOT / raw
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------ #
    # Project Root                                                         #
    # ------------------------------------------------------------------ #
    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    def __repr__(self) -> str:
        """Safe repr — never shows password."""
        return (
            f"EnvironmentConfig("
            f"env={self.environment}, "
            f"url={self.app_url}, "
            f"user={self.app_username}, "
            f"headless={self.browser_headless}"
            f")"
        )


@lru_cache(maxsize=1)
def get_env() -> EnvironmentConfig:
    """
    Cached singleton accessor.

    Usage:
        from config.environment import get_env
        env = get_env()
        url = env.app_url
    """
    return EnvironmentConfig()
