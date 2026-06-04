"""
config/constants.py
===================
Immutable framework-wide constants.
No imports from other config modules — zero circular dependency risk.
"""

from __future__ import annotations

# ------------------------------------------------------------------ #
# Framework Identity                                                   #
# ------------------------------------------------------------------ #
FRAMEWORK_NAME = "Enterprise Automation Framework"
FRAMEWORK_VERSION = "1.0.0"

# ------------------------------------------------------------------ #
# Execution Markers                                                    #
# ------------------------------------------------------------------ #
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILURE = "FAILURE"
STATUS_SKIPPED = "SKIPPED"
STATUS_PENDING = "PENDING"

# ------------------------------------------------------------------ #
# Excel Column Conventions                                             #
# ------------------------------------------------------------------ #
EXCEL_STATUS_COLUMN = "__status__"
EXCEL_ERROR_COLUMN = "__error__"
EXCEL_TIMESTAMP_COLUMN = "__timestamp__"
EXCEL_ROW_ID_COLUMN = "__row_id__"

# ------------------------------------------------------------------ #
# Timeouts (milliseconds)                                             #
# ------------------------------------------------------------------ #
TIMEOUT_IMPLICIT_MS = 500
TIMEOUT_SHORT_MS = 5_000
TIMEOUT_MEDIUM_MS = 15_000
TIMEOUT_LONG_MS = 30_000
TIMEOUT_NAVIGATION_MS = 60_000

# ------------------------------------------------------------------ #
# Retry                                                                #
# ------------------------------------------------------------------ #
RETRY_MAX_DEFAULT = 3
RETRY_BACKOFF_MIN = 1      # seconds
RETRY_BACKOFF_MAX = 10     # seconds

# ------------------------------------------------------------------ #
# Data Directories (relative to project root)                         #
# ------------------------------------------------------------------ #
DIR_INPUT = "data/input"
DIR_OUTPUT = "data/output"
DIR_FAILED = "data/failed"
DIR_SCREENSHOTS = "data/screenshots"
DIR_LOGS = "data/logs"
DIR_SESSION = "data/session"

# ------------------------------------------------------------------ #
# File Naming                                                          #
# ------------------------------------------------------------------ #
FAILED_FILE_SUFFIX = "_failed"
REPORT_FILE_SUFFIX = "_report"
SESSION_STATE_FILE = "session_state.json"

# ------------------------------------------------------------------ #
# Sensitive Field Names (for log masking)                              #
# ------------------------------------------------------------------ #
SENSITIVE_FIELDS = frozenset(
    {"password", "passwd", "token", "secret", "key", "credential", "auth"}
)

MASKED_VALUE = "****"
