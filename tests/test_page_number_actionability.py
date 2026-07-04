"""Focused regression tests for page-number actionability in the web UI."""
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
from njit_auditor.pdf_highlight import get_pdf_page_sizes
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict

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


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def app(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _write_real_pdf(path: Path, *, page_count: int = 8) -> None:
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 96), f"Synthetic thesis page {index + 1}.")
    doc.save(path)
    doc.close()


def _inject_job(
    wa: Any,
    findings: list[AuditFinding],
    *,
    file_name: str = "page-number-actionability.pdf",
    page_count: int = 8,
) -> tuple[str, Any]:
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": file_name, "audit_type": "pdf", "job_id": job_id}
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
        file_name=file_name,
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for finding in view.findings if finding.severity == "WARNING"),
        fail_count=sum(1 for finding in view.findings if finding.severity == "FAIL"),
        findings=[
            {
                "rule_id": finding["rule_id"],
                "severity": finding["severity"],
                "page": finding["page"],
                "issue_type": finding["issue_type"],
                "category": finding["category"],
                "polished_comment": finding["polished_comment"],
                "suggested_fix": finding.get("suggested_fix", ""),
                "triage_tier": finding.get("triage_tier", ""),
                "confidence": finding.get("confidence", ""),
                "source_file": finding.get("source_file", ""),
                "source_line": finding.get("source_line", ""),
                "location_label": finding.get("location_label", ""),
                "bbox": finding.get("bbox"),
                "action_kind": finding.get("action_kind", ""),
                "action_label": finding.get("action_label", ""),
                "has_highlight": finding.get("has_highlight", False),
                "no_highlight_reason": finding.get("no_highlight_reason", ""),
                "detailed_explanation": finding.get("detailed_explanation", ""),
                "issue_type_label": finding.get("issue_type_label", ""),
                "issue_type_explanation": finding.get("issue_type_explanation", ""),
            }
            for finding in view_dict.get("findings", [])
        ],
        grouped_summary=[
            {"rule_id": row.rule_id, "count": row.count, "category": row.category}
            for row in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id, view


def _get_html(client: TestClient, path: str, headers: dict[str, str] | None = None) -> str:
    resp = client.get(path, headers=headers or _DESKTOP_HEADERS)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return html.unescape(resp.text)


def _pdf_links(text: str) -> set[str]:
    return extract_audit_pdf_links(text)



def _summary_value(text: str, label: str) -> str:
    pattern = re.compile(
        rf'<div class="summary-card__label">{re.escape(label)}</div>\s*'
        r'<div class="summary-card__value">([^<]+)</div>'
    )
    match = pattern.search(text)
    assert match, f"Could not find summary card {label!r}"
    return match.group(1).strip()


def test_routine_p013_bottom_area_candidate_is_not_a_problem(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=2,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        )
    ]
    job_id, view = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")

    assert view.total_findings == 0
    assert len(view.inventory_findings) == 1
    assert _summary_value(text, "Items to review") == "0"
    assert "Page number candidate" not in text
    assert "Wrong page-number location" not in text
    assert f"/audits/{job_id}/problems/rule/P013" not in text
    assert "/pdf/highlighted" not in text


def test_p013_wrong_location_suspicion_is_shown_with_exact_location(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_right"},
        )
    ]
    job_id, view = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")

    assert view.total_findings == 1
    assert "Wrong page-number location" in text
    assert "appears at top right" in text
    assert "required bottom position" in text
    assert "Page number candidate" not in text


def test_p013_multiple_candidates_are_shown_as_duplicate_or_ambiguous(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=4,
            message="Page number candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "candidate_count_on_page": "2",
            },
        )
    ]
    job_id, view = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")

    assert view.total_findings == 1
    assert "Duplicate or ambiguous page number" in text
    assert "Multiple page-number-like tokens were detected on page 4" in text
    assert "remove or correct duplicates" in text


def test_real_page_number_defects_use_exact_wording(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=5,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
        ),
        AuditFinding(
            rule_id="P022",
            severity=Severity.WARNING,
            page=2,
            message="Visible page number on no-number page.",
            details={
                "issue_type": "visible_page_number_on_no_number_page",
                "page_type": "abstract",
            },
        ),
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=6,
            message="Wrong style.",
            details={
                "issue_type": "arabic_number_on_frontmatter_page",
                "observed_style": "Arabic numerals",
                "expected_style": "lowercase Roman numerals",
            },
        ),
    ]
    job_id, _ = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")

    assert "did not find a clear page number on page 5" in text
    assert "suppressed or hidden" in text
    assert "appears to use Arabic numerals" in text
    assert "expected to use lowercase Roman numerals" in text


