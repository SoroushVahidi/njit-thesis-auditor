"""Explicit provisioning and a single-owner, aggregate-only SQLite store."""

from __future__ import annotations

import os
import re
import sqlite3
import stat
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from .schema import METRICS, OUTCOMES, AuditTerminal, Event, encode, utc_now, validate_day

DDL = """
CREATE TABLE schema_meta (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  schema_version INTEGER NOT NULL CHECK(schema_version = 1),
  definition_version INTEGER NOT NULL CHECK(definition_version = 1),
  epoch TEXT NOT NULL,
  activated_at_utc TEXT NOT NULL,
  last_heartbeat_minute_utc TEXT,
  clean_shutdown INTEGER NOT NULL CHECK(clean_shutdown IN (0,1))
);
CREATE TABLE daily_count (
  epoch TEXT NOT NULL,
  day_utc TEXT NOT NULL,
  metric TEXT NOT NULL CHECK(metric IN
    ('page_view','upload_accepted','audit_completed','audit_failed')),
  n INTEGER NOT NULL CHECK(typeof(n)='integer' AND n >= 0),
  PRIMARY KEY(epoch,day_utc,metric)
) WITHOUT ROWID;
CREATE TABLE daily_duration (
  epoch TEXT NOT NULL,
  day_utc TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('completed','failed')),
  bucket INTEGER NOT NULL CHECK(bucket BETWEEN 0 AND 7),
  n INTEGER NOT NULL CHECK(typeof(n)='integer' AND n >= 0),
  PRIMARY KEY(epoch,day_utc,outcome,bucket)
) WITHOUT ROWID;
CREATE TABLE daily_coverage (
  epoch TEXT NOT NULL,
  day_utc TEXT NOT NULL,
  component TEXT NOT NULL CHECK(component IN ('counter','duration')),
  quality TEXT NOT NULL CHECK(quality IN ('observed','partial','unavailable')),
  known_dropped INTEGER NOT NULL CHECK(known_dropped >= 0),
  PRIMARY KEY(epoch,day_utc,component)
) WITHOUT ROWID;
CREATE TABLE committed_batch (
  batch_id BLOB PRIMARY KEY CHECK(length(batch_id)=16),
  expires_at_utc TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX committed_batch_expiry ON committed_batch(expires_at_utc);
CREATE TABLE month_rollup (
  epoch TEXT NOT NULL,
  month_utc TEXT NOT NULL,
  definition_version INTEGER NOT NULL CHECK(definition_version=1),
  coverage TEXT NOT NULL CHECK(coverage IN ('observed','partial','unavailable')),
  counts_json TEXT NOT NULL,
  histogram_json TEXT NOT NULL,
  rolled_up_at_utc TEXT NOT NULL,
  PRIMARY KEY(epoch,month_utc)
) WITHOUT ROWID;
"""


def validate_path(path: Path, *, existing: bool = True) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("INVALID_PATH")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("UNSAFE_LINK")
    parent = path.parent.stat()
    if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise ValueError("UNSAFE_DIRECTORY")
    for item in (path.parent, path) if existing else (path.parent,):
        if any(name.startswith("system.posix_acl") for name in os.listxattr(item)):
            raise ValueError("UNSAFE_ACL")
    if existing:
        info = path.stat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ValueError("UNSAFE_FILE")
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                info = sidecar.lstat()
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_nlink != 1
                ):
                    raise ValueError("UNSAFE_SIDECAR")


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path.as_uri() + "?mode=rw", timeout=0.05, isolation_level=None)
    try:
        db.execute("PRAGMA busy_timeout=50")
        if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise ValueError("UNSUPPORTED_JOURNAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA secure_delete=ON")
        db.execute("PRAGMA temp_store=MEMORY")
        return db
    except Exception:
        db.close()
        raise


