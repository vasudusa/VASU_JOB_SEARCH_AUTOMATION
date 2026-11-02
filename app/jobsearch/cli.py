from __future__ import annotations

import argparse
import json
from pathlib import Path

from .paths import ROOT
from .pipeline import run_phase1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vasu Job Search Automation Phase 1")
    parser.add_argument("command", nargs="?", default="dry-run", choices=["dry-run"], help="Run Phase 1 dry-run.")
    parser.add_argument("--root", default=str(ROOT), help="Project root.")
    parser.add_argument("--no-reset-db", action="store_true", help="Do not reset SQLite before running.")
    parser.add_argument("--json", action="store_true", help="Print full JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    summary = run_phase1(root, reset_db=not args.no_reset_db)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    else:
        print("Phase 1 dry-run completed.")
        print(f"Raw jobs: {summary['raw_jobs_count']}")
        print(f"Unique jobs: {summary['unique_jobs_count']}")
        print(f"Duplicates removed: {summary['duplicates_count']}")
        print(f"Category counts: {summary['category_counts']}")
        print(f"Approval queue items: {summary['approval_queue_count']}")
        print(f"Report: {summary['report_path']}")
        print(f"Export: {summary['export_path']}")
        print(f"Database: {summary['database_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

