"""
workflows/base_workflow.py
===========================
BaseWorkflow — abstract orchestrator for all automation workflows.

Implements the full execution flow:

  START → Load Config → Init Log → Start Browser → Authenticate
        → Restore Session → Read Excel → Validate Input
        → Loop Rows (Navigate → UI Action → Validate → Log → Save)
        → Generate Report → Close Browser → END

Every workflow inherits from BaseWorkflow and implements:
  - record_class  → property returning ExcelRecord subclass
  - process_row() → the actual UI action for one row
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, List, Optional, Type, TypeVar

from playwright.async_api import Page

from config.settings import get_settings
from config.environment import get_env
from framework.browser.browser_manager import BrowserManager
from framework.core.execution_context import ExecutionContext
from framework.core.exception_handler import (
    AuthenticationError,
    BrowserCrashError,
    WorkflowError,
)
from framework.core.logger import get_logger
from framework.reporting.report_manager import ReportManager
from models.excel_record import ExcelRecord
from models.execution_result import ExecutionResult
from services.auth_service import AuthService
from services.excel_service import ExcelService
from services.navigation_service import NavigationService
from services.validation_service import ValidationService
from services.workflow_service import WorkflowService

T = TypeVar("T", bound=ExcelRecord)


class BaseWorkflow(ABC, Generic[T]):
    """
    Abstract base for all automation workflows.

    Subclass this for each workflow you automate.

    Minimal implementation:
    -----------------------------------------------------------------------
    class CustomerCreationWorkflow(BaseWorkflow[CustomerRecord]):

        @property
        def record_class(self) -> Type[CustomerRecord]:
            return CustomerRecord

        @property
        def workflow_name(self) -> str:
            return "customer_creation"

        async def process_row(self, page: Page, record: CustomerRecord) -> None:
            form = CustomerCreationPage(page)
            await form.process_record(record)
    -----------------------------------------------------------------------
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._env = get_env()
        self._report_manager = ReportManager()
        self._excel_service: Optional[ExcelService[T]] = None
        self._workflow_service = WorkflowService()
        self._nav_service = NavigationService()
        self._validation_service = ValidationService()

    # ------------------------------------------------------------------ #
    # Abstract Interface                                                   #
    # ------------------------------------------------------------------ #

    @property
    @abstractmethod
    def record_class(self) -> Type[T]:
        """Return the ExcelRecord subclass for this workflow."""
        ...

    @property
    def workflow_name(self) -> str:
        """Override to give this workflow a human-readable name."""
        return self.__class__.__name__

    @abstractmethod
    async def process_row(self, page: Page, record: T) -> None:
        """
        Perform the UI action for a single Excel row.

        This is where your page object calls live.
        Raise any exception to mark the row as FAILED.
        The workflow orchestrator handles all error catching.

        Args:
            page:   Active Playwright Page.
            record: The typed Excel row data object.
        """
        ...

    # ------------------------------------------------------------------ #
    # Optional Hooks                                                       #
    # ------------------------------------------------------------------ #

    async def on_before_run(self, page: Page, ctx: ExecutionContext) -> None:
        """Hook: called once after login, before row processing starts."""
        pass

    async def on_after_run(
        self,
        page: Page,
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """Hook: called once after all rows are processed."""
        pass

    async def on_row_start(self, page: Page, record: T, ctx: ExecutionContext) -> None:
        """Hook: called before each row. Use for navigation if needed."""
        pass

    async def on_row_complete(
        self,
        page: Page,
        record: T,
        ctx: ExecutionContext,
    ) -> None:
        """Hook: called after each row regardless of success/failure."""
        pass

    # ------------------------------------------------------------------ #
    # Main Entry Point                                                     #
    # ------------------------------------------------------------------ #

    async def run(self, input_file: str | Path) -> ExecutionResult:
        """
        Execute the full workflow.

        Args:
            input_file: Path to the input Excel file.

        Returns:
            ExecutionResult with complete run metrics.
        """
        log = get_logger()
        ctx = ExecutionContext(workflow_name=self.workflow_name)
        execution_result = ExecutionResult(
            execution_id=ctx.execution_id,
            workflow_name=self.workflow_name,
        )

        log.info("=" * 60)
        log.info(
            "WORKFLOW START: {name} | ID: {id}",
            name=self.workflow_name,
            id=ctx.execution_id,
        )
        log.info("=" * 60)

        # ---- Step 1: Load & validate Excel -------------------------
        self._excel_service = ExcelService(self.record_class)
        records: List[T] = self._excel_service.load(input_file)
        execution_result.total_rows = len(records)
        ctx.total_rows = len(records)

        if not records:
            log.warning("No records found in {file}. Workflow complete.", file=input_file)
            self._report_manager.generate(execution_result)
            return execution_result

        log.info("Loaded {count} records for processing.", count=len(records))

        # ---- Step 2: Browser + Auth --------------------------------
        async with BrowserManager() as browser:
            page = await browser.new_page()
            auth = AuthService(browser)

            try:
                await auth.authenticate(page)
            except AuthenticationError as exc:
                log.error("Authentication failed: {exc}", exc=exc)
                raise WorkflowError("Workflow aborted — authentication failed.", cause=exc) from exc

            # ---- Step 3: Pre-run hook ---------------------------
            await self.on_before_run(page, ctx)

            # ---- Step 4: Process Rows --------------------------
            for idx, record in enumerate(records, start=1):
                ctx.update_row(row_index=idx, row_id=record.row_id)
                row_log = ctx.get_logger()

                try:
                    await self.on_row_start(page, record, ctx)
                except Exception as exc:
                    row_log.warning(
                        "on_row_start hook failed for {row_id}: {exc}",
                        row_id=record.row_id,
                        exc=exc,
                    )

                # Delegate to WorkflowService for lifecycle management
                await self._workflow_service.execute_row(
                    page=page,
                    record=record,
                    ctx=ctx,
                    execution_result=execution_result,
                    action=lambda r=record: self.process_row(page, r),
                )

                try:
                    await self.on_row_complete(page, record, ctx)
                except Exception as exc:
                    row_log.warning(
                        "on_row_complete hook failed for {row_id}: {exc}",
                        row_id=record.row_id,
                        exc=exc,
                    )

                # Stop on failure if configured
                if (
                    record.is_failure()
                    and not self._settings.workflow_continue_on_failure
                ):
                    log.error(
                        "Halting workflow — continue_on_failure=false and row failed.",
                    )
                    break

            # ---- Step 5: Post-run hook --------------------------
            await self.on_after_run(page, ctx, execution_result)

        # ---- Step 6: Save results ----------------------------------
        output_name = self.workflow_name
        self._excel_service.save_output(records, output_name)
        failed_path = self._excel_service.save_failed(records, output_name)
        if failed_path:
            execution_result.failed_file_path = failed_path

        # ---- Step 7: Generate report --------------------------------
        self._report_manager.generate(execution_result)
        try:
            from services.reporting_service import ReportingService
            ReportingService.generate_html_report(execution_result)
        except Exception as exc:
            log.error("Failed to generate HTML report: {exc}", exc=exc)

        return execution_result
