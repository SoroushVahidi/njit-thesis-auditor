"""Synthetic web boundaries, terminal failures and exact aggregate totals."""

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from test_analytics_collector import manual_collector
from test_analytics_schema import FakeClock
from test_analytics_store import database as database

from njit_auditor.analytics.runtime import AnalyticsRuntime
from njit_auditor.analytics.schema import (
    AuditTerminal,
    PageView,
    ReportResponse,
    SubmissionAttempted,
    UploadAccepted,
)
from njit_auditor.analytics.web import (
    AuditObservation,
    PageObserver,
    task_context,
    trusted_internal_activity,
)


class RecordingSink:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


def synthetic_pdf():
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((60, 80), "Synthetic chapter for analytics testing.", fontsize=12)
        page.insert_text(
            (60, 110), "This generated document contains no student material.", fontsize=12
        )
        return doc.tobytes()


@pytest.fixture
def web(tmp_path, monkeypatch):
    from njit_auditor import web_app as wa

    monkeypatch.setattr(wa, "RUNTIME_DIR", tmp_path / "uploads")
    monkeypatch.setattr(wa, "_jobs", {})
    monkeypatch.setattr(wa, "_after_audit_task", None)
    monkeypatch.setattr(wa.app, "state", SimpleNamespace(offline_mode=False))
    monkeypatch.setattr(wa.app.state, "analytics_runtime", AnalyticsRuntime(), raising=False)
    monkeypatch.setattr(wa.app.state, "audit_executor", wa._run_audit_task, raising=False)
    monkeypatch.setattr(wa.app.state, "prepare_audit", None, raising=False)
    return wa, TestClient(wa.app, raise_server_exceptions=False)


def submit(client, content=None):
    return client.post(
        "/audits",
        files={"file": ("synthetic.pdf", content or synthetic_pdf(), "application/pdf")},
        follow_redirects=False,
    )


def snapshot_audit(wa, client):
    response = submit(client)
    assert response.status_code == 303
    job_id = response.headers["location"].split("/")[-1]
    job = wa._get_job(job_id)
    directory = wa._job_dir(job_id)
    reports = {}
    for name in ("report.json", "report.md", "report.txt"):
        path = directory / name
        if not path.exists():
            continue
        text = path.read_text()
        if name.endswith(".json"):
            value = json.loads(text)
            value["metadata"].pop("generated_at", None)
            reports[name] = value
        else:
            reports[name] = re.sub(r"(?m)^- Generated at: .+$", "- Generated at: <time>", text)
    callback_state = job.state
    removed = wa.cleanup_expired_jobs(
        datetime.now(timezone.utc) + timedelta(seconds=wa.JOB_TTL_SECONDS + 2)
    )
    return {
        "status": response.status_code,
        "state": callback_state,
        "reports": reports,
        "findings": job.findings,
        "cleanup_count": removed,
        "workspace_exists": directory.exists(),
        "job_exists": wa._get_job(job_id) is not None,
    }


@pytest.mark.parametrize(
    "method,path,status,content_type,prefetch,expected",
    [
        ("GET", "/", 200, b"text/html; charset=utf-8", b"", 1),
        ("GET", "/help", 200, b"text/html", b"", 1),
        ("GET", "/about", 200, b"text/html", b"", 1),
        ("GET", "/rules", 200, b"text/html", b"", 1),
        ("HEAD", "/", 200, b"text/html", b"", 0),
        ("GET", "/", 200, b"application/json", b"", 0),
        ("GET", "/", 302, b"text/html", b"", 0),
        ("GET", "/", 500, b"text/html", b"", 0),
        ("GET", "/", 200, b"text/html", b"prefetch;prerender", 0),
        *[
            ("GET", p, 200, b"text/html", b"", 0)
            for p in (
                "/healthz",
                "/version",
                "/audits/id",
                "/audits/id/status",
                "/assets/a",
                "/admin",
                "/sample.pdf",
                "/rules/",
                "/audits/id/download/json",
            )
        ],
    ],
)
def test_final_page_boundary(method, path, status, content_type, prefetch, expected):
    sink = RecordingSink()
    runtime = AnalyticsRuntime(sink, FakeClock())
    application = SimpleNamespace(state=SimpleNamespace(analytics_runtime=runtime))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "app": application,
        "query_string": b"PRIVATE_CANARY",
        "headers": [(b"sec-purpose", prefetch), (b"user-agent", b"PRIVATE_CANARY")],
    }

    async def inner(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", content_type)],
            }
        )
        await send({"type": "http.response.body", "body": b"x", "more_body": True})
        assert not sink.events
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        assert len(sink.events) == expected  # before unrelated background work
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def send(message):
        pass

    asyncio.run(PageObserver(inner)(scope, None, send))
    assert sink.events == [PageView("2030-01-01")] * expected


