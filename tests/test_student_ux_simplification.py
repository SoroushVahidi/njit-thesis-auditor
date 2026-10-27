"""Synthetic-only coverage of concise web copy and upstream download errors."""

from __future__ import annotations

import importlib
import io
import socket
import urllib.error
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from njit_auditor.student_actions import _SHORT_ACTIONS, short_student_action

PDF = Path(__file__).parent / "fixtures" / "web_demo" / "issues_pdf.pdf"


@pytest.fixture()
def web(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Any]:
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "jobs"))
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    monkeypatch.setattr(wa, "list_builtin_samples", lambda: [])
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.mark.parametrize("original,short", _SHORT_ACTIONS.items())
def test_reviewed_actions_preserve_complete_instructions(original: str, short: str) -> None:
    assert short_student_action({"confidence_level": "high"}, original) == short
    assert len(short) < len(original)
    assert not short.endswith("...")


def test_dynamic_measurements_and_conditions_are_not_truncated() -> None:
    action = "Move the footer 12.5 pt upward, unless this is a landscape page."
    assert short_student_action({"confidence_level": "high"}, action) == action
    assert short_student_action({"confidence_level": "low"}, action) == (
        "Check whether to move the footer 12.5 pt upward, unless this is a landscape page."
    )
    qualified = "Verify whether this heading needs title case; preserve acronyms and proper names."
    assert short_student_action({"confidence_level": "low"}, qualified) == qualified


def test_rule_reference_is_background_not_a_primary_correction() -> None:
    action = (
        "For figure captions: use sentence case and end with a period. "
        "List of Figures entries end with a period; their capitalization is checked under R024E...."
    )
    result = short_student_action({}, action)
    assert "R024E" not in result and "..." not in result
    assert "sentence case" in result and "List of Figures entries end with a period" in result


@pytest.mark.parametrize("confidence", ["low", "medium"])
def test_uncertain_action_is_qualified(confidence: str) -> None:
    assert short_student_action({"confidence_level": confidence}, "Center this heading.") == (
        "Check whether to center this heading."
    )


