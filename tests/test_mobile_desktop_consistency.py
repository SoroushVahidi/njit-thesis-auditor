"""Mobile-vs-desktop consistency checks for the public PDF-only web UI.

These tests use FastAPI TestClient rather than a real browser. They verify
server-rendered content parity, link parity, and PDF-route safety for the same
audit job across two representative viewport/header profiles. They do not
assert CSS layout behavior such as stacking vs. columns.
"""

from __future__ import annotations

import html
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient

_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Viewport-Width": "390",
}

_DESKTOP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Viewport-Width": "1440",
}

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _write_real_pdf(path: Path, *, page_count: int = 8) -> None:
    doc = fitz.open()
    for page_index in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text(
            (72, 96),
            f"Synthetic thesis page {page_index + 1} for responsive consistency tests.",
        )
    doc.save(path)
    doc.close()


def _inject_complete_pdf_job(wa: Any) -> tuple[str, Any]:
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf")

    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
                "suggested_fix": "Increase the left margin to the NJIT requirement.",
            },
        ),
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=3,
            message="PDF annotation/comment detected (Text).",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,300.0,260.0",
                "triage_tier": "informational",
                "suggested_fix": "Resolve or remove reviewer comments before submission.",
            },
        ),
        AuditFinding(
            rule_id="P023",
            severity=Severity.WARNING,
            page=4,
            message="Body text spacing may not be double-spaced.",
            details={
                "issue_type": "possible_body_text_not_double_spaced",
                "suggested_fix": "Set body text to double spacing throughout.",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=5,
            message="Body text may not use the expected font.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "suggested_fix": "Set body text to Times New Roman 12pt throughout.",
            },
        ),
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=1,
            message="Front-matter page numbering style may need review.",
            details={
                "issue_type": "frontmatter_page_number_style_issue",
                "suggested_fix": (
                    "Use lowercase Roman numerals for front matter and "
                    "Arabic numerals for body pages."
                ),
            },
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.FAIL,
            page=6,
            message="Page number sequence appears inconsistent.",
            details={
                "issue_type": "page_number_sequence_error",
                "observed": "4",
                "suggested_fix": "Renumber the affected pages so the sequence is continuous.",
            },
        ),
    ]

    metadata = {"input_file_name": "synthetic-thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name="synthetic-thesis.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for finding in view.findings if finding.severity == "WARNING"),
        fail_count=sum(1 for finding in view.findings if finding.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv["rule_id"],
                "severity": fv["severity"],
                "page": fv["page"],
                "issue_type": fv["issue_type"],
                "category": fv["category"],
                "polished_comment": fv["polished_comment"],
                "suggested_fix": fv.get("suggested_fix", ""),
                "triage_tier": fv.get("triage_tier", ""),
                "confidence": fv.get("confidence", ""),
                "source_file": fv.get("source_file", ""),
                "source_line": fv.get("source_line", ""),
                "location_label": fv.get("location_label", ""),
                "bbox": fv.get("bbox"),
                "action_kind": fv.get("action_kind", ""),
                "action_label": fv.get("action_label", ""),
                "has_highlight": fv.get("has_highlight", False),
                "no_highlight_reason": fv.get("no_highlight_reason", ""),
                "detailed_explanation": fv.get("detailed_explanation", ""),
                "issue_type_label": fv.get("issue_type_label", ""),
                "issue_type_explanation": fv.get("issue_type_explanation", ""),
            }
            for fv in view_dict.get("findings", [])
        ],
        grouped_summary=[
            {"rule_id": row.rule_id, "count": row.count, "category": row.category}
            for row in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
        text_layer_quality="good",
    )
    wa._set_job(job)
    return job_id, view


def _inject_pending_job(wa: Any) -> str:
    job_id = secrets.token_urlsafe(16)
    job = wa.JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="pending-thesis.pdf",
        audit_type="pdf",
    )
    wa._set_job(job)
    return job_id


def _inject_failed_job(wa: Any) -> str:
    job_id = secrets.token_urlsafe(16)
    job = wa.JobState(
        job_id=job_id,
        state="failed",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name="failed-thesis.pdf",
        audit_type="pdf",
        error_message="File does not appear to be a valid PDF.",
    )
    wa._set_job(job)
    return job_id


def _get_html(client: TestClient, path: str, headers: dict[str, str]) -> str:
    resp = client.get(path, headers=headers)
    assert resp.status_code == 200
    return html.unescape(resp.text)


def _assert_contains_tokens(text: str, tokens: list[str]) -> None:
    for token in tokens:
        assert token in text, f"Missing token: {token!r}"


