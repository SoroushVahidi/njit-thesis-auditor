#!/usr/bin/env python3
"""Read owner-only aggregate UTC usage statistics."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from njit_auditor.analytics.query import query_usage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Absolute path to the analytics DB")
    parser.add_argument("--start", required=True, help="Inclusive UTC date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Exclusive UTC date, YYYY-MM-DD")
    parser.add_argument(
        "--grouping", choices=("daily", "weekly", "monthly", "custom"), default="custom",
    )
    args = parser.parse_args(argv)
    try:
        result = query_usage(args.db, args.start, args.end, args.grouping)
    except (OSError, ValueError, sqlite3.Error):
        print("Unable to read the private aggregate database or date range.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
