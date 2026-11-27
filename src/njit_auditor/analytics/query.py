"""Read private aggregate date ranges with explicit UTC coverage."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from .retention import next_month
from .schema import METRICS, validate_day
from .store import DEFINITION_VERSION, validate_path, validated_metadata

Grouping = Literal["daily", "weekly", "monthly", "custom"]
_DAY = timedelta(days=1)


def _ranges(start: date, end: date, grouping: Grouping) -> Iterator[tuple[date, date]]:
    while start < end:
        if grouping == "daily":
            stop = start + _DAY
        elif grouping == "weekly":
            stop = start + timedelta(days=7 - start.weekday())
        elif grouping == "monthly":
            stop = next_month(start)
        else:
            stop = end
        yield start, min(stop, end)
        start = stop


def _sum_period(
    start: date,
    end: date,
    daily: dict[str, dict[str, int]],
    observed_days: set[str],
    months: dict[str, dict[str, int]],
) -> dict[str, object]:
    observed = dict.fromkeys(METRICS, 0)
    observed_day_count = 0
    exact_day_count = 0
    current = start
    while current < end:
        label = current.isoformat()
        month = label[:7]
        month_end = next_month(current)
        if current.day == 1 and month_end <= end and month in months:
            cells = months[month]
            span = (month_end - current).days
            exact_day_count += span
            observed_day_count += span
            current = month_end
        else:
            cells = daily.get(label, {})
            exact_day_count += int(label in observed_days and len(cells) == len(METRICS))
            observed_day_count += int(bool(cells))
            current += _DAY
        for metric, count in cells.items():
            observed[metric] += count
    total_days = (end - start).days
    exact = exact_day_count == total_days
    return {
        "start_inclusive_utc": start.isoformat(),
        "end_exclusive_utc": end.isoformat(),
        "coverage": "observed" if exact else "partial" if observed_day_count else "unavailable",
        "complete_days": exact_day_count,
        "days_with_aggregate_data": observed_day_count,
        "totals": observed if exact else None,
        "observed_counts": observed if observed_day_count else None,
    }


def query_usage(
    path: Path, start: str, end: str, grouping: Grouping = "custom"
) -> dict[str, object]:
    """Read closed dimensions, retaining incomplete coverage and suppressing exact claims."""
    validate_day(start)
    validate_day(end)
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if not first < last or last.year >= 9999 or (last - first).days > 3660:
        raise ValueError("INVALID_RANGE")
    if grouping not in ("daily", "weekly", "monthly", "custom"):
        raise ValueError("INVALID_GROUPING")
    validate_path(path)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.05)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        epoch, activated_at = validated_metadata(db)
        daily: dict[str, dict[str, int]] = {}
        for day, metric, count in db.execute(
            "SELECT day_utc,metric,n FROM daily_count WHERE epoch=? AND day_utc>=? AND day_utc<?",
            (epoch, start, end),
        ):
            daily.setdefault(day, {})[metric] = count
        observed_days = {
            day for (day,) in db.execute(
                "SELECT day_utc FROM daily_coverage WHERE epoch=? AND day_utc>=? AND day_utc<? "
                "AND component='counter' AND quality='observed' AND known_dropped=0",
                (epoch, start, end),
            )
        }
        months = {}
        for month, payload in db.execute(
            "SELECT month_utc,counts_json FROM month_rollup WHERE epoch=? AND month_utc>=? "
            "AND month_utc<=? AND definition_version=? AND coverage='observed'",
            (epoch, start[:7], end[:7], DEFINITION_VERSION),
        ):
            cells = json.loads(payload)
            if (
                type(cells) is not dict
                or cells.keys() != set(METRICS)
                or any(type(n) is not int or n < 0 for n in cells.values())
            ):
                raise ValueError("INVALID_ROLLUP")
            months[month] = cells
    return {
        "definition_version": DEFINITION_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_start_utc": activated_at.isoformat(),
        "grouping": grouping,
        "periods": [
            _sum_period(begin, finish, daily, observed_days, months)
            for begin, finish in _ranges(first, last, grouping)
        ],
    }
