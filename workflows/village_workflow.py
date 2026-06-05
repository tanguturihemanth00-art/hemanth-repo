"""
workflows/village_workflow.py
=============================
Workflow to process Village Reports. Extracts Village Name, Month, and Year
from the Excel sheet name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Type

from playwright.async_api import Page

from framework.core.logger import get_logger
from models.execution_result import ExecutionResult
from models.village_record import VillageRecord
from services.village_excel_parser import VillageExcelParser
from workflows.base_workflow import BaseWorkflow

_log = get_logger()


class VillageReportWorkflow(BaseWorkflow[VillageRecord]):
    """
    Workflow for processing Village Reports.
    Reads metadata from the Excel sheet name before processing rows.
    """

    def __init__(self) -> None:
        super().__init__()
        self.village_name = "Unknown"
        self.report_month = "Unknown"
        self.report_year = "Unknown"

    @property
    def record_class(self) -> Type[VillageRecord]:
        return VillageRecord

    @property
    def workflow_name(self) -> str:
        return "village_report"

    async def run(self, input_file: str | Path) -> ExecutionResult:
        """
        Override run to extract metadata from the sheet name before starting.
        """
        v_name, r_month, r_year = VillageExcelParser.extract_metadata_from_sheet(input_file)
        self.village_name = v_name
        self.report_month = r_month
        self.report_year = r_year
        
        _log.info(
            "Workflow configured for Village: {v}, Month: {m}, Year: {y}",
            v=self.village_name,
            m=self.report_month,
            y=self.report_year,
        )
        
        # Proceed with normal execution
        return await super().run(input_file)

    async def process_row(self, page: Page, record: VillageRecord) -> None:
        """
        Process a single row. The UI automation goes here.
        """
        # Inject metadata into the record so it's available in the final output
        record.village_name = self.village_name
        record.report_month = self.report_month
        record.report_year = self.report_year

        _log.info(
            "Processing record {id} for {village} ({month} {year})",
            id=record.task_id or record.row_id,
            village=record.village_name,
            month=record.report_month,
            year=record.report_year,
        )

        # TODO: Implement the actual UI logic here!
        # Example:
        # await page.goto(self._env.app_url + "/reports")
        # await page.fill('input#search', str(record.task_id))
        # await page.click('button#submit')
        
        # Simulating work for now
        import asyncio
        await asyncio.sleep(1.0)
        
        record.mark_success()
