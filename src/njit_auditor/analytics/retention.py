"""Bounded writer-thread coverage and retention; no document filesystem access."""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime, time, timedelta, timezone

from .schema import METRICS, OUTCOMES, utc_now
from .store import DEFINITION_VERSION, AggregateStore

DAILY_DAYS = 90
MONTHLY_MONTHS = 24


def next_month(day: date) -> date:
    return date(day.year + (day.month == 12), day.month % 12 + 1, 1)


def month_expiry(day: date) -> date:
    end = next_month(day)
    return date(end.year + 2, end.month, 1)


class Retention:
    def __init__(self, store: AggregateStore) -> None:
        self.store = store
        self.previous: tuple[datetime, float] | None = None
        self.eligible: str | None = None
        self.maintenance_day: date | None = None

    def _initialize(self, day: str) -> None:
        db, epoch = self.store.db, self.store.epoch
        db.executemany(
            "INSERT OR IGNORE INTO daily_count VALUES(?,?,?,0)",
            ((epoch, day, metric) for metric in METRICS),
        )
        db.executemany(
            "INSERT OR IGNORE INTO daily_duration VALUES(?,?,?,?,0)",
            ((epoch, day, outcome, bucket) for outcome in OUTCOMES for bucket in range(8)),
        )
        db.executemany(
            "INSERT OR IGNORE INTO daily_coverage VALUES(?,?,?,'partial',0)",
            ((epoch, day, component) for component in ("counter", "duration")),
        )

    def heartbeat(
        self,
        now: datetime,
        monotonic: float,
        *,
        loss: bool = False,
        loss_days: tuple[str, ...] = (),
        unknown_loss: bool = False,
        uncertain: bool = False,
        unsettled_days: tuple[str, ...] = (),
    ) -> None:
        # Expiry must be attempted even when initialization/coverage cannot allocate.
        succeeded = False
        try:
            self._heartbeat(
                now,
                monotonic,
                loss=loss,
                loss_days=loss_days,
                unknown_loss=unknown_loss,
                uncertain=uncertain,
                unsettled_days=unsettled_days,
            )
            succeeded = True
        finally:
            if not succeeded or self.maintenance_day != now.date():
                self.maintain(now)
                self.maintenance_day = now.date()

    def _heartbeat(
        self,
        now: datetime,
        monotonic: float,
        *,
        loss: bool,
        loss_days: tuple[str, ...],
        unknown_loss: bool,
        uncertain: bool,
        unsettled_days: tuple[str, ...],
    ) -> None:
        utc_now(now)
        db, epoch = self.store.db, self.store.epoch
        day = now.date().isoformat()
        eligible = self.eligible
        db.execute("BEGIN IMMEDIATE")
        try:
            meta = db.execute(
                "SELECT activated_at_utc,last_heartbeat_minute_utc FROM schema_meta"
            ).fetchone()
            if now < datetime.fromisoformat(meta[0]):
                raise ValueError("CLOCK_BEFORE_ACTIVATION")
            self._initialize(day)
            if self.previous is None:
                # Producers accept current/previous UTC dates. An enqueue can cross
                # midnight before the next heartbeat, so restart includes two preceding
                # dates. Older queued dates are degraded before any heartbeat advances.
                start = datetime.fromisoformat(meta[1] or meta[0]).date() - timedelta(days=2)
                start = max(start, datetime.fromisoformat(meta[0]).date())
                db.execute(
                    "UPDATE month_rollup SET coverage='partial' WHERE epoch=? "
                    "AND month_utc>=? AND month_utc<=? AND coverage='observed'",
                    (epoch, start.isoformat()[:7], day[:7]),
                )
                start = max(start, now.date() - timedelta(days=DAILY_DAYS))
                # Never initialize missing-day count cells as measured zeros.
                for offset in range(min(DAILY_DAYS + 1, max(0, (now.date() - start).days) + 1)):
                    gap_day = (start + timedelta(days=offset)).isoformat()
                    for component in ("counter", "duration"):
                        db.execute(
                            "INSERT INTO daily_coverage VALUES(?,?,?,'unavailable',0) "
                            "ON CONFLICT DO UPDATE SET quality=CASE WHEN day_utc=? "
                            "AND quality!='unavailable' THEN 'partial' ELSE 'unavailable' END",
                            (epoch, gap_day, component, day),
                        )
                self.eligible = None  # even a clean restart has unknown downtime
            else:
                previous, mono = self.previous
                elapsed = monotonic - mono
                jump = elapsed < 0 or abs((now - previous).total_seconds() - elapsed) > 2
                gap = elapsed > 90 or jump
                if gap:
                    lower, upper = sorted((previous.date(), now.date()))
                    lower = max(lower, now.date() - timedelta(days=DAILY_DAYS))
                    for offset in range(min(DAILY_DAYS + 1, (upper - lower).days + 1)):
                        for component in ("counter", "duration"):
                            self.store.degrade(
                                (lower + timedelta(days=offset)).isoformat(), component
                            )
                    self.eligible = None
                if previous.date() != now.date():
                    if self.eligible == previous.date().isoformat() and not gap and not loss:
                        db.execute(
                            "UPDATE daily_coverage SET quality='observed' "
                            "WHERE epoch=? AND day_utc=? AND quality='partial' "
                            "AND known_dropped=0",
                            (epoch, self.eligible),
                        )
                    # Only an adjacent, timely boundary starts a potentially complete day.
                    self.eligible = (
                        day
                        if not gap and now.date() == (previous.date() + timedelta(days=1))
                        else None
                    )
            self._apply_loss(
                now,
                (*loss_days, day) if loss else loss_days,
                unknown_loss=unknown_loss,
                uncertain=uncertain,
                uncertain_days=tuple(d for d in unsettled_days if d != day),
            )
            db.execute(
                "UPDATE schema_meta SET last_heartbeat_minute_utc=?,clean_shutdown=0",
                (now.replace(second=0, microsecond=0).isoformat(),),
            )
            db.execute("DELETE FROM committed_batch WHERE expires_at_utc<=?", (now.isoformat(),))
            db.commit()
        except Exception:
            db.rollback()
            self.eligible = eligible
            raise
        self.previous = now, monotonic

    def _apply_loss(
        self,
        now: datetime,
        loss_days: tuple[str, ...],
        *,
        unknown_loss: bool = False,
        uncertain: bool = False,
        uncertain_days: tuple[str, ...] = (),
    ) -> None:
        """Inside the caller's transaction; retrying the same evidence is idempotent."""
        db = self.store.db
        day = now.date().isoformat()
        known = set(loss_days)
        if unknown_loss:
            # A new unlocalized quality-loss notification was observed on this day.
            # This is a presence marker, never an estimate of missing event volume.
            known.add(day)
        affected = set(known) | set(uncertain_days)
        if unknown_loss or uncertain:
            affected.add(day)
            affected.update(
                row[0] for row in db.execute("SELECT DISTINCT day_utc FROM daily_coverage")
            )
            db.execute("UPDATE month_rollup SET coverage='partial' WHERE coverage='observed'")
            self.eligible = None
        cutoff = (now.date() - timedelta(days=DAILY_DAYS)).isoformat()
        for affected_day in affected:
            if cutoff <= affected_day <= day:
                for component in ("counter", "duration"):
                    self.store.degrade(affected_day, component, known_loss=affected_day in known)
            else:
                # Never recreate expired/future daily rows just to record loss.
                db.execute(
                    "UPDATE daily_coverage SET quality=CASE WHEN quality='unavailable' "
                    "THEN quality ELSE 'partial' END, known_dropped=MAX(known_dropped,?) "
                    "WHERE day_utc=?",
                    (int(affected_day in known), affected_day),
                )
                db.execute(
                    "UPDATE month_rollup SET coverage='partial' "
                    "WHERE month_utc=? AND coverage='observed'",
                    (affected_day[:7],),
                )
            if affected_day == self.eligible:
                self.eligible = None

    def rollup(self, month: str, now: datetime) -> None:
        db, epoch = self.store.db, self.store.epoch
        first = date.fromisoformat(month + "-01")
        end = next_month(first).isoformat()
        if db.execute(
            "SELECT 1 FROM month_rollup WHERE epoch=? AND month_utc=?", (epoch, month)
        ).fetchone():
            return
        counts = dict.fromkeys(METRICS, 0)
        histogram = {outcome: [0] * 8 for outcome in OUTCOMES}
        for metric, n in db.execute(
            "SELECT metric,SUM(n) FROM daily_count "
            "WHERE epoch=? AND day_utc>=? AND day_utc<? GROUP BY metric",
            (epoch, first.isoformat(), end),
        ):
            counts[metric] = n
        for outcome, bucket, n in db.execute(
            "SELECT outcome,bucket,SUM(n) FROM daily_duration "
            "WHERE epoch=? AND day_utc>=? AND day_utc<? "
            "GROUP BY outcome,bucket",
            (epoch, first.isoformat(), end),
        ):
            histogram[outcome][bucket] = n
        qualities = [
            row[0]
            for row in db.execute(
                "SELECT quality FROM daily_coverage WHERE epoch=? AND day_utc>=? AND day_utc<?",
                (epoch, first.isoformat(), end),
            )
        ]
        quality = "observed"
        if len(qualities) != calendar.monthrange(first.year, first.month)[1] * 2:
            quality = "unavailable"
        elif "unavailable" in qualities:
            quality = "unavailable"
        elif "partial" in qualities:
            quality = "partial"
        db.execute(
            "INSERT INTO month_rollup VALUES(?,?,?,?,?,?,?)",
            (
                epoch,
                month,
                DEFINITION_VERSION,
                quality,
                json.dumps(counts),
                json.dumps(histogram),
                now.replace(second=0, microsecond=0).isoformat(),
            ),
        )

    def maintain(self, now: datetime) -> None:
        """At most 91 retained days/24 months in normal use; expiry survives rollup failure."""
        db, epoch = self.store.db, self.store.epoch
        try:
            months = db.execute(
                "SELECT DISTINCT substr(day_utc,1,7) FROM daily_count "
                "WHERE epoch=? ORDER BY day_utc LIMIT 91",
                (epoch,),
            ).fetchall()
            for (month,) in months:
                first = date.fromisoformat(month + "-01")
                closed = datetime.combine(next_month(first), time(), timezone.utc)
                if now < closed + timedelta(hours=48):
                    continue
                try:
                    db.execute("BEGIN IMMEDIATE")
                    self.rollup(month, now)
                    db.commit()
                except Exception:
                    db.rollback()
                    # Missing monthly state means unavailable. This optional marker
                    # cannot share the expiry transaction: SQLITE_FULL can abort it.
                    try:
                        db.execute("BEGIN IMMEDIATE")
                        db.execute(
                            "INSERT OR IGNORE INTO month_rollup VALUES(?,?,?,'unavailable',?,?,?)",
                            (
                                epoch,
                                month,
                                DEFINITION_VERSION,
                                json.dumps(dict.fromkeys(METRICS, 0)),
                                json.dumps({o: [0] * 8 for o in OUTCOMES}),
                                now.replace(second=0, microsecond=0).isoformat(),
                            ),
                        )
                        db.commit()
                    except Exception:
                        db.rollback()
        finally:
            self.expire(now)

    def expire(self, now: datetime) -> None:
        """Deletion-only transaction, independent of allocation/rollup failures."""
        db = self.store.db
        cutoff = (now.date() - timedelta(days=DAILY_DAYS)).isoformat()
        db.execute("BEGIN IMMEDIATE")
        try:
            for table in ("daily_count", "daily_duration", "daily_coverage"):
                db.execute(f"DELETE FROM {table} WHERE day_utc<?", (cutoff,))
            for (month,) in db.execute("SELECT month_utc FROM month_rollup").fetchall():
                if now.date() >= month_expiry(date.fromisoformat(month + "-01")):
                    db.execute("DELETE FROM month_rollup WHERE month_utc=?", (month,))
            db.execute("DELETE FROM committed_batch WHERE expires_at_utc<=?", (now.isoformat(),))
            db.commit()
        except Exception:
            db.rollback()
            raise

    def shutdown(
        self,
        clean: bool,
        *,
        now: datetime | None = None,
        loss_days: tuple[str, ...] = (),
        unknown_loss: bool = False,
        uncertain: bool = False,
    ) -> None:
        db = self.store.db
        db.execute("BEGIN IMMEDIATE")
        try:
            if now is not None:
                self._apply_loss(now, loss_days, unknown_loss=unknown_loss, uncertain=uncertain)
            db.execute("UPDATE schema_meta SET clean_shutdown=?", (int(clean),))
            db.commit()
        except Exception:
            db.rollback()
            raise
