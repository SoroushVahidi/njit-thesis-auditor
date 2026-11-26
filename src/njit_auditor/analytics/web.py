"""No-throw web observations; contexts retain only a sink, clock and timing."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .collector import BoundedCollector, Clock, NoOpSink, Sink
from .runtime import AnalyticsRuntime
from .schema import (
    AuditTerminal,
    Event,
    Outcome,
    PageView,
    ReportFormat,
    ReportResponse,
    Source,
    SubmissionAttempted,
    UploadAccepted,
    duration_bucket,
    utc_now,
)

_internal_activity = ContextVar("analytics_internal_activity", default=False)


@contextmanager
def trusted_internal_activity() -> Iterator[None]:
    """Mark a trusted in-process operator or synthetic context."""
    token = _internal_activity.set(True)
    try:
        yield
    finally:
        _internal_activity.reset(token)


def is_internal_activity() -> bool:
    return _internal_activity.get()


def _lost(sink: Sink) -> None:
    try:
        if isinstance(sink, BoundedCollector):
            sink.mark_loss()
    except Exception:
        pass


class AuditObservation:
    def __init__(
        self, runtime: AnalyticsRuntime, source: Source = "unknown", internal: bool = False
    ) -> None:
        self.sink = runtime.sink
        self.clock = runtime.clock
        self.source = source
        self.internal = internal
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
            _emit(
                self.sink,
                self.clock,
                lambda day: AuditTerminal(day, outcome, bucket, self.source, self.internal),
            )
        except Exception:
            _lost(self.sink)


_current: ContextVar[AuditObservation | None] = ContextVar("analytics_observation", default=None)


@contextmanager
def task_context(
    runtime: AnalyticsRuntime, source: Source = "unknown", internal: bool = False
) -> Iterator[None]:
    observation = None
    try:
        observation = AuditObservation(runtime, source, internal)
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


def _emit(sink: Sink, clock: Clock, make_event: Callable[[str], Event]) -> None:
    try:
        if isinstance(sink, BoundedCollector):
            sink.emit_current(make_event)
        else:
            sink.emit(make_event(utc_now(clock.utcnow()).date().isoformat()))
    except Exception:
        _lost(sink)


def submission_attempt(app: Any, source: Source) -> None:
    runtime = runtime_for(app)
    if runtime is not None:
        _emit(
            runtime.sink,
            runtime.clock,
            lambda day: SubmissionAttempted(day, source, is_internal_activity()),
        )


def accepted_upload(
    runtime: AnalyticsRuntime | None, source: Source = "unknown", internal: bool = False
) -> None:
    if runtime is not None:
        _emit(runtime.sink, runtime.clock, lambda day: UploadAccepted(day, source, internal))


_PAGES = frozenset(("/", "/help", "/about", "/rules"))
_REPORT_ROUTES: dict[str, tuple[ReportFormat, bytes]] = {
    "download_student_pdf_report": ("complete_pdf", b"application/pdf"),
    "serve_job_highlighted_page_pdf": ("focused_pdf", b"application/pdf"),
    "download_comments_pdf": ("comments_pdf", b"application/pdf"),
    "serve_job_pdf_highlighted": ("legacy_pdf", b"application/pdf"),
    "download_json": ("json", b"application/json"),
    "download_markdown": ("markdown", b"text/markdown"),
    "download_text": ("text", b"text/plain"),
}


def _content_type(message: Message) -> bytes:
    return next(
        (
            value.lower().split(b";", 1)[0].strip()
            for key, value in message.get("headers", [])
            if key.lower() == b"content-type"
        ),
        b"",
    )


class PageObserver:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        runtime = None
        try:
            if scope["type"] == "http" and scope["method"] == "GET":
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
        page_view = False
        report: ReportFormat | None = None
        full_response = False
        emitted = False

        async def observe_send(message: Message) -> None:
            nonlocal page_view, report, full_response, emitted
            # A failed send must retain the application's exception and must not count.
            await send(message)
            try:
                if message["type"] == "http.response.start":
                    status = message["status"]
                    content_type = _content_type(message)
                    page_view = (
                        scope["path"] in _PAGES and status == 200 and content_type == b"text/html"
                    )
                    route_name = getattr(scope.get("route"), "name", None)
                    route = _REPORT_ROUTES.get(route_name) if isinstance(route_name, str) else None
                    if route is not None and (
                        status in (200, 206) and (
                            content_type == route[1]
                            or (status == 206 and content_type == b"multipart/byteranges")
                        )
                    ):
                        report, full_response = route[0], status == 200
                final_body = (
                    message["type"] == "http.response.body" and not message.get("more_body", False)
                )
                if not emitted and (final_body or message["type"] == "http.response.pathsend"):
                    emitted = True
                    internal = is_internal_activity()
                    if page_view:
                        _emit(runtime.sink, runtime.clock, lambda day: PageView(day, internal))
                    elif report is not None:
                        report_format = report
                        _emit(
                            runtime.sink,
                            runtime.clock,
                            lambda day: ReportResponse(
                                day, report_format, "full" if full_response else "partial", internal
                            ),
                        )
            except Exception:
                _lost(runtime.sink)

        await self.app(scope, receive, observe_send)
