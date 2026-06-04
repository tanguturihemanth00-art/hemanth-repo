"""
services/workflow_service.py
=============================
Orchestrates a single row's lifecycle within a workflow execution.

Handles:
- Pre-row setup
- Action delegation to page objects
- Result capture
- Screenshot on success/failure
- Row status updates
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from playwright.async_api import Page

from config.settings import get_settings
from framework.core.exception_handler import (
    FrameworkError,
    RowValidationError,
    WorkflowError,
)
from framework.core.execution_context import ExecutionContext
from framework.core.logger import get_logger
from framework.reporting.screenshot_manager import ScreenshotManager
from models.excel_record import ExcelRecord
from models.execution_result import ExecutionResult, RowResult

_log = get_logger()


class WorkflowService:
    """
    Manages per-row execution lifecycle.

    This service is the bridge between the orchestrator (base_workflow.py)
    and the page objects. It handles timing, error capture, and result recording.

    Usage in BaseWorkflow subclasses:
        result = await self.workflow_service.execute_row(
            page=page,
            record=record,
            ctx=ctx,
            execution_result=execution_result,
            action=lambda: my_page.fill_and_submit(record),
        )
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._screenshots = ScreenshotManager()

    async def execute_row(
        self,
        page: Page,
        record: ExcelRecord,
        ctx: ExecutionContext,
        execution_result: ExecutionResult,
        action,  # Callable: async lambda that performs the UI action
    ) -> RowResult:
        """
        Execute a single row action with full lifecycle management.

        Args:
            page:             Active Playwright Page.
            record:           The Excel row data record.
            ctx:              Current ExecutionContext.
            execution_result: Running ExecutionResult to append to.
            action:           Async callable that performs the row's UI work.

        Returns:
            RowResult with final status, timing, and screenshot.
        """
        log = ctx.get_logger()
        start = time.monotonic()
        screenshot_path: Optional[str] = None

        log.info(
            "▶ Processing {row_id} ({progress}) | data={data}",
            row_id=record.row_id,
            progress=ctx.progress,
            data={
                k: v for k, v in record.model_dump().items()
                if k not in ("status", "error_message", "processed_at", "screenshot_path")
            },
        )

        try:
            # Execute the action
            await action()

            # Mark record success
            record.mark_success()

            # Screenshot on success (optional)
            if self._settings.workflow_screenshot_on_success:
                screenshot_path = await self._screenshots.capture_on_success(
                    page, exec_id=ctx.execution_id, row_id=record.row_id
                )
                record.screenshot_path = screenshot_path

            log.info("✅ {row_id} — SUCCESS", row_id=record.row_id)

        except RowValidationError as exc:
            # Validation failures: skip this row, not a system error
            record.mark_skipped(reason=str(exc))
            log.warning("⏭  {row_id} SKIPPED — {reason}", row_id=record.row_id, reason=exc)

        except FrameworkError as exc:
            # Known framework errors
            error_msg = str(exc)
            record.mark_failure(error=error_msg)

            if self._settings.workflow_screenshot_on_failure:
                screenshot_path = await self._screenshots.capture_on_failure(
                    page, exec_id=ctx.execution_id, row_id=record.row_id
                )
                record.screenshot_path = screenshot_path

            log.error(
                "❌ {row_id} — FAILURE | {err}",
                row_id=record.row_id,
                err=error_msg,
            )

        except Exception as exc:
            # Unexpected errors
            error_msg = f"Unexpected error: {type(exc).__name__}: {exc}"
            record.mark_failure(error=error_msg)

            if self._settings.workflow_screenshot_on_failure:
                screenshot_path = await self._screenshots.capture_on_failure(
                    page, exec_id=ctx.execution_id, row_id=record.row_id
                )
                record.screenshot_path = screenshot_path

            log.error(
                "❌ {row_id} — UNEXPECTED ERROR | {err}",
                row_id=record.row_id,
                err=error_msg,
            )

        finally:
            duration = time.monotonic() - start

        row_result = RowResult(
            row_id=record.row_id,
            status=record.status,
            error_message=record.error_message,
            screenshot_path=record.screenshot_path,
            duration_seconds=duration,
            processed_at=record.processed_at,
            raw_data=record.to_output_dict(),
        )

        execution_result.record_row(row_result)

        # Inter-row delay
        delay_ms = self._settings.workflow_row_delay_ms
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        return row_result
