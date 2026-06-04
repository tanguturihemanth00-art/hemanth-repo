"""
framework/browser/session_manager.py
======================================
Handles browser session persistence.

Responsibilities:
- Save browser session (cookies + localStorage) to disk
- Load existing session state for reuse
- Validate session health after restore
- Clear corrupted/expired sessions

Session file format: Playwright storage_state JSON
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page

from config.settings import get_settings
from framework.core.exception_handler import SessionError, SessionExpiredError
from framework.core.logger import get_logger

_log = get_logger()


class SessionManager:
    """
    Manages Playwright session state persistence.

    Usage:
        sm = SessionManager()
        await sm.save(context)           # after successful login
        path = sm.session_path           # pass to PlaywrightFactory.new_context()
        await sm.validate(page, url)     # after restoring session
        sm.clear()                       # on logout or session expiry
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session_path = Path(self._settings.session_storage_path)
        self._session_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def session_path(self) -> str:
        """Absolute path to the session state JSON file."""
        return str(self._session_path)

    @property
    def session_exists(self) -> bool:
        """True if a saved session file is present and non-empty."""
        return self._session_path.exists() and self._session_path.stat().st_size > 0

    @property
    def should_reuse(self) -> bool:
        """True if config says reuse AND a session file exists."""
        return self._settings.session_reuse and self.session_exists

    # ------------------------------------------------------------------ #
    # Save                                                                 #
    # ------------------------------------------------------------------ #

    async def save(self, context: BrowserContext) -> None:
        """
        Serialize the current browser session to disk.
        Call this immediately after successful authentication.

        Args:
            context: The active BrowserContext after login.
        """
        try:
            await context.storage_state(path=self.session_path)
            _log.info("Session saved to: {path}", path=self.session_path)
        except Exception as exc:
            raise SessionError("Failed to save session state.", cause=exc) from exc

    # ------------------------------------------------------------------ #
    # Validate                                                             #
    # ------------------------------------------------------------------ #

    async def validate(self, page: Page, expected_url_fragment: str) -> bool:
        """
        Validate that a restored session is still alive.

        Strategy: Navigate to the app URL and check if we land on the
        expected authenticated page (not redirected to login).

        Args:
            page:                  Active Playwright Page.
            expected_url_fragment: Fragment that should be in the URL if logged in.

        Returns:
            True if session is valid, False if expired.
        """
        from config.environment import get_env
        env = get_env()

        try:
            _log.info("Validating restored session...")
            await page.goto(env.app_url, wait_until="networkidle", timeout=30_000)
            current_url = page.url

            if expected_url_fragment.lower() in current_url.lower():
                _log.info("Session is valid. URL: {url}", url=current_url)
                return True
            else:
                _log.warning(
                    "Session expired or invalid. Expected '{fragment}' in URL, "
                    "got: {url}",
                    fragment=expected_url_fragment,
                    url=current_url,
                )
                return False

        except Exception as exc:
            _log.error("Session validation failed: {exc}", exc=exc)
            return False

    # ------------------------------------------------------------------ #
    # Clear                                                                #
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        """Delete the saved session file. Forces fresh login next run."""
        if self._session_path.exists():
            self._session_path.unlink()
            _log.info("Session file cleared: {path}", path=self.session_path)
        else:
            _log.debug("No session file to clear.")

    # ------------------------------------------------------------------ #
    # Introspect                                                           #
    # ------------------------------------------------------------------ #

    def get_session_info(self) -> Optional[dict]:
        """
        Load and return session metadata without launching a browser.
        Useful for debugging session contents.
        """
        if not self.session_exists:
            return None
        try:
            with self._session_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            cookie_count = len(data.get("cookies", []))
            origin_count = len(data.get("origins", []))
            return {
                "path": self.session_path,
                "cookie_count": cookie_count,
                "origin_count": origin_count,
            }
        except Exception as exc:
            _log.warning("Could not read session info: {exc}", exc=exc)
            return None
