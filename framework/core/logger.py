"""
framework/core/logger.py
========================
Enterprise logging built on Loguru.

Features:
- Structured console + rotating file output
- Execution ID and Row ID bound to every log line
- Automatic sensitive data masking
- Thread-safe singleton
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from loguru import logger as _loguru_logger

from config.constants import SENSITIVE_FIELDS, MASKED_VALUE


# ------------------------------------------------------------------ #
# Sensitive Data Masking Filter                                        #
# ------------------------------------------------------------------ #

_MASK_PATTERN = re.compile(
    r"(" + "|".join(re.escape(f) for f in SENSITIVE_FIELDS) + r")"
    r"([=:\s\"']+)([^\s,\"'\}\]]+)",
    re.IGNORECASE,
)


def _mask_sensitive(message: str) -> str:
    """Replace secret values with MASKED_VALUE in log output."""
    return _MASK_PATTERN.sub(rf"\1\2{MASKED_VALUE}", message)


class _MaskingFilter:
    def __call__(self, record: dict) -> bool:
        record["message"] = _mask_sensitive(record["message"])
        return True


# ------------------------------------------------------------------ #
# Logger Factory                                                       #
# ------------------------------------------------------------------ #

class FrameworkLogger:
    """
    Singleton wrapper around Loguru.

    Usage:
        from framework.core.logger import get_logger
        log = get_logger()
        log.info("Processing row {row}", row=42)

    Contextual binding:
        row_log = log.bind(exec_id="RUN-001", row_id="ROW_3")
        row_log.info("Navigating to form")
    """

    _initialised: bool = False

    def __init__(self) -> None:
        if not FrameworkLogger._initialised:
            self._setup()
            FrameworkLogger._initialised = True

    def _setup(self) -> None:
        from config.settings import get_settings
        from config.environment import get_env

        cfg = get_settings()
        env = get_env()

        _loguru_logger.remove()  # Remove default handler

        log_format = cfg.log_format
        masking_filter = _MaskingFilter()

        # ---- Console Handler ----------------------------------------
        if cfg.get("logging", "console_enabled", default=True):
            _loguru_logger.add(
                sys.stdout,
                format=log_format,
                level=cfg.log_level,
                colorize=True,
                filter=masking_filter,
                enqueue=True,
            )

        # ---- Rotating File Handler ----------------------------------
        if cfg.get("logging", "file_enabled", default=True):
            log_dir: Path = env.log_dir
            log_file = log_dir / "framework_{time:YYYY-MM-DD}.log"

            _loguru_logger.add(
                str(log_file),
                format=log_format,
                level=cfg.log_level,
                rotation=cfg.log_rotation,
                retention=cfg.log_retention,
                compression="zip",
                filter=masking_filter,
                enqueue=True,
                encoding="utf-8",
            )

        # Bind default extra fields to avoid KeyError in format string
        _loguru_logger.configure(
            extra={"exec_id": "INIT", "row_id": "-"}
        )

    @property
    def logger(self):
        return _loguru_logger


@lru_cache(maxsize=1)
def _get_framework_logger() -> FrameworkLogger:
    return FrameworkLogger()


def get_logger(exec_id: str = "INIT", row_id: str = "-"):
    """
    Get a logger instance optionally bound to an execution + row context.

    Args:
        exec_id: Unique identifier for the current execution run.
        row_id:  Current row being processed (e.g. 'ROW_5').

    Returns:
        A Loguru logger with bound context.
    """
    framework_logger = _get_framework_logger()
    return framework_logger.logger.bind(exec_id=exec_id, row_id=row_id)
