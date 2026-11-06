"""Real supervised Linux processes, synthetic PDFs, deterministic lifecycle faults."""

import asyncio
import json
import sys
import threading
import time
from pathlib import Path

import fitz
import httpx
import pytest
from fastapi import Request
from fastapi.responses import FileResponse
from test_web_app import _inject_complete_job_with_findings, _p012_annotation_finding_with_bbox

from njit_auditor import desktop_exports, web_app
from njit_auditor.desktop_executor import worker_command
from njit_auditor.desktop_exports import PdfExportExecutor
from njit_auditor.offline_app import create_offline_app, prepare_local_storage

HOST = "http://127.0.0.1:17391"


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    runtime = prepare_local_storage(tmp_path)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(web_app, "_jobs", {})
    monkeypatch.setattr(web_app, "_export_leases", {})
    monkeypatch.setattr(web_app, "_after_audit_task", None)
    managers = []

    def create(**kwargs):
        manager = PdfExportExecutor(**kwargs)
        managers.append(manager)
        app = create_offline_app(
            port=17391, data_root=tmp_path, launch_ticket="ticket", export_executor=manager
        )
        job_id = _inject_complete_job_with_findings(
            web_app,
            tmp_path,
            findings=[_p012_annotation_finding_with_bbox(page=1)],
            file_name="synthetic.pdf",
            audit_type="pdf",
            page_count=2,
        )
        return manager, app, job_id

    yield create
    for manager in managers:
        assert manager.close()
    assert not web_app._export_leases
    assert not list(runtime.glob("*/.export-tmp-*"))


def request(app):
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "path": "/",
            "root_path": "",
            "headers": [],
            "scheme": "http",
            "server": ("127.0.0.1", 17391),
            "query_string": b"",
        },
        receive=receive,
    )


def hanging(path):
    return [
        sys.executable,
        "-c",
        "import pathlib,time; "
        f"pathlib.Path({str(path.parent / 'partial.pdf')!r}).write_bytes(b'%PDF-partial'); "
        "time.sleep(60)",
    ]


def track(monkeypatch):
    processes = []
    started = threading.Event()
    original = desktop_exports.start_worker

    def start(*args):
        process, tree = original(*args)
        processes.append(process)
        started.set()
        return process, tree

    monkeypatch.setattr(desktop_exports, "start_worker", start)
    return processes, started


async def wait_started(started):
    assert await asyncio.to_thread(started.wait, 3)


@pytest.mark.parametrize(
    "kind,params",
    [
        ("student", {}),
        ("highlighted", {"page": 1}),
        ("page", {"page": 1}),
    ],
)
def test_worker_success_and_identical_concurrent_cache_reuse(setup, monkeypatch, kind, params):
    processes, _ = track(monkeypatch)
    manager, app, job_id = setup(deadline=15)

    async def run():
        return await asyncio.gather(
            *[manager.response(request(app), job_id, kind, params) for _ in range(3)]
        )

    results = asyncio.run(run())
    assert all(isinstance(result, FileResponse) for result in results)
    assert len({str(result.path) for result in results}) == 1
    assert len(processes) == 1
    assert all(process.poll() is not None for process in processes)
    with fitz.open(results[0].path) as pdf:
        assert pdf.page_count >= 1
        if kind != "student":
            assert list(pdf[0].annots())
    # An open downloader must not cause another replace (WinError 5 regression).
    with Path(results[0].path).open("rb") as downloader:
        again = asyncio.run(manager.response(request(app), job_id, kind, params))
        assert Path(again.path).read_bytes() == downloader.read()
    assert len(processes) == 1