def test_send_failure_not_counted():
    sink = RecordingSink()
    runtime = AnalyticsRuntime(sink, FakeClock())

    async def inner(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def send(message):
        if message["type"] == "http.response.body":
            raise RuntimeError("synthetic disconnect")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "app": SimpleNamespace(state=SimpleNamespace(analytics_runtime=runtime)),
    }
    with pytest.raises(RuntimeError):
        asyncio.run(PageObserver(inner)(scope, None, send))
    assert not sink.events


def test_exact_enabled_sequence_and_utc(web, database, monkeypatch):
    wa, client = web
    collector = manual_collector(database)
    clock = collector.clock
    runtime = AnalyticsRuntime(collector, clock)
    monkeypatch.setattr(wa.app.state, "analytics_runtime", runtime)
    for path in ("/", "/help", "/about", "/rules"):
        assert client.get(path).status_code == 200
    client.head("/")
    client.get("/", headers={"Purpose": "prefetch"})
    client.get("/healthz")
    client.post("/audits", files={"file": ("bad.txt", b"no", "text/plain")})
    original = wa.run_audit_for_uploaded_file

    def success(*args, **kwargs):
        clock.advance(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(wa, "run_audit_for_uploaded_file", success)
    assert submit(client).status_code == 303
    clock.now = datetime(2030, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

    def failed(*args, **kwargs):
        clock.advance(2)
        raise wa.AuditError("synthetic failure")

    monkeypatch.setattr(wa, "run_audit_for_uploaded_file", failed)
    assert submit(client).status_code == 303
    clock.advance(5)
    collector._tick()
    rows = collector._store.db.execute(
        "SELECT day_utc,metric,n FROM daily_count WHERE n>0"
    ).fetchall()
    assert sorted(rows) == sorted(
        [
            ("2030-01-01", "page_view", 4),
            ("2030-01-01", "submission_attempted", 2),
            ("2030-01-01", "submission_attempted_upload", 2),
            ("2030-01-31", "submission_attempted", 1),
            ("2030-01-31", "submission_attempted_upload", 1),
            ("2030-01-01", "upload_accepted", 1),
            ("2030-01-01", "upload_accepted_upload", 1),
            ("2030-01-31", "upload_accepted", 1),
            ("2030-01-31", "upload_accepted_upload", 1),
            ("2030-01-01", "audit_completed", 1),
            ("2030-01-01", "audit_completed_upload", 1),
            ("2030-02-01", "audit_failed", 1),
            ("2030-02-01", "audit_failed_upload", 1),
        ]
    )
    assert sorted(
        collector._store.db.execute(
            "SELECT day_utc,outcome,bucket,n FROM daily_duration WHERE n>0"
        ).fetchall()
    ) == [("2030-01-01", "completed", 2, 1), ("2030-02-01", "failed", 1, 1)]
    collector._disconnect()


def test_duplicate_terminal_invalid_duration_missing_job(web):
    wa, _ = web
    sink, clock = RecordingSink(), FakeClock()
    runtime = AnalyticsRuntime(sink, clock)
    observation = AuditObservation(runtime)
    observation.finish("failed")
    assert not sink.events
    observation.start()
    clock.mono = -1
    observation.finish("completed")
    observation.finish("failed")
    assert sink.events == [AuditTerminal("2030-01-01", "completed", None)]
    with task_context(runtime):
        wa._run_audit_task("missing")
    assert len(sink.events) == 1


@pytest.mark.parametrize(
    "failure",
    [
        "upload",
        "audit",
        "unexpected",
        "json",
        "markdown",
        "view",
        "view_dict",
        "preview",
        "text",
        "final_set",
        "initial_set",
    ],
)
def test_initial_failures_never_success(web, monkeypatch, failure):
    wa, client = web
    sink = RecordingSink()
    monkeypatch.setattr(wa.app.state, "analytics_runtime", AnalyticsRuntime(sink, FakeClock()))
    cleanup = []
    monkeypatch.setattr(wa, "_after_audit_task", lambda job_id: cleanup.append(job_id))

    def fail(*args, **kwargs):
        error = {"upload": wa.UploadValidationError, "audit": wa.AuditError}.get(
            failure, RuntimeError
        )
        raise error("synthetic")

    hooks = {
        "upload": "run_audit_for_uploaded_file",
        "audit": "run_audit_for_uploaded_file",
        "unexpected": "run_audit_for_uploaded_file",
        "markdown": "write_markdown_report",
        "view": "build_report_view",
        "view_dict": "report_view_to_dict",
    }
    if failure in hooks:
        monkeypatch.setattr(wa, hooks[failure], fail)
    if failure in ("json", "text"):
        original = Path.write_text

        def write(path, *args, **kwargs):
            if path.name == ("report.json" if failure == "json" else "report.txt"):
                fail()
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", write)
    if failure == "preview":
        original = Path.read_text

        def read(path, *args, **kwargs):
            if path.name == "report.md":
                fail()
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", read)
    if failure.endswith("_set"):
        original_set = wa._set_job

        def set_job(job):
            if job.state == ("complete" if failure == "final_set" else "running"):
                fail()
            return original_set(job)

        monkeypatch.setattr(wa, "_set_job", set_job)
    assert submit(client).status_code == 303
    terminals = [e for e in sink.events if isinstance(e, AuditTerminal)]
    assert len(terminals) == 1 and terminals[0].outcome == "failed"
    assert len(cleanup) == 1


def test_scheduling_rejection_repetition_and_lazy_export(web, monkeypatch):
    wa, client = web
    sink = RecordingSink()
    monkeypatch.setattr(wa.app.state, "analytics_runtime", AnalyticsRuntime(sink, FakeClock()))
    with patch("starlette.background.BackgroundTasks.add_task", side_effect=RuntimeError):
        assert submit(client).status_code == 500
    assert sink.events == [SubmissionAttempted("2030-01-01", "upload")]
    first = submit(client)
    assert submit(client).status_code == 303
    assert sum(e.kind == "upload_accepted" for e in sink.events) == 2
    before = list(sink.events)
    with patch.object(wa, "build_combined_student_pdf_report", side_effect=RuntimeError):
        client.get(first.headers["location"] + "/download/student-report.pdf")
    assert sink.events == before


def test_sample_and_report_boundaries_are_distinct_and_private(web, monkeypatch):
    wa, client = web
    sink = RecordingSink()
    monkeypatch.setattr(wa.app.state, "analytics_runtime", AnalyticsRuntime(sink, FakeClock()))
    headers = {
        "X-Internal-Activity": "true",
        "X-Forwarded-For": "192.0.2.44",
        "Cookie": "UNTRUSTED_ID=PRIVATE_CANARY",
    }
    assert client.get("/", headers=headers).status_code == 200
    assert sink.events == [PageView("2030-01-01")]
    with trusted_internal_activity():
        response = client.post(
            "/sample-audits", data={"sample_id": "synthetic_example"}, follow_redirects=False
        )
        assert response.status_code == 303
        path = response.headers["location"]
        assert client.get(path + "/download/json").status_code == 200
        assert client.get(
            path + "/download/json", headers={"Range": "bytes=0-32"}
        ).status_code == 206
        assert client.get(path + "/pdf").status_code == 200
        assert client.get("/audits/does-not-exist/download/json").status_code == 404
        assert client.head(path + "/download/json").status_code in (200, 405)
    assert sink.events == [
        PageView("2030-01-01"),
        SubmissionAttempted("2030-01-01", "approved_sample", True),
        UploadAccepted("2030-01-01", "approved_sample", True),
        AuditTerminal("2030-01-01", "completed", 0, "approved_sample", True),
        ReportResponse("2030-01-01", "json", "full", True),
        ReportResponse("2030-01-01", "json", "partial", True),
    ]
    assert client.get("/about").status_code == 200
    assert sink.events[-1] == PageView("2030-01-01")


@pytest.mark.parametrize(("route", "format_name", "content_type"), [
    ("download_student_pdf_report", "complete_pdf", b"application/pdf"),
    ("serve_job_highlighted_page_pdf", "focused_pdf", b"application/pdf"),
    ("download_comments_pdf", "comments_pdf", b"application/pdf"),
    ("serve_job_pdf_highlighted", "legacy_pdf", b"application/pdf"),
    ("download_json", "json", b"application/json"),
    ("download_markdown", "markdown", b"text/markdown"),
    ("download_text", "text", b"text/plain"),
])
def test_report_response_observer_ignores_body_and_path(route, format_name, content_type):
    sink = RecordingSink()
    runtime = AnalyticsRuntime(sink, FakeClock())
    app = SimpleNamespace(state=SimpleNamespace(analytics_runtime=runtime))
    scope = {"type": "http", "method": "GET", "path": "/PRIVATE-CANARY", "app": app}

    async def inner(scope, receive, send):
        scope["route"] = SimpleNamespace(name=route)
        await send({
            "type": "http.response.start", "status": 200,
            "headers": [(b"content-type", content_type)],
        })
        assert not sink.events
        await send({"type": "http.response.pathsend", "path": "/PRIVATE-CANARY"})
        await send({"type": "http.response.body", "body": b"PRIVATE-CANARY"})

    async def send(message):
        pass

    asyncio.run(PageObserver(inner)(scope, None, send))
    assert sink.events == [ReportResponse("2030-01-01", format_name, "full")]


@pytest.mark.parametrize("helper", ["signal", "accepted_upload", "runtime_for", "task_context"])
def test_helper_failures_preserve_success_and_cleanup(web, monkeypatch, helper):
    wa, client = web
    monkeypatch.setattr(wa, "_new_job_id", lambda: "syntheticjob00001")
    baseline = snapshot_audit(wa, client)
    monkeypatch.setattr(
        wa.app.state, "analytics_runtime", AnalyticsRuntime(RecordingSink(), FakeClock())
    )
    with patch.object(wa.analytics_web, helper, side_effect=RuntimeError("PRIVATE_CANARY")):
        assert snapshot_audit(wa, client) == baseline


def test_no_analytics_routes(web):
    wa, client = web
    assert not any("analytics" in getattr(route, "path", "") for route in wa.app.routes)
    for path in ("/analytics", "/api/public-statistics", "/admin/analytics"):
        assert client.get(path).status_code == 404


def test_concurrent_terminal_once():
    from concurrent.futures import ThreadPoolExecutor

    sink = RecordingSink()
    observation = AuditObservation(AnalyticsRuntime(sink, FakeClock()))
    observation.start()
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(observation.finish, ["completed"] * 32))
    assert sink.events == [AuditTerminal("2030-01-01", "completed", 0)]


def test_terminal_wall_clock_failure_marks_coverage(database):
    collector = manual_collector(database)
    runtime = AnalyticsRuntime(collector, collector.clock)
    observation = AuditObservation(runtime)
    observation.start()
    with patch.object(collector.clock, "utcnow", side_effect=RuntimeError("PRIVATE_CANARY")):
        observation.finish("completed")
    assert collector._loss
    collector._tick()
    assert collector._store.db.execute("SELECT MAX(known_dropped) FROM daily_coverage").fetchone()[
        0
    ]
    collector._disconnect()


def test_failure_state_write_and_finish_clock(web, monkeypatch):
    wa, client = web
    for failure in ("failure_state", "finished_at"):
        sink = RecordingSink()
        monkeypatch.setattr(wa.app.state, "analytics_runtime", AnalyticsRuntime(sink, FakeClock()))
        cleaned = []
        monkeypatch.setattr(wa, "_after_audit_task", lambda job_id: cleaned.append(job_id))
        with monkeypatch.context() as context:
            if failure == "failure_state":

                def fail_audit(*args, **kwargs):
                    raise wa.AuditError("synthetic")

                context.setattr(wa, "run_audit_for_uploaded_file", fail_audit)
                original = wa._set_job

                def fail_set(job):
                    if job.state == "failed":
                        raise RuntimeError("synthetic")
                    original(job)

                context.setattr(wa, "_set_job", fail_set)
            else:
                original_render = wa.render_student_report_text

                def render(*args, **kwargs):
                    value = original_render(*args, **kwargs)
                    context.setattr(wa, "datetime", SimpleNamespace(now=lambda *a: 1 / 0))
                    return value

                context.setattr(wa, "render_student_report_text", render)
            assert submit(client).status_code == 303
        assert len(cleaned) == 1
        assert [e.outcome for e in sink.events if isinstance(e, AuditTerminal)] == ["failed"]


def test_testclient_allows_explicit_synthetic_runtime(web, database, monkeypatch):
    import sqlite3
    import threading

    from njit_auditor.analytics.collector import BoundedCollector

    wa, _ = web
    monkeypatch.setenv("NJIT_AUDITOR_ANALYTICS_ENABLED", "1")
    monkeypatch.setenv("NJIT_AUDITOR_ANALYTICS_DB", str(database))
    monkeypatch.setattr(wa, "ENVIRONMENT_NAME", "production")
    collector = BoundedCollector(database, FakeClock())
    ready = threading.Event()
    tick = collector._tick

    def wrapped():
        tick()
        ready.set()

    monkeypatch.setattr(collector, "_tick", wrapped)
    wa.app.state.analytics_runtime = AnalyticsRuntime(collector, collector.clock)
    with TestClient(wa.app) as client:
        assert ready.wait(3)
        assert client.get("/").status_code == 200
    assert not collector.thread.is_alive()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT SUM(n) FROM daily_count WHERE metric='page_view'").fetchone() == (
            1,
        )