@pytest.mark.parametrize(
    "case,expected,status",
    [
        ("ok", None, 303),
        ("redirect", None, 303),
        ("403", "The source website blocked the request.", 400),
        ("challenge", "The source website requires a security check.", 400),
        ("404", "The PDF wasn't found (HTTP 404).", 400),
        ("503", "The source website is unavailable (HTTP 503).", 400),
        ("redirect_error", "The source website blocked the request.", 400),
        ("html", "instead of a PDF", 400),
        ("invalid", "valid PDF", 400),
        ("timeout", "download timed out", 400),
        ("wrapped_timeout", "download timed out", 400),
        ("unavailable", "Couldn't reach the source website", 400),
        ("oversize", "exceeds the", 400),
        ("private_redirect", "private or internal", 400),
    ],
)
def test_real_downloader_error_processing_and_cleanup(
    web: tuple[TestClient, Any],
    case: str,
    expected: str | None,
    status: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NJIT_AUDITOR_ENABLE_PDF_URL_AUDITING", "1")
    client, wa = web
    real_build = urllib.request.build_opener
    requested: list[str] = []

    class Transport(urllib.request.BaseHandler):
        handler_order = 400

        def https_open(self, req: urllib.request.Request) -> Any:
            requested.append(req.full_url)
            assert req.host == "fixture.example"
            current = req.full_url.rsplit("/", 1)[-1]
            if current == "timeout":
                raise TimeoutError("secret diagnostic text")
            if current == "wrapped_timeout":
                raise urllib.error.URLError(TimeoutError("secret diagnostic text"))
            if current == "unavailable":
                raise urllib.error.URLError("secret diagnostic text")
            headers = Message()
            headers["Content-Type"] = "application/pdf"
            code, body = 200, PDF.read_bytes()
            if current in {"redirect", "redirect_error", "private_redirect"}:
                code, body = 302, b""
                headers["Location"] = {
                    "redirect": "https://fixture.example/ok",
                    "redirect_error": "https://fixture.example/403",
                    "private_redirect": "https://127.0.0.1/secret",
                }[current]
            elif current in {"403", "404", "503", "challenge"}:
                code, body = (403 if current == "challenge" else int(current)), b"error"
                if current == "challenge":
                    headers["cf-mitigated"] = "challenge"
            elif current == "html":
                headers.replace_header("Content-Type", "text/html")
                body = b"<html>not a PDF</html>"
            elif current == "invalid":
                body = b"invalid PDF bytes"
            response = urllib.response.addinfourl(io.BytesIO(body), headers, req.full_url, code)
            response.msg = "synthetic response"
            return response

    def dns(host: str, port: Any, *args: Any, **kwargs: Any) -> Any:
        ip = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, port or 0))]

    with (
        patch("socket.getaddrinfo", side_effect=dns),
        patch("urllib.request.build_opener", side_effect=lambda *h: real_build(Transport(), *h)),
        patch.object(wa, "MAX_UPLOAD_BYTES", 32 if case == "oversize" else 50 * 1024 * 1024),
        patch.object(wa, "_run_audit_task") as task,
    ):
        response = client.post(
            "/audits/url",
            data={"pdf_url": f"https://fixture.example/{case}"},
            follow_redirects=False,
        )
    assert response.status_code == status
    if expected:
        from html import unescape

        assert expected in unescape(response.text)
        assert "secret diagnostic text" not in response.text
        assert "Couldn't download the PDF." in unescape(response.text)
        assert not wa._jobs and not task.called
        assert list(wa.RUNTIME_DIR.iterdir()) == []
        if case == "403":
            assert "security check" not in response.text
        if case == "private_redirect":
            assert len(requested) == 1
    else:
        assert task.call_count == 1 and len(wa._jobs) == 1


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/private.pdf",
        "http://localhost/a.pdf",
        "https:///a.pdf",
        "https://fixture.example:invalid/a.pdf",
    ],
)
def test_validation_keeps_requests_off_network(
    web: tuple[TestClient, Any], url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NJIT_AUDITOR_ENABLE_PDF_URL_AUDITING", "1")
    client, wa = web
    with patch("urllib.request.build_opener") as opener:
        response = client.post("/audits/url", data={"pdf_url": url})
    assert response.status_code == 400 and not opener.called and not wa._jobs
    assert list(wa.RUNTIME_DIR.iterdir()) == []


def test_about_privacy_and_primary_navigation(web: tuple[TestClient, Any]) -> None:
    client, _ = web
    home = client.get("/").text
    assert 'href="/about"' in home and 'href="/about#privacy"' in home
    assert "Processed on this server" in home and "valid result link" in home
    assert "4387" not in home and "Works with direct public PDF links such as" not in home
    about = client.get("/about")
    assert about.status_code == 200
    for content in [
        "How to use it",
        "What the findings mean",
        "Privacy and document retention",
        "Version information",
        "after you upload it",
        "still running",
        "restarts",
    ]:
        assert content in about.text
    assert 'aria-current="page"' in about.text


def test_short_actions_keep_full_correction_and_exports(web: tuple[TestClient, Any]) -> None:
    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.upload_handling import UploadKind

    client, wa = web
    findings = [AuditFinding(
        rule_id="P045", severity=Severity.WARNING, page=1,
        message="Synthetic numbered publication entry.",
        details={"issue_type": "biosketch_publication_entry_numbered", "confidence": "high"},
    )]
    result = UploadedAuditResult(upload_kind=UploadKind.PDF, audit_type="pdf", findings=findings)
    with patch.object(wa, "run_audit_for_uploaded_file", return_value=result):
        response = client.post("/audits", files={"file": ("synthetic.pdf", PDF.read_bytes(),
                                                          "application/pdf")},
                               follow_redirects=False)
    assert response.status_code == 303
    job = next(iter(wa._jobs.values()))
    assert job.state == "complete"
    action = job.findings[0]["student_web_action"]
    original = job.findings[0]["suggested_fix"]
    assert action != original and "References citation format" in action
    body = client.get(response.headers["location"]).text
    from html import unescape
    assert action in unescape(body)
    assert original in unescape(body)
    assert "Full correction:" in body and "Why is this flagged?" in body
    exported = client.get(response.headers["location"] + "/download/json").json()
    assert exported["findings"][0]["rule_id"] == "P045"
    # The web-only wording does not enter the structured detector export.
    assert "student_action" not in str(exported)
    assert "student_web_action" not in str(exported)
    text_report = client.get(response.headers["location"] + "/download/text").text
    assert original in " ".join(text_report.split())
    assert action not in text_report
    assert job.findings[0]["student_action"] == ""