def test_slow_export_keeps_navigation_status_and_heartbeat_responsive(setup, monkeypatch):
    processes, started = track(monkeypatch)
    manager, app, job_id = setup(deadline=10, command=hanging)

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=HOST) as client:
            await client.get("/_session/start?ticket=ticket")
            export = asyncio.create_task(
                client.get(f"/audits/{job_id}/download/student-report.pdf")
            )
            await wait_started(started)
            for _ in range(5):
                before = time.monotonic()
                await asyncio.sleep(0.01)
                assert time.monotonic() - before < 0.2
            for path in ("/help", "/sample.pdf", f"/audits/{job_id}/status"):
                assert (await asyncio.wait_for(client.get(path), 0.5)).status_code == 200
            # Both session and CSRF checks still protect a running export.
            assert (await client.post(f"/audits/{job_id}/cancel")).status_code == 403
            denied = httpx.AsyncClient(transport=transport, base_url=HOST)
            async with denied:
                assert (
                    await denied.get(f"/audits/{job_id}/download/student-report.pdf")
                ).status_code == 403
            response = await client.post(
                f"/audits/{job_id}/cancel",
                headers={"Origin": HOST},
                data={"csrf_token": app.state.csrf_token},
            )
            assert response.status_code == 303
            assert (await export).status_code == 503

    asyncio.run(run())
    assert all(process.poll() is not None for process in processes)
    manager.deadline, manager._command = 15, worker_command
    assert isinstance(
        asyncio.run(manager.response(request(app), job_id, "student", {})), FileResponse
    )


@pytest.mark.parametrize("mode", ["timeout", "task-cancel", "close", "crash"])
def test_termination_cleans_partial_outputs_and_preserves_server(setup, monkeypatch, mode):
    processes, started = track(monkeypatch)
    command = hanging
    if mode == "crash":

        def command(path):
            return [sys.executable, "-c", "raise SystemExit(7)"]

    manager, app, job_id = setup(deadline=0.3 if mode == "timeout" else 10, command=command)

    async def run():
        export = asyncio.create_task(manager.response(request(app), job_id, "student", {}))
        await wait_started(started)
        if mode == "task-cancel":
            export.cancel()
            with pytest.raises(asyncio.CancelledError):
                await export
        else:
            if mode == "close":
                assert await asyncio.wait_for(asyncio.to_thread(manager.close), 2)
            assert (await export).status_code == 503
        assert web_app._get_job(job_id).state == "complete"

    asyncio.run(run())
    assert processes and all(process.poll() is not None for process in processes)
    assert not manager._operations
    assert not list(web_app._job_dir(job_id).glob(".export-*"))
    if mode != "close":
        manager.deadline, manager._command = 15, worker_command
        assert isinstance(
            asyncio.run(manager.response(request(app), job_id, "student", {})), FileResponse
        )


def test_concurrency_and_queue_deadlines_bound_process_count(setup, monkeypatch):
    processes, _ = track(monkeypatch)
    manager, app, job_id = setup(deadline=0.3, max_active=1, command=hanging)

    async def run():
        return await asyncio.gather(
            *[manager.response(request(app), job_id, "student", {}) for _ in range(6)]
        )

    assert all(result.status_code == 503 for result in asyncio.run(run()))
    assert len(processes) == 1
    assert all(process.poll() is not None for process in processes)


@pytest.mark.parametrize("action", ["delete", "delete-all", "quit", "lifespan"])
def test_deletion_and_shutdown_stop_exports_before_removing_inputs(setup, monkeypatch, action):
    processes, started = track(monkeypatch)
    manager, app, job_id = setup(deadline=10, command=hanging)

    async def run():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url=HOST
            ) as client:
                await client.get("/_session/start?ticket=ticket")
                export = asyncio.create_task(
                    client.get(f"/audits/{job_id}/download/student-report.pdf")
                )
                await wait_started(started)
                if action != "lifespan":
                    path = {
                        "delete": f"/audits/{job_id}/delete",
                        "delete-all": "/local-data/delete-all",
                        "quit": "/quit",
                    }[action]
                    response = await asyncio.wait_for(
                        client.post(
                            path,
                            headers={"Origin": HOST},
                            data={"csrf_token": app.state.csrf_token},
                        ),
                        2,
                    )
                    assert response.status_code in (200, 303)
                    assert (await export).status_code == 503
        if action == "lifespan":
            assert (await export).status_code == 503

    asyncio.run(run())
    assert all(process.poll() is not None for process in processes)
    assert not web_app._job_dir(job_id).exists()


