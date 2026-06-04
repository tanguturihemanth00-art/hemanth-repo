"""
framework/core/execution_context.py
=====================================
Execution context — thread-local state for a single workflow run.

Holds:
- Unique execution ID
- Current row being processed
- Reference to the active logger
- Timing and metadata

Passed down through the workflow, services, and pages to provide
consistent context without global state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _generate_exec_id() -> str:
    """Generate a short, readable execution ID: RUN-YYYYMMDD-HHMMSS-XXXX"""
    now = datetime.now()
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"RUN-{now.strftime('%Y%m%d-%H%M%S')}-{short_uuid}"


@dataclass
class ExecutionContext:
    """
    Immutable-ish context object for one workflow execution.

    Create once at workflow start, pass to all services and page objects.
    Do not mutate after creation — use update_row() for row tracking.

    Attributes:
        execution_id:   Unique run identifier.
        workflow_name:  Name of the workflow being executed.
        started_at:     When this execution started.
        current_row_id: Identifier of the row currently being processed.
        current_row_index: Zero-based index of current row.
        total_rows:     Total number of rows in the batch.
        metadata:       Arbitrary metadata dict for workflow-specific context.
    """

    workflow_name: str
    execution_id: str = field(default_factory=_generate_exec_id)
    started_at: datetime = field(default_factory=datetime.now)

    current_row_id: str = "-"
    current_row_index: int = 0
    total_rows: int = 0

    metadata: dict = field(default_factory=dict)

    def update_row(self, row_index: int, row_id: str) -> None:
        """Update context when moving to a new row."""
        self.current_row_index = row_index
        self.current_row_id = row_id

    def get_logger(self):
        """
        Get a logger bound to this execution context.

        Usage:
            log = ctx.get_logger()
            log.info("Processing row {row_id}", row_id=ctx.current_row_id)
        """
        from framework.core.logger import get_logger
        return get_logger(
            exec_id=self.execution_id,
            row_id=self.current_row_id,
        )

    @property
    def progress(self) -> str:
        """Human-readable progress string: '5/100'"""
        return f"{self.current_row_index}/{self.total_rows}"

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.started_at).total_seconds()

    def __repr__(self) -> str:
        return (
            f"ExecutionContext("
            f"id={self.execution_id}, "
            f"workflow={self.workflow_name}, "
            f"row={self.current_row_id}, "
            f"progress={self.progress}"
            f")"
        )
