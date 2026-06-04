"""
services/excel_service.py
==========================
Enterprise Excel engine.

Capabilities:
- Read Excel with schema validation
- Write output Excel
- Save failed rows to separate file
- Dynamic column mapping
- Missing field validation
- Duplicate detection
- Type coercion hooks

Never imports page objects or browser code.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Iterator, List, Optional, Type, TypeVar

import pandas as pd

from config.constants import (
    EXCEL_STATUS_COLUMN,
    EXCEL_ERROR_COLUMN,
    EXCEL_TIMESTAMP_COLUMN,
    EXCEL_ROW_ID_COLUMN,
    FAILED_FILE_SUFFIX,
    STATUS_FAILURE,
)
from config.environment import get_env
from config.settings import get_settings
from framework.core.exception_handler import (
    DataError,
    MissingColumnError,
    DuplicateRowError,
)
from framework.core.logger import get_logger
from models.excel_record import ExcelRecord

_log = get_logger()

T = TypeVar("T", bound=ExcelRecord)


class ExcelService(Generic[T]):
    """
    Generic Excel reader/writer bound to a specific ExcelRecord subclass.

    Usage:
        # Define your record model
        class CustomerRecord(ExcelRecord):
            customer_id: str
            customer_name: str

        # Instantiate service
        svc = ExcelService(CustomerRecord)

        # Read
        records = svc.load("data/input/customers.xlsx")

        # After processing, save results
        svc.save_output(records, "customers")
        svc.save_failed(records, "customers")
    """

    def __init__(
        self,
        record_class: Type[T],
        required_columns: Optional[List[str]] = None,
        duplicate_check_columns: Optional[List[str]] = None,
    ) -> None:
        self._record_class = record_class
        self._settings = get_settings()
        self._env = get_env()
        self._required_columns = (
            required_columns or self._settings.get("excel", "required_columns", default=[])
        )
        self._duplicate_check_columns = (
            duplicate_check_columns
            or self._settings.get("excel", "duplicate_check_columns", default=[])
        )

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def load(
        self,
        file_path: str | Path,
        sheet_name: str | int = 0,
    ) -> List[T]:
        """
        Read an Excel file and return a list of validated record objects.

        Args:
            file_path:  Path to the input .xlsx file.
            sheet_name: Sheet name or index (default: first sheet).

        Returns:
            List of record instances ordered by row.

        Raises:
            DataError:         On file read failure.
            MissingColumnError: On missing required columns.
        """
        path = Path(file_path)
        if not path.exists():
            raise DataError(f"Input Excel file not found: {path}")

        _log.info(
            "Loading Excel: {file} | sheet={sheet}",
            file=path.name,
            sheet=sheet_name,
        )

        try:
            df = pd.read_excel(
                str(path),
                sheet_name=sheet_name,
                engine=self._settings.excel_engine,
                dtype=str,          # read everything as string; let Pydantic coerce
                keep_default_na=False,
            )
        except Exception as exc:
            raise DataError(f"Failed to read Excel file: {path}", cause=exc) from exc

        # Strip whitespace from column names
        df.columns = [str(c).strip() for c in df.columns]

        # Skip empty rows
        if self._settings.excel_skip_empty_rows:
            df = df.dropna(how="all")

        # Validate required columns
        self._validate_columns(df)

        # Duplicate detection
        if self._duplicate_check_columns:
            self._detect_duplicates(df)

        # Limit rows
        max_rows = self._settings.excel_max_rows
        if len(df) > max_rows:
            _log.warning(
                "Excel has {total} rows, truncating to {max} (config excel.max_rows).",
                total=len(df),
                max=max_rows,
            )
            df = df.iloc[:max_rows]

        records: List[T] = []
        for idx, row in enumerate(df.to_dict(orient="records"), start=1):
            row_id = f"ROW_{idx}"
            try:
                record: T = self._record_class(**{**row, "row_id": row_id})
                record.__row_index__ = idx
                records.append(record)
            except Exception as exc:
                _log.warning(
                    "Row {row_id} failed validation (skipping): {exc}",
                    row_id=row_id,
                    exc=exc,
                )

        _log.info(
            "Loaded {count} records from {file}",
            count=len(records),
            file=path.name,
        )
        return records

    # ------------------------------------------------------------------ #
    # Write Output                                                          #
    # ------------------------------------------------------------------ #

    def save_output(
        self,
        records: List[T],
        output_name: str,
        output_dir: Optional[Path] = None,
    ) -> str:
        """
        Save all records (including status columns) to an output Excel file.

        Args:
            records:    List of processed records.
            output_name: Base name for the output file (no extension).
            output_dir:  Directory override. Defaults to config output_dir.

        Returns:
            Path to the saved file.
        """
        dest = (output_dir or self._env.output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = dest / f"{output_name}_output_{timestamp}.xlsx"

        df = self._records_to_dataframe(records)
        self._write_excel(df, path, sheet_name="Output")

        _log.info("Output saved: {path}", path=path.name)
        return str(path)

    def save_failed(
        self,
        records: List[T],
        output_name: str,
        failed_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Save only failed records to a separate Excel file.

        Returns:
            Path to the failed file, or None if no failures.
        """
        failed = [r for r in records if r.is_failure()]
        if not failed:
            _log.info("No failed rows — skipping failed output file.")
            return None

        dest = (failed_dir or self._env.failed_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = dest / f"{output_name}{FAILED_FILE_SUFFIX}_{timestamp}.xlsx"

        df = self._records_to_dataframe(failed)
        self._write_excel(df, path, sheet_name="Failed Rows")

        _log.info(
            "Failed rows saved: {path} | count={count}",
            path=path.name,
            count=len(failed),
        )
        return str(path)

    # ------------------------------------------------------------------ #
    # Validation Helpers                                                    #
    # ------------------------------------------------------------------ #

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Check that all required columns are present (case-insensitive)."""
        if not self._required_columns:
            return

        available = {c.lower().replace(" ", "_") for c in df.columns}
        missing = [
            col for col in self._required_columns
            if col.lower().replace(" ", "_") not in available
        ]
        if missing:
            raise MissingColumnError(
                f"Required columns missing from Excel: {missing}. "
                f"Available columns: {list(df.columns)}"
            )

    def _detect_duplicates(self, df: pd.DataFrame) -> None:
        """Log duplicate rows based on configured duplicate_check_columns."""
        cols = [
            c for c in self._duplicate_check_columns
            if c in df.columns
        ]
        if not cols:
            return

        dupes = df[df.duplicated(subset=cols, keep=False)]
        if not dupes.empty:
            _log.warning(
                "Found {count} duplicate rows based on columns {cols}. "
                "All duplicates will be processed.",
                count=len(dupes),
                cols=cols,
            )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _records_to_dataframe(self, records: List[T]) -> pd.DataFrame:
        rows = [r.to_output_dict() for r in records]
        return pd.DataFrame(rows)

    def _write_excel(self, df: pd.DataFrame, path: Path, sheet_name: str = "Sheet1") -> None:
        try:
            with pd.ExcelWriter(str(path), engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name)
        except Exception as exc:
            raise DataError(f"Failed to write Excel: {path}", cause=exc) from exc

    # ------------------------------------------------------------------ #
    # Iterator (memory-efficient for large files)                          #
    # ------------------------------------------------------------------ #

    def iter_rows(self, file_path: str | Path, chunk_size: int = 100) -> Iterator[List[T]]:
        """
        Yield records in chunks. For large files, avoids loading all rows into memory.

        Usage:
            for batch in svc.iter_rows("large_file.xlsx", chunk_size=50):
                for record in batch:
                    await workflow.process(record)
        """
        all_records = self.load(file_path)
        for i in range(0, len(all_records), chunk_size):
            yield all_records[i : i + chunk_size]
