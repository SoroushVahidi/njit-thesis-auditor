"""Synthetic public audit and opt-in HTTP reviewer workflow."""

from __future__ import annotations

import io
import secrets
import sqlite3
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pymupdf
import pytest
from docx import Document
from fastapi.testclient import TestClient
from PIL import Image

from njit_auditor import admin_accounts, admin_feedback, web_app


def _attachment(extension: str) -> bytes:
    output = io.BytesIO()
    if extension in {"png", "jpg", "jpeg"}:
        with Image.new("RGB", (12, 12), "white") as image:
            image.save(output, format="PNG" if extension == "png" else "JPEG")
        return output.getvalue()
    if extension == "docx":
        document = Document()
        document.add_paragraph("Invented general feedback attachment")
        document.save(output)
        return output.getvalue()
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72, 72), "Invented general feedback attachment")
        return pdf.tobytes()


@pytest.fixture
def reviewer_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, Path]]:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    runtime = tmp_path / "audits"
    runtime.mkdir()
    db_path = private / "feedback.sqlite3"
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_SESSION_KEY", secrets.token_urlsafe(32))
    monkeypatch.setenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED", "1")
    monkeypatch.delenv("NJIT_AUDITOR_ADMIN_ENABLED", raising=False)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    with web_app._jobs_lock:
        saved = dict(web_app._jobs)
        web_app._jobs.clear()
    client = TestClient(web_app.app, base_url="http://testserver", raise_server_exceptions=False)
    try:
        yield client, db_path
    finally:
        client.close()
        with web_app._jobs_lock:
            web_app._jobs.clear()
            web_app._jobs.update(saved)


def _login(client: TestClient, username: str, password: str, *, next_url: str = "/"):
    page = client.get("/reviewer/login", params={"next": next_url})
    assert page.status_code == 200 and "Reviewer Access" in page.text
    csrf = client.cookies.get(admin_feedback._REVIEWER_LOGIN_CSRF)
    return client.post("/reviewer/login", data={
        "username": username, "password": password, "csrf_token": csrf, "next": next_url,
    }, headers={"Origin": "http://testserver"}, follow_redirects=False)


