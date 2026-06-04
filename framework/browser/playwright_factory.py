"""
framework/browser/playwright_factory.py
=========================================
Low-level Playwright instance factory.

Responsible for:
- Launching playwright context
- Selecting browser engine (chromium / firefox / webkit)
- Applying browser launch args from config
- No business logic — pure infrastructure
"""

from __future__ import annotations

from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    BrowserType,
    Playwright,
)

from config.settings import get_settings
from framework.core.exception_handler import BrowserError
from framework.core.logger import get_logger

_log = get_logger()


class PlaywrightFactory:
    """
    Manages the raw Playwright and Browser instances.

    Lifecycle:
        factory = PlaywrightFactory()
        await factory.start()
        browser = factory.browser
        ...
        await factory.stop()

    Prefer using BrowserManager which wraps this factory.
    """

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._settings = get_settings()

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Launch Playwright and open the browser."""
        if self._playwright is not None:
            _log.warning("PlaywrightFactory.start() called but already started.")
            return

        _log.info(
            "Starting Playwright | engine={engine} | headless={headless}",
            engine=self._settings.browser_type,
            headless=self._settings.browser_headless,
        )

        try:
            self._playwright = await async_playwright().start()
            browser_type: BrowserType = getattr(
                self._playwright, self._settings.browser_type
            )
            self._browser = await browser_type.launch(
                headless=self._settings.browser_headless,
                slow_mo=self._settings.browser_slow_mo,
                args=self._settings.browser_args,
            )
            _log.info("Browser launched successfully.")
        except Exception as exc:
            raise BrowserError(
                f"Failed to launch {self._settings.browser_type} browser.",
                cause=exc,
            ) from exc

    async def stop(self) -> None:
        """Close browser and stop Playwright cleanly."""
        try:
            if self._browser:
                await self._browser.close()
                _log.info("Browser closed.")
            if self._playwright:
                await self._playwright.stop()
                _log.info("Playwright stopped.")
        except Exception as exc:
            _log.error("Error during Playwright shutdown: {exc}", exc=exc)
        finally:
            self._browser = None
            self._playwright = None

    # ------------------------------------------------------------------ #
    # Browser / Context Factories                                          #
    # ------------------------------------------------------------------ #

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise BrowserError("Browser is not started. Call factory.start() first.")
        return self._browser

    async def new_context(
        self,
        storage_state: Optional[str] = None,
    ) -> BrowserContext:
        """
        Create a new BrowserContext, optionally restoring a session.

        Args:
            storage_state: Path to a JSON session state file. If provided
                           and exists, the session (cookies, localStorage) is
                           restored from this file.

        Returns:
            A configured BrowserContext.
        """
        cfg = self._settings
        viewport = cfg.browser_viewport

        context_kwargs = dict(
            viewport={"width": viewport["width"], "height": viewport["height"]},
        )

        if storage_state:
            from pathlib import Path
            if Path(storage_state).exists():
                context_kwargs["storage_state"] = storage_state
                _log.info("Restoring session from: {path}", path=storage_state)
            else:
                _log.warning(
                    "Session file not found: {path}. Starting fresh session.",
                    path=storage_state,
                )

        try:
            context = await self.browser.new_context(**context_kwargs)
            context.set_default_timeout(cfg.timeout_default)
            context.set_default_navigation_timeout(cfg.timeout_navigation)
            _log.debug("New BrowserContext created.")
            return context
        except Exception as exc:
            raise BrowserError("Failed to create BrowserContext.", cause=exc) from exc
