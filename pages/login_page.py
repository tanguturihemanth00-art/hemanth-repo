"""
pages/login_page.py
=====================
LoginPage — handles website authentication UI.

⚠️  IMPLEMENTATION REQUIRED:
    Replace the placeholder locators with real locators from your target website.
    Use the locator priority: role > label > data-testid > css > xpath

    Steps to implement:
    1. Inspect the login page of your website
    2. Find the username/FR-code field locator
    3. Find the password field locator
    4. Find the submit/login button locator
    5. Find the post-login success indicator

    Never hardcode credentials here — always use:
        from config.environment import get_env
        env = get_env()
        username = env.app_username
        password = env.app_password
"""

from __future__ import annotations

from playwright.async_api import Page

from pages.base_page import BasePage
from framework.core.exception_handler import AuthenticationError
from framework.core.logger import get_logger

_log = get_logger()


class LoginPage(BasePage):
    """
    Page object for the login/authentication page.

    Usage:
        login = LoginPage(page)
        await login.perform_login(username=env.app_username, password=env.app_password)
        assert login.url_contains("/dashboard"), "Login failed"
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------ #
    # Locators (implement with real selectors from your website)          #
    # ------------------------------------------------------------------ #
    # Priority: role > label > data-testid > css > xpath

    @property
    def _username_input(self):
        # ✏️  Replace with actual locator — examples:
        # return self.page.get_by_label("Username")
        # return self.page.get_by_label("FR Code")
        # return self.page.get_by_placeholder("Enter your username")
        # return self.page.locator("[data-testid='username-input']")
        # return self.page.locator("input[name='username']")
        return self.page.get_by_label("Username")  # ← REPLACE THIS

    @property
    def _password_input(self):
        # ✏️  Replace with actual locator — examples:
        # return self.page.get_by_label("Password")
        # return self.page.locator("[data-testid='password-input']")
        # return self.page.locator("input[type='password']")
        return self.page.get_by_label("Password")  # ← REPLACE THIS

    @property
    def _login_button(self):
        # ✏️  Replace with actual locator — examples:
        # return self.page.get_by_role("button", name="Login")
        # return self.page.get_by_role("button", name="Sign In")
        # return self.page.locator("[data-testid='login-btn']")
        return self.page.get_by_role("button", name="Login")  # ← REPLACE THIS

    @property
    def _error_message(self):
        # ✏️  Replace with actual error indicator locator
        # return self.page.locator("[class*='error-message']")
        # return self.page.get_by_role("alert")
        return self.page.get_by_role("alert")  # ← REPLACE THIS

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    async def enter_username(self, username: str) -> None:
        await self.safe_fill(
            self._username_input,
            username,
            label="Username / FR Code field",
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
    # High-Level                                                           #
    # ------------------------------------------------------------------ #

    async def perform_login(self, username: str, password: str) -> None:
        """
        Complete login sequence: fill username → fill password → click login.

        Args:
            username: FR code or username from environment config.
            password: Password from environment config.

        Raises:
            AuthenticationError: If login fails (error message visible after submit).
        """
        _log.info("Filling login form | user={user}", user=username)

        await self.enter_username(username)
        await self.enter_password(password)
        await self.click_login()

        await self.wait_for_network_idle()

        # Check for login error message
        if await self.safe_is_visible(self._error_message, timeout=3_000):
            error_text = await self.safe_get_text(self._error_message, label="Error message")
            raise AuthenticationError(
                f"Login failed — error message on page: '{error_text}'"
            )

        _log.info("Login form submitted successfully.")

    async def is_on_login_page(self) -> bool:
        """Check if we are currently on the login page."""
        return await self.safe_is_visible(self._username_input, timeout=3_000)