@pytest.mark.parametrize("failure", ["sharing", "disk-full", "cancel"])
def test_publication_failure_never_poisons_cache_and_retry_succeeds(setup, monkeypatch, failure):
    manager, app, job_id = setup(deadline=15)
    original = desktop_exports.os.replace

    def fail(source, destination):
        if Path(source).name.startswith(".export-tmp-"):
            assert (Path(source) / ".desktop-result.json").is_file()
            if failure == "cancel":
                manager._operations[0].cancel.set()
                raise desktop_exports.ExportUnavailable()
            error = (
                PermissionError("Synthetic sharing violation")
                if failure == "sharing"
                else OSError(28, "Disk full")
            )
            raise error
        return original(source, destination)

    monkeypatch.setattr(desktop_exports.os, "replace", fail)
    assert asyncio.run(manager.response(request(app), job_id, "student", {})).status_code == 503
    assert not list(web_app._job_dir(job_id).glob(".export-*"))
    monkeypatch.setattr(desktop_exports.os, "replace", original)
    assert isinstance(
        asyncio.run(manager.response(request(app), job_id, "student", {})), FileResponse
    )


def test_failed_new_generation_preserves_cached_download_and_success_retries(setup):
    manager, app, job_id = setup(deadline=15)
    first = asyncio.run(manager.response(request(app), job_id, "student", {}))
    previous = Path(first.path).read_bytes()
    web_app._get_job(job_id).findings[0]["polished_comment"] = "Updated synthetic explanation."
    manager.deadline, manager._command = 0.2, hanging
    with Path(first.path).open("rb") as downloading:
        assert asyncio.run(manager.response(request(app), job_id, "student", {})).status_code == 503
        assert downloading.read() == previous
    assert Path(first.path).read_bytes() == previous
    manager.deadline, manager._command = 15, worker_command
    second = asyncio.run(manager.response(request(app), job_id, "student", {}))
    assert second.path != first.path
    with fitz.open(second.path) as pdf:
        assert "Updated synthetic explanation." in "".join(page.get_text() for page in pdf)


def test_corrupted_published_cache_is_rejected_and_regenerated(setup):
    manager, app, job_id = setup(deadline=15)
    first = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    Path(first.path).write_bytes(b"%PDF-partial")
    second = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    with fitz.open(second.path) as pdf:
        assert pdf.page_count == 1
    third = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    assert third.path == second.path
    assert json.loads((Path(third.path).parent / ".desktop-result.json").read_text())["digest"]


@pytest.mark.parametrize("kind", ["full", "page"])
def test_hosted_concurrent_highlights_publish_once_and_reuse_valid_pdf(setup, monkeypatch, kind):
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    _, _, job_id = setup()
    attribute = "build_highlighted_pdf" if kind == "full" else "build_highlighted_single_page_pdf"
    original = getattr(web_app, attribute)
    calls = []

    def slow(*args, **kwargs):
        calls.append(1)
        time.sleep(0.05)
        return original(*args, **kwargs)

    monkeypatch.setattr(web_app, attribute, slow)
    suffix = "pdf/highlighted" if kind == "full" else "highlighted-page.pdf"
    client = TestClient(web_app.app)
    url = f"/audits/{job_id}/{suffix}?page=1"
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(client.get, [url] * 3))
    assert len(calls) == 1
    assert all(result.status_code == 200 for result in results)
    assert len({result.content for result in results}) == 1
    with fitz.open(stream=results[0].content, filetype="pdf") as document:
        assert document.page_count == (2 if kind == "full" else 1)
    client.close()


def test_shutdown_with_large_queue_does_not_starve_control_thread_pool(setup, monkeypatch):
    processes, started = track(monkeypatch)
    manager, app, job_id = setup(deadline=10, max_active=1, command=hanging)

    async def run():
        exports = [
            asyncio.create_task(manager.response(request(app), job_id, "student", {}))
            for _ in range(40)
        ]
        await wait_started(started)
        assert await asyncio.wait_for(asyncio.to_thread(manager.close), 2)
        assert all(response.status_code == 503 for response in await asyncio.gather(*exports))

    asyncio.run(run())
    assert len(processes) == 1 and processes[0].poll() is not None


def test_retention_preserves_inputs_until_export_lease_is_released(setup, monkeypatch):
    from datetime import datetime, timedelta, timezone

    _, started = track(monkeypatch)
    manager, app, job_id = setup(deadline=10, command=hanging)

    async def run():
        export = asyncio.create_task(manager.response(request(app), job_id, "student", {}))
        await wait_started(started)
        web_app.cleanup_expired_jobs(datetime.now(timezone.utc) + timedelta(days=10))
        assert web_app._get_job(job_id) is not None
        assert web_app._job_dir(job_id).is_dir()
        assert not web_app._delete_job_workspace(job_id)
        assert await asyncio.to_thread(manager.cancel, job_id)
        assert (await export).status_code == 503
        web_app.cleanup_expired_jobs(datetime.now(timezone.utc) + timedelta(days=10))
        assert not web_app._job_dir(job_id).exists()

    asyncio.run(run())


