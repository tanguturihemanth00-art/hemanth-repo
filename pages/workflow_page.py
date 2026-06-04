"""
pages/workflow_page.py
========================
WorkflowPage — handles the main form/action page for the workflow.

⚠️  IMPLEMENTATION REQUIRED:
    This is where you implement the actual website interactions
    for your business workflow (form filling, button clicking, etc.)

    Subclass this for each distinct workflow you automate.

    Example:
        class CustomerCreationPage(WorkflowPage):
            async def fill_form(self, record: CustomerRecord):
                await self.safe_fill(
                    self.page.get_by_label("Customer Name"),
                    record.customer_name
                )
                ...
"""

from __future__ import annotations

from typing import Optional

from playwright.async_api import Page

from models.excel_record import ExcelRecord
from pages.base_page import BasePage
from framework.core.exception_handler import ElementNotFoundError, ValidationError
from framework.core.logger import get_logger
from framework.core.wait_utils import wait_for_toast_or_alert

_log = get_logger()


class WorkflowPage(BasePage):
    """
    Base page object for workflow-specific form interactions.

    Subclass per workflow. Provides:
    - fill_form() stub to implement
    - submit_form() stub to implement
    - verify_success() helper
    - capture_result() for reading confirmation messages
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------ #
    # Stubs — implement in subclasses                                     #
    # ------------------------------------------------------------------ #

    async def fill_form(self, record: ExcelRecord) -> None:
        """
        ✏️  Fill all form fields using data from the Excel record.

        Override in your workflow-specific page class.

        Example:
            async def fill_form(self, record: CustomerRecord):
                await self.safe_fill(
                    self.page.get_by_label("Customer Name"),
                    record.customer_name,
                    label="Customer Name"
                )
                await self.safe_fill(
                    self.page.get_by_label("Email"),
                    record.email,
                    label="Email"
                )
                await self.safe_select(
                    self.page.get_by_label("Category"),
                    record.category,
                    label="Category"
                )
        """
        raise NotImplementedError(
            "Implement fill_form() in your WorkflowPage subclass."
        )

    async def submit_form(self) -> None:
        """
        ✏️  Click the submit/save button on the form.

        Example:
            async def submit_form(self):
                await self.safe_click(
                    self.page.get_by_role("button", name="Save"),
                    label="Save button"
                )
                await self.wait_for_network_idle()
        """
        raise NotImplementedError(
            "Implement submit_form() in your WorkflowPage subclass."
        )

    # ------------------------------------------------------------------ #
    # Success / Failure Verification                                       #
    # ------------------------------------------------------------------ #

    async def verify_success(
        self,
        success_url_fragment: Optional[str] = None,
        success_text: Optional[str] = None,
    ) -> bool:
        """
        Verify that the form submission succeeded.

        Checks (in order):
        1. URL contains success fragment (if provided)
        2. Toast/alert contains success text (if provided)

        Returns:
            True if success detected.

        Raises:
            ValidationError: If neither condition is met.
        """
        if success_url_fragment:
            if self.url_contains(success_url_fragment):
                _log.debug(
                    "Success verified via URL fragment: {frag}",
                    frag=success_url_fragment,
                )
                return True

        if success_text:
            toast = await wait_for_toast_or_alert(self._page, timeout=10_000)
            if toast and success_text.lower() in toast.lower():
                _log.debug("Success verified via toast text: '{toast}'", toast=toast)
                return True

        raise ValidationError(
            f"Success condition not met. "
            f"URL: {self.current_url} | "
            f"Expected fragment: {success_url_fragment} | "
            f"Expected text: {success_text}"
        )

    async def capture_confirmation_message(self) -> str:
        """
        Attempt to read a confirmation/success message from the page.
        Returns empty string if none found.
        """
        message = await wait_for_toast_or_alert(self._page, timeout=5_000)
        return message or ""

    # ------------------------------------------------------------------ #
    # Complete Row Action (template method)                               #
    # ------------------------------------------------------------------ #

    async def process_record(
        self,
        record: ExcelRecord,
        success_url_fragment: Optional[str] = None,
        success_text: Optional[str] = None,
    ) -> None:
        """
        Template method: fill → submit → verify.

        Subclasses should override fill_form() and submit_form().
        This method orchestrates the full action for one Excel row.
        """
        _log.debug("Starting form fill for {row_id}", row_id=record.row_id)
        await self.fill_form(record)

        _log.debug("Submitting form for {row_id}", row_id=record.row_id)
        await self.submit_form()

        await self.verify_success(
            success_url_fragment=success_url_fragment,
            success_text=success_text,
        )
