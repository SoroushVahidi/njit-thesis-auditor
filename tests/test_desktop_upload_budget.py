"""Synthetic ASGI streams: no large allocations or native Windows assumptions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from starlette import formparsers
from test_offline_desktop import _pdf

from njit_auditor import offline_app, web_app
from njit_auditor.request_body_limit import MULTIPART_OVERHEAD_BYTES

ORIGIN = "http://127.0.0.1:17391"
PAYLOAD_LIMIT = 4096
OVERHEAD = 1024
BOUNDARY = b"synthetic-boundary"


def multipart(csrf, files, padding=0):
    body = (
        b"--" + BOUNDARY + b'\r\nContent-Disposition: form-data; name="csrf_token"\r\n\r\n'
        + csrf.encode() + b"\r\n"
    )
    for data in files:
        body += (
            b"--" + BOUNDARY
            + b'\r\nContent-Disposition: form-data; name="file"; filename="synthetic.pdf"'
            + b"\r\nContent-Type: application/pdf\r\n\r\n" + data + b"\r\n"
        )
    if padding:
        body += (
            b"--" + BOUNDARY + b'\r\nContent-Disposition: form-data; name="padding"\r\n\r\n'
            + b"x" * padding + b"\r\n"
        )
    return body + b"--" + BOUNDARY + b"--\r\n"


def request(app, *, path="/audits", method="POST", headers=(), chunks=(), disconnect=False):
    """Bypass HTTP clients so absent/false lengths and chunk boundaries stay exact."""
    sent, consumed = [], []

    async def run():
        iterator = iter(chunks)
        exhausted = False

        async def receive():
            nonlocal exhausted
            if exhausted:
                if disconnect:
                    return {"type": "http.disconnect"}
                await asyncio.Event().wait()
            try:
                body = next(iterator)
            except StopIteration:
                exhausted = True
                if disconnect:
                    return {"type": "http.disconnect"}
                return {"type": "http.request", "body": b"", "more_body": False}
            consumed.append(len(body))
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message):
            sent.append(message)

        route, _, query = path.partition("?")
        request_headers = list(headers)
        if not any(k == b"host" for k, _ in request_headers):
            request_headers.insert(0, (b"host", b"127.0.0.1:17391"))
        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1", "method": method, "scheme": "http",
            "path": route, "raw_path": route.encode(), "query_string": query.encode(),
            "root_path": "", "server": ("127.0.0.1", 17391), "client": ("127.0.0.1", 40000),
            "headers": request_headers,
        }
        await asyncio.wait_for(app(scope, receive, send), timeout=15)

    asyncio.run(run())
    start = next(message for message in sent if message["type"] == "http.response.start")
    return SimpleNamespace(
        status=start["status"], headers=dict(start["headers"]), consumed=consumed,
        body=b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body"),
    )


@pytest.fixture()
def desktop(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "MAX_UPLOAD_BYTES", PAYLOAD_LIMIT)
    monkeypatch.setattr(offline_app, "MULTIPART_OVERHEAD_BYTES", OVERHEAD)
    monkeypatch.setattr(web_app, "_jobs", {})
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    monkeypatch.setattr(web_app, "_after_audit_task", None)
    offline_app.prepare_local_storage(tmp_path)
    app = offline_app.create_offline_app(port=17391, data_root=tmp_path, launch_ticket="ticket")
    login = request(app, path="/_session/start?ticket=ticket", method="GET")
    cookie = login.headers[b"set-cookie"].split(b";", 1)[0]
    handles = []
    original = formparsers.SpooledTemporaryFile

    def spool(*args, **kwargs):
        # Roll even small test files to disk, making explicit closure observable.
        kwargs["max_size"] = 1
        handle = original(*args, dir=tmp_path / "tmp", **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", spool)
    headers = [
        (b"cookie", cookie), (b"origin", ORIGIN.encode()),
        (b"content-type", b"multipart/form-data; boundary=" + BOUNDARY),
    ]
    yield SimpleNamespace(app=app, headers=headers, root=tmp_path, handles=handles)
    app.state.desktop_executor.close()
    assert all(handle.closed for handle in handles)
    assert not list((tmp_path / "tmp").iterdir())


def upload(desktop, body, *, length=None, chunk_size=511, disconnect=False, headers=None):
    actual_headers = list(desktop.headers if headers is None else headers)
    if length is not None:
        actual_headers.append((b"content-length", str(length).encode()))
    return request(
        desktop.app, headers=actual_headers,
        chunks=(body[i:i + chunk_size] for i in range(0, len(body), chunk_size)),
        disconnect=disconnect,
    )


@pytest.mark.parametrize("size", [None, PAYLOAD_LIMIT - 1, PAYLOAD_LIMIT])
@pytest.mark.parametrize("length_mode", ["accurate", "missing", "false-small"])
def test_valid_pdf_survives_body_replay_and_form_cleanup(desktop, size, length_mode):
    pdf = _pdf("normal")
    if size is not None:
        pdf += b"\n" * (size - len(pdf))
    body = multipart(desktop.app.state.csrf_token, [pdf])
    length = {"accurate": len(body), "missing": None, "false-small": 1}[length_mode]
    response = upload(desktop, body, length=length)
    assert response.status == 303
    job_id = response.headers[b"location"].decode().rsplit("/", 1)[-1]
    job = web_app._get_job(job_id)
    assert job.state == "complete"
    assert (desktop.root / "audits" / job_id / "upload.pdf").read_bytes() == pdf
    for format_name in ("json", "markdown", "text"):
        report = request(
            desktop.app, path=f"/audits/{job_id}/download/{format_name}", method="GET",
            headers=desktop.headers,
        )
        assert report.status == 200 and report.body


def test_declared_oversize_rejected_without_receiving_or_parsing(desktop):
    response = upload(desktop, b"not read", length=PAYLOAD_LIMIT + OVERHEAD + 1)
    assert response.status == 413
    assert response.consumed == []
    assert desktop.handles == []
    assert b"Choose one PDF" in response.body
    assert response.headers[b"cache-control"] == b"no-store"
    assert str(desktop.root).encode() not in response.body


@pytest.mark.parametrize("length", [None, 0, 1, PAYLOAD_LIMIT + OVERHEAD, "chunked"])
def test_stream_limit_stops_early_before_multipart_and_recovers(desktop, length):
    body = multipart(desktop.app.state.csrf_token, [b"x" * (PAYLOAD_LIMIT * 4)])
    headers = list(desktop.headers)
    if length == "chunked":
        headers.append((b"transfer-encoding", b"chunked"))
        length = None
    response = upload(desktop, body, length=length, headers=headers)
    assert response.status == 413
    assert sum(response.consumed) <= PAYLOAD_LIMIT + OVERHEAD + 511
    assert sum(response.consumed) < len(body)
    assert desktop.handles == []
    assert not web_app._jobs and not list((desktop.root / "audits").iterdir())
    assert request(desktop.app, path="/help", method="GET", headers=desktop.headers).status == 200
    valid = multipart(desktop.app.state.csrf_token, [_pdf("normal")])
    assert upload(desktop, valid).status == 303


@pytest.mark.parametrize("extra", [0, 1])
def test_exact_multipart_budget_boundary(desktop, extra):
    pdf = _pdf("normal")
    pdf += b"\n" * (PAYLOAD_LIMIT - len(pdf))
    baseline = multipart(desktop.app.state.csrf_token, [pdf], padding=1)
    padding = PAYLOAD_LIMIT + OVERHEAD - len(baseline) + 1 + extra
    body = multipart(desktop.app.state.csrf_token, [pdf], padding=padding)
    assert len(body) == PAYLOAD_LIMIT + OVERHEAD + extra
    response = upload(desktop, body)
    assert response.status == (413 if extra else 303)


def test_multiple_files_share_one_aggregate_budget(desktop):
    pdf = _pdf("normal")
    pdf += b"\n" * (3000 - len(pdf))
    assert len(pdf) < PAYLOAD_LIMIT
    response = upload(desktop, multipart(desktop.app.state.csrf_token, [pdf, pdf]))
    assert response.status == 413
    assert not desktop.handles and not web_app._jobs


def test_multiple_small_files_are_closed_and_cannot_raise_payload_limit(desktop):
    pdf = _pdf("normal")
    response = upload(desktop, multipart(desktop.app.state.csrf_token, [pdf, pdf]))
    assert response.status == 303  # Preserve the endpoint's existing selection semantics.
    assert len(desktop.handles) == 4  # Middleware and endpoint each parse both parts.
    assert all(handle.closed for handle in desktop.handles)


def test_file_payload_limit_remains_independent_of_envelope_allowance(desktop):
    pdf = _pdf("normal")
    pdf += b"\n" * (PAYLOAD_LIMIT + 1 - len(pdf))
    body = multipart(desktop.app.state.csrf_token, [pdf])
    assert len(body) < PAYLOAD_LIMIT + OVERHEAD
    response = upload(desktop, body)
    assert response.status == 303  # Existing endpoint redirects to its size-error page.
    assert b"status=413" in response.headers[b"location"]
    assert not web_app._jobs and not list((desktop.root / "audits").iterdir())


@pytest.mark.parametrize("failure", ["cookie", "origin", "missing-origin", "cross-site", "host"])
def test_security_rejection_precedes_body_read(desktop, failure):
    headers = list(desktop.headers)
    if failure in {"cookie", "origin", "missing-origin"}:
        key = b"cookie" if failure == "cookie" else b"origin"
        headers = [(k, v) for k, v in headers if k != key]
        if failure == "origin":
            headers.append((key, b"http://invalid.example"))
    elif failure == "cross-site":
        headers.append((b"sec-fetch-site", b"cross-site"))
    else:
        headers.append((b"host", b"invalid.example"))
    response = upload(desktop, b"not read", length=100000, headers=headers)
    assert response.status == 403 and response.consumed == []


@pytest.mark.parametrize("csrf", ["", "incorrect"])
def test_csrf_rejection_closes_temporary_files(desktop, csrf):
    response = upload(desktop, multipart(csrf, [_pdf("normal")]))
    assert response.status == 403
    assert desktop.handles and all(handle.closed for handle in desktop.handles)
    assert not web_app._jobs


@pytest.mark.parametrize("kind", [
    "disconnect", "malformed-header", "invalid-length", "truncated-part", "truncated-envelope",
])
def test_bad_requests_leave_no_unmanaged_files(desktop, kind):
    body = multipart(desktop.app.state.csrf_token, [_pdf("normal")])
    if kind == "malformed-header":
        body = body[:-len(BOUNDARY) - 6] + b"--" + BOUNDARY + b"\r\n\x00bad-header\r\n"
    elif kind == "truncated-part":
        body = body[:-100]
    elif kind == "truncated-envelope":
        body = body[:-5]
    response = upload(
        desktop, body, disconnect=kind == "disconnect",
        length="invalid" if kind == "invalid-length" else None,
    )
    assert response.status == 400
    assert all(handle.closed for handle in desktop.handles)
    assert not web_app._jobs and not list((desktop.root / "audits").iterdir())


def test_production_overhead_is_bounded():
    assert MULTIPART_OVERHEAD_BYTES == 64 * 1024


@pytest.mark.parametrize("lengths", [[b"-1"], [b"1.5"], [b"0", b"100"], [b"9" * 5000]])
def test_invalid_lengths_are_safe_and_do_not_read_body(desktop, lengths):
    response = upload(
        desktop, b"not read",
        headers=[*desktop.headers, *((b"content-length", value) for value in lengths)],
    )
    assert response.status == 400 and response.consumed == []
    assert not desktop.handles
