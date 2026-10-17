"""Synthetic checks for the shared "what was checked" coverage disclosure."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from test_web_app import _inject_complete_job, _inject_complete_job_with_findings, _make_app

from njit_auditor.coverage_disclosure import (
    COVERAGE_AREAS,
    COVERAGE_HEADING,
    COVERAGE_INTRO,
    STATUS_LABELS,
    coverage_markdown_lines,
    coverage_text_lines,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import write_markdown_report
from njit_auditor.student_pdf_report import (
    build_combined_student_pdf_report,
    render_student_report_text,
)

RULES_DIR = Path(__file__).resolve().parents[1] / "src" / "njit_auditor" / "rules"

# Phrases that would overstate what an automated check establishes.
_OVERCLAIM_RE = re.compile(
    r"\b(complies|compliant|compliance|approved|guarantee[sd]?|certif\w*|official)\b",
    re.IGNORECASE,
)


def _all_disclosure_text() -> str:
    parts = [COVERAGE_HEADING, *COVERAGE_INTRO]
    for area in COVERAGE_AREAS:
        parts.extend([area.title, area.checked, area.manual, area.status_label])
    return "\n".join(parts)


def _finding(page: int) -> AuditFinding:
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message="Left margin too narrow.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "left_margin",
            "confidence": "medium",
            "suggested_fix": "Adjust the left margin.",
        },
    )


def _student_finding(number: int, page: int | None) -> dict[str, object]:
    return {
        "problem_number": number,
        "page": page,
        "rule_id": "P012",
        "public_rule_reference_id": "P012",
        "issue_type_label": f"Annotation issue {number}",
        "polished_comment": f"Reviewer annotation {number} detected.",
        "suggested_fix": "Remove reviewer notes before submission.",
    }


# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------


def test_every_area_has_a_status_and_student_guidance() -> None:
    keys = [area.key for area in COVERAGE_AREAS]
    assert len(keys) == len(set(keys))
    for area in COVERAGE_AREAS:
        assert area.status in STATUS_LABELS
        assert area.status != "checked"  # No whole checklist section has a verified pass.
        assert area.title and area.manual
        if area.status == "manual":
            assert not area.checked and not area.rule_ids
        else:
            assert area.checked and area.rule_ids


def test_every_cited_rule_is_implemented_by_a_pdf_rule_module() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in RULES_DIR.glob("pdf_*.py"))
    for area in COVERAGE_AREAS:
        for rule_id in area.rule_ids:
            assert f'"{rule_id}"' in source, (area.key, rule_id)


def test_wording_never_claims_compliance_or_replaces_the_checklist() -> None:
    text = _all_disclosure_text()
    assert not _OVERCLAIM_RE.search(text)
    intro = " ".join(COVERAGE_INTRO)
    assert "does not replace" in intro
    assert "may be wrong" in intro
    assert "does not mean your document meets NJIT requirements" in intro


def test_known_policy_conflict_is_disclosed_not_resolved() -> None:
    by_key = {area.key: area for area in COVERAGE_AREAS}
    lof = by_key["list_of_figures"]
    assert lof.status == "guidance_differs"
    assert lof.status_label == "Partly checked; guidance differs"
    assert "title case" in lof.checked
    assert "sentence case" in lof.manual
    assert "Graduate Studies" in lof.manual


def test_text_and_markdown_renderings_list_every_area() -> None:
    text = "\n".join(coverage_text_lines())
    markdown = "\n".join(coverage_markdown_lines())
    assert markdown.startswith(f"## {COVERAGE_HEADING}")
    for area in COVERAGE_AREAS:
        assert f"{area.title}: {area.status_label}" in text
        assert f"**{area.title}** ({area.status_label})" in markdown


# ---------------------------------------------------------------------------
# Output surfaces
# ---------------------------------------------------------------------------


def test_markdown_report_places_coverage_before_findings(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    write_markdown_report([_finding(2)], {"input_file_name": "t.pdf"}, output)
    text = output.read_text(encoding="utf-8")
    assert text.count(f"## {COVERAGE_HEADING}") == 1
    assert text.index(f"## {COVERAGE_HEADING}") < text.index("## Findings by Rule")
    assert "## Notes" in text


def test_markdown_report_for_tex_audits_omits_pdf_coverage(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    write_markdown_report([], {"input_file_name": "t.tex", "audit_type": "tex"}, output)
    assert COVERAGE_HEADING not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("findings", [[], [_student_finding(1, 2), _student_finding(2, None)]])
def test_student_text_report_includes_coverage(findings: list[dict[str, object]]) -> None:
    text = render_student_report_text(findings, file_name="t.pdf")
    assert text.count(COVERAGE_HEADING.upper()) == 1
    for area in COVERAGE_AREAS:
        assert f"{area.title}: {area.status_label}" in text
    for finding in findings:
        assert f"Problem #{finding['problem_number']} — " in text


def _source(path: Path, pages: int) -> None:
    with fitz.open() as doc:
        for number in range(1, pages + 1):
            doc.new_page().insert_text((80, 100), f"Synthetic page {number}")
        doc.save(path)


def _pdf_report_text(path: Path, thesis_pages: int) -> str:
    with fitz.open(path) as doc:
        text = "\n".join(page.get_text() for page in list(doc)[thesis_pages:])
    return " ".join(text.split())


def test_combined_pdf_report_includes_coverage_and_keeps_problem_numbers(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=3)
    result = build_combined_student_pdf_report(
        source,
        output,
        [_student_finding(1, 1), _student_finding(2, 3)],
        boxes_by_problem={1: [(80, 85, 180, 110)]},
        file_name="t.pdf",
    )
    assert result.total_visible_findings == 2
    assert result.markers_drawn == 1
    text = _pdf_report_text(output, 3)
    assert COVERAGE_HEADING in text
    for area in COVERAGE_AREAS:
        assert f"{area.title} ({area.status_label})." in text
    assert text.index(COVERAGE_HEADING) < text.index("Problem #1") < text.index("Problem #2")


def test_zero_finding_pdf_report_stays_short(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=2)
    result = build_combined_student_pdf_report(
        source, output, [], boxes_by_problem={}, file_name="t.pdf"
    )
    assert result.report_pages <= 2
    text = _pdf_report_text(output, 2)
    assert "No formatting problems were detected by the implemented checks" in text
    assert "does not mean your document meets NJIT requirements" in text


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


def test_results_page_shows_coverage_after_summary(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    html = c.get(f"/audits/{job_id}").text
    assert 'id="section-coverage"' in html
    assert 'href="#section-coverage"' in html
    assert html.index('id="section-summary"') < html.index('id="section-coverage"')
    assert html.index('id="section-coverage"') < html.index('id="section-findings"')
    for area in COVERAGE_AREAS:
        assert f"coverage-item--{area.status}" in html
    assert "<details class=\"collapsible coverage-details\">" in html
    # Existing problem anchors and numbering are untouched.
    assert "Problem 1" in html and "Problem 2" in html


def test_results_page_with_no_findings_still_discloses_coverage(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[], file_name="thesis.pdf", audit_type="pdf"
    )
    html = c.get(f"/audits/{job_id}").text
    assert "No problems found" in html
    assert '<span class="badge badge-muted">No problems found</span>' in html
    assert '<span class="badge badge-pass">No problems found</span>' not in html
    assert 'id="section-coverage"' in html
    assert "does not mean your document meets NJIT requirements" in html


# ---------------------------------------------------------------------------
# Accuracy against detector behavior: each claim is tied to the constant that
# limits it, so changing the detector forces a review of the student wording.
# ---------------------------------------------------------------------------


def _area(key: str) -> Any:
    return {area.key: area for area in COVERAGE_AREAS}[key]


def test_font_is_partly_checked_while_p026_tolerates_size_and_majority() -> None:
    from njit_auditor.rules import pdf_font_compliance as p026

    font = _area("font")
    assert p026.BODY_SIZE_TOLERANCE_PT > 0 and p026._MIN_VIOLATION_FRACTION > 0
    assert font.status == "partial"
    low = p026.EXPECTED_BODY_SIZE_PT - p026.BODY_SIZE_TOLERANCE_PT
    high = p026.EXPECTED_BODY_SIZE_PT + p026.BODY_SIZE_TOLERANCE_PT
    assert f"{low:g} to {high:g} pt" in font.checked
    assert "exactly 12 pt" in font.manual
    assert "References" in font.manual


def test_approval_page_does_not_claim_retired_signature_block_check() -> None:
    from njit_auditor.rules import pdf_approval_page_committee_blocks as p068

    approval = _area("approval_page")
    assert p068._SIGNATURE_BLOCKS_SPARSE_REPORTING_ENABLED is False
    assert "signature" not in approval.checked.lower()
    assert "Signature and date lines" in approval.manual


def test_title_consistency_discloses_material_mismatch_threshold() -> None:
    from njit_auditor.rules import pdf_title_consistency as p033

    title_page = _area("title_page")
    assert p033._MATERIAL_MISMATCH_SIMILARITY < 1.0
    assert "Clear differences" in title_page.checked
    assert "small differences may not be flagged" in title_page.manual


def test_heading_case_claims_are_limited_to_numbered_headings() -> None:
    headings = _area("headings")
    assert "numbered level-3" in headings.checked
    assert "unnumbered" in headings.manual


def test_intro_discloses_pages_without_selectable_text() -> None:
    intro = " ".join(COVERAGE_INTRO)
    assert "without selectable text" in intro
    assert "cannot be checked" in intro


def test_no_area_claims_full_coverage() -> None:
    # Every implemented detector is heuristic; "Checked" without qualification
    # would tell students an item needs no manual review.
    assert all(area.status != "checked" for area in COVERAGE_AREAS)


def test_toc_list_spacing_claims_match_p032_and_disabled_r036() -> None:
    from njit_auditor.rules import pdf_toc_list_wrapped_spacing as p032
    from njit_auditor.rules import r036_production_page_relative_spacing as r036

    toc, lot, lof = _area("table_of_contents"), _area("list_of_tables"), _area("list_of_figures")
    # P032 only reports a wrapped-title gap well above single spacing, so the
    # disclosure must not claim that "single-spaced wrapped titles" are checked.
    assert p032.WRAPPED_GAP_RATIO_THRESHOLD > 1.0
    for area in (toc, lot):
        assert "single-spaced wrapped titles" not in area.checked
        assert "large gap" in area.checked
    # R036 (spacing between entries) has no reporting path while its gate is off.
    assert r036.PRODUCTION_REPORTING_GATE == "suppression_abstention_only"
    for area in (toc, lot):
        assert "Double spacing between entries" in area.manual
    assert "double-spaced" in lof.manual
