"""
framework/core/wait_utils.py
=============================
Smart, reusable Playwright wait utilities.

All waits use explicit conditions — no time.sleep() allowed.
Wraps Playwright's built-in locator waits with enhanced logging and error handling.
"""

from __future__ import annotations

import asyncio
from typing import Callable, Literal, Optional

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

from framework.core.logger import get_logger
from framework.core.exception_handler import ElementNotFoundError, PageLoadError

_log = get_logger()


# ------------------------------------------------------------------ #
# Network / Load State Waits                                           #
# ------------------------------------------------------------------ #

async def wait_for_page_load(
    page: Page,
    state: Literal["load", "domcontentloaded", "networkidle"] = "networkidle",
    timeout: int = 60_000,
) -> None:
    """
    Wait until the page reaches the specified load state.

    Args:
        page:    Playwright Page instance.
        state:   Load state to wait for.
        timeout: Max wait time in milliseconds.
    """
    try:
        _log.debug("Waiting for page load state: {state}", state=state)
        await page.wait_for_load_state(state, timeout=timeout)
        _log.debug("Page reached load state: {state}", state=state)
    except PlaywrightTimeoutError as exc:
        raise PageLoadError(
            f"Page did not reach '{state}' state within {timeout}ms",
            cause=exc,
        ) from exc


async def wait_for_url_contains(
    page: Page,
    url_fragment: str,
    timeout: int = 30_000,
) -> None:
    """
    Wait until the current URL contains a specific fragment.
    Useful for confirming navigation after a click.
    """
    try:
        _log.debug("Waiting for URL to contain: {frag}", frag=url_fragment)
        await page.wait_for_url(f"**{url_fragment}**", timeout=timeout)
        _log.debug("URL now contains: {frag}", frag=url_fragment)
    except PlaywrightTimeoutError as exc:
        raise PageLoadError(
            f"URL did not contain '{url_fragment}' within {timeout}ms. "
            f"Current URL: {page.url}",
            cause=exc,
        ) from exc


# ------------------------------------------------------------------ #
# Element Visibility / State Waits                                     #
# ------------------------------------------------------------------ #

async def wait_for_element(
    locator: Locator,
    state: Literal["visible", "hidden", "attached", "detached"] = "visible",
    timeout: int = 15_000,
    label: str = "element",
) -> None:
    """
    Wait for a locator to reach a specific state.

    Args:
        locator: Playwright Locator.
        state:   State to wait for.
        timeout: Max wait in milliseconds.
        label:   Human-readable name for logging.
    """
    try:
        _log.debug("Waiting for [{label}] to be {state}", label=label, state=state)
        await locator.wait_for(state=state, timeout=timeout)
        _log.debug("[{label}] is now {state}", label=label, state=state)
    except PlaywrightTimeoutError as exc:
        raise ElementNotFoundError(
            f"Element '{label}' did not reach state '{state}' within {timeout}ms",
            cause=exc,
        ) from exc


async def wait_for_element_enabled(
    locator: Locator,
    timeout: int = 15_000,
    label: str = "element",
) -> None:
    """Wait until an element is both visible and enabled (not disabled)."""
    await wait_for_element(locator, state="visible", timeout=timeout, label=label)
    try:
        await locator.wait_for(state="visible", timeout=timeout)
        # Playwright doesn't have wait_for_enabled — poll via is_enabled
        deadline = asyncio.get_event_loop().time() + (timeout / 1000)
        while asyncio.get_event_loop().time() < deadline:
            if await locator.is_enabled():
                _log.debug("[{label}] is enabled", label=label)
                return
            await asyncio.sleep(0.2)
        raise ElementNotFoundError(
            f"Element '{label}' was not enabled within {timeout}ms"
        )
    except PlaywrightTimeoutError as exc:
        raise ElementNotFoundError(
            f"Element '{label}' not enabled within {timeout}ms",
            cause=exc,
        ) from exc


# ------------------------------------------------------------------ #
# Text / Content Waits                                                  #
# ------------------------------------------------------------------ #

async def wait_for_text_in_element(
    locator: Locator,
    expected_text: str,
    timeout: int = 15_000,
    label: str = "element",
) -> None:
    """
    Wait until an element contains specific text.
    Case-insensitive, strips whitespace.
    """
    try:
        _log.debug(
            "Waiting for text '{text}' in [{label}]",
            text=expected_text,
            label=label,
        )
        await locator.filter(has_text=expected_text).wait_for(
            state="visible", timeout=timeout
        )
        _log.debug("Text '{text}' found in [{label}]", text=expected_text, label=label)
    except PlaywrightTimeoutError as exc:
        raise ElementNotFoundError(
            f"Text '{expected_text}' not found in '{label}' within {timeout}ms",
            cause=exc,
        ) from exc


async def wait_for_toast_or_alert(
    page: Page,
    timeout: int = 10_000,
) -> Optional[str]:
    """
    Try to capture a toast notification or alert text.
    Returns text content if found, None otherwise.
    Non-fatal — does not raise on timeout.
    """
    common_selectors = [
        "[role='alert']",
        "[class*='toast']",
        "[class*='notification']",
        "[class*='snackbar']",
        "[class*='message']",
        "[class*='alert']",
    ]
    for selector in common_selectors:
        try:
            locator = page.locator(selector)
            await locator.wait_for(state="visible", timeout=timeout // len(common_selectors))
            text = await locator.text_content() or ""
            _log.debug("Toast/alert captured: '{text}'", text=text.strip())
            return text.strip()
        except PlaywrightTimeoutError:
            continue
    return None


# ------------------------------------------------------------------ #
# Conditional Wait                                                      #
# ------------------------------------------------------------------ #

async def wait_until(
    condition: Callable[[], bool],
    timeout: int = 15_000,
    poll_interval: float = 0.3,
    label: str = "condition",
) -> None:
    """
    Poll a synchronous predicate until it returns True or timeout.

    Args:
        condition:     Callable returning bool.
        timeout:       Max wait in milliseconds.
        poll_interval: Polling interval in seconds.
        label:         Descriptive label for logging.
    """
    deadline = asyncio.get_event_loop().time() + (timeout / 1000)
    while asyncio.get_event_loop().time() < deadline:
        if condition():
            _log.debug("Condition '{label}' met", label=label)
            return
        await asyncio.sleep(poll_interval)

    raise ElementNotFoundError(
        f"Condition '{label}' not met within {timeout}ms"
    )