def test_http_reviewer_complete_synthetic_audit_workflow(
    reviewer_site: tuple[TestClient, Path],
) -> None:
    client, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    account_id = admin_accounts.create_account("ester", password, role="reviewer")
    admin_accounts.create_account("soroush", secrets.token_urlsafe(24), role="reviewer")
    operator_password = secrets.token_urlsafe(24)
    admin_accounts.create_account("operator", operator_password)

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 100), "Synthetic thesis audit text for reviewer testing.")
    page.add_text_annot((100, 200), "Synthetic annotation")
    pdf = doc.tobytes()
    doc.close()
    anonymous = client.post("/audits", files={
        "file": ("synthetic.pdf", pdf, "application/pdf"),
    }, follow_redirects=False)
    assert anonymous.status_code == 303
    job_url = anonymous.headers["location"]
    job_id = job_url.rsplit("/", 1)[1]
    job = web_app._get_job(job_id)
    assert job is not None and job.state == "complete" and job.findings
    finding_id = str(job.findings[0]["finding_id"])
    page = client.get(job_url)
    assert page.status_code == 200
    assert "Reviewer Access" in page.text
    assert f"Reviewer feedback for {finding_id}" not in page.text
    form_url = f"/audits/{job_id}/feedback/{finding_id}"
    assert client.post(form_url, data={"classification": "other"},
                       headers={"Origin": "http://testserver"}).status_code == 403

    wrong = _login(client, "ester", secrets.token_urlsafe(24), next_url=job_url)
    assert wrong.status_code == 401
    assert password not in wrong.text
    assert _login(client, "operator", operator_password).status_code == 401
    login = _login(client, "ester", password, next_url=job_url)
    assert login.status_code == 303 and login.headers["location"] == job_url
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=strict" in login.headers["set-cookie"].lower()
    assert "secure" not in login.headers["set-cookie"].lower()
    token = client.cookies.get(admin_feedback._REVIEWER_COOKIE)
    assert token
    results = client.get(job_url)
    assert f"Reviewer feedback for {finding_id}" in results.text
    assert 'value="true_positive"' in results.text
    assert 'value="false_positive"' in results.text
    assert 'value="unclear"' in results.text
    assert 'value="other"' in results.text
    assert "Feedback dashboard" not in results.text

    comment = "Synthetic reviewer observation, not dissertation text."
    csrf = admin_feedback._session_csrf(token)
    assert client.post(form_url, data={"csrf_token": csrf, "classification": "unclear",
                                       "comment": comment},
                       headers={"Origin": "http://elsewhere.invalid"}).status_code == 403
    saved = client.post(form_url, data={"csrf_token": csrf, "classification": "unclear",
                                        "comment": comment},
                        headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert saved.status_code == 303
    with sqlite3.connect(db_path) as db:
        row = db.execute("""SELECT f.audit_ref,f.finding_ref,f.classification,f.comment,
            f.created_at,a.username,a.role FROM feedback f JOIN admins a
            ON a.id=f.submitted_by_admin_id WHERE f.audit_ref=?""", (job_id,)).fetchone()
        assert row is not None
        assert row[0:4] == (job_id, finding_id, "unclear", comment)
        assert row[4] and row[5:] == ("ester", "reviewer")
        assert db.execute("SELECT count(*) FROM feedback").fetchone()[0] == 1
        stored_id = db.execute("SELECT id FROM admins WHERE username='ester'").fetchone()[0]
        assert stored_id == account_id
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5

    assert client.get("/admin/feedback").status_code == 403
    assert client.post("/admin/feedback/anything", data={"action": "delete"},
                       headers={"Origin": "http://testserver"}).status_code == 403
    assert client.get("/admin/login", headers={"X-Forwarded-Proto": "https"}).status_code == 503
    for extension in ("json", "markdown", "text", "student-report.pdf"):
        export = client.get(f"/audits/{job_id}/download/{extension}")
        assert export.status_code == 200
        assert comment.encode() not in export.content
        if extension == "student-report.pdf":
            with pymupdf.open(stream=export.content, filetype="pdf") as report:
                assert comment not in " ".join(page.get_text() for page in report)
    public = TestClient(web_app.app, base_url="http://testserver")
    try:
        assert public.get(job_url).status_code == 200
        assert comment not in public.get(job_url).text
        assert public.post(form_url, data={"classification": "other"},
                           headers={"Origin": "http://testserver"}).status_code == 403
    finally:
        public.close()


@pytest.mark.parametrize("username", ["soroush", "ester"])
def test_reviewer_feedback_on_direct_sample_audit(
    reviewer_site: tuple[TestClient, Path], username: str,
) -> None:
    client, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    admin_accounts.create_account(username, password, role="reviewer")

    submitted = client.post(
        "/sample-audits", data={"sample_id": "synthetic_example"}, follow_redirects=False,
    )
    assert submitted.status_code == 303
    job_url = submitted.headers["location"]
    job_id = job_url.rsplit("/", 1)[-1]
    job = web_app._get_job(job_id)
    assert job is not None and job.state == "complete" and job.findings
    finding = job.findings[0]
    finding_id = str(finding["finding_id"])
    form_url = f"/audits/{job_id}/feedback/{finding_id}"
    assert client.get(job_url).status_code == 200
    assert client.post(form_url, data={"classification": "unclear"},
                       headers={"Origin": "http://testserver"}).status_code == 403

    login = _login(client, username, password, next_url=job_url)
    assert login.status_code == 303 and login.headers["location"] == job_url
    assert f"Reviewer feedback for {finding_id}" in client.get(job_url).text
    token = client.cookies.get(admin_feedback._REVIEWER_COOKIE)
    assert token
    comment = "Direct sample review test comment."
    saved = client.post(form_url, data={
        "csrf_token": admin_feedback._session_csrf(token),
        "classification": "unclear", "comment": comment,
    }, headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert saved.status_code == 303
    with sqlite3.connect(db_path) as db:
        row = db.execute("""SELECT f.audit_ref,f.finding_ref,f.rule_id,f.classification,
            f.comment,f.created_at,f.status,a.username FROM feedback f JOIN admins a
            ON a.id=f.submitted_by_admin_id WHERE f.audit_ref=?""", (job_id,)).fetchone()
        assert row is not None
        assert row[:5] == (job_id, finding_id, finding["rule_id"], "unclear", comment)
        assert row[5] and row[6:] == ("Open", username)
    results = client.get(job_url)
    assert comment not in results.text
    assert client.get("/reviewer/feedback").status_code == 404


def test_http_reviewer_disabled_expiry_and_role_boundary(
    reviewer_site: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    admin_accounts.create_account("soroush", password, role="reviewer")
    monkeypatch.delenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED")
    assert "Reviewer Access" not in client.get("/").text
    assert client.get("/reviewer/login").status_code == 503
    monkeypatch.setenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED", "1")
    assert _login(client, "soroush", password).status_code == 303
    token = client.cookies.get(admin_feedback._REVIEWER_COOKIE)
    assert token
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE sessions SET expires_at=0 WHERE token_hash=?",
                   (admin_feedback._token_hash(token),))
    assert "Reviewer Access" in client.get("/").text
    assert client.get("/admin/feedback").status_code == 403
    https = TestClient(web_app.app, base_url="https://testserver")
    try:
        monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
        monkeypatch.setenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED", "1")
        https.cookies.set(admin_feedback._COOKIE, token)
        assert https.get("/admin/feedback").status_code == 403
        page = https.get("/admin/login")
        csrf = https.cookies.get(admin_feedback._LOGIN_CSRF)
        assert page.status_code == 200 and csrf
        assert https.post("/admin/login", data={"username": "soroush",
                                                  "password": password, "csrf_token": csrf},
                          headers={"Origin": "https://testserver"}).status_code == 401
    finally:
        https.close()


def test_reviewer_account_name_is_limited(reviewer_site: tuple[TestClient, Path]) -> None:
    with pytest.raises(ValueError, match="soroush or ester"):
        admin_accounts.create_account("thirdperson", secrets.token_urlsafe(24), role="reviewer")


def test_existing_v4_admin_database_gains_role_without_losing_accounts(
    reviewer_site: tuple[TestClient, Path],
) -> None:
    _, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    account_id = admin_accounts.create_account("operator", password)
    feedback_id = secrets.token_urlsafe(16)
    with sqlite3.connect(db_path) as db:
        db.execute("""INSERT INTO feedback (
            id,audit_ref,finding_ref,rule_id,issue_type,original_confidence,
            classification,comment,context,created_at,updated_at,submitted_by_admin_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                feedback_id, "synthetic-job", "f7", "P011", "margin_violation", "medium",
                "unclear", "Preserved synthetic feedback", "Rule P011",
                "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", account_id,
            ))
        db.execute("ALTER TABLE admins DROP COLUMN role")
        db.execute("PRAGMA user_version=4")
    with admin_feedback._connection() as db:
        row = db.execute("SELECT id,role,password_hash FROM admins WHERE username='operator'")
        account = row.fetchone()
        assert account is not None and account["id"] == account_id
        assert account["role"] == "admin"
        assert admin_accounts._HASHER.verify(account["password_hash"], password)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
        feedback = db.execute("SELECT finding_ref,comment,submitted_by_admin_id "
                              "FROM feedback WHERE id=?", (feedback_id,)).fetchone()
        assert tuple(feedback) == ("f7", "Preserved synthetic feedback", account_id)
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_general_feedback_is_separate_private_and_attachment_is_bounded(
    reviewer_site: tuple[TestClient, Path],
) -> None:
    client, db_path = reviewer_site
    ester_password = secrets.token_urlsafe(24)
    other_password = secrets.token_urlsafe(24)
    ester_id = admin_accounts.create_account("ester", ester_password, role="reviewer")
    admin_accounts.create_account("soroush", other_password, role="reviewer")
    url = "/reviewer/general-feedback"
    assert client.get(url).status_code == 403
    assert client.post(url, data={"comment": "test"},
                       headers={"Origin": "http://testserver"}).status_code == 403
    assert _login(client, "ester", ester_password, next_url=url).status_code == 303
    assert "General feedback" in client.get(url).text
    csrf = admin_feedback._session_csrf(client.cookies.get(admin_feedback._REVIEWER_COOKIE))
    headers = {"Origin": "http://testserver"}
    pdf = _attachment("pdf")
    assert client.post(url, data={"csrf_token": csrf, "comment": "A general suggestion."},
                       files={"attachment": ("example.pdf", pdf, "application/pdf")},
                       headers={"Origin": "http://other.invalid"}).status_code == 403
    assert client.post(url, data={"csrf_token": "wrong", "comment": "bad"},
                       files={"attachment": ("example.pdf", pdf, "application/pdf")},
                       headers=headers).status_code == 403
    assert client.post(url, data={"csrf_token": csrf, "comment": "bad"},
                       files={"attachment": ("example.html", b"<script>bad</script>", "text/html")},
                       headers=headers).status_code == 400
    assert client.post(url, data={"csrf_token": csrf, "comment": "bad"},
                       files={"attachment": ("oversized.pdf", b"%PDF-" + b"x" * (4 * 1024 * 1024),
                                               "application/pdf")},
                       headers=headers).status_code == 413
    saved = client.post(url, data={"csrf_token": csrf, "comment": "A general suggestion."},
                        files={"attachment": ("example.pdf", pdf, "application/pdf")},
                        headers=headers, follow_redirects=False)
    assert saved.status_code == 303
    assert saved.headers["location"] == url + "?notice=saved"
    with sqlite3.connect(db_path) as db:
        row = db.execute("SELECT id,submitted_by_admin_id,comment,attachment_data "
                         "FROM general_feedback").fetchone()
        assert row is not None and row[1:] == (ester_id, "A general suggestion.", pdf)
        assert db.execute("SELECT count(*) FROM feedback").fetchone()[0] == 0
    attachment_url = url + "/" + row[0] + "/attachment"
    download = client.get(attachment_url)
    assert download.status_code == 200 and download.content == pdf
    assert download.headers["content-type"] == "application/octet-stream"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert "A general suggestion." in client.get(url).text
    logout = client.post("/reviewer/logout", data={"csrf_token": csrf},
                         headers=headers, follow_redirects=False)
    assert logout.status_code == 303
    assert client.get(attachment_url).status_code == 403
    assert _login(client, "soroush", other_password).status_code == 303
    assert "A general suggestion." not in client.get(url).text
    assert client.get(attachment_url).status_code == 404


def test_general_feedback_accepts_text_only_and_rejects_empty(
    reviewer_site: tuple[TestClient, Path],
) -> None:
    client, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    admin_accounts.create_account("ester", password, role="reviewer")
    assert _login(client, "ester", password).status_code == 303
    csrf = admin_feedback._session_csrf(client.cookies.get(admin_feedback._REVIEWER_COOKIE))
    headers = {"Origin": "http://testserver"}
    url = "/reviewer/general-feedback"
    assert client.post(url, data={"csrf_token": csrf, "comment": "   "},
                       headers=headers, files={"attachment": ("", b"", "application/octet-stream")}
                       ).status_code == 400
    result = client.post(url, data={"csrf_token": csrf, "comment": "General observation"},
                         files={"attachment": ("", b"", "application/octet-stream")},
                         headers=headers, follow_redirects=False)
    assert result.status_code == 303
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT comment,attachment_data FROM general_feedback").fetchone() == (
            "General observation", None)


def test_general_attachment_sniffing_rejects_disguised_files() -> None:
    assert admin_feedback._valid_general_attachment("chart.png", _attachment("png"))
    assert not admin_feedback._valid_general_attachment("chart.png", b"<script>bad</script>")
    assert not admin_feedback._valid_general_attachment("fake.pdf", b"not a PDF")
    assert admin_feedback._valid_general_attachment("note.docx", _attachment("docx"))
    assert not admin_feedback._valid_general_attachment("fake.docx", b"not a zip")


@pytest.fixture
def general_reviewer(reviewer_site: tuple[TestClient, Path]) -> tuple[TestClient, Path, str, str]:
    client, path = reviewer_site
    password = secrets.token_urlsafe(24)
    identity = admin_accounts.create_account("ester", password, role="reviewer")
    assert _login(client, "ester", password).status_code == 303
    csrf = admin_feedback._session_csrf(client.cookies.get(admin_feedback._REVIEWER_COOKIE))
    return client, path, identity, csrf


def _general_post(client: TestClient, csrf: str, content: bytes | None = None,
                  filename: str = "invented.pdf"):
    return client.post("/reviewer/general-feedback", data={
        "csrf_token": csrf, "comment": "Invented independent observation",
    }, files={"attachment": (filename if content is not None else "", content or b"",
                             "application/octet-stream")},
        headers={"Origin": "http://testserver"}, follow_redirects=False)


@pytest.mark.parametrize("admin_view", [False, True])
def test_general_history_paginates_all_entries_with_stable_ties(
    general_reviewer: tuple[TestClient, Path, str, str], monkeypatch: pytest.MonkeyPatch,
    admin_view: bool,
) -> None:
    reviewer, path, identity, _ = general_reviewer
    other = admin_accounts.create_account("soroush", secrets.token_urlsafe(24), role="reviewer")
    with sqlite3.connect(path) as db:
        db.executemany("""INSERT INTO general_feedback(id,submitted_by_admin_id,comment,created_at)
            VALUES (?,?,?,?)""", [(f"entry-{i:03}", identity, f"invented-entry-{i:03}",
                                 "2026-01-01T00:00:00Z") for i in range(101)])
        db.execute("""INSERT INTO general_feedback(id,submitted_by_admin_id,comment,created_at)
            VALUES ('other',?,'other-private-observation','2025-01-01')""", (other,))
    client = reviewer
    if admin_view:
        monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
        monkeypatch.setenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED", "1")
        password = secrets.token_urlsafe(24)
        admin_accounts.create_account("operator", password)
        client = TestClient(web_app.app, base_url="https://testserver")
        client.get("/admin/login")
        assert client.post("/admin/login", data={
            "username": "operator", "password": password,
            "csrf_token": client.cookies.get(admin_feedback._LOGIN_CSRF),
        }, headers={"Origin": "https://testserver"}, follow_redirects=False).status_code == 303
    try:
        url = "/reviewer/general-feedback"
        first = client.get(url)
        assert first.status_code == 200
        assert first.text.count("invented-entry-") == 100
        assert "invented-entry-100" in first.text and "invented-entry-000" not in first.text
        assert 'aria-label="General feedback pages"' in first.text
        assert "Next" in first.text
        second = client.get(url, params={"page": "2"})
        assert second.status_code == 200
        assert "invented-entry-000" in second.text and "invented-entry-001" not in second.text
        assert ("other-private-observation" in second.text) == admin_view
        assert "Previous" in second.text
        smaller = client.get(url, params={"page": "51", "page_size": "2"})
        assert smaller.status_code == 200 and "invented-entry-000" in smaller.text
        assert client.get(url).text == first.text
        for query in ("page=0", "page_size=101", "page=1&page=2"):
            assert client.get(url + "?" + query).status_code == 400
    finally:
        if admin_view:
            client.close()


@pytest.mark.parametrize("query", ["page=0", "page=-1", "page=x", "page=1.0", "page=",
    "page=9999999999999999999", "page=2", "page_size=0", "page_size=101", "page_size=no",
    "page=1&page=2", "page_size=10&page_size=10"])
def test_general_pagination_rejects_invalid_parameters(
    general_reviewer: tuple[TestClient, Path, str, str], query: str,
) -> None:
    client, _, _, _ = general_reviewer
    response = client.get("/reviewer/general-feedback?" + query)
    assert response.status_code == 400 and "Invalid feedback page" in response.text
    with TestClient(web_app.app) as anonymous:
        assert anonymous.get("/reviewer/general-feedback?" + query).status_code == 403


@pytest.mark.parametrize("token", ["é", "令牌", "", "invalid-ascii", None])
def test_general_malformed_csrf_fails_without_writing(
    general_reviewer: tuple[TestClient, Path, str, str], token: str | None,
) -> None:
    client, path, _, csrf = general_reviewer
    if token is None:
        response = client.post("/reviewer/general-feedback", files={
            "comment": (None, "invented"),
        }, headers={"Origin": "http://testserver"})
    else:
        response = _general_post(client, token)
    assert response.status_code in (400, 403)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM general_feedback").fetchone()[0] == 0
    assert _general_post(client, csrf).status_code == 303


@pytest.mark.parametrize("extension", ["png", "jpg", "jpeg", "pdf", "docx"])
def test_general_structurally_valid_attachments_and_truncations(
    general_reviewer: tuple[TestClient, Path, str, str], extension: str,
) -> None:
    client, path, _, csrf = general_reviewer
    content = _attachment(extension)
    assert _general_post(client, csrf, content, "invented." + extension).status_code == 303
    with sqlite3.connect(path) as db:
        identifier, stored = db.execute(
            "SELECT id,attachment_data FROM general_feedback").fetchone()
        assert stored == content
    response = client.get(f"/reviewer/general-feedback/{identifier}/attachment")
    assert response.content == content and response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert _general_post(client, csrf, content[:len(content) // 2],
                         "truncated." + extension).status_code == 400


@pytest.mark.parametrize("filename,content", [
    ("bad.png", b"\x89PNG\r\n\x1a\nnot an image"),
    ("bad.jpg", b"\xff\xd8\xffnot an image"), ("bad.pdf", b"%PDF-not a PDF"),
])
def test_general_signature_only_files_are_rejected(filename: str, content: bytes) -> None:
    assert not admin_feedback._valid_general_attachment(filename, content)


@pytest.mark.parametrize("change", ["invalid_xml", "wrong_root", "dtd", "crc", "bomb",
                                  "duplicate", "traversal", "macro", "missing"])
def test_general_docx_rejects_unsafe_packages(change: str) -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(_attachment("docx"))) as original, zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED,
    ) as target:
        for name in original.namelist():
            if change == "missing" and name == "_rels/.rels":
                continue
            data = original.read(name)
            if name == "word/document.xml":
                if change == "invalid_xml":
                    data = b"not XML"
                elif change == "wrong_root":
                    data = b"<unrelated/>"
                elif change == "dtd":
                    data = '<!DOCTYPE doc [<!ENTITY e "invented">]><doc>&e;</doc>'.encode("utf-16")
            target.writestr(name, data)
        if change == "bomb":
            target.writestr("word/bomb.txt", b"0" * (9 * 1024 * 1024))
        elif change == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                target.writestr("word/document.xml", b"<duplicate/>")
        elif change == "traversal":
            target.writestr("../outside.xml", b"<outside/>")
        elif change == "macro":
            target.writestr("word/vbaProject.bin", b"invented")
    data = output.getvalue()
    if change == "crc":
        # Corrupt a compressed member while preserving ZIP directory metadata.
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entry = archive.infolist()[0]
            offset = entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)
        data = data[:offset] + bytes([data[offset] ^ 255]) + data[offset + 1:]
    assert not admin_feedback._valid_general_attachment("invented.docx", data)


def test_general_attachment_resource_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    from njit_auditor import general_feedback_attachments as validation

    assert not validation.valid_attachment("large.pdf", b"%PDF-" + b"x" * (4 * 1024 * 1024))
    monkeypatch.setattr(validation, "MAX_IMAGE_PIXELS", 100)
    assert not validation.valid_attachment("large.png", _attachment("png"))
    monkeypatch.setattr(validation, "MAX_PDF_PAGES", 0)
    assert not validation.valid_attachment("large.pdf", _attachment("pdf"))
    monkeypatch.setattr(validation, "MAX_ZIP_BYTES", 100)
    assert not validation.valid_attachment("large.docx", _attachment("docx"))


def test_general_accepts_valid_pdf_at_exact_four_mib_limit(
    general_reviewer: tuple[TestClient, Path, str, str],
) -> None:
    client, _, _, csrf = general_reviewer
    limit = 4 * 1024 * 1024
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        stream = pdf.get_new_xref()
        pdf.update_object(stream, "<<>>")
        pdf.xref_set_key(page.xref, "Contents", f"{stream} 0 R")
        size = limit - 1024
        for _ in range(4):
            pdf.update_stream(stream, b" " * size, compress=False)
            content = pdf.tobytes(deflate=False, no_new_id=True)
            if len(content) == limit:
                break
            size += limit - len(content)
    assert len(content) == limit
    assert _general_post(client, csrf, content).status_code == 303
    assert _general_post(client, csrf, content + b" ").status_code == 413


@pytest.mark.parametrize("phase", ["open", "after_insert"])
def test_general_storage_failure_rolls_back_and_retry_succeeds(
    general_reviewer: tuple[TestClient, Path, str, str], monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    client, path, _, csrf = general_reviewer
    original = admin_feedback._connection
    calls = 0

    @contextmanager
    def fail_once():
        nonlocal calls
        calls += 1
        if calls == 2 and phase == "open":
            raise sqlite3.OperationalError("private database path and SQL must not escape")
        with original() as db:
            yield db
            if calls == 2 and phase == "after_insert":
                raise sqlite3.OperationalError("private database path and SQL must not escape")

    content = _attachment("pdf")
    with monkeypatch.context() as patch:
        patch.setattr(admin_feedback, "_connection", fail_once)
        result = _general_post(client, csrf, content)
    assert result.status_code == 503 and "was not saved" in result.text
    assert "notice=saved" not in result.headers.get("location", "")
    assert "private database path" not in result.text
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM general_feedback").fetchone()[0] == 0
    assert _general_post(client, csrf, content).status_code == 303
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT comment,attachment_data FROM general_feedback").fetchall()
        assert rows == [("Invented independent observation", content)]