def test_page_number_problem_pages_avoid_vague_only_wording(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=5,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
        ),
    ]
    job_id, _ = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}/problems/category/page-numbering")

    for banned in (
        "verify page numbering",
        "manual verification signal",
        "page-number candidate",
        "candidate detected",
        "check placement and style",
    ):
        assert banned not in text.lower()


def test_counts_are_honest_when_only_routine_p013_candidates_exist(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=2,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_right"},
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")

    assert view.total_findings == 0
    assert _summary_value(text, "Items to review") == "0"
    assert "Page numbering" not in text or "/problems/category/page-numbering" not in text


def test_page_numbering_main_category_rule_issue_type_pages_stay_consistent(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        )
    ]
    job_id, _ = _inject_job(wa, findings)

    paths = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P013",
        f"/audits/{job_id}/problems/rule/P013/issue-type/wrong-page-number-location",
    ]
    for path in paths:
        text = _get_html(c, path)
        assert "Wrong page-number location" in text
        assert "appears at top center" in text
        assert "required bottom position" in text


def test_mobile_desktop_parity_for_page_number_actionability(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=5,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
        ),
    ]
    job_id, _ = _inject_job(wa, findings)

    main_mobile = _get_html(c, f"/audits/{job_id}", headers=_MOBILE_HEADERS)
    main_desktop = _get_html(c, f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    assert _summary_value(main_mobile, "Items to review") == _summary_value(
        main_desktop, "Items to review"
    )

    for path in (
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/page-numbering",
    ):
        mobile = _get_html(c, path, headers=_MOBILE_HEADERS)
        desktop = _get_html(c, path, headers=_DESKTOP_HEADERS)
        assert ("Wrong page-number location" in mobile) == (
            "Wrong page-number location" in desktop
        )
        assert ("did not find a clear page number" in mobile) == (
            "did not find a clear page number" in desktop
        )


def test_no_highlight_actions_and_no_500_routes_for_page_number_findings(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=5,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
        ),
    ]
    job_id, _ = _inject_job(wa, findings)
    paths = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/page-numbering",
        f"/audits/{job_id}/problems/rule/P013",
        f"/audits/{job_id}/problems/rule/P019",
        f"/audits/{job_id}/problems/rule/P013/issue-type/wrong-page-number-location",
    ]

    all_links: set[str] = set()
    for path in paths:
        text = _get_html(c, path)
        assert "/pdf/highlighted" not in text
        all_links.update(_pdf_links(text))

    for link in all_links:
        resp = c.get(link, headers=_DESKTOP_HEADERS)
        assert resp.status_code != 500, f"{link} returned 500"


# ---------------------------------------------------------------------------
# 14. Duplicate-card reduction: P013 candidates that restate a P019 defect
# ---------------------------------------------------------------------------


def test_p013_duplicate_candidate_is_folded_into_matching_p019_defect(
    app: tuple[TestClient, Any],
) -> None:
    """P013 and P019 both fire on the same page for the same duplicate-number defect.

    The student should see exactly one top-level problem for it, not two
    indistinguishable cards.
    """
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=4,
            message="Page number candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "candidate_count_on_page": "2",
            },
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=4,
            message="Multiple page numbers.",
            details={"issue_type": "multiple_page_numbers"},
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    text = _get_html(c, f"/audits/{job_id}")

    duplicate_cards = [
        f for f in view.findings if f.issue_type == "duplicate_or_ambiguous_page_number"
    ]
    assert len(duplicate_cards) == 1
    assert duplicate_cards[0].rule_id == "P019"
    assert view.total_findings == 1
    assert _summary_value(text, "Items to review") == "1"

    assert len(view.inventory_findings) == 1
    redundant = view.inventory_findings[0]
    assert redundant.rule_id == "P013"
    assert redundant.page == 4
    assert "already reported above" in redundant.polished_comment


def test_p013_wrong_location_candidate_is_folded_into_matching_p019_defect(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=3,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "top_center"},
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=3,
            message="Inconsistent position.",
            details={"issue_type": "inconsistent_position"},
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    _get_html(c, f"/audits/{job_id}")

    location_cards = [f for f in view.findings if f.issue_type == "wrong_page_number_location"]
    assert len(location_cards) == 1
    assert location_cards[0].rule_id == "P019"
    assert view.total_findings == 1

    assert len(view.inventory_findings) == 1
    assert view.inventory_findings[0].rule_id == "P013"
    assert "already reported above" in view.inventory_findings[0].polished_comment


