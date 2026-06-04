"""
pages/login_page.py
=====================
LoginPage — SSC LCO Portal login implementation.
URL: https://lcoportal.sscnxtdigital.in/

Selectors discovered by live inspection of the portal.
Credentials are always read from .env — never hardcoded.
"""

from __future__ import annotations

from playwright.async_api import Page

from pages.base_page import BasePage
from framework.core.exception_handler import AuthenticationError
from framework.core.logger import get_logger

_log = get_logger()


class LoginPage(BasePage):
    """
    Page object for the SSC LCO Portal login page.

    Usage:
        login = LoginPage(page)
        await login.perform_login(username=env.app_username, password=env.app_password)
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------ #
    # Locators — discovered from live portal inspection                   #
    # ------------------------------------------------------------------ #

    @property
    def _fr_code_input(self):
        # Label: "FR CODE", placeholder: "eg : FR5125"
        return self.page.get_by_placeholder("eg : FR5125")

    @property
    def _password_input(self):
        # Label: "PASSWORD", placeholder: "*******"
        return self.page.get_by_placeholder("*******")

    @property
    def _login_button(self):
        # Blue "Login" button
        return self.page.get_by_role("button", name="Login")

    @property
    def _error_alert(self):
        # Common error toast/alert after failed login
        return self.page.locator(".alert, .error-msg, [class*='error'], [class*='alert']").first

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    async def enter_fr_code(self, fr_code: str) -> None:
        await self.safe_fill(
            self._fr_code_input,
            fr_code,
            label="FR Code field",
        )

    async def enter_password(self, password: str) -> None:
        await self.safe_fill(
            self._password_input,
            password,
            label="Password field",
        )

    async def click_login(self) -> None:
        await self.safe_click(self._login_button, label="Login button")

    # ------------------------------------------------------------------ #
    # High-Level Login                                                     #
    # ------------------------------------------------------------------ #

    async def perform_login(self, username: str, password: str, post_login_url_fragment: str = "/lcoportal/") -> None:
        """
        Complete login: enter FR Code → enter Password → click Login.

        Args:
            username: FR Code from APP_USERNAME in .env
            password: Password from APP_PASSWORD in .env
            post_login_url_fragment: URL fragment to wait for after login

        Raises:
            AuthenticationError: If login fails (error visible or redirect to login)
        """
        _log.info("Entering FR Code: {user}", user=username)
        await self.enter_fr_code(username)
        await self.enter_password(password)
        await self.click_login()

        # Wait for the URL to change indicating success, or check for failure on the current page
        try:
            from framework.core.wait_utils import wait_for_url_contains
            await wait_for_url_contains(self._page, post_login_url_fragment, timeout=15_000)
            _log.info("Login successful. Redirected to {url}", url=self.current_url)
            return
        except Exception:
            # If it didn't redirect, it likely failed.
            pass

        # Check if still on login page (login failed)
        if await self.safe_is_visible(self._fr_code_input, timeout=3_000):
            # Try to read error message
            error_text = ""
            if await self.safe_is_visible(self._error_alert, timeout=2_000):
                error_text = await self.safe_get_text(self._error_alert, label="Error alert")
            raise AuthenticationError(
                f"Login failed — still on login page. "
                f"Error: '{error_text}' | "
                f"Check FR Code and Password in .env"
            )

        _log.info("Login successful. Current URL: {url}", url=self.current_url)

    async def is_on_login_page(self) -> bool:
        return await self.safe_is_visible(self._fr_code_input, timeout=3_000)