def initialize_database(path: Path, *, epoch: str, activated_at: datetime) -> None:
    """Offline provisioner only. Caller supplies an existing private directory."""
    utc_now(activated_at)
    if type(epoch) is not str or re.fullmatch(r"[0-9a-f]{32}", epoch) is None:
        raise ValueError("INVALID_EPOCH")
    validate_path(path, existing=False)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    db = _connect(path)
    try:
        db.executescript("BEGIN IMMEDIATE;\n" + DDL)
        db.execute(
            "INSERT INTO schema_meta VALUES(1,1,1,?,?,NULL,1)",
            (epoch, activated_at.replace(second=0, microsecond=0).isoformat()),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@dataclass(frozen=True)
class Deltas:
    counts: tuple[tuple[str, str, int], ...]
    durations: tuple[tuple[str, str, int, int], ...]
    invalid_duration: tuple[str, ...] = ()


def reduce_events(events: tuple[Event, ...]) -> Deltas:
    if len(events) > 100:
        raise ValueError("OVERSIZE_BATCH")
    counts: Counter[tuple[str, str]] = Counter()
    durations: Counter[tuple[str, str, int]] = Counter()
    invalid: set[str] = set()
    for event in events:
        encode(event)
        if isinstance(event, AuditTerminal):
            counts[event.day_utc, "audit_" + event.outcome] += 1
            if event.duration_bucket is None:
                invalid.add(event.day_utc)
            else:
                durations[event.day_utc, event.outcome, event.duration_bucket] += 1
        else:
            counts[event.day_utc, event.kind] += 1
    return Deltas(
        tuple((*key, n) for key, n in sorted(counts.items())),
        tuple((*key, n) for key, n in sorted(durations.items())),
        tuple(sorted(invalid)),
    )


class ExpiredObservation(Exception):
    """A batch expired before the next storage operation could begin."""


class AggregateStore:
    def __init__(self, db: sqlite3.Connection, lock: BinaryIO, epoch: str) -> None:
        self.db = db
        self._lock = lock
        self.epoch = epoch

    @classmethod
    def open_existing(cls, path: Path) -> AggregateStore:
        import fcntl

        validate_path(path)
        lock = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb")
        db = None
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            db = _connect(path)
            # Compare against the exact v1 schema, including constraints and absence of triggers.
            with sqlite3.connect(":memory:") as expected:
                expected.executescript(DDL)
                query = "SELECT type,name,sql FROM sqlite_master ORDER BY type,name"
                if db.execute(query).fetchall() != expected.execute(query).fetchall():
                    raise ValueError("UNSUPPORTED_SCHEMA")
            rows = db.execute("SELECT * FROM schema_meta").fetchall()
            if len(rows) != 1 or rows[0][0:3] != (1, 1, 1):
                raise ValueError("UNSUPPORTED_SCHEMA")
            if re.fullmatch(r"[0-9a-f]{32}", rows[0][3]) is None:
                raise ValueError("INVALID_EPOCH")
            utc_now(datetime.fromisoformat(rows[0][4]))
            return cls(db, lock, rows[0][3])
        except Exception:
            if db is not None:
                db.close()
            lock.close()
            raise

    def close(self) -> None:
        try:
            self.db.close()
        finally:
            self._lock.close()

    def has_batch(self, batch_id: bytes) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM committed_batch WHERE batch_id=?", (batch_id,)
            ).fetchone()
            is not None
        )

    def apply_batch(
        self,
        batch_id: bytes,
        deltas: Deltas,
        coverage: bool,
        expires_at: datetime,
        *,
        now: datetime,
        check_deadline: Callable[[], None] = lambda: None,
    ) -> bool:
        utc_now(now)
        utc_now(expires_at)
        if type(batch_id) is not bytes or len(batch_id) != 16:
            raise ValueError("INVALID_NONCE")
        if not now < expires_at <= now + timedelta(hours=48):
            raise ValueError("INVALID_EXPIRY")
        if len(deltas.counts) > 100 or len(deltas.durations) > 100:
            raise ValueError("OVERSIZE_BATCH")
        for day, metric, n in deltas.counts:
            validate_day(day)
            if metric not in METRICS or type(n) is not int or not 0 < n <= 100:
                raise ValueError("INVALID_DELTA")
        for day, outcome, bucket, n in deltas.durations:
            validate_day(day)
            if (
                outcome not in OUTCOMES
                or type(bucket) is not int
                or not 0 <= bucket < 8
                or type(n) is not int
                or not 0 < n <= 100
            ):
                raise ValueError("INVALID_DELTA")
        for day in deltas.invalid_duration:
            validate_day(day)
        try:
            check_deadline()
            self.db.execute("BEGIN IMMEDIATE")
            check_deadline()
            committed = self.has_batch(batch_id)
            check_deadline()
            if committed:
                self.db.rollback()
                return False
            check_deadline()
            self.db.execute(
                "INSERT INTO committed_batch VALUES(?,?)", (batch_id, expires_at.isoformat())
            )
            for day, metric, n in deltas.counts:
                check_deadline()
                self.db.execute(
                    "INSERT INTO daily_count VALUES(?,?,?,?) ON CONFLICT "
                    "DO UPDATE SET n=n+excluded.n",
                    (self.epoch, day, metric, n),
                )
            for day, outcome, bucket, n in deltas.durations:
                check_deadline()
                self.db.execute(
                    "INSERT INTO daily_duration VALUES(?,?,?,?,?) ON CONFLICT "
                    "DO UPDATE SET n=n+excluded.n",
                    (self.epoch, day, outcome, bucket, n),
                )
            for day in deltas.invalid_duration:
                check_deadline()
                self.degrade(day, "duration", check_deadline=check_deadline)
            if coverage:
                for day in {row[0] for row in deltas.counts} | {now.date().isoformat()}:
                    self.degrade(day, "counter", check_deadline=check_deadline)
                    self.degrade(day, "duration", check_deadline=check_deadline)
            check_deadline()
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def degrade(
        self,
        day: str,
        component: str,
        *,
        check_deadline: Callable[[], None] = lambda: None,
        known_loss: bool = True,
    ) -> None:
        # A coalesced, durable presence lower bound, not a reconstructed loss total.
        # MAX makes retries (including uncertain commits) idempotent without resetting
        # any larger value already present in an existing database.
        check_deadline()
        self.db.execute(
            "INSERT INTO daily_coverage VALUES(?,?,?,'partial',?) "
            "ON CONFLICT DO UPDATE SET quality=CASE WHEN quality='unavailable' "
            "THEN quality ELSE 'partial' END, known_dropped=MAX(known_dropped,"
            "excluded.known_dropped)",
            (self.epoch, day, component, int(known_loss)),
        )

        # A later clock/recovery gap can lower a closed month's confidence without
        # recomputing its immutable counts or double-counting its daily overlap.
        check_deadline()
        self.db.execute(
            "UPDATE month_rollup SET coverage=CASE WHEN coverage='unavailable' "
            "THEN coverage ELSE 'partial' END WHERE epoch=? AND month_utc=?",
            (self.epoch, day[:7]),
        )
