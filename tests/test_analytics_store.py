"""Disposable SQLite storage, permissions and transaction tests."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from njit_auditor.analytics.schema import AuditTerminal, PageView
from njit_auditor.analytics.store import AggregateStore, Deltas, initialize_database, reduce_events

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def database(tmp_path):
    private = tmp_path / "analytics"
    private.mkdir(mode=0o700)
    path = private / "test.sqlite3"
    initialize_database(path, epoch="0" * 32, activated_at=NOW)
    return path


def apply(store, events, nonce=b"a" * 16, now=NOW):
    return store.apply_batch(
        nonce, reduce_events(tuple(events)), False, now + timedelta(hours=47), now=now
    )


def test_atomic_idempotent(database):
    store = AggregateStore.open_existing(database)
    events = [PageView("2030-01-01"), AuditTerminal("2030-01-01", "completed", 3)]
    assert apply(store, events)
    assert not apply(store, events)
    assert store.db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0] == 2
    assert store.db.execute("SELECT SUM(n) FROM daily_duration").fetchone()[0] == 1
    assert store.db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert store.db.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert store.db.execute("PRAGMA busy_timeout").fetchone()[0] == 50
    assert store.db.execute("PRAGMA secure_delete").fetchone()[0] == 1
    store.close()


def test_rollback_pair_and_nonce(database):
    store = AggregateStore.open_existing(database)
    # Valid schema CHECK rejects overflow; preceding counter and nonce must roll back too.
    store.db.execute(
        "INSERT INTO daily_duration VALUES(?,?,?,?,?)",
        (store.epoch, "2030-01-01", "completed", 3, 2**63 - 1),
    )
    with pytest.raises(sqlite3.IntegrityError):
        apply(store, [AuditTerminal("2030-01-01", "completed", 3)])
    assert not store.has_batch(b"a" * 16)
    assert store.db.execute("SELECT COUNT(*) FROM daily_count").fetchone()[0] == 0
    store.close()


def test_invalid_duration_keeps_counter(database):
    store = AggregateStore.open_existing(database)
    apply(store, [AuditTerminal("2030-01-01", "failed", None)])
    assert store.db.execute("SELECT n FROM daily_count").fetchone() == (1,)
    assert store.db.execute("SELECT COUNT(*) FROM daily_duration").fetchone() == (0,)
    assert store.db.execute("SELECT component,quality FROM daily_coverage").fetchone() == (
        "duration",
        "partial",
    )
    store.close()


def test_no_automatic_creation(tmp_path):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises((ValueError, FileNotFoundError)):
        AggregateStore.open_existing(path)
    assert not path.exists()


@pytest.mark.parametrize("mode", [0o644, 0o666, 0o400])
def test_bad_file_permissions(database, mode):
    database.chmod(mode)
    with pytest.raises(ValueError):
        AggregateStore.open_existing(database)


def test_paths_links_owner_and_parent(database, monkeypatch):
    with pytest.raises(ValueError):
        AggregateStore.open_existing(Path("relative.sqlite3"))
    link = database.with_name("link.sqlite3")
    link.symlink_to(database)
    with pytest.raises(ValueError):
        AggregateStore.open_existing(link)
    database.parent.chmod(0o750)
    with pytest.raises(ValueError):
        AggregateStore.open_existing(database)
    database.parent.chmod(0o700)
    monkeypatch.setattr(os, "getuid", lambda: -1)
    with pytest.raises(ValueError):
        AggregateStore.open_existing(database)


def test_acl_sidecar_and_hardlink(database, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(os, "listxattr", lambda p: ["system.posix_acl_access"])
        with pytest.raises(ValueError):
            AggregateStore.open_existing(database)
    sidecar = Path(str(database) + "-journal")
    sidecar.symlink_to(database)
    with pytest.raises(ValueError):
        AggregateStore.open_existing(database)
    sidecar.unlink()
    os.link(database, database.with_name("hardlink"))
    with pytest.raises(ValueError):
        AggregateStore.open_existing(database)


def test_schema_and_single_owner(database):
    first = AggregateStore.open_existing(database)
    with pytest.raises(BlockingIOError):
        AggregateStore.open_existing(database)
    first.close()
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE forbidden(payload TEXT)")
    with pytest.raises(ValueError):
        AggregateStore.open_existing(database)


def test_provision_never_overwrites(database):
    before = database.read_bytes()
    with pytest.raises(FileExistsError):
        initialize_database(database, epoch="1" * 32, activated_at=NOW)
    assert database.read_bytes() == before


def test_privacy_no_event_rows(database, caplog):
    from test_analytics_collector import manual_collector

    collector = manual_collector(database)
    # Supply the forbidden sentinel to the actual producer input boundary.
    collector.emit({"filename": "PRIVATE_CANARY", "text": "PRIVATE_CANARY"})
    assert collector.dropped == 1 and collector.queue.empty()
    collector.emit(PageView("2030-01-01"))
    collector.clock.advance(5)
    collector._tick()
    collector._disconnect()
    store = AggregateStore.open_existing(database)
    apply(store, [PageView("2030-01-01"), AuditTerminal("2030-01-01", "failed", 1)])
    tables = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {
        "schema_meta",
        "daily_count",
        "daily_duration",
        "daily_coverage",
        "committed_batch",
        "month_rollup",
    }
    store.close()
    for path in database.parent.iterdir():
        if path.is_file():
            assert b"PRIVATE_CANARY" not in path.read_bytes()
    assert not caplog.records


def test_invalid_deltas_nonce_expiry(database):
    store = AggregateStore.open_existing(database)
    with pytest.raises(ValueError):
        store.apply_batch(
            b"a" * 16,
            Deltas((("2030-01-01", "job_id", 1),), ()),
            False,
            NOW + timedelta(hours=1),
            now=NOW,
        )
    with pytest.raises(ValueError):
        store.apply_batch(b"a", Deltas((), ()), False, NOW + timedelta(hours=1), now=NOW)
    with pytest.raises(ValueError):
        store.apply_batch(b"a" * 16, Deltas((), ()), False, NOW + timedelta(hours=49), now=NOW)
    store.close()
