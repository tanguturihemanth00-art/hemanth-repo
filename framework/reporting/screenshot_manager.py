"""
framework/reporting/screenshot_manager.py
==========================================
Captures and organizes screenshots for audit trails.

Naming convention:
    <exec_id>_<row_id>_<label>_<timestamp>.png

Examples:
    RUN-20240605-120000-ABC123_ROW_3_failure_20240605_120045.png
    RUN-20240605-120000-ABC123_ROW_5_success_20240605_120130.png
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import Page

from config.environment import get_env
from framework.core.logger import get_logger

_log = get_logger()


class ScreenshotManager:
    """
    Manages screenshot capture and file organization.

    Usage:
        sm = ScreenshotManager()
        path = await sm.capture(page, exec_id="RUN-001", row_id="ROW_3", label="failure")
    """

    def __init__(self) -> None:
        self._base_dir: Path = get_env().screenshot_dir

    def _build_path(self, exec_id: str, row_id: str, label: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:21]
        filename = f"{exec_id}_{row_id}_{label}_{timestamp}.png"
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
        return self._base_dir / filename

    async def capture(
        self,
        page: Page,
        exec_id: str = "INIT",
        row_id: str = "-",
        label: str = "screenshot",
        full_page: bool = False,
    ) -> Optional[str]:
        """
        Capture a screenshot of the current page state.

        Args:
            page:      Active Playwright Page.
            exec_id:   Execution run identifier.
            row_id:    Current row identifier.
            label:     Descriptive label (e.g., 'failure', 'success', 'before_submit').
            full_page: Capture full scrollable page if True.

        Returns:
            Absolute path to the saved screenshot, or None on failure.
        """
        if page.is_closed():
            _log.warning(
                "Cannot capture screenshot — page is closed. "
                "exec_id={exec_id}, row_id={row_id}",
                exec_id=exec_id,
                row_id=row_id,
            )
            return None

        path = self._build_path(exec_id, row_id, label)

        try:
            await page.screenshot(path=str(path), full_page=full_page)
            _log.info(
                "Screenshot saved: {path} | exec={exec_id} | row={row_id}",
                path=path.name,
                exec_id=exec_id,
                row_id=row_id,
            )
            return str(path)
        except Exception as exc:
            _log.error(
                "Screenshot capture failed: {exc} | exec={exec_id} | row={row_id}",
                exc=exc,
                exec_id=exec_id,
                row_id=row_id,
            )
            return None

    async def capture_on_failure(
        self,
        page: Page,
        exec_id: str,
        row_id: str,
    ) -> Optional[str]:
        """Convenience wrapper for failure screenshots."""
        return await self.capture(
            page,
            exec_id=exec_id,
            row_id=row_id,
            label="failure",
            full_page=True,
        )

    async def capture_on_success(
        self,
        page: Page,
        exec_id: str,
        row_id: str,
    ) -> Optional[str]:
        """Convenience wrapper for success screenshots."""
        return await self.capture(
            page,
            exec_id=exec_id,
            row_id=row_id,
            label="success",
            full_page=False,
        )
