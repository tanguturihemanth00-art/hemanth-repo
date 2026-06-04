"""
workflows/interactive_workflow.py
==================================
Interactive Workflow — logs in and pauses execution.
Useful for recording actions, exploring the site, or manually testing logic.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from framework.browser.browser_manager import BrowserManager
from framework.core.exception_handler import WorkflowError
from framework.core.logger import get_logger
from models.execution_result import ExecutionResult
from services.auth_service import AuthService
from workflows.base_workflow import BaseWorkflow
from models.excel_record import ExcelRecord


class InteractiveWorkflow(BaseWorkflow[ExcelRecord]):
    @property
    def record_class(self):
        return ExcelRecord

    @property
    def workflow_name(self) -> str:
        return "interactive"

    async def process_row(self, page, record):
        pass  # Not used in interactive mode

    async def run(self, input_file: str | Path = "") -> ExecutionResult:
        """
        Overrides run() to skip Excel reading and just login + pause.
        """
        log = get_logger()
        result = ExecutionResult(execution_id="INTERACTIVE", workflow_name=self.workflow_name)

        log.info("=" * 60)
        log.info("INTERACTIVE MODE: Logging in and pausing execution...")
        log.info("=" * 60)

        async with BrowserManager() as browser:
            page = await browser.new_page()
            auth = AuthService(browser)

            try:
                await auth.authenticate(page)
                log.info("[OK] Login successful!")
                
                log.info("=====================================================")
                log.info("[PAUSED] EXECUTION for interactive exploration.")
                log.info("Use the Playwright Inspector to record or explore.")
                log.info("Close the browser window or press Resume to end.")
                log.info("=====================================================")
                
                # Pause execution and open inspector
                await page.pause()

            except Exception as exc:
                log.error("Interactive mode failed: {exc}", exc=exc)
                raise WorkflowError("Interactive mode aborted.", cause=exc) from exc

        return result
