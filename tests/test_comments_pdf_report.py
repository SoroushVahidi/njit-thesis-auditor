"""Synthetic acceptance and publication tests for the comments-only PDF."""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor

import fitz
import pytest
from fastapi.testclient import TestClient
from test_web_app import _inject_complete_job_with_findings, _p012_annotation_finding_with_bbox

from njit_auditor import desktop_exports, web_app
from njit_auditor.coverage_disclosure import COVERAGE_HEADING
from njit_auditor.incomplete_audit import INCOMPLETE_AUDIT_TITLE
from njit_auditor.offline_app import create_offline_app, prepare_local_storage
from njit_auditor.student_pdf_report import build_comments_pdf_report


def _comment(problem_number: int, page: int | None) -> dict[str, object]:
    return {
        "problem_number": problem_number,
        "page": page,
        "rule_id": "P012",
        "public_rule_reference_id": "P012",
        "issue_type_label": "Annotation issue",
        "polished_comment": "Inspect résumé, Δ ≤ 3, 中文, 😀, and <literal> symbols.",
        "suggested_fix": "Remove reviewer notes before submission.",
        "location_label": "Upper-left area",
        "confidence_label": "High confidence",
        "detailed_explanation": "REVIEWER_DETAIL_CANARY",
    }


def _all_text(pdf: fitz.Document) -> str:
    return "\n".join(page.get_text() for page in pdf)


def test_comments_include_public_advice_and_pdf_and_printed_page_labels(tmp_path):
    output = tmp_path / "comments.pdf"
    build_comments_pdf_report(
        output, [_comment(2, None), _comment(1, 3)], manuscript_page_labels={3: "iv"},
        failed_check_count=1,
    )
    with fitz.open(output) as pdf:
        text = _all_text(pdf)
        assert pdf.metadata["title"] == "NJIT Formatting Comments"
        assert pdf.xref_get_key(pdf.pdf_catalog(), "Lang") == ("string", "en")
        assert pdf.embfile_count() == 0
        assert all(page.first_annot is None for page in pdf)
    assert re.findall(r"Problem #(\d+)", text) == ["1", "2"]
    assert "PDF PAGE 3" in text and "Manuscript page: iv" in text
    assert "DOCUMENT-LEVEL FINDINGS" in text and "High confidence" in text
    assert "résumé, Δ ≤ 3, 中文, 😀, and <literal> symbols." in text
    assert "Remove reviewer notes before submission." in text and "R012" in text
    assert "REVIEWER_DETAIL_CANARY" not in text
    assert COVERAGE_HEADING in text and INCOMPLETE_AUDIT_TITLE in text
    assert text.index("Problem #2") < text.index(COVERAGE_HEADING)


def test_comments_pagination_preserves_all_problems_and_long_text(tmp_path):
    output = tmp_path / "comments.pdf"
    findings = [_comment(number, 10) for number in range(1, 151)]
    findings[1]["polished_comment"] = "長文" * 400 + " LONG_COMMENT_TAIL"
    build_comments_pdf_report(output, findings)
    with fitz.open(output) as pdf:
        text = _all_text(pdf)
        assert pdf.page_count > 4
        assert all(f"Report page {index}" in page.get_text() for index, page in enumerate(pdf, 1))
    assert re.findall(r"Problem #(\d+)", text) == [str(n) for n in range(1, 151)]
    assert "LONG_COMMENT_TAIL" in text


def test_empty_comments_explain_the_automated_check_limit(tmp_path):
    output = tmp_path / "empty.pdf"
    build_comments_pdf_report(output, [])
    with fitz.open(output) as pdf:
        text = " ".join(_all_text(pdf).split())
    assert "No formatting problems were detected by the implemented checks." in text
    assert "does not establish full compliance with NJIT requirements." in text
    assert "Problem #" not in text


@pytest.fixture
def completed_job(tmp_path, monkeypatch):
    runtime = prepare_local_storage(tmp_path)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(web_app, "_jobs", {})
    monkeypatch.setattr(web_app, "_export_leases", {})
    monkeypatch.setattr(web_app, "_after_audit_task", None)
    job_id = _inject_complete_job_with_findings(
        web_app, tmp_path, findings=[_p012_annotation_finding_with_bbox(page=2)],
        file_name="PRIVATE_FILENAME_CANARY.pdf", audit_type="pdf", page_count=3,
    )
    work = runtime / job_id
    with fitz.open(work / "upload.pdf") as pdf:
        pdf[0].insert_text((100, 75), "PRIVATE_MANUSCRIPT_PAGE_CANARY")
        pdf.saveIncr()
    return job_id, work, tmp_path