def test_p013_and_p019_on_different_pages_both_stay_visible(
    app: tuple[TestClient, Any],
) -> None:
    """Suppression only applies on a shared page; unrelated findings stay separate."""
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=4,
            message="Page number candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "candidate_count_on_page": "2",
            },
        ),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=9,
            message="Multiple page numbers.",
            details={"issue_type": "multiple_page_numbers"},
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    _get_html(c, f"/audits/{job_id}")

    duplicate_cards = [
        f for f in view.findings if f.issue_type == "duplicate_or_ambiguous_page_number"
    ]
    assert len(duplicate_cards) == 2
    assert {f.rule_id for f in duplicate_cards} == {"P013", "P019"}
    assert view.total_findings == 2
    assert len(view.inventory_findings) == 0


# ---------------------------------------------------------------------------
# 15. P019/P028 wrong-style overlap: differentiated, not duplicated, wording
# ---------------------------------------------------------------------------


def test_p019_and_p028_wrong_style_overlap_is_clearly_differentiated(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=None,
            message="Mixed numbering style.",
            details={
                "issue_type": "mixed_numbering_style",
                "observed_style": "Arabic and Roman numerals",
                "expected_style": "one consistent page-numbering style per numbering section",
            },
        ),
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=8,
            message="Wrong style.",
            details={
                "issue_type": "arabic_number_on_frontmatter_page",
                "observed_style": "Arabic numerals",
                "expected_style": "lowercase Roman numerals",
                "page_region": "front_matter",
            },
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    _get_html(c, f"/audits/{job_id}")

    style_cards = {
        f.rule_id: f.polished_comment
        for f in view.findings
        if f.issue_type == "wrong_page_numbering_style"
    }
    assert set(style_cards) == {"P019", "P028"}
    assert style_cards["P019"] != style_cards["P028"]
    assert "across the document" in style_cards["P019"]
    assert "broader consistency check" in style_cards["P019"]
    assert "front matter section" in style_cards["P028"]
    assert "expected to use lowercase Roman numerals" in style_cards["P028"]


# ---------------------------------------------------------------------------
# 16. P019/P029/P037 wrong-sequence overlap: differentiated, not duplicated
# ---------------------------------------------------------------------------


def test_p019_and_p029_sequence_overlap_is_clearly_differentiated(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=7,
            message="Roman page-number candidate sequence shows an obvious gap/break.",
            details={
                "issue_type": "sequence_gap",
                "observed_sequence": "viii",
                "expected_sequence": "vii",
            },
        ),
        AuditFinding(
            rule_id="P029",
            severity=Severity.WARNING,
            page=7,
            message="Roman numeral decreased on a front-matter page.",
            details={
                "issue_type": "roman_sequence_decrease",
                "observed_sequence": "viii",
                "expected_sequence": "vii",
                "page_region": "front_matter",
            },
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    _get_html(c, f"/audits/{job_id}")

    sequence_cards = {
        f.rule_id: f.polished_comment
        for f in view.findings
        if f.issue_type == "wrong_page_number_sequence"
    }
    assert set(sequence_cards) == {"P019", "P029"}
    assert sequence_cards["P019"] != sequence_cards["P029"]
    assert "document-wide numbering sequence" in sequence_cards["P019"]
    assert "front-matter sequence" in sequence_cards["P029"]
    assert "Roman numeral page number" in sequence_cards["P029"]


def test_p029_and_p037_sequence_overlap_is_clearly_differentiated(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    findings = [
        AuditFinding(
            rule_id="P029",
            severity=Severity.WARNING,
            page=11,
            message="Roman numeral sequence gap on a front-matter page.",
            details={
                "issue_type": "roman_sequence_gap",
                "observed_sequence": "vi",
                "expected_sequence": "v",
                "page_region": "front_matter",
            },
        ),
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=11,
            message="Section Roman numeral does not match the NJIT template value.",
            details={
                "issue_type": "roman_section_wrong_value",
                "section_key": "dedication",
                "observed_sequence": "vi",
                "expected_sequence": "v",
            },
        ),
    ]
    job_id, view = _inject_job(wa, findings)
    _get_html(c, f"/audits/{job_id}")

    sequence_cards = {
        f.rule_id: f.polished_comment
        for f in view.findings
        if f.issue_type == "wrong_page_number_sequence"
    }
    assert set(sequence_cards) == {"P029", "P037"}
    assert sequence_cards["P029"] != sequence_cards["P037"]
    assert "front-matter sequence" in sequence_cards["P029"]
    assert "NJIT front-matter template" in sequence_cards["P037"]
    assert "fixed template position" in sequence_cards["P037"]