def _normalize_pdf_links(text: str) -> set[str]:
    links = set(
        re.findall(
            r'href="(/audits/[^"]*?(?:/highlighted-page\.pdf|/highlighted\.pdf|/pdf)(?:[/?#][^"]*)?)"',
            text,
        )
    )
    normalized: set[str] = set()
    for link in links:
        resolved = html.unescape(link)
        normalized.add(resolved.split("#", 1)[0])
    return normalized


def _assert_pdf_links_inline(client: TestClient, html_text: str) -> None:
    for link in _normalize_pdf_links(html_text):
        resp = client.get(link)
        assert resp.status_code != 500, f"{link} returned 500"
        assert resp.status_code == 200, f"{link} returned {resp.status_code}"
        assert resp.headers["content-type"].startswith("application/pdf")
        disposition = resp.headers.get("content-disposition", "").lower()
        assert "attachment" not in disposition
        assert "inline" in disposition


def test_home_page_content_parity(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    mobile = _get_html(c, "/", _MOBILE_HEADERS)
    desktop = _get_html(c, "/", _DESKTOP_HEADERS)

    common_tokens = [
        "Upload a file",
        "Audit a public PDF URL",
        "Audit a built-in sample PDF",
        "Supported inputs",
        "Privacy-safe processing",
        "processed locally",
        "What you get",
        "Help",
        "Rule Reference",
        "Drop a PDF file here",
        "Use this URL",
        "Start audit",
        "Audit PDF URL",
        "Audit Sample",
    ]
    _assert_contains_tokens(mobile, common_tokens)
    _assert_contains_tokens(desktop, common_tokens)
    assert "TeX" not in mobile
    assert "TeX" not in desktop
    assert ".zip" not in mobile
    assert ".zip" not in desktop


def test_upload_post_redirect_is_consistent(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(wa, "_run_audit_task", lambda job_id: None)
        mobile = c.post(
            "/audits",
            headers=_MOBILE_HEADERS,
            files={"file": ("thesis.pdf", _MINIMAL_PDF, "application/pdf")},
            follow_redirects=False,
        )
        desktop = c.post(
            "/audits",
            headers=_DESKTOP_HEADERS,
            files={"file": ("thesis.pdf", _MINIMAL_PDF, "application/pdf")},
            follow_redirects=False,
        )

    assert mobile.status_code == 303
    assert desktop.status_code == 303
    assert mobile.headers["location"].startswith("/audits/")
    assert desktop.headers["location"].startswith("/audits/")


def test_pending_and_failed_pages_content_parity(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    pending_job_id = _inject_pending_job(wa)
    failed_job_id = _inject_failed_job(wa)

    mobile_pending = _get_html(c, f"/audits/{pending_job_id}", _MOBILE_HEADERS)
    desktop_pending = _get_html(c, f"/audits/{pending_job_id}", _DESKTOP_HEADERS)
    _assert_contains_tokens(
        mobile_pending,
        ["Processing audit", "pending-thesis.pdf", "Started:"],
    )
    _assert_contains_tokens(
        desktop_pending,
        ["Processing audit", "pending-thesis.pdf", "Started:"],
    )

    mobile_failed = _get_html(c, f"/audits/{failed_job_id}", _MOBILE_HEADERS)
    desktop_failed = _get_html(c, f"/audits/{failed_job_id}", _DESKTOP_HEADERS)
    _assert_contains_tokens(
        mobile_failed,
        ["Audit could not complete", "Something went wrong.", "Try another file", "Help"],
    )
    _assert_contains_tokens(
        desktop_failed,
        ["Audit could not complete", "Something went wrong.", "Try another file", "Help"],
    )


def test_result_page_content_parity(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    job_id, view = _inject_complete_pdf_job(wa)

    mobile = _get_html(c, f"/audits/{job_id}", _MOBILE_HEADERS)
    desktop = _get_html(c, f"/audits/{job_id}", _DESKTOP_HEADERS)

    common_tokens = [
        "Audit complete",
        "Problems found",
        "Needs fixing",
        "Worth checking",
        "Pages affected",
        "Rules flagged",
        "Grouped problems",
        "All individual findings",
        "Download JSON",
        "Download Markdown",
        "View original PDF",
        "Privacy note",
        "Audit another file",
    ]
    common_tokens.extend(sorted({finding.rule_id for finding in view.findings}))
    common_tokens.extend(
        sorted(
            {
                wa._humanize_cat(finding.category)
                for finding in view.findings
                if finding.category
            }
        )
    )
    common_tokens.extend(
        sorted(
            {
                finding.issue_type_label or finding.issue_type.replace("_", " ")
                for finding in view.findings
                if finding.issue_type
            }
        )
    )
    common_tokens.extend(
        sorted(
            {
                finding.polished_comment
                for finding in view.findings
                if finding.polished_comment
            }
        )
    )
    common_tokens.extend(
        sorted(
            {
                finding.suggested_fix
                for finding in view.findings
                if finding.suggested_fix
            }
        )
    )

    _assert_contains_tokens(mobile, common_tokens)
    _assert_contains_tokens(desktop, common_tokens)
    assert _normalize_pdf_links(mobile) == _normalize_pdf_links(desktop)


def test_problem_page_content_parity(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    job_id, view = _inject_complete_pdf_job(wa)

    category_mobile = _get_html(
        c,
        f"/audits/{job_id}/problems/category/page-numbering",
        _MOBILE_HEADERS,
    )
    category_desktop = _get_html(
        c,
        f"/audits/{job_id}/problems/category/page-numbering",
        _DESKTOP_HEADERS,
    )
    rule_mobile = _get_html(c, f"/audits/{job_id}/problems/rule/P012", _MOBILE_HEADERS)
    rule_desktop = _get_html(c, f"/audits/{job_id}/problems/rule/P012", _DESKTOP_HEADERS)

    category_tokens = [
        "Problems in this category",
        "Page numbering",
        "Back to all results",
        "Open original PDF page",
        "No exact highlight is available",
        "Page 1",
        "Page 6",
        "Issue type:",
    ]
    rule_tokens = [
        "Examples for this rule",
        "Back to all results",
        "Open highlighted PDF page",
        "Page 3",
        "Issue type:",
        "PDF annotation detected",
    ]
    for comment in {f.polished_comment for f in view.findings if f.category == "page_numbering"}:
        category_tokens.append(comment)
    for comment in {f.polished_comment for f in view.findings if f.rule_id == "P012"}:
        rule_tokens.append(comment)

    _assert_contains_tokens(category_mobile, category_tokens)
    _assert_contains_tokens(category_desktop, category_tokens)
    _assert_contains_tokens(rule_mobile, rule_tokens)
    _assert_contains_tokens(rule_desktop, rule_tokens)
    assert _normalize_pdf_links(category_mobile) == _normalize_pdf_links(category_desktop)
    assert _normalize_pdf_links(rule_mobile) == _normalize_pdf_links(rule_desktop)


def test_pdf_link_safety_parity(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    job_id, _ = _inject_complete_pdf_job(wa)

    page_urls = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P012",
    ]
    for headers in (_MOBILE_HEADERS, _DESKTOP_HEADERS):
        for page_url in page_urls:
            html_text = _get_html(c, page_url, headers)
            _assert_pdf_links_inline(c, html_text)


def test_hidden_content_regression_scan() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    template_sources = [
        (repo_root / "src/njit_auditor/templates/base.html").read_text(encoding="utf-8"),
        (repo_root / "src/njit_auditor/templates/job.html").read_text(encoding="utf-8"),
        (repo_root / "src/njit_auditor/templates/problem_group.html").read_text(encoding="utf-8"),
        (repo_root / "src/njit_auditor/templates/index.html").read_text(encoding="utf-8"),
    ]
    combined = "\n".join(template_sources)

    for forbidden_class in ("mobile-only", "desktop-only", "sm:hidden", "md:hidden", "lg:hidden"):
        assert forbidden_class not in combined

    critical_class_names = [
        "grouped-problem__actions",
        "page-link",
        "dl-links",
        "privacy-note",
        "example-card__actions",
    ]
    for class_name in critical_class_names:
        assert not re.search(
            rf"@media[\s\S]*?\.{re.escape(class_name)}[\s\S]*?display\s*:\s*none",
            combined,
        ), f"responsive media query hides critical class {class_name}"


def test_help_and_rules_pdf_only_wording_parity(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    for path in ("/help", "/rules"):
        mobile = _get_html(c, path, _MOBILE_HEADERS)
        desktop = _get_html(c, path, _DESKTOP_HEADERS)
        assert "TeX / ZIP source" not in mobile
        assert "TeX / ZIP source" not in desktop
        assert ".zip" not in mobile
        assert ".zip" not in desktop
        assert "source audit" not in mobile.lower()
        assert "source audit" not in desktop.lower()
        if path == "/help":
            _assert_contains_tokens(mobile, ["How it works", "How results are organized"])
            _assert_contains_tokens(desktop, ["How it works", "How results are organized"])
        if path == "/rules":
            _assert_contains_tokens(mobile, ["Rule Reference", "Formatting checks", "Search"])
            _assert_contains_tokens(desktop, ["Rule Reference", "Formatting checks", "Search"])
