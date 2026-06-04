"""
framework/browser/browser_manager.py
======================================
High-level browser lifecycle orchestrator.

Composes PlaywrightFactory + SessionManager into a single entry point
for workflows. Handles:
- Browser start/stop
- Context creation (with/without session restore)
- Page lifecycle
- Context-level timeout defaults
- Crash recovery stubs
"""

from __future__ import annotations

from typing import Optional

from playwright.async_api import BrowserContext, Page

from config.settings import get_settings
from framework.browser.playwright_factory import PlaywrightFactory
from framework.browser.session_manager import SessionManager
from framework.core.exception_handler import BrowserError
from framework.core.logger import get_logger

_log = get_logger()


class BrowserManager:
    """
    Unified browser lifecycle manager for workflow use.

    Usage (async context manager — preferred):
        async with BrowserManager() as bm:
            page = await bm.new_page()
            await page.goto("https://...")

    Usage (manual):
        bm = BrowserManager()
        await bm.start()
        page = await bm.new_page()
        ...
        await bm.stop()
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._factory = PlaywrightFactory()
        self._session = SessionManager()
        self._context: Optional[BrowserContext] = None

    # ------------------------------------------------------------------ #
    # Async Context Manager                                                #
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "BrowserManager":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def start(self, restore_session: Optional[bool] = None) -> None:
        """
        Launch browser and create a new BrowserContext.

        Args:
            restore_session: Override config session.reuse setting.
                             If None, uses config value.
        """
        await self._factory.start()

        use_session = (
            restore_session
            if restore_session is not None
            else self._session.should_reuse
        )

        storage_state = self._session.session_path if use_session else None
        self._context = await self._factory.new_context(storage_state=storage_state)

        _log.info(
            "BrowserManager started | session_restored={restored}",
            restored=bool(storage_state and use_session),
        )

    async def stop(self) -> None:
        """Teardown context and browser cleanly."""
        try:
            if self._context:
                await self._context.close()
                _log.info("BrowserContext closed.")
        except Exception as exc:
            _log.error("Error closing context: {exc}", exc=exc)
        finally:
            self._context = None

        await self._factory.stop()

    # ------------------------------------------------------------------ #
    # Page Management                                                      #
    # ------------------------------------------------------------------ #

    async def new_page(self) -> Page:
        """
        Open and return a new Page in the active context.

        Returns:
            A Playwright Page with default timeouts applied.

        Raises:
            BrowserError: If the context is not yet initialised.
        """
        if self._context is None:
            raise BrowserError(
                "BrowserManager context not initialized. Call start() first."
            )
        try:
            page = await self._context.new_page()
            _log.debug("New page opened.")
            return page
        except Exception as exc:
            raise BrowserError("Failed to open new page.", cause=exc) from exc

    async def close_page(self, page: Page) -> None:
        """Safely close a page, suppressing already-closed errors."""
        try:
            if not page.is_closed():
                await page.close()
                _log.debug("Page closed.")
        except Exception as exc:
            _log.warning("Error closing page (may already be closed): {exc}", exc=exc)

    # ------------------------------------------------------------------ #
    # Session Helpers                                                      #
    # ------------------------------------------------------------------ #

    async def save_session(self) -> None:
        """
        Persist current browser session to disk.
        Call immediately after successful login.
        """
        if self._context is None:
            raise BrowserError("Cannot save session — no active context.")
        await self._session.save(self._context)

    async def validate_session(self, page: Page, expected_url_fragment: str) -> bool:
        """
        Validate that the current session is still authenticated.

        Returns:
            True if session is valid, False if it needs re-authentication.
        """
        return await self._session.validate(page, expected_url_fragment)

    def clear_session(self) -> None:
        """Delete the saved session file to force fresh login next run."""
        self._session.clear()

    # ------------------------------------------------------------------ #
    # Crash Recovery (stub for future implementation)                     #
    # ------------------------------------------------------------------ #

    async def restart_on_crash(self) -> Page:
        """
        Recovery stub: restart browser and return a fresh page.
        Called by the workflow orchestrator on BrowserCrashError detection.

        TODO: Implement crash detection via page.on('crash') event listener.
        """
        _log.warning("Browser crash recovery initiated. Restarting browser...")
        await self.stop()
        await self.start(restore_session=False)
        return await self.new_page()

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def session_manager(self) -> SessionManager:
        return self._session

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context