def test_web_comments_preserve_existing_exports_and_original(completed_job):
    job_id, work, _ = completed_job
    base = f"/audits/{job_id}"
    with TestClient(web_app.app) as client:
        original = (work / "upload.pdf").read_bytes()
        first_complete = client.get(base + "/download/student-report.pdf")
        first_text = client.get(base + "/download/text")
        page = client.get(base).text
        comments = client.get(base + "/download/comments.pdf")
        assert comments.status_code == 200 and first_complete.status_code == 200
        assert "application/pdf" in comments.headers["content-type"]
        assert 'filename="NJIT_Comments.pdf"' in comments.headers["content-disposition"]
        assert f'href="{base}/download/comments.pdf"' in page
        assert f'href="{base}/download/text"' in page
        with fitz.open(stream=comments.content) as pdf:
            comments_text = _all_text(pdf)
            metadata = str(pdf.metadata)
        for canary in ("PRIVATE_FILENAME_CANARY", "PRIVATE_MANUSCRIPT_PAGE_CANARY", job_id):
            assert canary not in comments_text and canary not in metadata
        assert "Problem #1" in comments_text and "PDF PAGE 2" in comments_text
        assert client.get(base + "/download/student-report.pdf").content == first_complete.content
        assert client.get(base + "/download/text").content == first_text.content
        assert (work / "upload.pdf").read_bytes() == original
        assert client.get("/audits/missing/download/comments.pdf").status_code == 404


def test_web_comments_reject_partial_output_and_retry(completed_job, monkeypatch, caplog):
    job_id, work, _ = completed_job
    url = f"/audits/{job_id}/download/comments.pdf"
    original = web_app.build_comments_pdf_report

    def write_invalid(path, *args, **kwargs):
        path.write_bytes(b"%PDF-private-failure-canary")

    monkeypatch.setattr(web_app, "build_comments_pdf_report", write_invalid)
    with TestClient(web_app.app) as client:
        response = client.get(url)
        assert response.status_code == 500
        assert "private-failure-canary" not in response.text + caplog.text
        assert not list(work.glob("comments-*"))
        assert not list(work.glob(".pdf-export-*"))
        monkeypatch.setattr(web_app, "build_comments_pdf_report", original)
        first = client.get(url)
        assert first.status_code == 200
        (cache,) = work.glob("comments-*.pdf")
        cache.write_bytes(b"%PDF-corrupt")
        second = client.get(url)
        assert second.status_code == 200
        with fitz.open(stream=second.content) as pdf:
            assert "Problem #1" in _all_text(pdf)
        assert not list(work.glob(".pdf-export-*"))


def test_simultaneous_web_downloads_share_one_comments_publication(completed_job, monkeypatch):
    job_id, _, _ = completed_job
    url = f"/audits/{job_id}/download/comments.pdf"
    started = threading.Event()
    finish = threading.Event()
    original = web_app.build_comments_pdf_report
    calls = []

    def gated(*args, **kwargs):
        calls.append(1)
        started.set()
        assert finish.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(web_app, "build_comments_pdf_report", gated)
    with ThreadPoolExecutor(max_workers=2) as pool:
        with TestClient(web_app.app) as client:
            first = pool.submit(client.get, url)
            assert started.wait(5)
            second = pool.submit(client.get, url)
            finish.set()
            responses = [first.result(timeout=10), second.result(timeout=10)]
    assert len(calls) == 1
    assert all(result.status_code == 200 for result in responses)
    assert responses[0].content == responses[1].content


def test_desktop_downloads_use_one_supervised_comments_export(completed_job, monkeypatch):
    job_id, work, data = completed_job
    url = f"/audits/{job_id}/download/comments.pdf"
    original = desktop_exports.start_worker
    spawned = []

    def track(*args, **kwargs):
        spawned.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(desktop_exports, "start_worker", track)
    desktop = create_offline_app(port=17391, data_root=data, launch_ticket="test-ticket")
    with TestClient(desktop, base_url="http://127.0.0.1:17391") as client:
        assert client.get(url).status_code != 200
        assert client.get("/_session/start?ticket=test-ticket", follow_redirects=False).is_redirect
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(client.get, (url, url)))
        assert first.status_code == second.status_code == 200
        assert first.content == second.content
        assert "NJIT_Comments.pdf" in first.headers["content-disposition"]
        assert len(spawned) == 1
        with fitz.open(stream=first.content) as pdf:
            text = _all_text(pdf)
            assert "Problem #1" in text
            assert "PRIVATE_MANUSCRIPT_PAGE_CANARY" not in text
    assert not list(work.glob(".export-tmp-*"))
    assert not list(work.glob("**/.desktop-request.json"))
