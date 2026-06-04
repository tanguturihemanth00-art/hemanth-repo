"""
models/config_model.py
======================
Pydantic models for validating framework configuration at startup.
Catches misconfiguration before any browser or workflow starts.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class BrowserTimeoutModel(BaseModel):
    default: int = Field(30000, ge=1000)
    navigation: int = Field(60000, ge=1000)
    element: int = Field(15000, ge=1000)


class BrowserModel(BaseModel):
    type: str = Field("chromium", pattern="^(chromium|firefox|webkit)$")
    headless: bool = False
    slow_mo: int = Field(0, ge=0)
    timeout: BrowserTimeoutModel = Field(default_factory=BrowserTimeoutModel)
    args: List[str] = Field(default_factory=list)


class SessionModel(BaseModel):
    reuse: bool = True
    storage_path: str = "data/session/session_state.json"


class LoggingModel(BaseModel):
    level: str = Field("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    rotation: str = "10 MB"
    retention: str = "30 days"
    mask_fields: List[str] = Field(default_factory=lambda: ["password", "token"])
    console_enabled: bool = True
    file_enabled: bool = True


class RetryModel(BaseModel):
    max_attempts: int = Field(3, ge=1, le=10)
    wait_min: float = Field(1.0, ge=0.1)
    wait_max: float = Field(10.0, ge=1.0)
    multiplier: float = Field(2.0, ge=1.0)

    @model_validator(mode="after")
    def wait_min_lte_max(self) -> "RetryModel":
        if self.wait_min > self.wait_max:
            raise ValueError("retry.wait_min must be <= retry.wait_max")
        return self


class ExcelModel(BaseModel):
    engine: str = "openpyxl"
    skip_empty_rows: bool = True
    max_rows: int = Field(10000, ge=1)
    required_columns: List[str] = Field(default_factory=list)
    duplicate_check_columns: List[str] = Field(default_factory=list)


class WorkflowModel(BaseModel):
    continue_on_failure: bool = True
    screenshot_on_failure: bool = True
    screenshot_on_success: bool = False
    row_delay_ms: int = Field(500, ge=0)


class FrameworkConfigModel(BaseModel):
    """
    Root config validation model.
    Instantiate with the raw parsed YAML dict to validate on startup.
    """

    browser: BrowserModel = Field(default_factory=BrowserModel)
    session: SessionModel = Field(default_factory=SessionModel)
    logging: LoggingModel = Field(default_factory=LoggingModel)
    retry: RetryModel = Field(default_factory=RetryModel)
    excel: ExcelModel = Field(default_factory=ExcelModel)
    workflow: WorkflowModel = Field(default_factory=WorkflowModel)

    model_config = {"extra": "allow"}   # allow future yaml keys gracefully