def test_failed_process_stop_retains_ownership_and_files_until_retry(setup, monkeypatch):
    from njit_auditor.desktop_process import ProcessTree

    manager, app, job_id = setup(deadline=0.2, command=hanging)
    original = ProcessTree.stop
    with monkeypatch.context() as patch:

        def failed_stop(self):
            raise OSError("Synthetic termination failure")

        patch.setattr(ProcessTree, "stop", failed_stop)
        assert asyncio.run(manager.response(request(app), job_id, "student", {})).status_code == 503
        assert manager.cleanup_failed.is_set()
        assert manager._operations and web_app._export_leases[job_id]
        assert not web_app._delete_job_workspace(job_id)
        assert not manager.close()
    assert ProcessTree.stop is original
    assert manager.close()
    assert not manager._operations and not web_app._export_leases


@pytest.mark.parametrize("phase", ["before", "after"])
def test_cancellation_at_publication_boundary_never_exposes_partial_pdf(setup, monkeypatch, phase):
    manager, app, job_id = setup(deadline=15)
    original_cached, original_replace = manager._cached, desktop_exports.os.replace

    def cached(directory, source):
        value = original_cached(directory, source)
        if value and directory.name.startswith(".export-tmp-") and phase == "before":
            manager._operations[0].cancel.set()
        return value

    def replace(source, target):
        result = original_replace(source, target)
        if Path(source).name.startswith(".export-tmp-") and phase == "after":
            manager._operations[0].cancel.set()
        return result

    monkeypatch.setattr(manager, "_cached", cached)
    monkeypatch.setattr(desktop_exports.os, "replace", replace)
    assert asyncio.run(manager.response(request(app), job_id, "student", {})).status_code == 503
    outputs = list(web_app._job_dir(job_id).glob(".export-*/student-report.pdf"))
    assert len(outputs) == (0 if phase == "before" else 1)
    for path in outputs:
        with fitz.open(path) as pdf:
            assert pdf.page_count > 2


@pytest.mark.parametrize("deadline,max_active", [(0, 1), (-1, 1), (float("inf"), 1), (1, 0)])
def test_invalid_export_limits_are_rejected(deadline, max_active):
    with pytest.raises(ValueError):
        PdfExportExecutor(deadline=deadline, max_active=max_active)


def test_disconnected_download_cancels_worker_without_waiting_for_deadline(setup, monkeypatch):
    processes, started = track(monkeypatch)
    manager, app, job_id = setup(deadline=10, command=hanging)

    async def run():
        disconnected = asyncio.Event()

        async def receive():
            await disconnected.wait()
            return {"type": "http.disconnect"}

        incoming = Request(request(app).scope, receive=receive)
        export = asyncio.create_task(manager.response(incoming, job_id, "student", {}))
        await wait_started(started)
        disconnected.set()
        assert (await asyncio.wait_for(export, 2)).status_code == 503

    asyncio.run(run())
    assert processes and all(process.poll() is not None for process in processes)
    assert not manager._operations


@pytest.mark.parametrize("limit", [1, 2])
def test_independent_jobs_respect_configured_concurrency(setup, monkeypatch, tmp_path, limit):
    manager, app, first = setup(deadline=0.4, max_active=limit, command=hanging)
    jobs = [first] + [
        _inject_complete_job_with_findings(
            web_app,
            tmp_path,
            findings=[],
            file_name="synthetic.pdf",
            audit_type="pdf",
            page_count=1,
        )
        for _ in range(3)
    ]
    processes, peaks = [], []
    original = desktop_exports.start_worker

    def start(*args):
        process, tree = original(*args)
        processes.append(process)
        peaks.append(sum(p.poll() is None for p in processes))
        return process, tree

    monkeypatch.setattr(desktop_exports, "start_worker", start)

    async def run():
        return await asyncio.gather(
            *[manager.response(request(app), job, "student", {}) for job in jobs]
        )

    assert all(response.status_code == 503 for response in asyncio.run(run()))
    assert max(peaks) == limit
    assert all(process.poll() is not None for process in processes)


