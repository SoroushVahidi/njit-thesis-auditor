"""Idle coverage, discontinuities, rollup and hard retention using injected time."""

import json
from datetime import datetime, timedelta, timezone

from test_analytics_schema import FakeClock
from test_analytics_store import NOW, apply
from test_analytics_store import database as database

from njit_auditor.analytics.retention import Retention
from njit_auditor.analytics.schema import METRICS, PageView
from njit_auditor.analytics.store import DEFINITION_VERSION, AggregateStore


def test_idle_full_day_and_startup_gap(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    clock = FakeClock()
    retention.heartbeat(clock.now, clock.mono)
    assert store.db.execute("SELECT SUM(n),COUNT(*) FROM daily_count").fetchone() == (
        0, len(METRICS),
    )
    assert store.db.execute("SELECT COUNT(*) FROM daily_duration").fetchone() == (16,)
    for _ in range(2 * 24 * 60):
        clock.advance(60)
        retention.heartbeat(clock.now, clock.mono)
    assert store.db.execute(
        "SELECT DISTINCT quality FROM daily_coverage WHERE day_utc='2030-01-02'"
    ).fetchall() == [("observed",)]
    assert store.db.execute(
        "SELECT DISTINCT quality FROM daily_coverage WHERE day_utc='2030-01-01'"
    ).fetchall() == [("partial",)]
    store.close()
    store = AggregateStore.open_existing(database)
    Retention(store).heartbeat(NOW + timedelta(days=5), 1)
    assert store.db.execute(
        "SELECT DISTINCT quality FROM daily_coverage WHERE day_utc='2030-01-04'"
    ).fetchall() == [("unavailable",)]
    assert not store.db.execute("SELECT 1 FROM daily_count WHERE day_utc='2030-01-04'").fetchall()
    store.close()


def test_clock_jump_and_loss_never_upgraded(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 100)
    retention.heartbeat(NOW + timedelta(days=1), 110)
    retention.heartbeat(NOW + timedelta(days=1, minutes=1), 170, loss=True)
    assert store.db.execute("SELECT MAX(known_dropped) FROM daily_coverage").fetchone()[0] > 0
    assert not store.db.execute("SELECT 1 FROM daily_coverage WHERE quality='observed'").fetchall()
    store.close()


def test_rollup_once_and_expiry(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 0)
    apply(store, [PageView("2030-01-01")])
    later = datetime(2030, 2, 3, tzinfo=timezone.utc)
    retention.maintain(later)
    retention.maintain(later)
    row = store.db.execute("SELECT counts_json,coverage FROM month_rollup").fetchone()
    assert json.loads(row[0])["page_view"] == 1
    assert row[1] == "unavailable"  # missing days, not full-month zero
    assert store.db.execute("SELECT COUNT(*) FROM month_rollup").fetchone()[0] == 1
    retention.maintain(NOW + timedelta(days=90))
    assert store.db.execute("SELECT COUNT(*) FROM daily_count").fetchone()[0] == len(METRICS)
    retention.maintain(NOW + timedelta(days=91))
    assert store.db.execute("SELECT COUNT(*) FROM daily_count").fetchone()[0] == 0
    retention.maintain(datetime(2032, 2, 1, tzinfo=timezone.utc))
    assert store.db.execute("SELECT COUNT(*) FROM month_rollup").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM committed_batch").fetchone()[0] == 0
    store.close()


def test_expiry_despite_rollup_failure(database, monkeypatch):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 0)
    apply(store, [PageView("2030-01-01")])

    def fail(*args):
        raise RuntimeError("SYNTHETIC_ROLLUP_FAILURE")

    monkeypatch.setattr(retention, "rollup", fail)
    retention.maintain(NOW + timedelta(days=91))
    for table in ("daily_count", "daily_duration", "daily_coverage"):
        assert store.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert store.db.execute("SELECT coverage FROM month_rollup").fetchone() == ("unavailable",)
    store.close()


def test_leap_day_and_nonce_expiry(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 0)
    apply(store, [PageView("2030-01-01")])
    retention.heartbeat(NOW + timedelta(hours=48), 48 * 3600)
    assert store.db.execute("SELECT COUNT(*) FROM committed_batch").fetchone()[0] == 0
    retention.heartbeat(datetime(2032, 2, 29, tzinfo=timezone.utc), 100000000)
    assert store.db.execute("SELECT COUNT(*) FROM daily_coverage").fetchone()[0] <= 182
    store.close()


