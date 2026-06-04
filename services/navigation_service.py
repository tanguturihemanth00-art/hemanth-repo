"""
services/navigation_service.py
================================
Handles page navigation concerns.

Separates navigation logic from page object interactions and workflow logic.
"""

from __future__ import annotations

from typing import Optional
from playwright.async_api import Page

from config.environment import get_env
from framework.core.exception_handler import NavigationError
from framework.core.logger import get_logger
from framework.core.wait_utils import wait_for_page_load, wait_for_url_contains
from framework.core.retry_handler import with_async_retry

_log = get_logger()


class NavigationService:
    """
    Reusable navigation helper.

    Usage:
        nav = NavigationService()
        await nav.goto(page, "/customers/create")
        await nav.goto_full_url(page, "https://app.example.com/portal")
    """

    def __init__(self) -> None:
        self._env = get_env()

    @with_async_retry(max_attempts=3)
    async def goto(
        self,
        page: Page,
        path: str,
        wait_state: str = "networkidle",
        timeout: int = 60_000,
    ) -> None:
        """
        Navigate to a path relative to APP_URL.

        Args:
            page:       Active Playwright Page.
            path:       Relative path (e.g., '/customers/new').
            wait_state: Load state to wait for after navigation.
            timeout:    Navigation timeout in ms.
        """
        base = self._env.app_url.rstrip("/")
        path = path.lstrip("/")
        full_url = f"{base}/{path}" if path else base

        _log.info("Navigating to: {url}", url=full_url)
        try:
            await page.goto(full_url, wait_until=wait_state, timeout=timeout)
            _log.info("Navigation complete: {url}", url=page.url)
        except Exception as exc:
            raise NavigationError(
                f"Failed to navigate to: {full_url}", cause=exc
            ) from exc

    @with_async_retry(max_attempts=3)
    async def goto_full_url(
        self,
        page: Page,
        url: str,
        wait_state: str = "networkidle",
        timeout: int = 60_000,
    ) -> None:
        """Navigate to an absolute URL."""
        _log.info("Navigating to full URL: {url}", url=url)
        try:
            await page.goto(url, wait_until=wait_state, timeout=timeout)
        except Exception as exc:
            raise NavigationError(
                f"Failed to navigate to: {url}", cause=exc
            ) from exc

    async def reload(self, page: Page, wait_state: str = "networkidle") -> None:
        """Reload the current page."""
        _log.debug("Reloading page: {url}", url=page.url)
        try:
            await page.reload(wait_until=wait_state)
        except Exception as exc:
            raise NavigationError("Page reload failed.", cause=exc) from exc

    async def go_back(self, page: Page) -> None:
        """Navigate browser back."""
        await page.go_back(wait_until="networkidle")

    @property
    def base_url(self) -> str:
        return self._env.app_url
