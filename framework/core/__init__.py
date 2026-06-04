"""
framework/core/__init__.py
"""
from framework.core.logger import get_logger
from framework.core.execution_context import ExecutionContext
from framework.core.exception_handler import (
    FrameworkError,
    AuthenticationError,
    NavigationError,
    ElementError,
    ValidationError,
    DataError,
    WorkflowError,
)

__all__ = [
    "get_logger",
    "ExecutionContext",
    "FrameworkError",
    "AuthenticationError",
    "NavigationError",
    "ElementError",
    "ValidationError",
    "DataError",
    "WorkflowError",
]
