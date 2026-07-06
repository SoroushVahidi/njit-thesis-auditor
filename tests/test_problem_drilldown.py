"""Regression tests for problem drill-down pages and summary navigation.

Required test groups:
A. Summary by category exists on result page
B. Category page shows all instances for that category
C. Rule page shows all instances for that rule
D. Issue-type drill-down
E. Summary count equals drill-down count
F. Mobile/desktop parity
G. PDF link safety (no 500s)
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
from pdf_link_helpers import extract_audit_pdf_links

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict

# ---------------------------------------------------------------------------
# Viewport profiles
# ---------------------------------------------------------------------------

_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def app(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _write_real_pdf(path: Path, *, page_count: int = 10) -> None:
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Synthetic thesis page {i + 1}.")
    doc.save(path)
    doc.close()


def _inject_job(
    wa: Any,
    findings: list[AuditFinding],
    *,
    file_name: str = "synthetic-thesis.pdf",
    page_count: int = 10,
) -> str:
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": file_name, "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name=file_name,
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=sum(1 for f in view.findings if f.severity == "WARNING"),
        fail_count=sum(1 for f in view.findings if f.severity == "FAIL"),
        findings=[
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "page": f.page,
                "issue_type": f.issue_type,
                "category": f.category,
                "polished_comment": f.polished_comment,
                "suggested_fix": f.suggested_fix,
                "triage_tier": f.triage_tier,
                "confidence": f.confidence,
                "confidence_level": f.confidence_level,
                "confidence_label": f.confidence_label,
                "confidence_css_class": f.confidence_css_class,
                "source_file": f.source_file,
                "source_line": f.source_line,
                "location_label": f.location_label,
                "bbox": list(f.bbox) if f.bbox else None,
                "action_kind": f.action_kind,
                "action_label": f.action_label,
                "has_highlight": f.has_highlight,
                "no_highlight_reason": f.no_highlight_reason,
                "detailed_explanation": f.detailed_explanation,
                "issue_type_label": f.issue_type_label,
                "issue_type_explanation": f.issue_type_explanation,
            }
            for f in view.findings
        ],
        grouped_summary=[
            {"rule_id": r.rule_id, "count": r.count, "category": r.category}
            for r in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id


def _get_html(client: TestClient, path: str, headers: dict[str, str] | None = None) -> str:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    assert resp.status_code == 200, f"GET {path} returned {resp.status_code}"
    return html.unescape(resp.text)


def _pdf_links(text: str) -> set[str]:
    return extract_audit_pdf_links(text)



# ---------------------------------------------------------------------------
# Synthetic findings for all test groups
# ---------------------------------------------------------------------------
#
# Indentation: P015 — 5 findings (page_numbering category maps from P013 which is
# page_numbering; for P015 let's use indentation category)
# Font formatting: P026 — 3 findings
# Annotations: P012 — 2 findings
# Page numbering: P013 — 4 findings
#
# Note: P015 maps to "indentation" category.


def _make_drilldown_findings() -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    # P015 indentation — 5 findings
    for pg in [2, 3, 4, 5, 6]:
        findings.append(
            AuditFinding(
                rule_id="P015",
                severity=Severity.WARNING,
                page=pg,
                message="Indentation issue detected.",
                details={"issue_type": "indentation_issue"},
            )
        )
    # P026 font formatting — 3 findings
    for pg in [1, 4, 7]:
        findings.append(
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=pg,
                message="Possible font family issue.",
                details={"issue_type": "possible_body_font_family_issue"},
            )
        )
    # P012 annotations — 2 findings
    for pg in [3, 8]:
        findings.append(
            AuditFinding(
                rule_id="P012",
                severity=Severity.WARNING,
                page=pg,
                message="PDF annotation detected.",
                details={
                    "issue_type": "pdf_annotation_detected",
                    "rect": "72.0,100.0,200.0,120.0",
                },
            )
        )
    # P013 page numbering — 4 findings
    for pg in [1, 2, 3, 5]:
        findings.append(
            AuditFinding(
                rule_id="P013",
                severity=Severity.WARNING,
                page=pg,
                message="Page number candidate detected.",
                details={
                    "issue_type": "page_number_candidate",
                    "position_type": "top_center",
                },
            )
        )
    return findings


@pytest.fixture()
def drilldown_job(app: tuple[TestClient, Any]) -> tuple[TestClient, Any, str]:
    c, wa = app
    findings = _make_drilldown_findings()
    job_id = _inject_job(wa, findings)
    return c, wa, job_id


# ---------------------------------------------------------------------------
# A. Summary by category exists on result page
# ---------------------------------------------------------------------------


def test_result_page_has_no_duplicate_category_summary(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    """Neither the old standalone "Summary by problem type" table nor the
    later "Most common issues" root-cause cards should render — "Findings by
    topic" is now the single category overview, so category information must
    still surface there without a second, duplicate summary alongside it."""
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Findings by topic" in text
    assert "Summary by problem type" not in text
    assert "Most common issues" not in text


def test_result_page_shows_font_format_category(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Font formatting" in text


def test_result_page_shows_annotations_category(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Annotations" in text


def test_result_page_shows_page_numbering_category(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Page numbering" in text


def test_result_page_category_links_present(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert f"/audits/{job_id}/problems/category/" in text


def test_result_page_review_action_present_in_category_rows(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    """Findings by topic rows use a clear, non-repetitive "Review all" action
    label instead of a "View all" button repeated in every summary row."""
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Review all" in text


def test_result_page_category_counts_nonzero(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, wa, job_id = drilldown_job
    job = wa._get_job(job_id)
    report_view = job.report_view or {}
    counts = report_view.get("counts_by_category", {}) or {}
    assert sum(counts.values()) > 0


def test_result_page_rule_summary_has_view_all(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    # Rule summary table should have View all buttons
    assert f"/audits/{job_id}/problems/rule/" in text


def test_result_page_rule_category_names_are_links(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    # The category column in summary-by-rule should link to category pages
    assert f"/audits/{job_id}/problems/category/" in text


# ---------------------------------------------------------------------------
# B. Category page shows all instances
# ---------------------------------------------------------------------------


def test_font_category_page_returns_200(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    resp = c.get(f"/audits/{job_id}/problems/category/font-format",
                 headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200


def test_font_category_page_title(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/font-format")
    # All 3 P026 findings share one issue type, so the page uses a precise,
    # issue-specific title instead of the broad "Font formatting" category
    # label — it still mentions "font" via that issue-specific title.
    assert "font" in text.lower()


def test_font_category_page_shows_p026_findings(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/font-format")
    assert "P026" in text


def test_font_category_page_shows_3_examples(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/font-format")
    # 3 font findings — check count in page
    assert "3 example" in text


def test_font_category_page_has_no_pdf_link_without_highlight(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/font-format")
    assert "/pdf/highlighted" not in text
    # "original_page" resolves through the same true single-page endpoint as
    # "highlight" rather than a #page=N fragment into the full PDF.
    assert f"/audits/{job_id}/highlighted-page.pdf?page=" in text
    assert f"/audits/{job_id}/pdf#page=" not in text
    assert "Open original PDF page" in text
    assert "No exact highlight is available" in text


def test_annotations_category_page_does_not_show_p026(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    # Should show P012, not P026
    assert "P012" in text
    assert "P026" not in text or text.count("P026") == 0


def test_page_numbering_category_page_returns_200(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    resp = c.get(f"/audits/{job_id}/problems/category/page-numbering",
                 headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200


def test_page_numbering_category_shows_4_examples(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/page-numbering")
    assert "4 example" in text


# ---------------------------------------------------------------------------
# C. Rule page shows all instances
# ---------------------------------------------------------------------------


def test_p013_rule_page_returns_200(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    resp = c.get(f"/audits/{job_id}/problems/rule/P013", headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200


def test_p013_rule_page_shows_4_examples(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    assert "4 example" in text


def test_p013_rule_page_has_no_pdf_link_without_highlight(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    assert "/pdf/highlighted" not in text
    # "original_page" resolves through the same true single-page endpoint as
    # "highlight" rather than a #page=N fragment into the full PDF.
    assert f"/audits/{job_id}/highlighted-page.pdf?page=" in text
    assert f"/audits/{job_id}/pdf#page=" not in text
    assert "Open original PDF page" in text
    assert "Page 1" in text or "Page 2" in text or "Page 3" in text or "Page 5" in text


def test_p026_rule_page_shows_3_examples(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert "3 example" in text


def test_p012_rule_page_shows_2_examples(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert "2 example" in text


def test_p026_rule_page_does_not_show_p013_content(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    # P026 page should not contain P013 findings
    assert "page_number_candidate" not in text
    assert "Page number candidate" not in text


# ---------------------------------------------------------------------------
# D. Issue-type drill-down
# ---------------------------------------------------------------------------


def test_issue_type_page_returns_200(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    resp = c.get(
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
        headers=_DESKTOP_HEADERS,
    )
    assert resp.status_code == 200


def test_issue_type_page_title_contains_readable_label(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(
        c,
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    )
    assert "Possible body font family issue" in text or "font" in text.lower()


def test_issue_type_page_shows_3_examples(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(
        c,
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    )
    assert "3 example" in text


def test_issue_type_page_does_not_show_unrelated_findings(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(
        c,
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    )
    assert "pdf_annotation_detected" not in text
    assert "page_number_candidate" not in text


def test_issue_type_page_p012_annotations(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    resp = c.get(
        f"/audits/{job_id}/problems/rule/P012/issue-type/pdf-annotation-detected",
        headers=_DESKTOP_HEADERS,
    )
    assert resp.status_code == 200
    text = html.unescape(resp.text)
    assert "2 example" in text


def test_issue_type_page_missing_returns_404(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    resp = c.get(
        f"/audits/{job_id}/problems/rule/P026/issue-type/no-such-issue",
        headers=_DESKTOP_HEADERS,
    )
    assert resp.status_code == 400 or resp.status_code == 404


def test_issue_type_link_appears_in_main_page(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "/issue-type/" in text


def test_issue_type_link_appears_in_rule_page(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert "/issue-type/" in text


def test_issue_type_link_appears_in_category_page(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/font-format")
    assert "/issue-type/" in text


# ---------------------------------------------------------------------------
# E. Summary count equals drill-down count
# ---------------------------------------------------------------------------


def test_p013_rule_summary_count_matches_drilldown(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, wa, job_id = drilldown_job
    job = wa._get_job(job_id)
    report_view = job.report_view or {}
    counts_by_rule = report_view.get("counts_by_rule", {}) or {}
    expected_count = int(counts_by_rule.get("P013", 0))
    assert expected_count == 4
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P013")
    assert f"{expected_count} example" in text


def test_p026_rule_summary_count_matches_drilldown(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, wa, job_id = drilldown_job
    job = wa._get_job(job_id)
    report_view = job.report_view or {}
    counts_by_rule = report_view.get("counts_by_rule", {}) or {}
    expected_count = int(counts_by_rule.get("P026", 0))
    assert expected_count == 3
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert f"{expected_count} example" in text


def test_p012_rule_summary_count_matches_drilldown(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, wa, job_id = drilldown_job
    job = wa._get_job(job_id)
    report_view = job.report_view or {}
    counts_by_rule = report_view.get("counts_by_rule", {}) or {}
    expected_count = int(counts_by_rule.get("P012", 0))
    assert expected_count == 2
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert f"{expected_count} example" in text


def test_category_summary_count_matches_drilldown(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, wa, job_id = drilldown_job
    job = wa._get_job(job_id)
    report_view = job.report_view or {}
    counts = report_view.get("counts_by_category", {}) or {}
    # page_numbering category: 4 P013 findings
    expected = int(counts.get("page_numbering", 0))
    assert expected == 4
    text = _get_html(c, f"/audits/{job_id}/problems/category/page-numbering")
    assert f"{expected} example" in text


def test_total_finding_count_equals_sum_of_category_counts(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    _, wa, job_id = drilldown_job
    job = wa._get_job(job_id)
    report_view = job.report_view or {}
    counts = report_view.get("counts_by_category", {}) or {}
    total = sum(counts.values())
    assert total == job.finding_count


# ---------------------------------------------------------------------------
# F. Mobile/desktop parity
# ---------------------------------------------------------------------------


def test_mobile_desktop_category_summary_label_parity(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    mobile_text = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop_text = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    for label in ("Font formatting", "Annotations", "Page numbering"):
        assert label in mobile_text, f"'{label}' missing from mobile result page"
        assert label in desktop_text, f"'{label}' missing from desktop result page"


def test_mobile_desktop_rule_summary_parity(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    mobile_text = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop_text = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    for rule_id in ("P013", "P026", "P012"):
        assert rule_id in mobile_text, f"{rule_id} missing from mobile result page"
        assert rule_id in desktop_text, f"{rule_id} missing from desktop result page"


def test_mobile_desktop_category_drilldown_links_parity(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    mobile_text = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop_text = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    for link_fragment in (
        f"/audits/{job_id}/problems/category/",
        f"/audits/{job_id}/problems/rule/",
    ):
        assert link_fragment in mobile_text, f"{link_fragment!r} missing from mobile"
        assert link_fragment in desktop_text, f"{link_fragment!r} missing from desktop"


def test_mobile_desktop_category_page_parity(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    mobile_text = _get_html(
        c, f"/audits/{job_id}/problems/category/font-format", headers=_MOBILE_HEADERS
    )
    desktop_text = _get_html(
        c, f"/audits/{job_id}/problems/category/font-format", headers=_DESKTOP_HEADERS
    )
    assert "3 example" in mobile_text
    assert "3 example" in desktop_text
    assert "P026" in mobile_text
    assert "P026" in desktop_text


def test_mobile_desktop_rule_page_parity(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    mobile_text = _get_html(
        c, f"/audits/{job_id}/problems/rule/P013", headers=_MOBILE_HEADERS
    )
    desktop_text = _get_html(
        c, f"/audits/{job_id}/problems/rule/P013", headers=_DESKTOP_HEADERS
    )
    assert "4 example" in mobile_text
    assert "4 example" in desktop_text


def test_mobile_desktop_issue_type_page_parity(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    path = f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue"
    mobile_text = _get_html(c, path, headers=_MOBILE_HEADERS)
    desktop_text = _get_html(c, path, headers=_DESKTOP_HEADERS)
    assert "3 example" in mobile_text
    assert "3 example" in desktop_text


def test_no_hidden_content_classes_on_result_page(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    text = _get_html(c, f"/audits/{job_id}")
    for cls in ("mobile-only", "desktop-only", "sm:hidden", "md:hidden", "lg:hidden"):
        assert cls not in text, f"Responsive-hiding class {cls!r} found in result page"


# ---------------------------------------------------------------------------
# G. PDF link safety (no 500s)
# ---------------------------------------------------------------------------


def _collect_pdf_links(client: TestClient, job_id: str) -> set[str]:
    paths = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/category/annotations",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P013",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P012",
        (
            f"/audits/{job_id}/problems/rule/P026"
            "/issue-type/possible-body-font-family-issue"
        ),
    ]
    pdf_links: set[str] = set()
    for path in paths:
        resp = client.get(path, headers=_DESKTOP_HEADERS)
        if resp.status_code != 200:
            continue
        pdf_links.update(_pdf_links(html.unescape(resp.text)))
    return pdf_links


def test_all_pdf_links_return_non_500(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    pdf_links = _collect_pdf_links(c, job_id)
    assert pdf_links, "No PDF links found to test"
    for link in pdf_links:
        resp = c.get(link, headers=_DESKTOP_HEADERS)
        assert resp.status_code != 500, (
            f"PDF link {link!r} returned 500"
        )


def test_all_drilldown_routes_return_non_500(
    drilldown_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = drilldown_job
    routes = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/category/annotations",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P013",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P012",
        (
            f"/audits/{job_id}/problems/rule/P026"
            "/issue-type/possible-body-font-family-issue"
        ),
        (
            f"/audits/{job_id}/problems/rule/P012"
            "/issue-type/pdf-annotation-detected"
        ),
        (
            f"/audits/{job_id}/problems/rule/P013"
            "/issue-type/wrong-page-number-location"
        ),
    ]
    for path in routes:
        resp = c.get(path, headers=_DESKTOP_HEADERS)
        assert resp.status_code != 500, f"Route {path!r} returned 500"


# ---------------------------------------------------------------------------
# H. Confidence badge display guarantee (student-facing problem cards)
# ---------------------------------------------------------------------------
#
# Regression coverage for a bug where "All examples in this category" / rule /
# issue-type drill-down pages (problem_group.html) rendered example cards with
# no confidence badge at all -- _problem_group_examples() built each example
# dict without confidence_level/confidence_label/confidence_css_class, so the
# confidence_badge() macro never received real data for those pages.
#
# Confidence-sorting and page-order-sorting regression coverage for the main
# job page already exists in test_web_app.py
# (test_sort_query_param_page_order_orders_by_earliest_page,
# test_sort_query_param_confidence_desc_orders_high_confidence_first,
# test_sort_query_param_confidence_asc_orders_low_confidence_first) and none
# of that sorting logic is touched by this template-only fix, so it isn't
# duplicated here -- the full suite passing is the regression guard for it.


def _make_confidence_badge_findings() -> list[AuditFinding]:
    """Four P026 font-formatting findings sharing one issue type, with
    high/medium/low/missing confidence respectively. Because they share a
    rule_id and issue_type, the main job page groups them into a single card
    with mixed confidence_levels (proving mixed collapses to Low there), while
    every drill-down view renders them as four separate example cards, each
    with its own real confidence (proving per-example granularity there)."""
    findings: list[AuditFinding] = []
    for pg, confidence in [(1, "high"), (2, "medium"), (3, "low"), (4, "")]:
        details: dict[str, str] = {"issue_type": "possible_body_font_family_issue"}
        if confidence:
            details["confidence"] = confidence
        findings.append(
            AuditFinding(
                rule_id="P026",
                severity=Severity.WARNING,
                page=pg,
                message="Possible font family issue.",
                details=details,
            )
        )
    return findings


@pytest.fixture()
def confidence_badge_job(app: tuple[TestClient, Any]) -> tuple[TestClient, Any, str]:
    c, wa = app
    findings = _make_confidence_badge_findings()
    job_id = _inject_job(wa, findings)
    return c, wa, job_id


def _extract_example_cards(text: str) -> list[str]:
    return re.findall(
        r'<article[^>]*class="card example-card"[^>]*>(.*?)</article>', text, re.DOTALL
    )


def test_main_job_page_each_problem_card_has_exactly_one_confidence_badge(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = confidence_badge_job
    text = _get_html(c, f"/audits/{job_id}")
    summaries = re.findall(
        r'<div class="grouped-problem__summary">(.*?)</div>', text, re.DOTALL
    )
    assert summaries, "expected at least one grouped-problem card on the job page"
    for summary in summaries:
        assert summary.count('class="confidence-badge') == 1, summary


def test_main_job_page_mixed_confidence_group_shows_low_not_mixed(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    """The P026 group has high/medium/low/missing confidence occurrences --
    it must show as a single Low-confidence card, never "Mixed confidence" or
    "Needs review", even though the raw occurrence table nested underneath
    (a separate, already-covered surface) does show each real value."""
    c, _, job_id = confidence_badge_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Mixed confidence" not in text
    assert "Needs review" not in text
    summary = re.search(
        r'<div class="grouped-problem__summary">(.*?)</div>', text, re.DOTALL
    )
    assert summary is not None
    assert "Low confidence" in summary.group(1)


def test_category_page_each_example_card_has_exactly_one_confidence_badge(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = confidence_badge_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/font-format")
    cards = _extract_example_cards(text)
    assert len(cards) == 4, f"expected 4 example cards, found {len(cards)}"
    for card in cards:
        assert card.count('class="confidence-badge') == 1, card


def test_rule_page_each_example_card_has_exactly_one_confidence_badge(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = confidence_badge_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    cards = _extract_example_cards(text)
    assert len(cards) == 4, f"expected 4 example cards, found {len(cards)}"
    for card in cards:
        assert card.count('class="confidence-badge') == 1, card


def test_issue_type_page_each_example_card_has_exactly_one_confidence_badge(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = confidence_badge_job
    path = f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue"
    text = _get_html(c, path)
    cards = _extract_example_cards(text)
    assert len(cards) == 4, f"expected 4 example cards, found {len(cards)}"
    for card in cards:
        assert card.count('class="confidence-badge') == 1, card


def test_drilldown_pages_show_per_example_confidence_not_group_mixed(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    """Unlike the main job page's single mixed-confidence group card, each
    drill-down example card shows its own real confidence: High once, Medium
    once, and Low twice (one explicit low, one from the missing-confidence
    finding)."""
    c, _, job_id = confidence_badge_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    cards = _extract_example_cards(text)
    assert len(cards) == 4
    label_counts = {"High confidence": 0, "Medium confidence": 0, "Low confidence": 0}
    for card in cards:
        matched = [label for label in label_counts if label in card]
        assert len(matched) == 1, f"expected exactly one confidence label, found {matched}"
        label_counts[matched[0]] += 1
    assert label_counts == {"High confidence": 1, "Medium confidence": 1, "Low confidence": 2}


def test_drilldown_pages_never_show_needs_review_or_mixed_confidence(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = confidence_badge_job
    for path in (
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    ):
        text = _get_html(c, path)
        assert "Needs review" not in text, path
        assert "Mixed confidence" not in text, path


def test_drilldown_pages_confidence_badges_use_only_three_public_values(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = confidence_badge_job
    for path in (
        f"/audits/{job_id}/problems/category/font-format",
        f"/audits/{job_id}/problems/rule/P026",
        f"/audits/{job_id}/problems/rule/P026/issue-type/possible-body-font-family-issue",
    ):
        text = _get_html(c, path)
        badge_classes = set(re.findall(r"confidence-badge--(\S+?)[\"' ]", text))
        assert badge_classes, f"expected at least one confidence badge on {path}"
        assert badge_classes <= {"high", "medium", "low"}, (path, badge_classes)


def test_drilldown_page_anchors_and_problem_links_still_render(
    confidence_badge_job: tuple[TestClient, Any, str],
) -> None:
    """Adding the confidence badge to the example-card header must not
    disturb the pre-existing anchor ids, "back to results" link, or rule
    reference link on the same drill-down page."""
    c, _, job_id = confidence_badge_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert re.search(r'<article id="[^"]+"', text), "expected example cards to have anchor ids"
    assert "Back to all results" in text
    assert "P026" in text
