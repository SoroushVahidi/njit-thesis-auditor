#!/usr/bin/env python3
"""Record or report private Windows installer counter observations."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

from njit_auditor.analytics.downloads import (
    APPROVED_INSTALLERS,
    capture,
    initialize,
    report,
    snapshot_details,
)


def _day(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected a UTC date in YYYY-MM-DD format.") from exc
    if value != parsed.isoformat():
        raise argparse.ArgumentTypeError("Expected a UTC date in YYYY-MM-DD format.")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Private snapshot SQLite path")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("init", help="Create a separate owner-only snapshot database")
    collect = commands.add_parser("capture", help="Fetch approved public asset metadata")
    collect.add_argument("--slot", required=True, type=_day, help="Intended UTC date")
    view = commands.add_parser("report", help="Read observed counter intervals for a UTC range")
    view.add_argument("--start", required=True, type=_day, help="First UTC date, inclusive")
    view.add_argument("--end", required=True, type=_day, help="Last UTC date, exclusive")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            initialize(args.db)
            return 0
        if args.action == "capture":
            results = []
            for installer in APPROVED_INSTALLERS:
                if installer.active:
                    snapshot = capture(args.db, installer, args.slot)
                    results.append({
                        "release_id": installer.release_id,
                        "asset_id": installer.asset_id,
                        **snapshot_details(snapshot),
                    })
            print(json.dumps(results, indent=2))
            return 0 if results and all(row["status"] == "observed" for row in results) else 1
        start = datetime.combine(args.start, time.min, timezone.utc)
        end = datetime.combine(args.end, time.min, timezone.utc)
        print(json.dumps(
            [report(args.db, installer, start, end) for installer in APPROVED_INSTALLERS],
            indent=2,
        ))
        return 0
    except (OSError, ValueError, sqlite3.Error):
        print("Installer snapshot operation failed. Check the private database and date range.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
