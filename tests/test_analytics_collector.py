"""Bounded queue, deterministic retries and real thread lifecycle."""

import sqlite3
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_analytics_schema import FakeClock
from test_analytics_store import database as database

from njit_auditor.analytics.collector import BoundedCollector
from njit_auditor.analytics.schema import AuditTerminal, PageView
from njit_auditor.analytics.store import AggregateStore


def manual_collector(database):
    collector = BoundedCollector(database, FakeClock())
    collector.thread = SimpleNamespace(is_alive=lambda: True)
    collector._tick()
    return collector


def start_ready(collector, monkeypatch):
    ready = threading.Event()
    tick = collector._tick

    def wrapped():
        tick()
        ready.set()

    monkeypatch.setattr(collector, "_tick", wrapped)
    collector.start()
    assert ready.wait(3), collector.status


def test_queue_and_batch_bounds_expiry(database):
    collector = manual_collector(database)
    for _ in range(1100):
        collector.emit(PageView("2030-01-01"))
    assert collector.queue.qsize() == 1000
    assert collector.dropped == 100
    collector._tick()
    assert collector.queue.qsize() == 900
    assert collector._store.db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0] == 100
    collector.clock.advance(61)
    for _ in range(9):
        collector._tick()
    assert collector.queue.empty()
    assert collector._store.db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0] == 100
    collector._disconnect()


def test_five_second_flush(database):
    collector = manual_collector(database)
    collector.emit(PageView("2030-01-01"))
    collector.clock.advance(4.99)
    collector._tick()
    assert collector.queue.qsize() == 1
    collector.clock.advance(0.01)
    collector._tick()
    assert collector.queue.empty()
    collector._disconnect()


def test_nonce_retry_after_uncertain_commit(database, monkeypatch):
    collector = manual_collector(database)
    collector.emit(AuditTerminal("2030-01-01", "completed", 2))
    collector.clock.advance(5)
    original = AggregateStore.apply_batch

    def uncertain(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise sqlite3.OperationalError("AMBIGUOUS_COMMIT")

    monkeypatch.setattr(AggregateStore, "apply_batch", uncertain)
    with pytest.raises(sqlite3.OperationalError):
        collector._tick()
    nonce = collector.pending.nonce
    collector._disconnect()
    monkeypatch.setattr(AggregateStore, "apply_batch", original)
    collector._tick()
    assert collector.pending is None
    assert collector._store.has_batch(nonce)
    assert collector._store.db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0] == 1
    assert collector._store.db.execute("SELECT SUM(n) FROM daily_duration").fetchone()[0] == 1
    collector._disconnect()


def test_live_writer_shutdown(database, monkeypatch):
    collector = BoundedCollector(database, FakeClock())
    start_ready(collector, monkeypatch)
    for _ in range(22):
        collector.emit(PageView("2030-01-01"))
    collector.stop()
    assert not collector.thread.is_alive()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0] == 22
        assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone()[0] == 1


def test_shutdown_bound_blocked_writer(database, monkeypatch):
    collector = BoundedCollector(database, FakeClock())
    entered, release = threading.Event(), threading.Event()

    def blocked():
        entered.set()
        release.wait(3)

    monkeypatch.setattr(collector, "_tick", blocked)
    collector.start()
    assert entered.wait(2)
    before = time.monotonic()
    collector.stop(0.02)
    assert time.monotonic() - before < 0.2
    assert collector.thread.is_alive()
    release.set()
    collector.thread.join(2)
    assert not collector.thread.is_alive()


def test_writer_unexpected_termination(database, monkeypatch):
    collector = BoundedCollector(database, FakeClock())

    def die():
        raise SystemExit

    monkeypatch.setattr(collector, "_tick", die)
    collector.start()
    collector.thread.join(2)
    assert not collector.thread.is_alive()
    collector.emit(PageView("2030-01-01"))
    assert collector.queue.empty()
    assert collector.dropped > 0


def test_three_failures_breaker_and_single_probe(database, monkeypatch):
    collector = BoundedCollector(database, FakeClock())
    calls = []

    def fail(path):
        calls.append(path)
        if len(calls) == 4:
            collector._stop.set()
        raise sqlite3.OperationalError("SYNTHETIC")

    monkeypatch.setattr(AggregateStore, "open_existing", fail)

    def advance(timeout):
        if len(calls) >= 3:
            assert not collector._accepting
            collector.clock.advance(30)

    monkeypatch.setattr(collector._wake, "wait", advance)
    collector._run()
    assert len(calls) == 4
    assert collector.clock.mono == 160


def test_bad_clock_type_nonce_and_payload(database, monkeypatch):
    collector = manual_collector(database)
    collector.emit({"filename": "PRIVATE_CANARY"})
    collector.clock.mono = float("nan")
    collector.emit(PageView("2030-01-01"))
    assert collector.queue.empty()
    collector.clock.mono = 100
    collector.emit(PageView("2030-01-01"))
    collector.clock.advance(5)

    def fail(n):
        raise OSError("PRIVATE_CANARY")

    monkeypatch.setattr("njit_auditor.analytics.collector.secrets.token_bytes", fail)
    with pytest.raises(OSError):
        collector._tick()
    assert collector.pending is None
    collector._disconnect()


