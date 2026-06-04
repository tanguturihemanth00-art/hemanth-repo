"""
services/auth_service.py
=========================
Authentication service — login flow abstraction.

Handles:
- Fresh login via credentials from .env
- Session restore + validation
- Logout
- Login failure detection
"""

from __future__ import annotations

from playwright.async_api import Page

from config.environment import get_env
from framework.browser.browser_manager import BrowserManager
from framework.core.exception_handler import AuthenticationError, SessionExpiredError
from framework.core.logger import get_logger
from framework.core.wait_utils import wait_for_page_load, wait_for_url_contains

_log = get_logger()


class AuthService:
    """
    Handles all authentication concerns.

    Usage:
        auth = AuthService(browser_manager)

        # Option A: Let auth decide (reuse session or fresh login)
        page = await auth.authenticate(page, post_login_url_fragment="/dashboard")

        # Option B: Force fresh login
        page = await auth.login(page)
    """

    # The URL fragment expected after successful login.
    # Override this in your concrete workflow or subclass.
    POST_LOGIN_URL_FRAGMENT = "/lcoportal/"

    def __init__(self, browser_manager: BrowserManager) -> None:
        self._bm = browser_manager
        self._env = get_env()

    async def authenticate(
        self,
        page: Page,
        post_login_url_fragment: str = POST_LOGIN_URL_FRAGMENT,
    ) -> bool:
        """
        Smart authentication: restore session if available, else login fresh.

        Args:
            page:                    Active Playwright Page.
            post_login_url_fragment: URL fragment that confirms authenticated state.

        Returns:
            True if authenticated successfully.

        Raises:
            AuthenticationError: If authentication fails.
        """
        _log.info("Starting authentication flow...")

        # Try session restore first
        if self._bm.session_manager.should_reuse:
            _log.info("Attempting session restore...")
            session_valid = await self._bm.validate_session(
                page, post_login_url_fragment
            )
            if session_valid:
                _log.info("Session restored successfully. Skipping login.")
                return True
            else:
                _log.warning("Saved session is invalid/expired. Performing fresh login.")
                self._bm.clear_session()

        # Fresh login
        return await self.login(page, post_login_url_fragment)

    async def login(
        self,
        page: Page,
        post_login_url_fragment: str = POST_LOGIN_URL_FRAGMENT,
    ) -> bool:
        """
        Perform a fresh login using credentials from environment.

        ⚠️  This method contains placeholder logic.
        Implement _fill_login_form() in your concrete workflow's LoginPage.

        Args:
            page:                    Active Playwright Page.
            post_login_url_fragment: URL fragment expected after login.

        Returns:
            True if login succeeded.

        Raises:
            AuthenticationError: On login failure.
        """
        _log.info(
            "Logging in as: {user} | URL: {url}",
            user=self._env.app_username,
            url=self._env.app_url,
        )

        try:
            await page.goto(self._env.app_url, wait_until="networkidle")
            await wait_for_page_load(page)

            # --- Delegate to page object --------------------------------
            from pages.login_page import LoginPage
            login_page = LoginPage(page)
            await login_page.perform_login(
                username=self._env.app_username,
                password=self._env.app_password,
                post_login_url_fragment=post_login_url_fragment,
            )
            # ------------------------------------------------------------

            _log.info("Login successful. Saving session...")
            await self._bm.save_session()
            return True

        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError(
                f"Unexpected error during login: {exc}", cause=exc
            ) from exc

    async def logout(self, page: Page) -> None:
        """
        Perform logout and clear saved session.
        Implement logout navigation in your workflow's page objects.
        """
        _log.info("Logging out...")
        self._bm.clear_session()
        # Implement logout navigation here when building specific workflows
        _log.info("Session cleared. Logout complete.")
