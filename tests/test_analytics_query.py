"""Owner access, exact and partial aggregate periods, and privacy canaries."""

import hashlib
import json
import threading
from pathlib import Path

import pytest
from test_analytics_collector import manual_collector
from test_analytics_store import NOW
from test_analytics_store import database as database

from njit_auditor.analytics.query import query_usage
from njit_auditor.analytics.schema import METRICS, PageView, SubmissionAttempted, encode
from njit_auditor.analytics.store import DEFINITION_VERSION, AggregateStore


def _seed_day(path: Path, day: str, activity: int, *, covered: bool) -> None:
    store = AggregateStore.open_existing(path)
    store.db.executemany(
        "INSERT INTO daily_count VALUES(?,?,?,?)",
        [
            (store.epoch, day, metric, activity if metric == "page_view" else 0)
            for metric in METRICS
        ],
    )
    store.db.execute(
        "INSERT INTO daily_coverage VALUES(?,?,'counter',?,?)",
        (store.epoch, day, "observed" if covered else "partial", int(not covered)),
    )
    store.close()


def test_daily_zero_partial_and_missing_data(database):
    _seed_day(database, "2030-01-01", 0, covered=True)
    _seed_day(database, "2030-01-02", 4, covered=False)
    before = hashlib.sha256(database.read_bytes()).digest()
    report = query_usage(database, "2030-01-01", "2030-01-04", "daily")
    assert report["definition_version"] == DEFINITION_VERSION
    assert report["coverage_start_utc"] == NOW.isoformat()
    full, partial, absent = report["periods"]
    assert full["coverage"] == "observed" and full["totals"]["page_view"] == 0
    assert partial["coverage"] == "partial" and partial["totals"] is None
    assert partial["observed_counts"]["page_view"] == 4
    assert absent["coverage"] == "unavailable" and absent["observed_counts"] is None
    assert hashlib.sha256(database.read_bytes()).digest() == before


def test_monday_and_custom_period_boundaries(database):
    weekly = query_usage(database, "2030-01-02", "2030-01-10", "weekly")
    assert [
        (p["start_inclusive_utc"], p["end_exclusive_utc"]) for p in weekly["periods"]
    ] == [("2030-01-02", "2030-01-07"), ("2030-01-07", "2030-01-10")]
    custom = query_usage(database, "2030-01-02", "2030-01-10")
    assert len(custom["periods"]) == 1


def test_months_use_only_complete_rollups_and_prevent_overlap(database):
    _seed_day(database, "2030-01-01", 4, covered=True)
    store = AggregateStore.open_existing(database)
    counts = dict.fromkeys(METRICS, 0)
    counts["page_view"] = 42
    for month, quality in [("2030-01", "observed"), ("2030-02", "partial")]:
        store.db.execute(
            "INSERT INTO month_rollup VALUES(?,?,?,?,?,?,?)",
            (
                store.epoch,
                month,
                DEFINITION_VERSION,
                quality,
                json.dumps(counts),
                "{}",
                NOW.isoformat(),
            ),
        )
    store.close()
    monthly = query_usage(database, "2030-01-01", "2030-03-01", "monthly")
    jan, feb = monthly["periods"]
    assert jan["totals"]["page_view"] == 42 and jan["complete_days"] == 31
    assert feb["totals"] is None and feb["coverage"] == "unavailable"
    whole_day = query_usage(database, "2030-01-01", "2030-01-02")["periods"][0]
    assert whole_day["totals"]["page_view"] == 4
    assert query_usage(database, "2030-01-02", "2030-01-03")["periods"][0]["totals"] is None


def test_permissions_symlinks_and_missing_path_fail_closed(database):
    link = database.with_name("link")
    link.symlink_to(database)
    missing = database.with_name("missing")
    for path in (link, missing, Path("relative.sqlite3")):
        with pytest.raises((OSError, ValueError)):
            query_usage(path, "2030-01-01", "2030-01-02")
    assert not missing.exists()
    database.chmod(0o644)
    with pytest.raises(ValueError, match="UNSAFE_FILE"):
        query_usage(database, "2030-01-01", "2030-01-02")


def test_day_closing_with_inflight_producer_has_no_exact_report(database):
    collector = manual_collector(database)
    for _ in range(2 * 24 * 60 - 1):
        collector.clock.advance(60)
        collector._tick()
    ready = threading.Event()
    resume = threading.Event()

    def slow_observation(day):
        assert day == "2030-01-02"
        ready.set()
        assert resume.wait(5)
        return PageView(day)

    producer = threading.Thread(target=collector.emit_current, args=(slow_observation,))
    producer.start()
    assert ready.wait(5)
    try:
        collector.clock.advance(60)
        collector._tick()
        during = query_usage(database, "2030-01-02", "2030-01-03")["periods"][0]
        assert during["coverage"] == "partial"
        assert during["totals"] is None
        assert during["observed_counts"]["page_view"] == 0
    finally:
        resume.set()
        producer.join(5)
    assert not producer.is_alive()
    collector.clock.advance(5)
    collector._tick()
    after = query_usage(database, "2030-01-02", "2030-01-03")["periods"][0]
    assert after["coverage"] == "partial"
    assert after["observed_counts"]["page_view"] == 1
    collector._disconnect()


@pytest.mark.parametrize("value", ["user@invalid", "PRIVATE_CANARY", "127.0.0.1"])
def test_closed_dimensions_reject_private_values(value):
    with pytest.raises(ValueError):
        SubmissionAttempted("2030-01-01", value)
    with pytest.raises(ValueError):
        encode(PageView("2030-01-01", value))
