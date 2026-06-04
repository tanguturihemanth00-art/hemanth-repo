"""
pages/base_page.py
===================
BasePage — foundation for all Page Object Model classes.

Provides:
- safe_click()      — click with retry and error handling
- safe_fill()       — fill with clear + retry
- safe_select()     — dropdown selection
- safe_wait()       — explicit element wait
- safe_get_text()   — safe text extraction
- safe_is_visible() — non-throwing visibility check
- screenshot()      — context-aware screenshot

Locator Priority (enforced across all page objects):
  1. get_by_role()
  2. get_by_label()
  3. data-testid attribute
  4. CSS selector
  5. XPath (last resort only)
"""

from __future__ import annotations

from typing import Optional

from playwright.async_api import (
    Page,
    Locator,
    TimeoutError as PlaywrightTimeoutError,
)

from config.settings import get_settings
from framework.core.exception_handler import (
    ElementNotFoundError,
    ElementNotInteractableError,
)
from framework.core.logger import get_logger
from framework.core.wait_utils import wait_for_element, wait_for_page_load
from framework.core.retry_handler import with_async_retry

_log = get_logger()


class BasePage:
    """
    Abstract base for all page objects.

    Every page class must inherit from BasePage and pass the Playwright Page.

    Usage:
        class LoginPage(BasePage):
            def __init__(self, page: Page):
                super().__init__(page)

            async def fill_username(self, value: str):
                await self.safe_fill(
                    self.page.get_by_label("Username"),
                    value,
                    label="Username field"
                )
    """

    def __init__(self, page: Page) -> None:
        self._page = page
        self._settings = get_settings()

    @property
    def page(self) -> Page:
        return self._page

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    async def wait_for_load(self, state: str = "networkidle") -> None:
        """Wait for the page to reach the given load state."""
        await wait_for_page_load(self._page, state=state)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    # Safe Interactions                                                    #
    # ------------------------------------------------------------------ #

    async def safe_click(
        self,
        locator: Locator,
        label: str = "element",
        timeout: Optional[int] = None,
        force: bool = False,
    ) -> None:
        """
        Click an element safely with explicit wait and error handling.

        Args:
            locator: Playwright Locator object.
            label:   Human-readable name for logging.
            timeout: Override default element timeout (ms).
            force:   If True, bypass actionability checks (use sparingly).
        """
        t = timeout or self._settings.timeout_element
        try:
            _log.debug("Clicking [{label}]", label=label)
            await locator.wait_for(state="visible", timeout=t)
            await locator.click(timeout=t, force=force)
            _log.debug("Clicked [{label}]", label=label)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Element '{label}' not visible for click within {t}ms", cause=exc
            ) from exc
        except Exception as exc:
            raise ElementNotInteractableError(
                f"Could not click '{label}': {exc}", cause=exc
            ) from exc

    async def safe_fill(
        self,
        locator: Locator,
        value: str,
        label: str = "field",
        timeout: Optional[int] = None,
        clear_first: bool = True,
    ) -> None:
        """
        Fill an input field safely.

        Args:
            locator:     Playwright Locator.
            value:       Text to type.
            label:       Human-readable name.
            timeout:     Element wait timeout (ms).
            clear_first: Clear existing content before filling.
        """
        t = timeout or self._settings.timeout_element
        try:
            _log.debug("Filling [{label}] with value", label=label)
            await locator.wait_for(state="visible", timeout=t)
            if clear_first:
                await locator.clear()
            await locator.fill(value, timeout=t)
            _log.debug("Filled [{label}]", label=label)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Field '{label}' not visible within {t}ms", cause=exc
            ) from exc
        except Exception as exc:
            raise ElementNotInteractableError(
                f"Could not fill '{label}': {exc}", cause=exc
            ) from exc

    async def safe_type(
        self,
        locator: Locator,
        value: str,
        label: str = "field",
        delay: int = 50,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Type into a field character-by-character (for JS-driven inputs).

        Args:
            delay: Milliseconds between keystrokes (simulates human typing).
        """
        t = timeout or self._settings.timeout_element
        try:
            await locator.wait_for(state="visible", timeout=t)
            await locator.clear()
            await locator.type(value, delay=delay)
            _log.debug("Typed into [{label}]", label=label)
        except Exception as exc:
            raise ElementNotInteractableError(
                f"Could not type into '{label}': {exc}", cause=exc
            ) from exc

    async def safe_select(
        self,
        locator: Locator,
        value: str,
        label: str = "dropdown",
        timeout: Optional[int] = None,
    ) -> None:
        """
        Select a dropdown option by value.

        Args:
            locator: Playwright Locator pointing to a <select> element.
            value:   Option value (or label) to select.
            label:   Human-readable name.
        """
        t = timeout or self._settings.timeout_element
        try:
            await locator.wait_for(state="visible", timeout=t)
            await locator.select_option(value=value, timeout=t)
            _log.debug("Selected '{value}' in [{label}]", value=value, label=label)
        except PlaywrightTimeoutError as exc:
            raise ElementNotFoundError(
                f"Dropdown '{label}' not visible within {t}ms", cause=exc
            ) from exc
        except Exception as exc:
            raise ElementNotInteractableError(
                f"Could not select '{value}' in '{label}': {exc}", cause=exc
            ) from exc

    async def safe_check(
        self,
        locator: Locator,
        label: str = "checkbox",
        timeout: Optional[int] = None,
    ) -> None:
        """Check (tick) a checkbox."""
        t = timeout or self._settings.timeout_element
        try:
            await locator.wait_for(state="visible", timeout=t)
            await locator.check(timeout=t)
            _log.debug("Checked [{label}]", label=label)
        except Exception as exc:
            raise ElementNotInteractableError(
                f"Could not check '{label}': {exc}", cause=exc
            ) from exc

    # ------------------------------------------------------------------ #
    # Safe Reads                                                           #
    # ------------------------------------------------------------------ #

    async def safe_get_text(
        self,
        locator: Locator,
        label: str = "element",
        timeout: Optional[int] = None,
        default: str = "",
    ) -> str:
        """
        Get text content of an element safely.

        Returns:
            Text content stripped of whitespace, or default on failure.
        """
        t = timeout or self._settings.timeout_element
        try:
            await locator.wait_for(state="visible", timeout=t)
            text = await locator.text_content() or default
            return text.strip()
        except Exception as exc:
            _log.warning(
                "Could not read text from [{label}]: {exc}",
                label=label,
                exc=exc,
            )
            return default

    async def safe_get_value(
        self,
        locator: Locator,
        label: str = "input",
        timeout: Optional[int] = None,
        default: str = "",
    ) -> str:
        """Get the current input value of a field."""
        t = timeout or self._settings.timeout_element
        try:
            await locator.wait_for(state="visible", timeout=t)
            return await locator.input_value() or default
        except Exception as exc:
            _log.warning("Could not get value from [{label}]: {exc}", label=label, exc=exc)
            return default

    async def safe_is_visible(
        self,
        locator: Locator,
        timeout: int = 3_000,
    ) -> bool:
        """
        Non-throwing visibility check.

        Returns:
            True if visible within timeout, False otherwise.
        """
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            return True
        except (PlaywrightTimeoutError, Exception):
            return False

    # ------------------------------------------------------------------ #
    # Waiting                                                              #
    # ------------------------------------------------------------------ #

    async def safe_wait(
        self,
        locator: Locator,
        state: str = "visible",
        label: str = "element",
        timeout: Optional[int] = None,
    ) -> None:
        """Wait for an element to reach a specific state."""
        await wait_for_element(
            locator,
            state=state,  # type: ignore[arg-type]
            timeout=timeout or self._settings.timeout_element,
            label=label,
        )

    async def wait_for_network_idle(self, timeout: int = 30_000) -> None:
        """Wait for all network requests to finish."""
        await self._page.wait_for_load_state("networkidle", timeout=timeout)

    # ------------------------------------------------------------------ #
    # Screenshot                                                           #
    # ------------------------------------------------------------------ #

    async def screenshot(
        self,
        exec_id: str = "INIT",
        row_id: str = "-",
        label: str = "page",
    ) -> Optional[str]:
        """Capture a screenshot using ScreenshotManager naming conventions."""
        from framework.reporting.screenshot_manager import ScreenshotManager
        sm = ScreenshotManager()
        return await sm.capture(self._page, exec_id=exec_id, row_id=row_id, label=label)

    # ------------------------------------------------------------------ #
    # URL Helpers                                                          #
    # ------------------------------------------------------------------ #

    @property
    def current_url(self) -> str:
        return self._page.url

    def url_contains(self, fragment: str) -> bool:
        return fragment.lower() in self._page.url.lower()
