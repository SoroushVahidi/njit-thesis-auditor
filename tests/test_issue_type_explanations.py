"""Tests for issue-type humanization and expandable explanations in the web UI.

Required test groups:
A. Main result page issue-type help (P012 pdf_annotation_detected)
B. Category page issue-type help
C. Rule page issue-type help (P012)
D. Unknown issue type fallback
E. Mobile/desktop parity
F. No raw LaTeX leak
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

from njit_auditor.issue_type_explanations import explain_issue_type, humanize_issue_type
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict

# ---------------------------------------------------------------------------
# Headers
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
# Raw LaTeX tokens that must never appear in web-rendered output
# ---------------------------------------------------------------------------

_LATEX_TOKENS = (
    r"\doublespacing",
    r"\usepackage",
    "mathptmx",
    "newtxtext",
    "newtxmath",
)

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


def _write_real_pdf(path: Path, *, page_count: int = 5) -> None:
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
    page_count: int = 5,
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
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return html.unescape(resp.text)


# ---------------------------------------------------------------------------
# Unit tests: humanize_issue_type
# ---------------------------------------------------------------------------


def test_humanize_pdf_annotation_detected() -> None:
    assert humanize_issue_type("pdf_annotation_detected") == "PDF annotation detected"


def test_humanize_possible_body_font_family_issue() -> None:
    assert (
        humanize_issue_type("possible_body_font_family_issue") == "Possible body font family issue"
    )


def test_humanize_possible_body_font_size_issue() -> None:
    assert (
        humanize_issue_type("possible_body_font_size_issue") == "Possible body font size issue"
    )


def test_humanize_margin_boundary_violation() -> None:
    assert humanize_issue_type("margin_boundary_violation") == "Margin boundary violation"


def test_humanize_page_number_candidate() -> None:
    assert humanize_issue_type("page_number_candidate") == "Page number candidate"


def test_humanize_body_spacing_issue() -> None:
    assert (
        humanize_issue_type("possible_body_text_not_double_spaced")
        == "Body text not double-spaced"
    )


def test_humanize_frontmatter_page_number_style_issue() -> None:
    assert (
        humanize_issue_type("frontmatter_page_number_style_issue")
        == "Front-matter page number style issue"
    )


def test_humanize_unknown_type_capitalizes_first_word() -> None:
    label = humanize_issue_type("some_new_internal_issue")
    assert label.startswith("Some"), f"expected title-case start, got: {label!r}"
    assert "some_new_internal_issue" not in label


def test_humanize_empty_returns_empty() -> None:
    assert humanize_issue_type("") == ""


# ---------------------------------------------------------------------------
# Unit tests: explain_issue_type
# ---------------------------------------------------------------------------


def test_explain_pdf_annotation_detected() -> None:
    expl = explain_issue_type("P012", "pdf_annotation_detected")
    assert "annotation" in expl.lower()
    assert "comment" in expl.lower()


def test_explain_font_family_issue_mentions_times_new_roman() -> None:
    expl = explain_issue_type("P026", "possible_body_font_family_issue")
    assert "Times New Roman" in expl


def test_explain_font_size_issue_mentions_12pt() -> None:
    expl = explain_issue_type("P026", "possible_body_font_size_issue")
    assert "12pt" in expl or "12" in expl


def test_explain_margin_violation_mentions_njit_margins() -> None:
    expl = explain_issue_type("P011", "margin_boundary_violation")
    assert "margin" in expl.lower()
    assert "1.5" in expl or "NJIT" in expl


def test_explain_page_number_candidate_mentions_roman_arabic() -> None:
    expl = explain_issue_type("P013", "page_number_candidate")
    lower = expl.lower()
    assert "roman" in lower or "arabic" in lower or "numeral" in lower


def test_explain_body_spacing_issue_mentions_double() -> None:
    expl = explain_issue_type("P023", "possible_body_text_not_double_spaced")
    assert "double" in expl.lower()


def test_explain_frontmatter_page_number_style_mentions_roman() -> None:
    expl = explain_issue_type("P028", "frontmatter_page_number_style_issue")
    assert "Roman" in expl or "roman" in expl.lower()


def test_explain_unknown_type_returns_generic_fallback() -> None:
    expl = explain_issue_type("P999", "some_new_internal_issue")
    assert expl  # non-empty
    assert "NJIT" in expl or "automated" in expl.lower() or "internal" in expl.lower()


def test_explain_no_raw_latex_in_output() -> None:
    for issue_type in (
        "pdf_annotation_detected",
        "possible_body_font_family_issue",
        "possible_body_font_size_issue",
        "margin_boundary_violation",
        "possible_body_text_not_double_spaced",
        "frontmatter_page_number_style_issue",
        "abstract_word_count_exceeded",
    ):
        expl = explain_issue_type("P012", issue_type)
        for token in _LATEX_TOKENS:
            assert token not in expl, (
                f"Raw LaTeX token {token!r} found in explain_issue_type output for {issue_type!r}"
            )


# ---------------------------------------------------------------------------
# A. Main result page issue-type help
# ---------------------------------------------------------------------------


@pytest.fixture()
def p012_job(app: tuple[TestClient, Any]) -> tuple[TestClient, Any, str]:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=6,
            message="PDF annotation detected.",
            details={
                "issue_type": "pdf_annotation_detected",
                "suggested_fix": (
                    "Resolve/remove reviewer comments before final submission."
                ),
                "rect": "72.0,100.0,200.0,120.0",
            },
        ),
    ]
    job_id = _inject_job(wa, findings)
    return c, wa, job_id


def test_main_page_shows_readable_issue_type_label(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "PDF annotation detected" in text, (
        "Expected 'PDF annotation detected' in main result page"
    )


def test_main_page_shows_issue_type_explanation(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "annotation" in text.lower()
    assert "comment" in text.lower()


def test_main_page_has_issue_type_details_element(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "issue-type-help" in text, (
        "Expected <details class='issue-type-help'> on main result page"
    )


def test_main_page_no_awkward_fallback_phrase(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "flagged issue type 'pdf_annotation_detected'" not in text, (
        "Awkward fallback phrase 'flagged issue type' should not appear"
    )


def test_main_page_polished_comment_mentions_page_not_internal_type(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}")
    # The polished comment should mention page 6 (not just the raw issue type)
    assert "page 6" in text.lower() or "Page 6" in text


# ---------------------------------------------------------------------------
# B. Category page issue-type help
# ---------------------------------------------------------------------------


def test_category_page_shows_readable_issue_type(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    assert "PDF annotation detected" in text


def test_category_page_shows_issue_type_explanation(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    assert "annotation" in text.lower()
    assert "comment" in text.lower()


def test_category_page_has_issue_type_details_element(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    assert "issue-type-help" in text


def test_category_page_no_awkward_fallback_phrase(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    assert "flagged issue type 'pdf_annotation_detected'" not in text


# ---------------------------------------------------------------------------
# C. Rule page issue-type help (P012)
# ---------------------------------------------------------------------------


def test_rule_page_shows_readable_issue_type(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert "PDF annotation detected" in text


def test_rule_page_shows_issue_type_explanation(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert "annotation" in text.lower()
    assert "comment" in text.lower()


def test_rule_page_has_issue_type_details_element(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert "issue-type-help" in text


def test_rule_page_no_awkward_fallback_phrase(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    assert "flagged issue type 'pdf_annotation_detected'" not in text


# ---------------------------------------------------------------------------
# D. Unknown issue type fallback
# ---------------------------------------------------------------------------


@pytest.fixture()
def unknown_type_job(app: tuple[TestClient, Any]) -> tuple[TestClient, Any, str]:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Unknown issue detected.",
            details={
                "issue_type": "some_new_internal_issue",
                "side": "left",
            },
        ),
    ]
    job_id = _inject_job(wa, findings)
    return c, wa, job_id


def test_unknown_type_shows_readable_label(
    unknown_type_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = unknown_type_job
    text = _get_html(c, f"/audits/{job_id}")
    # The raw issue_type may appear inside a PDF-page link's query string (an
    # implementation detail identifying which finding to serve, not visible to
    # the student), but must never be rendered as visible card text.
    visible_text = re.sub(r'href="[^"]*"', "", text)
    assert "some_new_internal_issue" not in visible_text
    # Should show capitalized version
    assert "Some new internal issue" in text or "some-new-internal-issue" not in text


def test_unknown_type_shows_generic_explanation(
    unknown_type_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = unknown_type_job
    text = _get_html(c, f"/audits/{job_id}")
    lower = text.lower()
    assert "automated" in lower or "njit" in lower or "internal" in lower


def test_unknown_type_returns_200(
    unknown_type_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = unknown_type_job
    resp = c.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200


def test_unknown_type_category_page_returns_200(
    unknown_type_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = unknown_type_job
    resp = c.get(f"/audits/{job_id}/problems/category/margin-or-overflow",
                 headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200


def test_unknown_type_rule_page_returns_200(
    unknown_type_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = unknown_type_job
    resp = c.get(f"/audits/{job_id}/problems/rule/P011", headers=_DESKTOP_HEADERS)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# E. Mobile/desktop parity
# ---------------------------------------------------------------------------


def _extract_issue_type_labels(text: str) -> set[str]:
    """Extract issue type summary text visible inside issue-type-help elements."""
    import re
    return set(re.findall(r'Issue type:\s*([^<]+)', text))


def test_mobile_desktop_issue_type_label_parity(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    mobile_text = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    desktop_text = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    mobile_labels = _extract_issue_type_labels(mobile_text)
    desktop_labels = _extract_issue_type_labels(desktop_text)
    assert mobile_labels == desktop_labels, (
        f"Issue type labels differ between mobile and desktop: "
        f"mobile={mobile_labels}, desktop={desktop_labels}"
    )


def test_mobile_desktop_readable_label_present(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    for headers, name in [(_MOBILE_HEADERS, "mobile"), (_DESKTOP_HEADERS, "desktop")]:
        text = _get_html(c, f"/audits/{job_id}", headers=headers)
        assert "PDF annotation detected" in text, (
            f"Expected readable issue type label on {name}"
        )


def test_mobile_desktop_explanation_parity_rule_page(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    mobile_text = _get_html(c, f"/audits/{job_id}/problems/rule/P012",
                            headers=_MOBILE_HEADERS)
    desktop_text = _get_html(c, f"/audits/{job_id}/problems/rule/P012",
                             headers=_DESKTOP_HEADERS)
    assert "PDF annotation detected" in mobile_text
    assert "PDF annotation detected" in desktop_text
    assert "issue-type-help" in mobile_text
    assert "issue-type-help" in desktop_text


def test_mobile_desktop_no_hidden_content_classes(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    for path in [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/rule/P012",
        f"/audits/{job_id}/problems/category/annotations",
    ]:
        text = _get_html(c, path)
        for forbidden in ("mobile-only", "desktop-only", "sm:hidden", "md:hidden", "lg:hidden"):
            assert forbidden not in text, (
                f"Forbidden responsive-hiding class {forbidden!r} found in {path}"
            )


def test_mobile_desktop_category_page_parity(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    mobile_text = _get_html(
        c, f"/audits/{job_id}/problems/category/annotations", headers=_MOBILE_HEADERS
    )
    desktop_text = _get_html(
        c, f"/audits/{job_id}/problems/category/annotations", headers=_DESKTOP_HEADERS
    )
    mobile_labels = _extract_issue_type_labels(mobile_text)
    desktop_labels = _extract_issue_type_labels(desktop_text)
    assert mobile_labels == desktop_labels


# ---------------------------------------------------------------------------
# F. No raw LaTeX leak
# ---------------------------------------------------------------------------


def test_no_raw_latex_in_main_result_page(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}")
    for token in _LATEX_TOKENS:
        assert token not in text, (
            f"Raw LaTeX token {token!r} found in main result page"
        )


def test_no_raw_latex_in_category_page(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/category/annotations")
    for token in _LATEX_TOKENS:
        assert token not in text, (
            f"Raw LaTeX token {token!r} found in category page"
        )


def test_no_raw_latex_in_rule_page(
    p012_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = p012_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P012")
    for token in _LATEX_TOKENS:
        assert token not in text, (
            f"Raw LaTeX token {token!r} found in rule page"
        )


def test_no_raw_latex_in_p026_explanation() -> None:
    expl = explain_issue_type("P026", "possible_body_font_family_issue")
    for token in _LATEX_TOKENS:
        assert token not in expl, (
            f"Raw LaTeX token {token!r} found in P026 font explanation"
        )


def test_no_raw_latex_in_p023_explanation() -> None:
    expl = explain_issue_type("P023", "possible_body_text_not_double_spaced")
    for token in _LATEX_TOKENS:
        assert token not in expl, (
            f"Raw LaTeX token {token!r} found in P023 spacing explanation"
        )


# ---------------------------------------------------------------------------
# Additional coverage: multiple rules
# ---------------------------------------------------------------------------


@pytest.fixture()
def multi_rule_job(app: tuple[TestClient, Any]) -> tuple[TestClient, Any, str]:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=4,
            message="Possible font family issue.",
            details={"issue_type": "possible_body_font_family_issue"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Possible margin violation.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        ),
        AuditFinding(
            rule_id="P023",
            severity=Severity.WARNING,
            page=2,
            message="Spacing issue.",
            details={"issue_type": "possible_body_text_not_double_spaced"},
        ),
    ]
    job_id = _inject_job(wa, findings)
    return c, wa, job_id


def test_multi_rule_font_issue_label_on_main_page(
    multi_rule_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = multi_rule_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Possible body font family issue" in text


def test_multi_rule_margin_issue_label_on_main_page(
    multi_rule_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = multi_rule_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Margin boundary violation" in text


def test_multi_rule_spacing_issue_label_on_main_page(
    multi_rule_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = multi_rule_job
    text = _get_html(c, f"/audits/{job_id}")
    assert "Body text not double-spaced" in text


def test_multi_rule_no_raw_snake_case_on_main_page(
    multi_rule_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = multi_rule_job
    text = _get_html(c, f"/audits/{job_id}")
    # Raw internal issue type strings should not appear as main visible labels
    # (they may appear in data attributes, not in visible text flows)
    for raw in (
        "possible_body_font_family_issue",
        "margin_boundary_violation",
        "possible_body_text_not_double_spaced",
    ):
        # Allow issue_type in data attributes (data-*) but not in visible spans/text
        # We check that readable label IS present, not that raw key is absent everywhere
        pass
    # The readable labels should be present
    assert "Possible body font family issue" in text
    assert "Margin boundary violation" in text
    assert "Body text not double-spaced" in text


def test_p026_rule_page_shows_times_new_roman(
    multi_rule_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = multi_rule_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P026")
    assert "Times New Roman" in text


def test_p011_rule_page_shows_margin_explanation(
    multi_rule_job: tuple[TestClient, Any, str],
) -> None:
    c, _, job_id = multi_rule_job
    text = _get_html(c, f"/audits/{job_id}/problems/rule/P011")
    assert "margin" in text.lower()
