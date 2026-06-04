"""
main.py
========
Framework entry point.

Usage:
    python main.py --input data/input/records.xlsx
    python main.py --input data/input/records.xlsx --workflow customer_creation

Add your workflow registrations in _get_workflow() below.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Run bootstrap before anything else
from bootstrap import bootstrap

_PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enterprise Automation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input data/input/customers.xlsx
  python main.py --input data/input/tickets.xlsx --workflow ticket_update
  python main.py --bootstrap-only
        """,
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="Path to input Excel file",
    )
    parser.add_argument(
        "--workflow", "-w",
        type=str,
        default="default",
        help="Workflow name to run (default: 'default')",
    )
    parser.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Run bootstrap checks only and exit",
    )
    return parser.parse_args()


def _get_workflow(name: str):
    """
    Workflow registry.

    Register your concrete workflow classes here:

        from workflows.customer_creation import CustomerCreationWorkflow
        from workflows.ticket_update import TicketUpdateWorkflow

        registry = {
            "customer_creation": CustomerCreationWorkflow,
            "ticket_update": TicketUpdateWorkflow,
        }

    ⚠️  Add your workflow imports and mappings below.
    """
    registry: dict = {
        # "default": YourDefaultWorkflow,
        # "customer_creation": CustomerCreationWorkflow,
    }

    if not registry:
        print(
            "\n[ERROR] No workflows registered in main.py.\n"
            "  1. Create a workflow in workflows/ that extends BaseWorkflow\n"
            "  2. Import it in _get_workflow() in main.py\n"
            "  3. Add it to the registry dict\n"
        )
        sys.exit(1)

    workflow_class = registry.get(name)
    if not workflow_class:
        print(
            f"\n[ERROR] Unknown workflow: '{name}'\n"
            f"Available workflows: {list(registry.keys())}\n"
        )
        sys.exit(1)

    return workflow_class()


async def run(input_file: str, workflow_name: str) -> None:
    """Main async execution."""
    from framework.core.logger import get_logger
    log = get_logger()

    log.info("Framework starting | workflow={w} | input={f}", w=workflow_name, f=input_file)

    workflow = _get_workflow(workflow_name)
    result = await workflow.run(input_file=input_file)

    summary = result.summary()
    print()
    print("=" * 60)
    print(f"  Run Complete: {summary['workflow']}")
    print(f"  Total:   {summary['total']}")
    print(f"  Success: {summary['success']}  ✅")
    print(f"  Failed:  {summary['failure']}  ❌")
    print(f"  Skipped: {summary['skipped']}  ⏭")
    print(f"  Rate:    {summary['success_rate_pct']}%")
    print(f"  Time:    {summary['duration_seconds']}s")
    print("=" * 60)

    if summary["failure"] > 0:
        sys.exit(1)


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("  Enterprise Automation Framework")
    print("=" * 60)

    # Always run bootstrap
    bootstrap(strict=True)

    if args.bootstrap_only:
        print("Bootstrap-only mode. Exiting.")
        sys.exit(0)

    if not args.input:
        print("\n[ERROR] --input is required. Provide path to Excel file.\n")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"\n[ERROR] Input file not found: {input_path}\n")
        sys.exit(1)

    asyncio.run(run(str(input_path), args.workflow))


if __name__ == "__main__":
    main()
