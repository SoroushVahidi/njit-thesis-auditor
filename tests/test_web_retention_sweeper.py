"""Retention cleanup independent of HTTP traffic, and accurate privacy wording.

All fixtures are synthetic: empty job directories and a minimal PDF header.
Timestamps are backdated (``created_at`` and ``os.utime``) instead of waiting
for a real TTL; the sweeper interval is a few milliseconds.
"""

from __future__ import annotations

import importlib
import logging
import os
import threading
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import njit_auditor.web_app as web_app

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"
_TTL = 60


@pytest.fixture()
def wa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The web app module pointed at a private runtime dir with a 60 s TTL."""
    runtime = tmp_path / "web_audits"
    runtime.mkdir()
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    monkeypatch.setattr(web_app, "JOB_TTL_SECONDS", _TTL)
    monkeypatch.setattr(web_app, "_last_cleanup_failures", 0)
    with web_app._jobs_lock:
        saved = dict(web_app._jobs)
        web_app._jobs.clear()
    yield web_app
    with web_app._jobs_lock:
        web_app._jobs.clear()
        web_app._jobs.update(saved)


def _iso(age_seconds: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()


def _make_job(wa: Any, job_id: str, state: str, age_seconds: float) -> Path:
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    wa._set_job(
        wa.JobState(job_id=job_id, state=state, created_at=_iso(age_seconds), file_name="t.pdf")
    )
    return jdir


def _make_orphan(wa: Any, name: str, age_seconds: float) -> Path:
    jdir = wa.RUNTIME_DIR / name
    jdir.mkdir()
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    stamp = time.time() - age_seconds
    os.utime(jdir, (stamp, stamp))
    return jdir


def _wait_until(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


# ---------------------------------------------------------------------------
# Sweeper lifecycle
# ---------------------------------------------------------------------------


def test_sweeper_deletes_expired_uploads_without_any_request(wa: Any) -> None:
    expired = _make_job(wa, "expiredcomplete1", "complete", age_seconds=2 * _TTL)
    orphan = _make_orphan(wa, "orphanafterrestart", age_seconds=2 * _TTL)
    fresh = _make_job(wa, "freshcomplete001", "complete", age_seconds=1)

    sweeper = wa.RetentionSweeper(wa.cleanup_expired_jobs, 0.005)
    sweeper.start()
    try:
        assert _wait_until(lambda: not expired.exists() and not orphan.exists())
    finally:
        sweeper.stop()

    assert wa._get_job("expiredcomplete1") is None
    assert fresh.exists()
    assert wa._get_job("freshcomplete001") is not None


def test_sweeper_runs_periodically(wa: Any) -> None:
    calls: list[float] = []
    done = threading.Event()

    def sweep() -> int:
        calls.append(time.monotonic())
        if len(calls) >= 3:
            done.set()
        return 0

    sweeper = wa.RetentionSweeper(sweep, 0.005)
    sweeper.start()
    try:
        assert done.wait(5.0)
    finally:
        sweeper.stop()
    assert len(calls) >= 3


def test_sweeper_stop_is_prompt_and_final(wa: Any) -> None:
    calls: list[int] = []
    sweeper = wa.RetentionSweeper(lambda: calls.append(1) or 0, 3600)
    sweeper.start()
    assert sweeper.is_running

    started = time.monotonic()
    sweeper.stop()
    assert time.monotonic() - started < 2.0
    assert not sweeper.is_running
    count = len(calls)
    time.sleep(0.02)
    assert len(calls) == count  # nothing runs after stop


def test_sweeper_survives_a_failing_sweep_and_logs_once(
    wa: Any, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[int] = []
    done = threading.Event()

    def sweep() -> int:
        calls.append(1)
        if len(calls) >= 4:
            done.set()
        raise OSError("synthetic failure")

    sweeper = wa.RetentionSweeper(sweep, 0.005)
    with caplog.at_level(logging.WARNING, logger="njit_auditor.web_app"):
        sweeper.start()
        try:
            assert done.wait(5.0)
        finally:
            sweeper.stop()
    failures = [r for r in caplog.records if "Retention sweep failed" in r.getMessage()]
    assert len(failures) == 1
    assert "synthetic failure" not in failures[0].getMessage()


def test_startup_sweeps_before_requests_and_shutdown_stops_sweeper(wa: Any) -> None:
    expired = _make_job(wa, "expiredatstartup", "failed", age_seconds=2 * _TTL)
    orphan = _make_orphan(wa, "orphanatstartup1", age_seconds=2 * _TTL)

    with TestClient(wa.app):
        # Lifespan startup has run; no request has been sent yet.
        assert not expired.exists()
        assert not orphan.exists()
        assert wa._retention_sweeper.is_running
    assert not wa._retention_sweeper.is_running


def test_cleanup_interval_env_default_and_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "rt"))
    try:
        monkeypatch.delenv("NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS", raising=False)
        assert importlib.reload(web_app).CLEANUP_INTERVAL_SECONDS == 300
        for bad in ("0", "-5", "soon"):
            monkeypatch.setenv("NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS", bad)
            assert importlib.reload(web_app).CLEANUP_INTERVAL_SECONDS == 300
        monkeypatch.setenv("NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS", "120")
        assert importlib.reload(web_app).CLEANUP_INTERVAL_SECONDS == 120
    finally:
        monkeypatch.undo()
        importlib.reload(web_app)


# ---------------------------------------------------------------------------
# What a sweep deletes and keeps
# ---------------------------------------------------------------------------


def test_expired_complete_and_failed_jobs_are_deleted(wa: Any) -> None:
    done = _make_job(wa, "expiredcomplete2", "complete", age_seconds=2 * _TTL)
    failed = _make_job(wa, "expiredfailed001", "failed", age_seconds=2 * _TTL)

    assert wa.cleanup_expired_jobs() == 2
    assert not done.exists() and not failed.exists()
    assert wa._get_job("expiredcomplete2") is None
    assert wa._get_job("expiredfailed001") is None


def test_unexpired_job_is_kept(wa: Any) -> None:
    jdir = _make_job(wa, "freshcomplete002", "complete", age_seconds=_TTL - 10)
    assert wa.cleanup_expired_jobs() == 0
    assert jdir.exists()
    assert wa._get_job("freshcomplete002") is not None


@pytest.mark.parametrize("state", ["pending", "running"])
def test_pending_and_running_jobs_are_never_deleted(wa: Any, state: str) -> None:
    jdir = _make_job(wa, f"old{state}job0001", state, age_seconds=100 * _TTL)
    os.utime(jdir, (0, 0))
    assert wa.cleanup_expired_jobs() == 0
    assert jdir.exists()
    assert wa._get_job(f"old{state}job0001") is not None


def test_already_deleted_directory_is_tolerated(wa: Any) -> None:
    jdir = _make_job(wa, "vanishedjob00001", "complete", age_seconds=2 * _TTL)
    for child in jdir.iterdir():
        child.unlink()
    jdir.rmdir()
    assert wa.cleanup_expired_jobs() == 1
    assert wa._get_job("vanishedjob00001") is None


def test_missing_runtime_root_is_tolerated(wa: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wa, "RUNTIME_DIR", wa.RUNTIME_DIR / "does-not-exist")
    assert wa.cleanup_expired_jobs() == 0


def test_old_orphan_is_deleted_and_fresh_orphan_is_kept(wa: Any) -> None:
    old = _make_orphan(wa, "oldorphan0000001", age_seconds=2 * _TTL)
    # A just-created upload directory whose job is not registered yet.
    fresh = _make_orphan(wa, "uploadinprogress", age_seconds=0)

    assert wa.cleanup_expired_jobs() == 1
    assert not old.exists()
    assert fresh.exists()


def test_stray_file_in_runtime_root_is_left_alone(wa: Any) -> None:
    stray = wa.RUNTIME_DIR / "notes.txt"
    stray.write_text("synthetic", encoding="utf-8")
    os.utime(stray, (0, 0))
    wa.cleanup_expired_jobs()
    assert stray.exists()


def test_undeletable_workspace_is_retried_and_logged_without_job_id(
    wa: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    orphan = _make_orphan(wa, "secretjobtoken01", age_seconds=2 * _TTL)

    with monkeypatch.context() as patched:
        patched.setattr(wa.shutil, "rmtree", lambda *args, **kwargs: None)
        with caplog.at_level(logging.WARNING, logger="njit_auditor.web_app"):
            assert wa.cleanup_expired_jobs() == 0
            assert wa.cleanup_expired_jobs() == 0  # same failure: not logged again
    assert orphan.exists()
    warnings = [r.getMessage() for r in caplog.records if "could not delete" in r.getMessage()]
    assert warnings == ["Retention cleanup could not delete 1 job workspace(s)."]
    assert all("secretjobtoken01" not in r.getMessage() for r in caplog.records)

    assert wa.cleanup_expired_jobs() == 1  # retried on a later sweep
    assert not orphan.exists()


def test_unreadable_entry_does_not_abort_the_sweep(
    wa: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    flaky = _make_orphan(wa, "flakyorphan00001", age_seconds=2 * _TTL)
    old = _make_orphan(wa, "oldorphan0000002", age_seconds=2 * _TTL)
    real_lstat = Path.lstat

    def lstat(self: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        if self.name == flaky.name:
            raise FileNotFoundError(self.name)
        return real_lstat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat)
    assert wa.cleanup_expired_jobs() == 1
    assert not old.exists()


# ---------------------------------------------------------------------------
# Path-boundary and symlink protection
# ---------------------------------------------------------------------------


def test_symlinked_entry_is_never_followed_or_deleted(wa: Any, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    keep = outside / "keep.txt"
    keep.write_text("stay", encoding="utf-8")
    link = wa.RUNTIME_DIR / "linkedorphan0001"
    link.symlink_to(outside, target_is_directory=True)
    os.utime(outside, (0, 0))
    os.utime(link, (0, 0), follow_symlinks=False)

    assert wa.cleanup_expired_jobs() == 0
    assert keep.exists()
    assert link.is_symlink()


def test_symlinked_job_workspace_is_not_followed(wa: Any, tmp_path: Path) -> None:
    outside = tmp_path / "outside2"
    outside.mkdir()
    keep = outside / "keep.txt"
    keep.write_text("stay", encoding="utf-8")
    (wa.RUNTIME_DIR / "symlinkjob000001").symlink_to(outside, target_is_directory=True)
    wa._set_job(
        wa.JobState(
            job_id="symlinkjob000001", state="complete", created_at=_iso(2 * _TTL), file_name="t"
        )
    )

    assert wa.cleanup_expired_jobs() == 1  # the job is evicted from memory...
    assert keep.exists()  # ...but nothing outside the runtime root is touched


@pytest.mark.parametrize("job_id", ["", ".", ".."])
def test_runtime_root_and_its_parent_are_never_deleted(wa: Any, job_id: str) -> None:
    marker = wa.RUNTIME_DIR / "marker.txt"
    marker.write_text("stay", encoding="utf-8")
    parent_marker = wa.RUNTIME_DIR.parent / "parent-marker.txt"
    parent_marker.write_text("stay", encoding="utf-8")
    wa._set_job(
        wa.JobState(job_id=job_id, state="complete", created_at=_iso(2 * _TTL), file_name="t")
    )

    wa.cleanup_expired_jobs()
    assert wa.RUNTIME_DIR.is_dir()
    assert marker.exists()
    assert parent_marker.exists()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_jobs_created_and_completed_during_sweeps_are_kept(wa: Any) -> None:
    errors: list[BaseException] = []

    def sweep() -> int:
        try:
            return wa.cleanup_expired_jobs()
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)
            raise

    sweeper = wa.RetentionSweeper(sweep, 0.0005)
    stale = [_make_job(wa, f"stalejob{i:08d}", "complete", 2 * _TTL) for i in range(20)]
    sweeper.start()
    created: list[Path] = []
    try:
        for i in range(150):
            job_id = f"livejob{i:09d}"
            jdir = wa._job_dir(job_id)
            jdir.mkdir()  # directory first, job registered after: like POST /audits
            (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
            job = wa.JobState(job_id=job_id, state="pending", created_at=_iso(0), file_name="t")
            wa._set_job(job)
            job.state = "running"
            wa._set_job(job)
            job.state = "complete"
            wa._set_job(job)
            created.append(jdir)
        assert _wait_until(lambda: not any(p.exists() for p in stale))
    finally:
        sweeper.stop()

    assert not errors
    assert all(p.exists() for p in created)
    assert all(wa._get_job(p.name) is not None for p in created)


# ---------------------------------------------------------------------------
# Student-facing wording
# ---------------------------------------------------------------------------


@pytest.fixture()
def configured_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "rt"))
    monkeypatch.setenv("NJIT_AUDITOR_WEB_JOB_TTL_SECONDS", "3600")
    monkeypatch.setenv("NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS", "300")
    try:
        yield importlib.reload(web_app)
    finally:
        monkeypatch.undo()
        importlib.reload(web_app)


_FALSE_CLAIMS = (
    b"no dissertation body text",
    b"not stored permanently",
    b"privacy-safe processing",
    b"rule metadata only",
)


def test_retention_notice_matches_configuration(configured_app: Any) -> None:
    notice = configured_app._retention_notice()
    assert "deleted automatically about 1 hour after the audit" in notice
    assert "checks for expired files every 5 minutes" in notice
    assert "still running is not deleted" in notice
    assert "server restarts" in notice


def test_index_and_help_describe_retention_and_excerpts_accurately(
    configured_app: Any,
) -> None:
    c = TestClient(configured_app.app)
    notice = configured_app._retention_notice().encode()
    for path in ("/", "/help"):
        body = c.get(path).content
        assert notice in body.replace(b"&#39;", b"'")
        assert b"may quote short pieces of your document" in body
        assert b"anyone with your result link can open the results" in body
        for claim in _FALSE_CLAIMS:
            assert claim not in body.lower(), (path, claim)


def test_results_page_privacy_note_is_accurate(configured_app: Any) -> None:
    wa = configured_app
    job_id = "wordingjob000001"
    wa._job_dir(job_id).mkdir(parents=True)
    wa._set_job(
        wa.JobState(
            job_id=job_id,
            state="complete",
            created_at=_iso(0),
            finished_at=_iso(0),
            file_name="t.pdf",
        )
    )
    body = TestClient(wa.app).get(f"/audits/{job_id}").content
    assert b"Privacy note" in body
    assert b"may quote short pieces of your" in body
    assert b"deleted automatically about 1 hour after the audit" in body
    for claim in _FALSE_CLAIMS:
        assert claim not in body.lower(), claim


def test_markdown_report_privacy_note_is_accurate(tmp_path: Path) -> None:
    from njit_auditor.report_outputs import write_markdown_report

    out = tmp_path / "report.md"
    write_markdown_report([], {"audit_type": "pdf", "input_file_name": "t.pdf"}, out)
    text = out.read_text(encoding="utf-8")
    assert "may quote short excerpts of the audited document" in text
    assert "avoids dissertation body text" not in text