def test_short_synthetic_performance(tmp_path):
    """Five bounded trials per mode, each in a fresh process with its own warmup.

    Disabled trials never create a collector, database or analytics writer. Raw
    measurements and between-trial variability are retained; no sub-1% claim.
    """
    import json
    import os
    import random
    import statistics
    import subprocess
    import sys

    script = r"""
import json,statistics,sys,threading,time,tracemalloc
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from njit_auditor.analytics.collector import BoundedCollector
from njit_auditor.analytics.runtime import AnalyticsRuntime
from njit_auditor.analytics.schema import PageView
from njit_auditor.analytics.store import initialize_database
from njit_auditor import web_app as wa
from test_analytics_web import synthetic_pdf

def rss():
    return int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
                    if line.startswith('VmRSS:')))*1024

def p95(values):return sorted(values)[int(.95*(len(values)-1))]
enabled=sys.argv[1]=='1'
# Diagnostics deliberately share stdout; the structured result uses its own file.
print('Synthetic benchmark trial, enabled=' + str(enabled))
with TemporaryDirectory() as temporary:
    root=Path(temporary);path=root/'analytics.sqlite3';collector=None;runtime=None
    result={'enabled':enabled,'warmup_audits':5,'measured_audits':60}
    if enabled:
        initialize_database(path,epoch='1'*32,activated_at=datetime.now(timezone.utc))
        before=rss();tracemalloc.start()
        collector=BoundedCollector(path);ready=threading.Event();tick=collector._tick
        def wrapped():tick();ready.set()
        collector._tick=wrapped;collector.start();assert ready.wait(3)
        event=PageView(datetime.now(timezone.utc).date().isoformat())
        for _ in range(100):collector.emit(event)
        samples=[]
        for _ in range(1000):
            start=time.perf_counter_ns();collector.emit(event)
            samples.append((time.perf_counter_ns()-start)/1e6)
        peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop();added=max(0,rss()-before)
        result.update(producer_p95_ms=p95(samples),producer_median_ms=statistics.median(samples),
            producer_samples=len(samples),queue_limit=collector.queue.maxsize,
            tracemalloc_peak_bytes=peak,rss_added_bytes=added)
        runtime=AnalyticsRuntime(collector)
    else:
        assert not path.exists()
        assert not any(t.name=='njit-analytics-writer' for t in threading.enumerate())
    wa.RUNTIME_DIR=root/'uploads';wa._jobs={};wa._after_audit_task=None
    pdf=synthetic_pdf();measurements=[]
    for index in range(65):
        job_id='syntheticjob00001';directory=wa._job_dir(job_id);directory.mkdir(parents=True)
        wa._job_pdf_path(directory).write_bytes(pdf)
        wa._set_job(wa.JobState(job_id=job_id,state='pending',
            created_at=datetime.now(timezone.utc).isoformat(),file_name='synthetic.pdf'))
        start=time.perf_counter_ns()
        if enabled:wa._run_web_audit(job_id,runtime)
        else:wa._run_audit_task(job_id)
        elapsed=(time.perf_counter_ns()-start)/1e6
        assert wa._get_job(job_id).state=='complete'
        if index>=5:measurements.append(elapsed)
        wa._delete_job_workspace(job_id);wa._jobs.clear()
    if collector:
        collector.stop();assert not collector.thread.is_alive()
    else:
        assert not path.exists()
        assert not any(t.name=='njit-analytics-writer' for t in threading.enumerate())
    result.update(audit_samples_ms=measurements,audit_p95_ms=p95(measurements),
        audit_median_ms=statistics.median(measurements),
        audit_stdev_ms=statistics.stdev(measurements),disabled_writer_absent=not enabled)
    Path(sys.argv[2]).write_text(json.dumps(result), encoding="utf-8")
"""
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(root / "src"), str(root / "tests")]))
    trials = []
    rng = random.Random(42)
    for trial in range(5):
        order = [False, True]
        rng.shuffle(order)
        pair = {}
        for enabled in order:
            result_path = tmp_path / f"trial-{trial}-{int(enabled)}.json"
            result = subprocess.run(
                [sys.executable, "-c", script, str(int(enabled)), str(result_path)],
                env=env,
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stderr
            values = json.loads(result_path.read_text(encoding="utf-8"))
            if enabled:
                assert values["queue_limit"] == 1000
                assert values["producer_p95_ms"] < 2
                assert values["rss_added_bytes"] < 32 * 1024 * 1024
                assert values["tracemalloc_peak_bytes"] < 32 * 1024 * 1024
            else:
                assert values["disabled_writer_absent"]
            pair["enabled" if enabled else "disabled"] = values
        pair["trial"] = trial + 1
        pair["order"] = order
        pair["p95_change_percent"] = 100 * (
            pair["enabled"]["audit_p95_ms"] / pair["disabled"]["audit_p95_ms"] - 1
        )
        trials.append(pair)
    changes = [trial["p95_change_percent"] for trial in trials]
    values = {
        "trials": trials,
        "trial_count": len(trials),
        "median_p95_change_percent": statistics.median(changes),
        "min_p95_change_percent": min(changes),
        "max_p95_change_percent": max(changes),
        "stdev_p95_change_percent": statistics.stdev(changes),
        "uncertainty": "Five short trials on one host; descriptive spread, not a confidence "
        "interval or evidence of consistently sub-1% overhead.",
    }
    print("SYNTHETIC_PERFORMANCE " + json.dumps(values, sort_keys=True))
    destination = os.environ.get("ANALYTICS_BENCHMARK_RESULT")
    if destination:
        Path(destination).write_text(json.dumps(values, indent=2) + "\n")


@pytest.mark.parametrize("location", ["queue", "pending", "reconnect", "breaker"])
def test_january_second_loss_at_third_midnight(database, monkeypatch, location):
    from datetime import datetime, timezone

    collector = manual_collector(database)
    # Establish an eligible January 2, then observe every minute through 23:59.
    for _ in range(2 * 24 * 60 - 1):
        collector.clock.advance(60)
        collector._tick()
    assert collector.clock.now == datetime(2030, 1, 2, 23, 59, tzinfo=timezone.utc)
    assert collector._retention.eligible == "2030-01-02"
    collector.emit(PageView("2030-01-02"))
    store = collector._store
    store.db.execute(
        "INSERT INTO month_rollup VALUES(?,?,1,'observed','{}','{}',?)",
        (store.epoch, "2030-01", collector.clock.now.isoformat()),
    )
    if location in ("pending", "reconnect"):
        original = AggregateStore.apply_batch

        def unavailable(*args, **kwargs):
            raise sqlite3.OperationalError("synthetic unavailable")

        monkeypatch.setattr(AggregateStore, "apply_batch", unavailable)
        collector.clock.advance(5)
        with pytest.raises(sqlite3.OperationalError):
            collector._tick()
        assert collector.pending is not None
        monkeypatch.setattr(AggregateStore, "apply_batch", original)
        if location == "reconnect":
            collector._disconnect()
        collector.clock.advance(55)
    else:
        collector.clock.advance(60)
    if location == "breaker":
        collector._probe_at = collector.clock.mono + 60
        collector._tick()
        collector.clock.advance(60)
    collector._tick()
    db = collector._store.db
    assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (0,)
    rows = db.execute(
        "SELECT quality,known_dropped FROM daily_coverage WHERE day_utc='2030-01-02'"
    ).fetchall()
    assert len(rows) == 2 and all(q != "observed" and n >= 1 for q, n in rows)
    assert db.execute("SELECT coverage,counts_json FROM month_rollup").fetchone() == (
        "partial",
        "{}",
    )
    collector._disconnect()


def test_concurrent_overflow_during_loss_consumption(database):
    collector = manual_collector(database)
    for _ in range(1000):
        collector.emit(PageView("2030-01-01"))
    collector.mark_loss()
    produced = threading.Event()

    class InterleavedDays(set):
        def clear(self):
            # Force a producer precisely between snapshot read and clear, while the
            # writer owns the lock. Producer must return without waiting for release.
            producer = threading.Thread(
                target=lambda: (collector.emit(PageView("2030-01-01")), produced.set())
            )
            producer.start()
            assert produced.wait(1)
            producer.join(1)
            super().clear()

    collector._loss_days = InterleavedDays(collector._loss_days)
    days, unknown = collector._take_loss()
    assert days == ("2030-01-01",) and not unknown
    assert collector._loss  # concurrent notification survived snapshot consumption
    collector._loss_days = set()
    collector._tick()
    assert (
        collector._store.db.execute("SELECT MIN(known_dropped) FROM daily_coverage").fetchone()[0]
        >= 1
    )
    collector._disconnect()


def test_loss_snapshot_restored_when_heartbeat_fails(database, monkeypatch):
    collector = manual_collector(database)
    collector._drop("EXPIRED", "2030-01-01")
    original = collector._retention.heartbeat

    def fail(*args, **kwargs):
        collector._drop("EXPIRED", "2030-01-02")
        raise sqlite3.OperationalError("synthetic")

    monkeypatch.setattr(collector._retention, "heartbeat", fail)
    with pytest.raises(sqlite3.OperationalError):
        collector._tick()
    assert collector._loss_days == {"2030-01-01", "2030-01-02"}
    monkeypatch.setattr(collector._retention, "heartbeat", original)
    collector._tick()
    assert not collector._loss
    collector._disconnect()


@pytest.mark.parametrize("boundary", ["open", "heartbeat", "lookup", "begin", "nonce", "count"])
def test_expiry_after_blocking_storage(database, monkeypatch, boundary):
    collector = manual_collector(database)
    collector.emit(AuditTerminal("2030-01-01", "completed", 2))
    collector.clock.advance(5)
    if boundary == "open":
        collector._disconnect()
        original = AggregateStore.open_existing

        def slow(path):
            store = original(path)
            collector.clock.advance(60)
            return store

        monkeypatch.setattr(AggregateStore, "open_existing", slow)
    elif boundary == "heartbeat":
        original = collector._retention.heartbeat

        def slow(*args, **kwargs):
            original(*args, **kwargs)
            collector.clock.advance(60)

        monkeypatch.setattr(collector._retention, "heartbeat", slow)
        collector.mark_loss()
    elif boundary == "lookup":
        original = collector._store.has_batch

        def slow(nonce):
            result = original(nonce)
            collector.clock.advance(60)
            return result

        monkeypatch.setattr(collector._store, "has_batch", slow)
    else:
        prefix = {
            "begin": "BEGIN IMMEDIATE",
            "nonce": "INSERT INTO committed_batch",
            "count": "INSERT INTO daily_count",
        }[boundary]
        fired = []

        def slow(statement):
            if statement.startswith(prefix) and not fired:
                fired.append(True)
                collector.clock.advance(60)

        collector._store.db.set_trace_callback(slow)
    collector._tick()
    db = collector._store.db
    assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (0,)
    assert db.execute("SELECT SUM(n) FROM daily_duration").fetchone() == (0,)
    assert db.execute("SELECT COUNT(*) FROM committed_batch").fetchone() == (0,)
    assert db.execute("SELECT MIN(known_dropped) FROM daily_coverage").fetchone()[0] >= 1
    assert collector.pending is None and collector.queue.empty()
    collector._disconnect()


def test_commit_crossing_deadline_preserves_atomic_counts_and_marks_loss(database):
    collector = manual_collector(database)
    collector.emit(AuditTerminal("2030-01-01", "completed", 2))
    collector.clock.advance(5)
    fired = []

    def slow_commit(statement):
        if statement == "COMMIT" and not fired:
            fired.append(True)
            collector.clock.advance(60)

    db = collector._store.db
    db.set_trace_callback(slow_commit)
    collector._tick()
    assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (1,)
    assert db.execute("SELECT SUM(n) FROM daily_duration").fetchone() == (1,)
    assert db.execute("SELECT COUNT(*) FROM committed_batch").fetchone() == (1,)
    assert db.execute("SELECT MIN(known_dropped) FROM daily_coverage").fetchone()[0] >= 1
    assert collector.pending is None
    collector._tick()
    assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (1,)
    collector._disconnect()


def test_rejected_future_date_cannot_create_retained_coverage(database):
    collector = manual_collector(database)
    collector.emit(PageView("2099-01-01"))
    assert collector.queue.empty()
    collector._tick()
    assert collector._store.db.execute(
        "SELECT DISTINCT day_utc FROM daily_coverage"
    ).fetchall() == [("2030-01-01",)]
    assert (
        collector._store.db.execute("SELECT MIN(known_dropped) FROM daily_coverage").fetchone()[0]
        >= 1
    )
    collector._disconnect()


def prepared_midnight_collector(database):
    """Seed a healthy history; full-day heartbeat qualification is tested separately."""
    collector = manual_collector(database)
    collector.clock.advance(2 * 86400 - 60)
    collector._tick()
    db = collector._store.db
    db.execute("UPDATE daily_coverage SET quality='observed',known_dropped=0")
    db.execute("UPDATE daily_coverage SET quality='partial' WHERE day_utc='2030-01-02'")
    collector._retention.eligible = "2030-01-02"
    collector.clock.advance(59)
    return collector


@pytest.mark.parametrize(
    "scenario",
    [
        "before",
        "after",
        "mixed",
        "pending",
        "shutdown_failure",
        "process_death",
        "mixed_shutdown_failure",
        "shutdown_after_commit",
    ],
)
def test_shutdown_original_dates_restart_and_month(database, monkeypatch, scenario):
    import json
    from datetime import datetime, timedelta, timezone

    from njit_auditor.analytics.retention import Retention

    collector = prepared_midnight_collector(database)
    first_day = "2030-01-02"
    second_day = "2030-01-01" if scenario in ("mixed", "mixed_shutdown_failure") else first_day
    for day in [first_day] * 100 + [second_day] * 100:
        collector.emit(PageView(day))
    persisted = 0
    if scenario != "before":
        collector.clock.advance(1)
        if scenario == "pending":
            with monkeypatch.context() as patch:
                patch.setattr(
                    AggregateStore,
                    "apply_batch",
                    lambda *a, **k: (_ for _ in ()).throw(
                        sqlite3.OperationalError("synthetic batch failure")
                    ),
                )
                with pytest.raises(sqlite3.OperationalError):
                    collector._tick()
            assert collector.pending is not None
        else:
            collector._tick()
            persisted = 100
        assert collector.queue.qsize() == 100
        # Coverage is already conservative before teardown or process death.
        assert collector._store.db.execute(
            "SELECT COUNT(*) FROM daily_coverage WHERE day_utc=? AND quality='observed'",
            (second_day,),
        ).fetchone() == (0,)
    if scenario in ("shutdown_failure", "mixed_shutdown_failure", "shutdown_after_commit"):
        original_shutdown = collector._retention.shutdown

        def fail(*args, **kwargs):
            if scenario == "shutdown_after_commit":
                original_shutdown(*args, **kwargs)
            raise sqlite3.OperationalError("synthetic shutdown write failure")

        monkeypatch.setattr(collector._retention, "shutdown", fail)
    if scenario == "process_death":
        # No finalizer or RAM transfer to the new collector; only durable metadata survives.
        collector._disconnect()
    else:
        collector._stop.set()
        collector._shutdown_deadline = time.monotonic() - 1
        collector._run()
        assert collector.pending is None and collector.queue.empty()
    restarted = BoundedCollector(database, collector.clock)
    restarted.thread = SimpleNamespace(is_alive=lambda: True)
    restarted._tick()
    db = restarted._store.db
    rows = db.execute(
        "SELECT quality,known_dropped FROM daily_coverage WHERE day_utc=?", (second_day,)
    ).fetchall()
    assert len(rows) == 2 and all(q != "observed" for q, _ in rows)
    if scenario not in ("shutdown_failure", "mixed_shutdown_failure", "process_death"):
        assert all(n == 1 for _, n in rows)
    assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (persisted,)
    # Fill the other days with synthetic healthy coverage, then form the real rollup.
    # The lost day remains uncertain and must prevent a falsely observed month.
    for offset in range(31):
        day = (datetime(2030, 1, 1) + timedelta(days=offset)).date().isoformat()
        if day == second_day:
            continue
        for component in ("counter", "duration"):
            db.execute(
                "INSERT INTO daily_coverage VALUES(?,?,?,'observed',0) "
                "ON CONFLICT DO UPDATE SET quality='observed',known_dropped=0",
                (restarted._store.epoch, day, component),
            )
    retention = Retention(restarted._store)
    later = datetime(2030, 2, 3, tzinfo=timezone.utc)
    retention.maintain(later)
    month = db.execute(
        "SELECT coverage,counts_json FROM month_rollup WHERE month_utc='2030-01'"
    ).fetchone()
    assert month[0] != "observed"
    assert json.loads(month[1])["page_view"] == persisted
    retention.maintain(later)
    assert (
        db.execute(
            "SELECT coverage,counts_json FROM month_rollup WHERE month_utc='2030-01'"
        ).fetchone()
        == month
    )
    restarted._disconnect()


def test_single_contended_overflow_is_idle_after_persistence(database):
    collector = manual_collector(database)
    for _ in range(1000):
        collector.emit(PageView("2030-01-01"))
    with collector._loss_lock:
        producer = threading.Thread(target=lambda: collector.emit(PageView("2030-01-01")))
        producer.start()
        producer.join(1)
        assert not producer.is_alive()  # returns while writer still owns snapshot lock
    for _ in range(10):
        collector._tick()
    db = collector._store.db
    assert collector.queue.empty() and not collector._loss
    assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (1000,)
    assert db.execute("SELECT DISTINCT known_dropped FROM daily_coverage").fetchall() == [(1,)]
    trace = []
    db.set_trace_callback(trace.append)
    for _ in range(10):
        collector._tick()
    assert trace.count("BEGIN IMMEDIATE") == 0
    assert db.execute("SELECT DISTINCT known_dropped FROM daily_coverage").fetchall() == [(1,)]
    collector._disconnect()


def test_contended_loss_keeps_original_date_across_midnight(database):
    collector = prepared_midnight_collector(database)
    with collector._loss_lock:
        collector._drop("ENQUEUE_LOSS", "2030-01-02")
    collector.clock.advance(1)
    collector._tick()
    db = collector._store.db
    assert db.execute(
        "SELECT DISTINCT quality,known_dropped FROM daily_coverage WHERE day_utc='2030-01-02'"
    ).fetchall() == [("partial", 1)]
    assert db.execute(
        "SELECT MAX(known_dropped) FROM daily_coverage WHERE day_utc='2030-01-03'"
    ).fetchone() == (0,)
    collector._disconnect()


@pytest.mark.parametrize("phase", ["before_commit", "after_commit", "maintenance"])
def test_loss_persistence_retry_is_idempotent(database, monkeypatch, phase):
    from njit_auditor.analytics.retention import Retention

    collector = manual_collector(database)
    collector._drop("ENQUEUE_LOSS", "2030-01-01")
    original = Retention._heartbeat
    failed = []

    def fault(self, *args, **kwargs):
        if not failed:
            failed.append(True)
            if phase != "before_commit":
                original(self, *args, **kwargs)
            raise sqlite3.OperationalError("synthetic ambiguous heartbeat")
        return original(self, *args, **kwargs)

    if phase == "maintenance":
        collector._retention.maintenance_day = None
        original_maintain = Retention.maintain

        def fail_maintenance(self, now):
            if not failed:
                failed.append(True)
                raise sqlite3.OperationalError("synthetic maintenance after commit")
            return original_maintain(self, now)

        monkeypatch.setattr(Retention, "maintain", fail_maintenance)
    else:
        monkeypatch.setattr(Retention, "_heartbeat", fault)
    with pytest.raises(sqlite3.OperationalError):
        collector._tick()
    assert collector._loss
    collector._disconnect()
    collector._tick()
    assert not collector._loss
    db = collector._store.db
    assert db.execute("SELECT DISTINCT known_dropped FROM daily_coverage").fetchall() == [(1,)]
    for _ in range(3):
        collector._drop("ENQUEUE_LOSS", "2030-01-01")
        collector._tick()
    # This field is a coalesced lower bound (presence), not an exact lost-event total.
    assert db.execute("SELECT DISTINCT known_dropped FROM daily_coverage").fetchall() == [(1,)]
    collector._disconnect()


def test_loss_during_persistence_survives_acknowledgement(database, monkeypatch):
    collector = manual_collector(database)
    collector._drop("ENQUEUE_LOSS", "2030-01-01")
    heartbeat = collector._retention.heartbeat
    notified = []

    def interleaved(*args, **kwargs):
        result = heartbeat(*args, **kwargs)
        if not notified:
            notified.append(True)
            producer = threading.Thread(
                target=lambda: collector._drop("ENQUEUE_LOSS", "2030-01-02")
            )
            producer.start()
            producer.join(1)
            assert not producer.is_alive()
        return result

    monkeypatch.setattr(collector._retention, "heartbeat", interleaved)
    collector._heartbeat()
    assert collector._loss_days == {"2030-01-02"}
    collector.clock.advance(86400)
    collector._heartbeat()
    assert not collector._loss
    assert collector._store.db.execute(
        "SELECT DISTINCT known_dropped FROM daily_coverage WHERE day_utc='2030-01-02'"
    ).fetchall() == [(1,)]
    collector._disconnect()


def test_saturated_loss_mailbox_is_persistent_uncertainty_not_idle_work(database):
    collector = manual_collector(database)
    with collector._loss_lock:
        for _ in range(1001):
            collector._drop("ENQUEUE_LOSS", "2030-01-01")
    assert collector._loss_saturated.is_set()
    collector._tick()
    assert not collector._loss and collector._saturation_persisted
    db = collector._store.db
    original = db.execute("SELECT * FROM daily_coverage").fetchall()
    trace = []
    db.set_trace_callback(trace.append)
    for _ in range(10):
        collector._tick()
    assert trace.count("BEGIN IMMEDIATE") == 0
    assert db.execute("SELECT * FROM daily_coverage").fetchall() == original
    collector.clock.advance(60)
    collector._tick()
    assert trace.count("BEGIN IMMEDIATE") == 1
    assert db.execute("SELECT * FROM daily_coverage").fetchall() == original
    collector._disconnect()
    collector._tick()
    assert not collector._loss
    assert collector._store.db.execute(
        "SELECT DISTINCT known_dropped FROM daily_coverage"
    ).fetchall() == [(1,)]
    collector._disconnect()


def test_loss_survives_breaker_recovery_without_recount(database):
    collector = manual_collector(database)
    collector.emit(PageView("2030-01-01"))
    collector._probe_at = collector.clock.mono + 60
    collector._tick()
    assert collector.queue.empty() and collector._loss
    collector._disconnect()
    collector.clock.advance(60)
    collector._tick()
    assert not collector._loss
    assert collector._store.db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (0,)
    assert collector._store.db.execute(
        "SELECT DISTINCT known_dropped FROM daily_coverage"
    ).fetchall() == [(1,)]
    collector._disconnect()


def test_blocked_shutdown_persistence_keeps_join_budget(database, monkeypatch):
    from njit_auditor.analytics.retention import Retention

    collector = BoundedCollector(database, FakeClock())
    entered, release = threading.Event(), threading.Event()
    original = Retention.shutdown

    def blocked(self, *args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Retention, "shutdown", blocked)
    start_ready(collector, monkeypatch)
    collector.emit(PageView("2030-01-01"))
    before = time.monotonic()
    collector.stop(0.02)
    assert time.monotonic() - before < 0.2
    assert entered.wait(1) and collector.thread.is_alive()
    release.set()
    collector.thread.join(2)
    assert not collector.thread.is_alive()


def test_saturation_acknowledged_only_after_success(database, monkeypatch):
    collector = manual_collector(database)
    with collector._loss_lock:
        for _ in range(1001):
            collector._drop("ENQUEUE_LOSS", "2030-01-01")
    original = collector._retention.heartbeat

    def ambiguous(*args, **kwargs):
        original(*args, **kwargs)
        raise sqlite3.OperationalError("synthetic uncertain commit")

    monkeypatch.setattr(collector._retention, "heartbeat", ambiguous)
    with pytest.raises(sqlite3.OperationalError):
        collector._tick()
    assert not collector._saturation_persisted and collector._loss
    collector._disconnect()
    collector._tick()
    assert collector._saturation_persisted and not collector._loss
    assert collector._store.db.execute(
        "SELECT DISTINCT known_dropped FROM daily_coverage"
    ).fetchall() == [(1,)]
    collector._disconnect()


def test_new_saturation_during_snapshot_is_not_erased(database):
    collector = manual_collector(database)
    collector.mark_loss()

    class SaturatingDays(set):
        def clear(self):
            def producer():
                for _ in range(1001):
                    collector._drop("ENQUEUE_LOSS", "2030-01-01")

            thread = threading.Thread(target=producer)
            thread.start()
            thread.join(1)
            assert not thread.is_alive()
            super().clear()

    collector._loss_days = SaturatingDays(collector._loss_days)
    collector._heartbeat()
    assert collector._loss and not collector._saturation_persisted
    collector._loss_days = set()
    collector._heartbeat()
    assert collector._saturation_persisted and not collector._loss
    assert collector._store.db.execute(
        "SELECT DISTINCT known_dropped FROM daily_coverage"
    ).fetchall() == [(1,)]
    collector._disconnect()


@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize("producers", [1, 8])
def test_shutdown_interleaves_queue_admission(database, monkeypatch, phase, producers):
    """A paused put must either precede closure or fail; never strand an envelope."""
    collector = BoundedCollector(database, FakeClock())
    start_ready(collector, monkeypatch)
    entered = threading.Barrier(producers + 1)
    release = threading.Event()
    original = collector.queue.put_nowait
    accepted = []

    def paused(item):
        if phase == "after":
            try:
                original(item)
                accepted.append(item)
            finally:
                entered.wait(3)
                assert release.wait(3)
        else:
            entered.wait(3)
            assert release.wait(3)
            original(item)

    monkeypatch.setattr(collector.queue, "put_nowait", paused)
    threads = [threading.Thread(target=collector.emit, args=(PageView("2030-01-01"),))
               for _ in range(producers)]
    try:
        for thread in threads:
            thread.start()
        entered.wait(3)
        collector.stop()
        assert not collector.thread.is_alive()
    finally:
        release.set()
        for thread in threads:
            thread.join(3)
        collector.stop()
    assert all(not thread.is_alive() for thread in threads)
    assert collector.queue.empty()
    with sqlite3.connect(database) as db:
        persisted = db.execute("SELECT COALESCE(SUM(n),0) FROM daily_count").fetchone()[0]
    assert persisted == len(accepted)
    assert persisted + collector.dropped == producers
    if phase == "before":
        assert collector.dropped == producers


@pytest.mark.parametrize("publication", ["after_shutdown", "during_snapshot"])
def test_terminal_rejected_producer_cannot_leave_observed_coverage(
    database, monkeypatch, publication,
):
    collector = prepared_midnight_collector(database)
    collector.clock.advance(1)
    collector._tick()
    assert collector._store.db.execute(
        "SELECT DISTINCT quality FROM daily_coverage WHERE day_utc='2030-01-02'"
    ).fetchall() == [("observed",)]
    entered, release = threading.Event(), threading.Event()
    record = collector._record_loss

    def paused(day, **kwargs):
        if threading.current_thread() is producer:
            entered.set()
            assert release.wait(3)
        return record(day, **kwargs)

    monkeypatch.setattr(collector, "_record_loss", paused)
    producer = threading.Thread(target=collector.emit, args=(PageView("2030-01-02"),))
    try:
        # The insertion has failed BEFORE shutdown, but its dated loss is unpublished.
        with collector.queue.mutex:
            producer.start()
            assert entered.wait(2)
        if publication == "during_snapshot":
            class ReleaseDuringSnapshot(set):
                def clear(self):
                    release.set()
                    producer.join(2)
                    assert not producer.is_alive()
                    super().clear()

            collector._loss_days = ReleaseDuringSnapshot()
        collector._stop.set()
        collector._shutdown_deadline = 0
        collector._run()
        with sqlite3.connect(database) as db:
            before = db.execute(
                "SELECT * FROM daily_coverage ORDER BY day_utc,component"
            ).fetchall()
            assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone() == (0,)
            rows = db.execute(
                "SELECT quality,known_dropped FROM daily_coverage WHERE day_utc='2030-01-02'"
            ).fetchall()
            # Unresolved publication is uncertainty, not an invented exact loss count.
            assert rows == [("partial", 0), ("partial", 0)]
            assert db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (0,)
    finally:
        release.set()
        producer.join(3)
        collector._disconnect()
    assert not producer.is_alive()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone() == (0,)
        assert db.execute(
            "SELECT * FROM daily_coverage ORDER BY day_utc,component"
        ).fetchall() == before
    restarted = BoundedCollector(database, collector.clock)
    restarted.thread = SimpleNamespace(is_alive=lambda: True)
    restarted._tick()
    assert restarted._store.db.execute(
        "SELECT DISTINCT quality FROM daily_coverage WHERE day_utc='2030-01-02'"
    ).fetchall() == [("unavailable",)]
    restarted._disconnect()


def test_loss_publication_does_not_wait_for_mailbox_mutex(database):
    collector = manual_collector(database)
    collector.queue.closed.set()
    done = threading.Event()

    def emit():
        collector.emit(PageView("2030-01-01"))
        done.set()

    producer = threading.Thread(target=emit)
    try:
        with collector._loss_lock, collector._contended_loss.mutex:
            producer.start()
            completed_without_mutex = done.wait(0.5)
        producer.join(2)
        assert completed_without_mutex
        collector._stop.set()
        collector._shutdown_deadline = 0
        collector._run()
        with sqlite3.connect(database) as db:
            assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone() == (0,)
            assert db.execute(
                "SELECT DISTINCT quality,known_dropped FROM daily_coverage"
            ).fetchall() == [("partial", 1)]
    finally:
        producer.join(2)
        collector._disconnect()


@pytest.mark.parametrize("phase", ["before_publication", "after_publication"])
def test_overlapping_stop_preserves_zero_budget(tmp_path, monkeypatch, phase):
    collector = BoundedCollector(tmp_path / "absent.sqlite3", FakeClock())
    collector.thread = SimpleNamespace(is_alive=lambda: True, join=lambda timeout: None)
    entered, release = threading.Event(), threading.Event()
    real_lock = collector._stop_lock

    class PausedLock:
        def acquire(self, **kwargs):
            acquired = real_lock.acquire(**kwargs)
            if acquired and phase == "before_publication":
                entered.set()
                assert release.wait(3)
            return acquired

        def release(self):
            if phase == "after_publication":
                entered.set()
                assert release.wait(3)
            real_lock.release()

    monkeypatch.setattr(collector, "_stop_lock", PausedLock())
    first = threading.Thread(target=collector.stop, args=(1,))
    first.start()
    try:
        assert entered.wait(2)
        started = time.monotonic()
        collector.stop(0)
        assert time.monotonic() - started < 0.2
        signalled = collector._stop.is_set()
    finally:
        release.set()
        first.join(2)
    assert signalled
    ticks = []
    monkeypatch.setattr(collector, "_tick", lambda: ticks.append(True))
    collector._run()
    assert ticks == []  # the effective zero deadline survives the first caller resuming
    assert collector.queue.closed.is_set()
    assert not collector.path.exists()


@pytest.mark.parametrize("phase", ["before_append", "after_append"])
def test_shutdown_suspended_insertion_is_bounded_and_uncertain(database, monkeypatch, phase):
    collector = manual_collector(database)
    collector.emit(PageView("2030-01-01"))
    collector.clock.advance(86400)
    collector._tick()
    # One already accepted envelope must be conservatively accounted for even
    # when shutdown cannot acquire the mutex to inspect its original date.
    collector.emit(PageView("2030-01-02"))
    entered, release = threading.Event(), threading.Event()
    original = collector.queue._put

    def paused(item):
        if phase == "after_append":
            original(item)
        entered.set()
        assert release.wait(3)
        if phase == "before_append":
            original(item)

    monkeypatch.setattr(collector.queue, "_put", paused)
    producer = threading.Thread(target=collector.emit, args=(PageView("2030-01-01"),))
    producer.start()
    try:
        assert entered.wait(2)
        collector._stop.set()
        collector._shutdown_deadline = 0
        start = time.monotonic()
        collector._run()
        assert time.monotonic() - start < 0.5
        with sqlite3.connect(database) as db:
            assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone() == (0,)
            rows = db.execute("SELECT day_utc,quality FROM daily_coverage").fetchall()
            assert {day for day, _ in rows} >= {"2030-01-01", "2030-01-02"}
            assert all(quality != "observed" for _, quality in rows)
    finally:
        release.set()
        producer.join(3)
        collector._disconnect()
    assert not producer.is_alive()
    assert collector.queue.qsize() == 1
    assert collector.queue.closed.is_set()


def test_producer_does_not_wait_for_queue_mutex(database):
    collector = manual_collector(database)
    done = threading.Event()

    def emit():
        collector.emit(PageView("2030-01-01"))
        done.set()

    producer = threading.Thread(target=emit)
    with collector.queue.mutex:
        producer.start()
        completed_without_mutex = done.wait(0.5)
    producer.join(2)
    try:
        assert completed_without_mutex
        assert collector.queue.empty()
        collector._tick()
        assert collector._store.db.execute(
            "SELECT MIN(known_dropped) FROM daily_coverage WHERE day_utc='2030-01-01'"
        ).fetchone() == (1,)
    finally:
        collector._disconnect()


def test_enqueue_error_releases_mutex_and_retains_dated_loss(database, monkeypatch):
    collector = manual_collector(database)
    original = collector.queue._put
    try:
        with monkeypatch.context() as patch:
            def fail(item):
                raise OSError("synthetic enqueue failure")
            patch.setattr(collector.queue, "_put", fail)
            collector.emit(PageView("2030-01-01"))
        collector.emit(PageView("2030-01-01"))
        assert collector.queue.qsize() == 1
        assert collector.queue._put == original
        collector.clock.advance(5)
        collector._tick()
        assert collector._store.db.execute("SELECT SUM(n) FROM daily_count").fetchone() == (1,)
        assert collector._store.db.execute(
            "SELECT MIN(known_dropped) FROM daily_coverage"
        ).fetchone() == (1,)
    finally:
        collector._disconnect()


def test_repeated_shutdown_never_reopens_or_extends_deadline(tmp_path):
    collector = BoundedCollector(tmp_path / "absent.sqlite3", FakeClock())
    collector.thread = SimpleNamespace(is_alive=lambda: True, join=lambda timeout: None)
    collector._accepting = True
    collector.stop(0.01)
    deadline = collector._shutdown_deadline
    collector.stop(1)
    assert collector._shutdown_deadline <= deadline
    # Even a stale accepting flag cannot reopen the closed admission boundary.
    collector._accepting = True
    collector.emit(PageView("2030-01-01"))
    assert collector.queue.empty()
    assert collector.dropped == 1
    assert not collector.path.exists()


def test_concurrent_stop_call_does_not_wait_for_stop_lock(tmp_path):
    collector = BoundedCollector(tmp_path / "absent.sqlite3", FakeClock())
    collector.thread = SimpleNamespace(is_alive=lambda: True, join=lambda timeout: None)
    done = threading.Event()

    def stop():
        collector.stop(0)
        done.set()

    with collector._stop_lock:
        other = threading.Thread(target=stop)
        other.start()
        completed = done.wait(0.5)
    other.join(2)
    assert completed
    assert collector.queue.closed.is_set()
    collector.stop(0)
    deadline = collector._shutdown_deadline
    threads = [threading.Thread(target=collector.stop, args=(1,)) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(2)
    assert collector._shutdown_deadline == deadline
    assert all(not thread.is_alive() for thread in threads)


@pytest.mark.parametrize("held", ["loss", "mailbox"])
def test_terminal_snapshot_does_not_wait_for_loss_mutexes(database, held):
    collector = manual_collector(database)
    entered, release = threading.Event(), threading.Event()
    lock = collector._loss_lock if held == "loss" else collector._contended_loss.mutex

    def holder():
        with lock:
            entered.set()
            assert release.wait(3)

    thread = threading.Thread(target=holder)
    thread.start()
    try:
        assert entered.wait(2)
        collector.mark_loss()
        collector._stop.set()
        collector._shutdown_deadline = 0
        started = time.monotonic()
        collector._run()
        assert time.monotonic() - started < 0.5
        with sqlite3.connect(database) as db:
            assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone() == (0,)
            assert db.execute(
                "SELECT DISTINCT quality,known_dropped FROM daily_coverage"
            ).fetchall() == [("partial", 1)]
    finally:
        release.set()
        thread.join(2)
        collector._disconnect()


def test_terminal_closure_excludes_new_activity_without_erasing_inflight_producer():
    from njit_auditor.analytics.collector import ProducerActivity

    activity = ProducerActivity()
    assert activity.enter()  # an older producer remains suspended
    finished = activity._finished

    class ConcurrentCompletion:
        def __next__(self):
            value = next(finished)
            # Arrive and complete between the two terminal counter reads.
            assert not activity.enter()
            return value

    activity._finished = ConcurrentCompletion()
    # Avoid recursion when enter() balances the late registration.
    original_finish = activity.finish
    activity.finish = lambda: next(finished)
    assert activity.close()
    activity._finished = finished
    activity.finish = original_finish
    activity.finish()
    assert not activity.enter()


def test_post_terminal_observations_cannot_change_clean_snapshot(database):
    collector = manual_collector(database)
    collector._stop.set()
    collector._shutdown_deadline = 0
    collector._run()
    collector.emit(PageView("2030-01-01"))
    collector.mark_loss()
    assert not collector._loss and collector.queue.empty()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT clean_shutdown FROM schema_meta").fetchone() == (1,)
        assert db.execute("SELECT MAX(known_dropped) FROM daily_coverage").fetchone() == (0,)
