"""
models/execution_result.py
==========================
Immutable result envelope for workflow execution runs.
Holds aggregated metrics, per-row results, and timing data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class RowResult:
    """Result for a single processed Excel row."""

    row_id: str
    status: str                      # SUCCESS | FAILURE | SKIPPED
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    duration_seconds: float = 0.0
    processed_at: datetime = field(default_factory=datetime.now)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """
    Aggregated result for an entire workflow execution run.
    Populated progressively during the run, finalized at completion.
    """

    execution_id: str
    workflow_name: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    total_rows: int = 0
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0

    row_results: List[RowResult] = field(default_factory=list)
    failed_file_path: Optional[str] = None
    report_file_path: Optional[str] = None

    def record_row(self, result: RowResult) -> None:
        """Add a row result and update counters."""
        self.row_results.append(result)
        from config.constants import STATUS_SUCCESS, STATUS_FAILURE, STATUS_SKIPPED
        if result.status == STATUS_SUCCESS:
            self.success_count += 1
        elif result.status == STATUS_FAILURE:
            self.failure_count += 1
        elif result.status == STATUS_SKIPPED:
            self.skipped_count += 1

    def finalize(self) -> None:
        """Mark the run as complete."""
        self.finished_at = datetime.now()

    @property
    def duration_seconds(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return (datetime.now() - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round((self.success_count / self.total_rows) * 100, 2)

    @property
    def failed_rows(self) -> List[RowResult]:
        from config.constants import STATUS_FAILURE
        return [r for r in self.row_results if r.status == STATUS_FAILURE]

    def summary(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow": self.workflow_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "total": self.total_rows,
            "success": self.success_count,
            "failure": self.failure_count,
            "skipped": self.skipped_count,
            "success_rate_pct": self.success_rate,
        }
