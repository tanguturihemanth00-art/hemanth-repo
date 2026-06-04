from playwright.async_api import Page

from models.demo_record import DemoRecord
from workflows.base_workflow import BaseWorkflow
from framework.core.logger import get_logger

_log = get_logger()

class DemoWorkflow(BaseWorkflow[DemoRecord]):
    @property
    def record_class(self):
        return DemoRecord

    @property
    def workflow_name(self):
        return "demo_workflow"

    async def process_row(self, page: Page, record: DemoRecord) -> None:
        _log.info(f"Processing row {record.row_id}: Task {record.task_id} -> {record.action}")
        # Normally you would do some page interactions here
        # Example: await page.locator("selector").click()
        # For demo, just wait a second
        await page.wait_for_timeout(2000)
        _log.info(f"Finished processing row {record.row_id} - login was successful if we reached here!")
