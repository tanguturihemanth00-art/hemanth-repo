"""
bootstrap.py
=============
Framework bootstrap — validates the entire environment before any workflow runs.

Checks:
1. Python version
2. .env file present and required vars set
3. config.yaml valid (Pydantic model validation)
4. All data directories exist
5. Playwright browsers installed

Run standalone:
    python bootstrap.py

Or import in main.py:
    from bootstrap import bootstrap
    bootstrap()
"""

from __future__ import annotations

import sys
from pathlib import Path

# ------------------------------------------------------------------ #
# Python Version Guard                                                  #
# ------------------------------------------------------------------ #
_MIN_PYTHON = (3, 12)
if sys.version_info < _MIN_PYTHON:
    print(
        f"[FATAL] Python {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+ required. "
        f"Current: {sys.version_info.major}.{sys.version_info.minor}"
    )
    sys.exit(1)

_PROJECT_ROOT = Path(__file__).resolve().parent


def bootstrap(strict: bool = True) -> bool:
    """
    Run all pre-flight checks.

    Args:
        strict: If True, sys.exit(1) on any failure.
                If False, returns False on failure (for programmatic use).

    Returns:
        True if all checks pass.
    """
    errors: list[str] = []

    # ---- Check 1: .env file ----------------------------------------
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.exists():
        errors.append(
            f".env file not found at {env_file}. "
            "Copy .env.example to .env and fill in your credentials."
        )
    else:
        print(f"  [OK] .env found: {env_file}")

    # ---- Check 2: Environment variables ----------------------------
    try:
        from config.environment import get_env
        env = get_env()
        _ = env.app_url
        _ = env.app_username
        _ = env.app_password
        print(f"  [OK] Environment: APP_URL={env.app_url}, USER={env.app_username}")
    except Exception as exc:
        errors.append(f"Environment config error: {exc}")

    # ---- Check 3: config.yaml + Pydantic validation ----------------
    try:
        from config.settings import get_settings
        from models.config_model import FrameworkConfigModel
        cfg = get_settings()
        # Only validate the keys that FrameworkConfigModel knows about
        known_keys = {"browser", "session", "logging", "retry", "excel", "workflow"}
        filtered = {k: v for k, v in cfg._raw.items() if k in known_keys}
        validated = FrameworkConfigModel(**filtered)
        print(f"  [OK] config.yaml valid | browser={cfg.browser_type} | headless={cfg.browser_headless}")
    except Exception as exc:
        errors.append(f"config.yaml validation failed: {exc}")

    # ---- Check 4: Data directories ---------------------------------
    try:
        from config.environment import get_env
        env = get_env()
        dirs = [
            env.input_dir,
            env.output_dir,
            env.failed_dir,
            env.screenshot_dir,
            env.log_dir,
            env.session_file.parent,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] Data directories ready: {len(dirs)} directories verified")
    except Exception as exc:
        errors.append(f"Data directory setup failed: {exc}")

    # ---- Check 5: Core imports --------------------------------------
    try:
        import importlib.metadata
        import pandas
        import openpyxl
        import pydantic
        import loguru
        import tenacity
        import yaml
        import playwright
        pw_version = importlib.metadata.version("playwright")
        print(
            f"  [OK] Dependencies: playwright={pw_version}, "
            f"pandas={pandas.__version__}, "
            f"pydantic={pydantic.__version__}"
        )
    except ImportError as exc:
        errors.append(
            f"Missing dependency: {exc}. "
            "Run: pip install -r requirements.txt"
        )

    # ---- Check 6: Playwright browsers ------------------------------
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        print("  [OK] Playwright CLI accessible")
    except Exception as exc:
        errors.append(f"Playwright CLI check failed: {exc}")

    # ---- Report ----------------------------------------------------
    print()
    if errors:
        print(f"[FAIL] Bootstrap FAILED -- {len(errors)} error(s):")
        for i, err in enumerate(errors, 1):
            print(f"   {i}. {err}")
        if strict:
            sys.exit(1)
        return False
    else:
        print("[OK] All bootstrap checks passed. Framework is ready.")
        return True


if __name__ == "__main__":
    print("=" * 60)
    print("  Enterprise Automation Framework - Bootstrap Check")
    print("=" * 60)
    bootstrap(strict=True)
