"""No-throw web observations; contexts retain only a sink, clock and timing."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .collector import BoundedCollector, NoOpSink, Sink
from .runtime import AnalyticsRuntime
from .schema import AuditTerminal, Outcome, PageView, UploadAccepted, duration_bucket, utc_now


def _lost(sink: Sink) -> None:
    try:
        if isinstance(sink, BoundedCollector):
            sink.mark_loss()
    except Exception:
        pass


class AuditObservation:
    def __init__(self, runtime: AnalyticsRuntime) -> None:
        self.sink = runtime.sink
        self.clock = runtime.clock
        self._started = False
        self._terminal = False
        self._start: float | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        try:
            with self._lock:
                if self._started:
                    return
                self._started = True
                self._start = self.clock.monotonic()
        except Exception:
            pass

    def finish(self, outcome: Outcome) -> None:
        try:
            with self._lock:
                if not self._started or self._terminal:
                    return
                self._terminal = True
            bucket = None
            try:
                if self._start is not None:
                    bucket = duration_bucket(self.clock.monotonic() - self._start)
            except Exception:
                pass
            day = utc_now(self.clock.utcnow()).date().isoformat()
            self.sink.emit(AuditTerminal(day, outcome, bucket))
        except Exception:
            _lost(self.sink)


_current: ContextVar[AuditObservation | None] = ContextVar("analytics_observation", default=None)


@contextmanager
def task_context(runtime: AnalyticsRuntime) -> Iterator[None]:
    observation = None
    try:
        observation = AuditObservation(runtime)
    except Exception:
        pass
    token = _current.set(observation)
    try:
        yield
    finally:
        _current.reset(token)


def signal(action: str) -> None:
    try:
        observation = _current.get()
        if observation is not None:
            if action == "start":
                observation.start()
            elif action in ("completed", "failed"):
                observation.finish(action)  # type: ignore[arg-type]
    except Exception:
        pass


def runtime_for(app: Any) -> AnalyticsRuntime | None:
    try:
        if getattr(app.state, "offline_mode", False):
            return None
        runtime = getattr(app.state, "analytics_runtime", None)
        if isinstance(runtime, AnalyticsRuntime) and not isinstance(runtime.sink, NoOpSink):
            return runtime
    except Exception:
        pass
    return None


def accepted_upload(runtime: AnalyticsRuntime | None) -> None:
    try:
        if runtime is not None:
            runtime.sink.emit(UploadAccepted(utc_now(runtime.clock.utcnow()).date().isoformat()))
    except Exception:
        if runtime is not None:
            _lost(runtime.sink)


class PageObserver:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        runtime = None
        try:
            if (
                scope["type"] == "http"
                and scope["method"] == "GET"
                and scope["path"] in ("/", "/help", "/about", "/rules")
            ):
                prefetch = any(
                    key.lower() in (b"purpose", b"sec-purpose") and b"prefetch" in value.lower()
                    for key, value in scope.get("headers", [])
                )
                if not prefetch:
                    runtime = runtime_for(scope.get("app"))
        except Exception:
            pass
        if runtime is None:
            await self.app(scope, receive, send)
            return
        qualifies = False
        emitted = False

        async def observe_send(message: Message) -> None:
            nonlocal qualifies, emitted
            # A failed send must retain the application's exception and must not count.
            await send(message)
            try:
                if message["type"] == "http.response.start":
                    qualifies = message["status"] == 200 and any(
                        key.lower() == b"content-type"
                        and value.lower().split(b";", 1)[0].strip() == b"text/html"
                        for key, value in message.get("headers", [])
                    )
                if (
                    message["type"] == "http.response.body"
                    and not message.get("more_body", False)
                    and qualifies
                    and not emitted
                ):
                    emitted = True
                    runtime.sink.emit(PageView(utc_now(runtime.clock.utcnow()).date().isoformat()))
            except Exception:
                _lost(runtime.sink)

        await self.app(scope, receive, observe_send)
