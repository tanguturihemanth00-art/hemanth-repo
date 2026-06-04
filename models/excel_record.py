"""
models/excel_record.py
======================
Pydantic base model for a single Excel row record.
Each workflow subclasses ExcelRecord to add its own typed fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from config.constants import STATUS_PENDING


class ExcelRecord(BaseModel):
    """
    Base class for all Excel row data models.

    Subclass this for each workflow and declare the expected columns as fields:

        class CustomerRecord(ExcelRecord):
            customer_id: str
            customer_name: str
            email: str

    Framework will map Excel column headers -> field names (case-insensitive,
    strip whitespace, replace spaces with underscores).
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
        protected_namespaces=(),
    )

    # Internal tracking — use row_index_ (no dunders) for Pydantic v2 compat
    row_index_: int = Field(0, exclude=True)

    row_id: str = Field(
        default="",
        description="Auto-assigned row identifier: ROW_<index>"
    )
    status: str = Field(
        default=STATUS_PENDING,
        description="Execution status: PENDING | SUCCESS | FAILURE | SKIPPED"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error detail if status is FAILURE"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when this row was processed"
    )
    screenshot_path: Optional[str] = Field(
        default=None,
        description="Path to screenshot captured for this row"
    )



    @model_validator(mode="before")
    @classmethod
    def normalise_column_names(cls, values: Any) -> Any:
        """
        Normalise incoming dict keys:
        - Strip surrounding whitespace
        - Lowercase
        - Replace spaces with underscores

        Allows Excel headers like 'Customer ID' to map to field 'customer_id'.
        """
        if not isinstance(values, dict):
            return values
        return {
            k.strip().lower().replace(" ", "_"): v
            for k, v in values.items()
        }

    def mark_success(self) -> None:
        from config.constants import STATUS_SUCCESS
        self.status = STATUS_SUCCESS
        self.processed_at = datetime.now()
        self.error_message = None

    def mark_failure(self, error: str) -> None:
        from config.constants import STATUS_FAILURE
        self.status = STATUS_FAILURE
        self.processed_at = datetime.now()
        self.error_message = error

    def mark_skipped(self, reason: str = "") -> None:
        from config.constants import STATUS_SKIPPED
        self.status = STATUS_SKIPPED
        self.processed_at = datetime.now()
        self.error_message = reason or None

    def is_success(self) -> bool:
        from config.constants import STATUS_SUCCESS
        return self.status == STATUS_SUCCESS

    def is_failure(self) -> bool:
        from config.constants import STATUS_FAILURE
        return self.status == STATUS_FAILURE

    def to_output_dict(self) -> dict[str, Any]:
        """Return a flat dict suitable for writing back to Excel."""
        return self.model_dump(
            exclude={"__row_index__"},
            mode="python",
        )