def test_plain_fallback_after_worker_highlight_failure_is_not_cached(setup):
    manager, app, job_id = setup(deadline=15)
    code = (
        "import sys; from njit_auditor import web_app; "
        "web_app.build_highlighted_pdf = lambda *a, **k: "
        "(_ for _ in ()).throw(OSError('Synthetic save failure')); "
        "from njit_auditor.desktop_worker import main; sys.exit(main(sys.argv[1:]))"
    )
    manager._command = lambda path: [sys.executable, "-c", code, str(path)]
    first = asyncio.run(manager.response(request(app), job_id, "highlighted", {"page": 1}))
    assert Path(first.path).name == "upload.pdf"
    assert not list(web_app._job_dir(job_id).glob(".export-*"))
    manager._command = worker_command
    second = asyncio.run(manager.response(request(app), job_id, "highlighted", {"page": 1}))
    assert Path(second.path).name.startswith("highlighted-")
    with fitz.open(second.path) as document:
        page = document[0]
        assert list(page.annots())


def test_immutable_cache_count_is_bounded_and_existing_download_still_works(setup, monkeypatch):
    processes, _ = track(monkeypatch)
    manager, app, job_id = setup(deadline=15, max_cached_exports=2)
    first = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    second = asyncio.run(manager.response(request(app), job_id, "page", {"page": 2}))
    assert isinstance(second, FileResponse)
    with Path(first.path).open("rb") as reader:
        for rule in ("synthetic-a", "synthetic-b", "synthetic-c"):
            denied = asyncio.run(
                manager.response(request(app), job_id, "page", {"page": 1, "rule_id": rule})
            )
            assert denied.status_code == 503
            assert b"storage limit" in denied.body
        cached = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
        assert Path(cached.path).read_bytes() == reader.read()
    assert len(processes) == 2
    assert len(list(web_app._job_dir(job_id).glob(".export-*"))) == 2


def test_cache_byte_limit_rejects_publication_and_preserves_prior_generation(setup):
    manager, app, job_id = setup(deadline=15)
    first = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    previous = Path(first.path).read_bytes()
    # Leave room for admission, but not for a new PDF plus its completion manifest.
    manager.max_cache_bytes = manager._directory_bytes(Path(first.path).parent) + 1
    denied = asyncio.run(manager.response(request(app), job_id, "page", {"page": 2}))
    assert denied.status_code == 503 and b"storage limit" in denied.body
    assert Path(first.path).read_bytes() == previous
    assert len(list(web_app._job_dir(job_id).glob(".export-*"))) == 1
    assert not list(web_app._job_dir(job_id).glob(".export-tmp-*"))
    manager.max_cache_bytes *= 10
    assert isinstance(
        asyncio.run(manager.response(request(app), job_id, "page", {"page": 2})), FileResponse
    )


def test_quarantined_generations_count_toward_storage_limit(setup, monkeypatch):
    processes, _ = track(monkeypatch)
    manager, app, job_id = setup(deadline=15, max_cached_exports=2)
    first = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    Path(first.path).write_bytes(b"partial")
    second = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    Path(second.path).write_bytes(b"partial")
    denied = asyncio.run(manager.response(request(app), job_id, "page", {"page": 1}))
    assert denied.status_code == 503 and b"storage limit" in denied.body
    assert len(processes) == 2
    assert len(list(web_app._job_dir(job_id).glob(".invalid-export-*"))) == 1


def test_completed_export_cache_cannot_be_reused_after_deletion(setup, monkeypatch):
    from njit_auditor.offline_app import _delete_job

    processes, _ = track(monkeypatch)
    manager, app, job_id = setup(deadline=15)
    exported = asyncio.run(manager.response(request(app), job_id, "student", {}))
    assert isinstance(exported, FileResponse)
    assert _delete_job(job_id) == "deleted"
    assert not Path(exported.path).exists()
    response = asyncio.run(manager.response(request(app), job_id, "student", {}))
    assert response.status_code == 404 and len(processes) == 1
    assert not web_app._job_dir(job_id).exists()


@pytest.mark.parametrize("kwargs", [{"max_cached_exports": 0}, {"max_cache_bytes": 0}])
def test_nonpositive_cache_limits_rejected(kwargs):
    with pytest.raises(ValueError):
        PdfExportExecutor(**kwargs)
