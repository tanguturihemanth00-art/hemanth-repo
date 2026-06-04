"""
framework/core/retry_handler.py
================================
Enterprise retry framework built on Tenacity.

Provides:
- Decorator for arbitrary callables
- UI-specific async retry wrapper for Playwright actions
- Configurable exponential backoff per call or globally from settings
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, Optional, Tuple, Type

from tenacity import (
    AsyncRetrying,
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)
from tenacity.stop import stop_base
from tenacity.wait import wait_base

from framework.core.logger import get_logger

_log = get_logger()


# ------------------------------------------------------------------ #
# Default Retry Exceptions                                             #
# ------------------------------------------------------------------ #

# Add more playwright / network exceptions here as the project evolves
_DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
)


# ------------------------------------------------------------------ #
# Synchronous Retry Decorator                                          #
# ------------------------------------------------------------------ #

def with_retry(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None,
    multiplier: Optional[float] = None,
    retry_on: Tuple[Type[Exception], ...] = _DEFAULT_RETRY_EXCEPTIONS,
    reraise: bool = True,
):
    """
    Synchronous retry decorator with exponential backoff.

    Args:
        max_attempts: Override default max attempts from settings.
        wait_min:     Minimum wait between retries (seconds).
        wait_max:     Maximum wait between retries (seconds).
        multiplier:   Backoff multiplier.
        retry_on:     Exception types to retry on.
        reraise:      If True, re-raises the last exception after all attempts.

    Usage:
        @with_retry(max_attempts=3)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from config.settings import get_settings
            cfg = get_settings()

            attempts = max_attempts or cfg.retry_max_attempts
            w_min = wait_min or cfg.retry_wait_min
            w_max = wait_max or cfg.retry_wait_max
            mult = multiplier or cfg.retry_multiplier

            for attempt in Retrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential(multiplier=mult, min=w_min, max=w_max),
                retry=retry_if_exception_type(retry_on),
                reraise=reraise,
                before_sleep=lambda rs: _log.warning(
                    "Retry {attempt}/{max} for {fn} — {exc}",
                    attempt=rs.attempt_number,
                    max=attempts,
                    fn=func.__name__,
                    exc=rs.outcome.exception(),
                ),
            ):
                with attempt:
                    return func(*args, **kwargs)

        return wrapper
    return decorator


# ------------------------------------------------------------------ #
# Asynchronous Retry Decorator                                         #
# ------------------------------------------------------------------ #

def with_async_retry(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None,
    multiplier: Optional[float] = None,
    retry_on: Tuple[Type[Exception], ...] = _DEFAULT_RETRY_EXCEPTIONS,
    reraise: bool = True,
):
    """
    Async retry decorator — for Playwright coroutines.

    Usage:
        @with_async_retry(max_attempts=3)
        async def click_submit(page):
            await page.get_by_role("button", name="Submit").click()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            from config.settings import get_settings
            cfg = get_settings()

            attempts = max_attempts or cfg.retry_max_attempts
            w_min = wait_min or cfg.retry_wait_min
            w_max = wait_max or cfg.retry_wait_max
            mult = multiplier or cfg.retry_multiplier

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential(multiplier=mult, min=w_min, max=w_max),
                retry=retry_if_exception_type(retry_on),
                reraise=reraise,
                before_sleep=lambda rs: _log.warning(
                    "Async retry {attempt}/{max} for {fn} — {exc}",
                    attempt=rs.attempt_number,
                    max=attempts,
                    fn=func.__name__,
                    exc=rs.outcome.exception(),
                ),
            ):
                with attempt:
                    return await func(*args, **kwargs)

        return wrapper
    return decorator


# ------------------------------------------------------------------ #
# Inline Retry Helper (no decorator needed)                            #
# ------------------------------------------------------------------ #

async def retry_action(
    action: Callable,
    *args,
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    retry_on: Tuple[Type[Exception], ...] = _DEFAULT_RETRY_EXCEPTIONS,
    label: str = "action",
    **kwargs,
) -> Any:
    """
    Execute an async callable with retries without needing a decorator.

    Args:
        action:       Async callable to execute.
        *args:        Positional arguments for the callable.
        max_attempts: Max number of total attempts.
        delay_seconds: Fixed delay between attempts (no backoff).
        retry_on:     Exception types that trigger a retry.
        label:        Human-readable label for log output.
        **kwargs:     Keyword arguments for the callable.

    Returns:
        The return value of the callable.

    Raises:
        The last exception if all attempts fail.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await action(*args, **kwargs)
        except retry_on as exc:
            last_exc = exc
            _log.warning(
                "Attempt {attempt}/{max} failed for '{label}': {exc}",
                attempt=attempt,
                max=max_attempts,
                label=label,
                exc=exc,
            )
            if attempt < max_attempts:
                await asyncio.sleep(delay_seconds)

    raise last_exc  # type: ignore[misc]
