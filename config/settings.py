"""
config/settings.py
==================
Loads config.yaml and merges with environment overrides.
Provides a unified Settings object consumed by the entire framework.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from config.environment import get_env

_CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"


def _load_yaml() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {_CONFIG_FILE}. "
            "Ensure the file exists before starting the framework."
        )
    with _CONFIG_FILE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class Settings:
    """
    Merged settings: YAML config + environment overrides.

    yaml config.yaml  → structural/non-secret config
    .env              → secrets + environment-specific overrides

    The .env always wins for overlapping values.
    """

    def __init__(self) -> None:
        self._raw: dict[str, Any] = _load_yaml()
        self._env = get_env()
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Environment variables override yaml defaults."""
        browser = self._raw.setdefault("browser", {})
        browser["headless"] = self._env.browser_headless
        browser["slow_mo"] = self._env.browser_slow_mo
        browser.setdefault("timeout", {})["default"] = self._env.browser_timeout

        session = self._raw.setdefault("session", {})
        session["reuse"] = self._env.session_reuse
        session["storage_path"] = str(self._env.session_file)

        logging_cfg = self._raw.setdefault("logging", {})
        logging_cfg["level"] = self._env.log_level

    # ------------------------------------------------------------------ #
    # Accessors                                                            #
    # ------------------------------------------------------------------ #
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Safe nested key accessor.
        Example: settings.get("browser", "timeout", "navigation")
        """
        node = self._raw
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
            if node is default:
                return default
        return node

    # ---- Browser -------------------------------------------------------
    @property
    def browser_type(self) -> str:
        return self.get("browser", "type", default="chromium")

    @property
    def browser_headless(self) -> bool:
        return bool(self.get("browser", "headless", default=False))

    @property
    def browser_slow_mo(self) -> int:
        return int(self.get("browser", "slow_mo", default=0))

    @property
    def browser_viewport(self) -> dict[str, int]:
        return self.get("browser", "viewport", default={"width": 1920, "height": 1080})

    @property
    def timeout_default(self) -> int:
        return int(self.get("browser", "timeout", "default", default=30000))

    @property
    def timeout_navigation(self) -> int:
        return int(self.get("browser", "timeout", "navigation", default=60000))

    @property
    def timeout_element(self) -> int:
        return int(self.get("browser", "timeout", "element", default=15000))

    @property
    def browser_args(self) -> list[str]:
        return self.get("browser", "args", default=[])

    # ---- Session -------------------------------------------------------
    @property
    def session_reuse(self) -> bool:
        return bool(self.get("session", "reuse", default=True))

    @property
    def session_storage_path(self) -> str:
        return str(self.get("session", "storage_path", default="data/session/session_state.json"))

    # ---- Logging -------------------------------------------------------
    @property
    def log_level(self) -> str:
        return str(self.get("logging", "level", default="INFO"))

    @property
    def log_rotation(self) -> str:
        return str(self.get("logging", "rotation", default="10 MB"))

    @property
    def log_retention(self) -> str:
        return str(self.get("logging", "retention", default="30 days"))

    @property
    def log_format(self) -> str:
        return str(self.get("logging", "format", default="{time} | {level} | {message}"))

    @property
    def log_mask_fields(self) -> list[str]:
        return self.get("logging", "mask_fields", default=["password", "token", "secret"])

    # ---- Retry ---------------------------------------------------------
    @property
    def retry_max_attempts(self) -> int:
        return int(self.get("retry", "max_attempts", default=3))

    @property
    def retry_wait_min(self) -> float:
        return float(self.get("retry", "wait_min", default=1))

    @property
    def retry_wait_max(self) -> float:
        return float(self.get("retry", "wait_max", default=10))

    @property
    def retry_multiplier(self) -> float:
        return float(self.get("retry", "multiplier", default=2))

    # ---- Excel ---------------------------------------------------------
    @property
    def excel_engine(self) -> str:
        return str(self.get("excel", "engine", default="openpyxl"))

    @property
    def excel_skip_empty_rows(self) -> bool:
        return bool(self.get("excel", "skip_empty_rows", default=True))

    @property
    def excel_max_rows(self) -> int:
        return int(self.get("excel", "max_rows", default=10000))

    # ---- Workflow ------------------------------------------------------
    @property
    def workflow_continue_on_failure(self) -> bool:
        return bool(self.get("workflow", "continue_on_failure", default=True))

    @property
    def workflow_screenshot_on_failure(self) -> bool:
        return bool(self.get("workflow", "screenshot_on_failure", default=True))

    @property
    def workflow_screenshot_on_success(self) -> bool:
        return bool(self.get("workflow", "screenshot_on_success", default=False))

    @property
    def workflow_row_delay_ms(self) -> int:
        return int(self.get("workflow", "row_delay_ms", default=500))

    def __repr__(self) -> str:
        return (
            f"Settings(env={self._env.environment}, "
            f"browser={self.browser_type}, "
            f"headless={self.browser_headless})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached singleton accessor.

    Usage:
        from config.settings import get_settings
        cfg = get_settings()
        timeout = cfg.timeout_navigation
    """
    return Settings()
