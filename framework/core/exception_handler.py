"""
framework/core/exception_handler.py
=====================================
Centralized exception taxonomy and safe execution helpers.

Defines a hierarchy of typed exceptions so the framework can distinguish:
  - Configuration errors  (fix before run)
  - Authentication errors (may be retryable)
  - Navigation errors     (retryable)
  - Element errors        (retryable with different strategy)
  - Validation errors     (non-retryable, row-level)
  - Data errors           (non-retryable, input problems)
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, Optional, Type

from framework.core.logger import get_logger

_log = get_logger()


# ================================================================== #
# Exception Hierarchy                                                  #
# ================================================================== #

class FrameworkError(Exception):
    """Root exception for all framework errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        base = super().__str__()
        if self.cause:
            return f"{base} | Caused by: {type(self.cause).__name__}: {self.cause}"
        return base


# ---- Configuration Errors ------------------------------------------
class ConfigurationError(FrameworkError):
    """Raised when framework configuration is invalid or missing."""


class EnvironmentError(FrameworkError):  # noqa: A001 (shadows builtin intentionally)
    """Raised when a required environment variable is missing."""


# ---- Browser Errors ------------------------------------------------
class BrowserError(FrameworkError):
    """Raised when browser lifecycle operations fail."""


class BrowserCrashError(BrowserError):
    """Raised when the browser process crashes unexpectedly."""


class SessionError(FrameworkError):
    """Raised when session cannot be loaded or stored."""


# ---- Authentication Errors -----------------------------------------
class AuthenticationError(FrameworkError):
    """Raised when login or authentication fails."""


class SessionExpiredError(AuthenticationError):
    """Raised when a reused session has expired."""


# ---- Navigation Errors ---------------------------------------------
class NavigationError(FrameworkError):
    """Raised when page navigation fails or times out."""


class PageLoadError(NavigationError):
    """Raised when a page does not load within the expected timeout."""


# ---- Element / UI Errors -------------------------------------------
class ElementError(FrameworkError):
    """Raised when a UI element interaction fails."""


class ElementNotFoundError(ElementError):
    """Raised when a required element cannot be located."""


class ElementNotInteractableError(ElementError):
    """Raised when an element is present but cannot be interacted with."""


class PopupInterruptionError(ElementError):
    """Raised when an unexpected popup/dialog blocks automation."""


# ---- Validation Errors ---------------------------------------------
class ValidationError(FrameworkError):
    """Raised when business or data validation fails."""


class RowValidationError(ValidationError):
    """Raised when an Excel row fails field-level validation."""


# ---- Data / Excel Errors -------------------------------------------
class DataError(FrameworkError):
    """Raised for Excel read/write or data processing failures."""


class MissingColumnError(DataError):
    """Raised when a required Excel column is not found."""


class DuplicateRowError(DataError):
    """Raised when duplicate rows are detected in the input."""


# ---- Workflow Errors -----------------------------------------------
class WorkflowError(FrameworkError):
    """Raised for workflow-level orchestration failures."""


# ================================================================== #
# Safe Execution Helpers                                               #
# ================================================================== #

def safe_execute(
    func: Callable,
    *args,
    error_message: str = "Operation failed",
    reraise: bool = True,
    default: Any = None,
    **kwargs,
) -> Any:
    """
    Execute a synchronous callable, catching and logging all exceptions.

    Args:
        func:          Callable to execute.
        error_message: Context message for logging on failure.
        reraise:       If True, re-raises the caught exception.
        default:       Return value when reraise=False and an error occurs.

    Returns:
        Result of func(*args, **kwargs) or default on error.
    """
    try:
        return func(*args, **kwargs)
    except FrameworkError:
        raise  # Always propagate typed framework errors
    except Exception as exc:
        _log.error(
            "{msg} | Exception: {exc_type}: {exc}",
            msg=error_message,
            exc_type=type(exc).__name__,
            exc=exc,
        )
        _log.debug("Traceback:\n{tb}", tb=traceback.format_exc())
        if reraise:
            raise WorkflowError(error_message, cause=exc) from exc
        return default


async def safe_execute_async(
    func: Callable,
    *args,
    error_message: str = "Async operation failed",
    reraise: bool = True,
    default: Any = None,
    **kwargs,
) -> Any:
    """
    Execute an async callable, catching and logging all exceptions.
    Same contract as safe_execute but for coroutines.
    """
    try:
        return await func(*args, **kwargs)
    except FrameworkError:
        raise
    except Exception as exc:
        _log.error(
            "{msg} | Exception: {exc_type}: {exc}",
            msg=error_message,
            exc_type=type(exc).__name__,
            exc=exc,
        )
        _log.debug("Traceback:\n{tb}", tb=traceback.format_exc())
        if reraise:
            raise WorkflowError(error_message, cause=exc) from exc
        return default
