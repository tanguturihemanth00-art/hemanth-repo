"""
services/validation_service.py
================================
Row-level and post-action validation.

Responsibilities:
- Validate an ExcelRecord before processing (pre-flight)
- Validate UI outcome after an action (post-action)
- Provide reusable field validators
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from models.excel_record import ExcelRecord
from framework.core.exception_handler import RowValidationError, ValidationError
from framework.core.logger import get_logger

_log = get_logger()


# ------------------------------------------------------------------ #
# Built-in Field Validators                                            #
# ------------------------------------------------------------------ #

def is_non_empty(value: Any, field: str) -> None:
    """Raise if value is empty string or None."""
    if value is None or str(value).strip() == "":
        raise RowValidationError(f"Field '{field}' is required but is empty.")


def is_valid_email(value: str, field: str) -> None:
    """Raise if value is not a valid email address."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, str(value).strip()):
        raise RowValidationError(f"Field '{field}' has invalid email: '{value}'")


def is_numeric(value: Any, field: str) -> None:
    """Raise if value cannot be parsed as a number."""
    try:
        float(str(value).strip())
    except (ValueError, TypeError):
        raise RowValidationError(f"Field '{field}' must be numeric, got: '{value}'")


def max_length(value: Any, field: str, max_len: int) -> None:
    """Raise if string value exceeds max_len characters."""
    if len(str(value)) > max_len:
        raise RowValidationError(
            f"Field '{field}' exceeds max length {max_len}: got {len(str(value))} chars."
        )


def in_allowed_values(value: Any, field: str, allowed: List[str]) -> None:
    """Raise if value is not in the allowed set (case-insensitive)."""
    normalised = str(value).strip().lower()
    if normalised not in [a.lower() for a in allowed]:
        raise RowValidationError(
            f"Field '{field}' must be one of {allowed}, got: '{value}'"
        )


# ------------------------------------------------------------------ #
# Validation Service                                                   #
# ------------------------------------------------------------------ #

class ValidationService:
    """
    Row-level and UI-outcome validation.

    Usage:
        vs = ValidationService()

        # Pre-processing: validate input record
        vs.validate_record(record, rules={
            "customer_id": [is_non_empty],
            "email": [is_non_empty, is_valid_email],
        })

        # Post-processing: validate UI result
        vs.validate_success_condition(
            condition=success_message_visible,
            message="Success toast not found after form submit"
        )
    """

    def validate_record(
        self,
        record: ExcelRecord,
        rules: Dict[str, List[Callable[[Any, str], None]]],
    ) -> List[str]:
        """
        Apply validation rules to an ExcelRecord.

        Args:
            record: The Excel row record to validate.
            rules:  Dict mapping field names to lists of validator callables.

        Returns:
            List of error messages (empty if valid).

        Raises:
            RowValidationError: If any validation rule fails.
        """
        errors: List[str] = []

        for field_name, validators in rules.items():
            value = getattr(record, field_name, None)
            for validator in validators:
                try:
                    validator(value, field_name)
                except RowValidationError as exc:
                    errors.append(str(exc))
                    _log.warning(
                        "Validation failed | row={row_id} | {err}",
                        row_id=record.row_id,
                        err=exc,
                    )

        if errors:
            raise RowValidationError(
                f"Record {record.row_id} failed validation: " + " | ".join(errors)
            )

        _log.debug("Record {row_id} passed validation.", row_id=record.row_id)
        return errors

    def validate_success_condition(
        self,
        condition: bool,
        message: str = "Success condition not met after action.",
    ) -> None:
        """
        Assert a boolean success condition.

        Args:
            condition: True if the action was successful.
            message:   Error message if condition is False.

        Raises:
            ValidationError: If condition is False.
        """
        if not condition:
            raise ValidationError(message)
        _log.debug("Success condition validated: {msg}", msg=message)

    def extract_required_fields(
        self,
        record: ExcelRecord,
        fields: List[str],
    ) -> Dict[str, str]:
        """
        Extract and validate that specified fields exist and are non-empty.

        Args:
            record: Excel row record.
            fields: List of field names to extract.

        Returns:
            Dict of {field: value} for all specified fields.

        Raises:
            RowValidationError: If any field is missing or empty.
        """
        result: Dict[str, str] = {}
        errors: List[str] = []

        for field in fields:
            value = getattr(record, field, None)
            if value is None or str(value).strip() == "":
                errors.append(f"'{field}' is required but missing or empty")
            else:
                result[field] = str(value).strip()

        if errors:
            raise RowValidationError(
                f"Record {record.row_id} missing required fields: " + ", ".join(errors)
            )

        return result