def test_broken_monthly_writes_do_not_block_raw_expiry(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 0)
    apply(store, [PageView("2030-01-01")])
    # An injected monthly-write fault affects both rollup and its missing-coverage marker.
    # The store was opened before fault injection; production schema validation rejects triggers.
    store.db.execute(
        "CREATE TRIGGER synthetic_fault BEFORE INSERT ON month_rollup "
        "BEGIN SELECT RAISE(ABORT,'synthetic monthly failure'); END"
    )
    retention.maintain(NOW + timedelta(days=91))
    assert store.db.execute("SELECT COUNT(*) FROM daily_count").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM month_rollup").fetchone()[0] == 0
    store.close()


def test_clock_loss_downgrades_closed_month_without_recount(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    store.db.execute(
        "INSERT INTO month_rollup VALUES(?,?,?,?,?,?,?)",
        (store.epoch, "2030-01", DEFINITION_VERSION, "observed", "{}", "{}", NOW.isoformat()),
    )
    store.degrade("2030-01-31", "counter")
    assert store.db.execute("SELECT coverage,counts_json FROM month_rollup").fetchone() == (
        "partial",
        "{}",
    )
    retention.maintain(datetime(2030, 2, 3, tzinfo=timezone.utc))
    assert store.db.execute("SELECT COUNT(*) FROM month_rollup").fetchone()[0] == 1
    store.close()


def test_full_database_initialization_cannot_block_expiry(database):
    """Real SQLITE_FULL on a new daily cell, followed by independently possible DELETE."""
    import sqlite3

    import pytest

    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 100)
    apply(store, [PageView("2030-01-01")])
    pages = store.db.execute("PRAGMA page_count").fetchone()[0]
    store.db.execute(f"PRAGMA max_page_count={pages}")
    # Fill the actual daily B-tree, with synthetic expired dates, until it cannot split.
    with pytest.raises(sqlite3.OperationalError, match="full"):
        for index in range(1, 2000):
            day = (NOW - timedelta(days=index)).date().isoformat()
            store.db.execute(
                "INSERT INTO daily_count VALUES(?,?,?,1)", (store.epoch, day, "page_view")
            )
    later = NOW + timedelta(days=91)
    # Confirm the precise failing boundary before exercising heartbeat's recovery path.
    with pytest.raises(sqlite3.OperationalError, match="full"):
        retention._initialize(later.date().isoformat())
    with pytest.raises(sqlite3.OperationalError, match="full"):
        retention.heartbeat(later, 100 + 91 * 86400)
    for table in ("daily_count", "daily_duration", "daily_coverage", "committed_batch"):
        assert store.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (0,)
    # Freed space permits today's cells. Full coverage-gap repair needs additional
    # capacity; simulate its restoration without resetting cutoffs or the database.
    retention._initialize(later.date().isoformat())
    store.db.execute(f"PRAGMA max_page_count={pages + 100}")
    retention.heartbeat(later, 100 + 91 * 86400)
    assert store.db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (0,)
    store.close()


def test_failed_initialization_retries_expiry_within_same_day(database, monkeypatch):
    import sqlite3

    import pytest

    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 100)
    apply(store, [PageView("2030-01-01")])
    store.db.execute(
        "UPDATE committed_batch SET expires_at_utc=?", ((NOW + timedelta(minutes=1)).isoformat(),)
    )

    def fail(day):
        raise sqlite3.OperationalError("synthetic initialization failure")

    monkeypatch.setattr(retention, "_initialize", fail)
    with pytest.raises(sqlite3.OperationalError):
        retention.heartbeat(NOW + timedelta(minutes=2), 220)
    assert store.db.execute("SELECT COUNT(*) FROM committed_batch").fetchone() == (0,)
    store.close()


def test_loss_marker_retry_preserves_larger_existing_values(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 100)
    store.db.execute("UPDATE daily_coverage SET known_dropped=7")
    for _ in range(3):
        retention.heartbeat(NOW, 100, loss_days=("2030-01-01",))
    assert store.db.execute("SELECT DISTINCT known_dropped FROM daily_coverage").fetchall() == [
        (7,)
    ]
    store.close()


def test_shutdown_loss_degrades_existing_month_without_recount(database):
    store = AggregateStore.open_existing(database)
    retention = Retention(store)
    retention.heartbeat(NOW, 100)
    store.db.execute(
        "INSERT INTO month_rollup VALUES(?,?,?,'observed',?,?,?)",
        (store.epoch, "2030-01", DEFINITION_VERSION, '{"page_view":100}', "{}", NOW.isoformat()),
    )
    for _ in range(2):
        retention.shutdown(False, now=NOW, loss_days=("2030-01-01",))
    assert store.db.execute("SELECT coverage,counts_json FROM month_rollup").fetchone() == (
        "partial",
        '{"page_view":100}',
    )
    assert store.db.execute("SELECT DISTINCT known_dropped FROM daily_coverage").fetchall() == [
        (1,)
    ]
    store.close()
