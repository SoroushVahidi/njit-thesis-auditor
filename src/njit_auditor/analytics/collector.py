"""Nonblocking producers and a single bounded, failure-isolated writer."""

from __future__ import annotations

import math
import queue
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .retention import Retention
from .schema import Event, decode, encode, utc_now
from .store import AggregateStore, Deltas, ExpiredObservation, reduce_events


class Clock(Protocol):
    def utcnow(self) -> datetime: ...
    def monotonic(self) -> float: ...


class SystemClock:
    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


class Sink(Protocol):
    def emit(self, event: Event) -> None: ...


class NoOpSink:
    def emit(self, event: Event) -> None:
        pass


@dataclass(frozen=True, slots=True)
class Pending:
    nonce: bytes
    deltas: Deltas
    deadline: float
    expires_at: datetime


class BoundedCollector:
    def __init__(self, path: Path, clock: Clock | None = None) -> None:
        self.path = path
        self.clock = clock or SystemClock()
        self.queue: queue.Queue[tuple[float, bytes]] = queue.Queue(maxsize=1000)
        self.pending: Pending | None = None
        self.thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._shutdown_deadline = 0.0
        self._accepting = False
        self._loss_lock = threading.Lock()
        self._loss_days: set[str] = set()
        self._unknown_loss = False
        # A separate bounded mailbox preserves dates when the snapshot lock is busy.
        self._contended_loss: queue.Queue[str | None] = queue.Queue(maxsize=1000)
        # Mailbox exhaustion leaves persistent uncertainty, not a recurring new loss.
        self._loss_saturated = threading.Event()
        self._saturation_persisted = False
        self._taken_saturation = False
        self.dropped = 0
        self.status = "STOPPED"
        self._failures = 0
        self._probe_at = 0.0
        self._store: AggregateStore | None = None
        self._retention: Retention | None = None
        self._last_flush = 0.0
        self._last_heartbeat = -float("inf")

    @property
    def _loss(self) -> bool:
        with self._loss_lock:
            return bool(
                self._loss_days
                or self._unknown_loss
                or not self._contended_loss.empty()
                or (self._loss_saturated.is_set() and not self._saturation_persisted)
            )

    def _record_loss(self, day: str | None, *, dropped: bool = False) -> None:
        # Request threads never wait for the writer or perform storage I/O.
        if not self._loss_lock.acquire(blocking=False):
            try:
                self._contended_loss.put_nowait(day)
            except queue.Full:
                self._loss_saturated.set()
            return
        try:
            if dropped:
                self.dropped = min(self.dropped + 1, 2147483647)
            if day is None:
                self._unknown_loss = True
            elif len(self._loss_days) < 92:
                self._loss_days.add(day)
            else:
                self._loss_saturated.set()
        finally:
            self._loss_lock.release()

    def _take_loss(self) -> tuple[tuple[str, ...], bool]:
        with self._loss_lock:
            days = set(self._loss_days)
            self._taken_saturation = (
                self._loss_saturated.is_set() and not self._saturation_persisted
            )
            unknown = self._unknown_loss or self._taken_saturation
            # Bound work even while producers continue adding notifications.
            for _ in range(1000):
                try:
                    day = self._contended_loss.get_nowait()
                except queue.Empty:
                    break
                if day is None:
                    unknown = True
                elif len(days) < 92:
                    days.add(day)
                else:
                    self._loss_saturated.set()
                    self._taken_saturation = True
                    unknown = True
            self._loss_days.clear()
            self._unknown_loss = False
            return tuple(sorted(days)), unknown

    def _drop(self, code: str, day: str | None = None) -> None:
        self._record_loss(day, dropped=True)
        self.status = code

    def mark_loss(self) -> None:
        try:
            day = utc_now(self.clock.utcnow()).date().isoformat()
        except Exception:
            day = None
        self._drop("HELPER_LOSS", day)

    def emit(self, event: Event) -> None:
        event_day = None
        try:
            payload = encode(event)
            now = self.clock.monotonic()
            if not math.isfinite(now):
                raise ValueError("INVALID_CLOCK")
            day = utc_now(self.clock.utcnow()).date()
            if event.day_utc not in (day.isoformat(), (day - timedelta(days=1)).isoformat()):
                raise ValueError("INVALID_DAY")
            event_day = event.day_utc
            if not self._accepting or self.thread is None or not self.thread.is_alive():
                self._drop("UNAVAILABLE", event_day)
                return
            self.queue.put_nowait((now, payload))
            if self.queue.qsize() >= 100:
                self._wake.set()
        except Exception:
            self._drop("ENQUEUE_LOSS", event_day)

    def start(self) -> None:
        try:
            if self.thread is not None:
                return
            self.thread = threading.Thread(
                target=self._run, name="njit-analytics-writer", daemon=True
            )
            self.thread.start()
        except Exception:
            self._accepting = False
            self._drop("START_FAILED")

    def stop(self, timeout: float = 1.0) -> None:
        try:
            budget = min(1.0, max(0.0, timeout))
            self._accepting = False
            self._shutdown_deadline = time.monotonic() + budget
            self._stop.set()
            self._wake.set()
            if self.thread is not None:
                self.thread.join(budget)
        except Exception:
            self._drop("STOP_FAILED")

    def _disconnect(self) -> None:
        if self._store is not None:
            try:
                self._store.close()
            finally:
                self._store = None
                self._retention = None

    def _check_deadline(self, pending: Pending) -> None:
        mono = self.clock.monotonic()
        if not math.isfinite(mono) or not pending.deadline - 60 <= mono < pending.deadline:
            raise ExpiredObservation("EXPIRED")

    def _expire_pending(self) -> None:
        if self.pending is not None:
            for day in {row[0] for row in self.pending.deltas.counts}:
                self._drop("EXPIRED", day)
            self.pending = None

    def _heartbeat(self) -> None:
        mono = self.clock.monotonic()
        now = utc_now(self.clock.utcnow())
        if mono - self._last_heartbeat >= 60 or mono < self._last_heartbeat or self._loss:
            assert self._retention is not None
            days, unknown = self._take_loss()
            # Copy at most 1,000 immutable envelopes under the queue's short lock;
            # decode and all storage work happen after releasing it.
            with self.queue.mutex:
                waiting = tuple(self.queue.queue)
            unsettled = {decode(payload).day_utc for _, payload in waiting}
            if self.pending is not None:
                unsettled.update(row[0] for row in self.pending.deltas.counts)
            try:
                self._retention.heartbeat(
                    now,
                    mono,
                    loss_days=days,
                    unknown_loss=unknown,
                    uncertain=self._loss_saturated.is_set(),
                    unsettled_days=tuple(sorted(unsettled)),
                )
            except Exception:
                for day in days:
                    self._record_loss(day)
                if unknown:
                    self._record_loss(None)
                raise
            if self._taken_saturation:
                self._saturation_persisted = True
            self._last_heartbeat = mono

    def _tick(self) -> None:
        mono = self.clock.monotonic()
        if not math.isfinite(mono):
            raise ValueError("INVALID_CLOCK")
        if self.pending is not None:
            try:
                self._check_deadline(self.pending)
            except ExpiredObservation:
                self._expire_pending()
        if mono < self._probe_at:
            while not self.queue.empty():
                _, payload = self.queue.get_nowait()
                self._drop("BREAKER_LOSS", decode(payload).day_utc)
            return
        if self._store is None:
            self._store = AggregateStore.open_existing(self.path)
            self._retention = Retention(self._store)
            self._last_heartbeat = -float("inf")
        self._heartbeat()
        # Opening and maintenance may block. Never reuse their entry timestamps.
        mono = self.clock.monotonic()
        now = utc_now(self.clock.utcnow())
        self._accepting = not self._stop.is_set()
        if self.pending is None and (
            self.queue.qsize() >= 100 or mono - self._last_flush >= 5 or self._stop.is_set()
        ):
            events: list[Event] = []
            oldest = mono
            for _ in range(100):
                try:
                    enqueued, payload = self.queue.get_nowait()
                except queue.Empty:
                    break
                event = decode(payload)
                if not 0 <= mono - enqueued < 60:
                    self._drop("EXPIRED", event.day_utc)
                    continue
                oldest = min(oldest, enqueued)
                events.append(event)
            if events:
                try:
                    self.pending = Pending(
                        secrets.token_bytes(16),
                        reduce_events(tuple(events)),
                        oldest + 60,
                        now + timedelta(hours=48, minutes=-1),
                    )
                except Exception:
                    for event in events:
                        self._drop("BATCH_LOSS", event.day_utc)
                    raise
            self._last_flush = mono
        if self.pending is not None:
            pending = self.pending
            try:
                self._check_deadline(pending)
                committed = self._store.has_batch(pending.nonce)
                self._check_deadline(pending)
                if not committed:
                    self._store.apply_batch(
                        pending.nonce,
                        pending.deltas,
                        False,
                        pending.expires_at,
                        now=utc_now(self.clock.utcnow()),
                        check_deadline=lambda: self._check_deadline(pending),
                    )
                # A COMMIT already in progress cannot be cancelled safely. Preserve
                # its counts/nonce, but record uncertainty if it returned past expiry.
                self._check_deadline(pending)
                self.pending = None
            except ExpiredObservation:
                self._expire_pending()
        # Loss discovered while draining or writing must also downgrade yesterday.
        self._heartbeat()
        self._failures = 0
        self._probe_at = 0.0
        self.status = "HEALTHY"

    def _run(self) -> None:
        try:
            while True:
                if self._stop.is_set() and time.monotonic() >= self._shutdown_deadline:
                    break
                try:
                    self._tick()
                except Exception:
                    self._accepting = False
                    self._drop("STORAGE_FAILED")
                    self._failures += 1
                    self._disconnect()
                    if self._failures >= 3:
                        self._probe_at = self.clock.monotonic() + 60
                    if self._stop.is_set():
                        break
                if self._stop.is_set() and self.queue.empty() and self.pending is None:
                    break
                self._wake.wait(0.05 if self._stop.is_set() else 0.25)
                self._wake.clear()
        except BaseException:
            self._drop("WRITER_TERMINATED")
        finally:
            self._accepting = False
            clean = self.queue.empty() and self.pending is None and not self._loss
            if self.pending is not None:
                for day in {row[0] for row in self.pending.deltas.counts}:
                    self._drop("SHUTDOWN_LOSS", day)
                self.pending = None
            for _ in range(1000):
                try:
                    _, payload = self.queue.get_nowait()
                except queue.Empty:
                    break
                self._drop("SHUTDOWN_LOSS", decode(payload).day_utc)
            days, unknown = self._take_loss()
            try:
                if self._retention is not None:
                    # Writer-only, best effort. stop() still joins for at most its
                    # original budget; a blocked SQLite call may outlive that join.
                    self._retention.shutdown(
                        clean,
                        now=utc_now(self.clock.utcnow()),
                        loss_days=days,
                        unknown_loss=unknown,
                        uncertain=self._loss_saturated.is_set(),
                    )
            except Exception:
                for day in days:
                    self._record_loss(day)
                if unknown:
                    self._record_loss(None)
                self._drop("SHUTDOWN_LOSS")
            try:
                self._disconnect()
            except Exception:
                pass
