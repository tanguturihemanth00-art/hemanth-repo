"""
pages/navigation_page.py
==========================
NavigationPage — handles main navigation menus and routing.

⚠️  IMPLEMENTATION REQUIRED:
    Replace placeholder locators with real selectors from your website's
    navigation menu / sidebar / top bar.

    Implement one method per navigation destination. Example:
        async def goto_customer_creation(self) -> None:
            await self.safe_click(
                self.page.get_by_role("link", name="New Customer"),
                label="New Customer menu item"
            )
            await self.wait_for_network_idle()
"""

from __future__ import annotations

from playwright.async_api import Page

from pages.base_page import BasePage
from framework.core.exception_handler import NavigationError
from framework.core.logger import get_logger
from framework.core.wait_utils import wait_for_url_contains

_log = get_logger()


class NavigationPage(BasePage):
    """
    Page object for main navigation interactions.

    Represents the app's nav bar, sidebar, or any shared navigation element.

    Usage:
        nav = NavigationPage(page)
        await nav.goto_module("Customer Management")
        await nav.goto_create_record()
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------ #
    # Locators (replace with your website's actual nav selectors)        #
    # ------------------------------------------------------------------ #

    @property
    def _main_menu(self):
        # ✏️  Replace with actual nav locator
        # return self.page.get_by_role("navigation")
        # return self.page.locator("[data-testid='main-nav']")
        return self.page.get_by_role("navigation")

    def _menu_item(self, name: str):
        # ✏️  Replace with actual menu item locator strategy
        # return self.page.get_by_role("link", name=name)
        # return self.page.get_by_role("menuitem", name=name)
        return self.page.get_by_role("link", name=name)

    # ------------------------------------------------------------------ #
    # Generic Navigation                                                   #
    # ------------------------------------------------------------------ #

    async def goto_module(self, module_name: str) -> None:
        """
        Click a named navigation item and wait for load.

        Args:
            module_name: The visible text of the menu item.
        """
        _log.info("Navigating to module: {module}", module=module_name)
        await self.safe_click(
            self._menu_item(module_name),
            label=f"Nav item: {module_name}",
        )
        await self.wait_for_network_idle()
        _log.info("Arrived at module: {module} | URL: {url}", module=module_name, url=self.current_url)

    async def wait_for_navigation_ready(self) -> None:
        """Wait until the main navigation is visible and ready."""
        await self.safe_wait(
            self._main_menu,
            state="visible",
            label="Main navigation menu",
        )

    # ------------------------------------------------------------------ #
    # Workflow-Specific Navigation (stub — implement per workflow)        #
    # ------------------------------------------------------------------ #

    async def goto_create_record(self) -> None:
        """
        ✏️  Navigate to the record creation form.
        Implement this based on your website's routing.

        Example:
            await self.safe_click(
                self.page.get_by_role("button", name="New Record"),
                label="New Record button"
            )
            await wait_for_url_contains(self.page, "/create")
        """
        raise NotImplementedError(
            "Implement goto_create_record() in NavigationPage "
            "with your website's specific navigation locators."
        )

    async def goto_record_list(self) -> None:
        """
        ✏️  Navigate to the records listing page.
        """
        raise NotImplementedError(
            "Implement goto_record_list() with your website's locators."
        )
