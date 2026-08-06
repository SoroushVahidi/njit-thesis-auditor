from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_text import write_text_report


def _metadata(**overrides: str) -> dict[str, str]:
    base = {
        "input_file_name": "thesis.pdf",
        "audit_type": "pdf",
        "generated_at": "2026-08-06T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _toc_finding(page: int, index: int, prev: str, nxt: str) -> AuditFinding:
    return AuditFinding(
        rule_id="P036",
        severity=Severity.WARNING,
        page=page,
        message="TOC spacing too tight.",
        details={
            "issue_type": "toc_inter_entry_spacing_too_tight",
            "section_type": "table_of_contents",
            "previous_entry_preview": prev,
            "next_entry_preview": nxt,
            "entry_pair_index": str(index),
            "confidence": "medium",
        },
    )


def _margin_finding(page: int, *, absolute_path: str | None = None) -> AuditFinding:
    details = {
        "issue_type": "margin_boundary_violation",
        "side": "left_margin",
        "worst_overflow_pt": "9.0",
        "confidence": "medium",
    }
    if absolute_path is not None:
        details["source_q_rule_id"] = "Q123"
        details["source_file"] = absolute_path
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message="Left margin too narrow.",
        details=details,
    )


def _lof_punctuation_finding(page: int, entry_index: int, page_entry_index: int) -> AuditFinding:
    return AuditFinding(
        rule_id="P040",
        severity=Severity.WARNING,
        page=page,
        message="List of Figures entry missing terminal punctuation.",
        details={
            "issue_type": "lof_entry_missing_terminal_punctuation",
            "page_type": "list_of_figures",
            "entry_index": str(entry_index),
            "page_entry_index": str(page_entry_index),
            "confidence": "high",
        },
    )


def _page_number_candidate(page: int, *, label: str = "") -> AuditFinding:
    details = {
        "issue_type": "page_number_candidate",
        "position_type": "bottom_center",
        "number_style": "roman",
        "confidence": "medium",
    }
    if label:
        details["document_page_label"] = label
    return AuditFinding(
        rule_id="P013",
        severity=Severity.WARNING,
        page=page,
        message="Detected page-number candidate.",
        details=details,
    )


def _write(findings: list[AuditFinding], tmp_path: Path, **meta: str) -> str:
    output_path = tmp_path / "report.txt"
    write_text_report(findings, _metadata(**meta), output_path)
    return output_path.read_text(encoding="utf-8")


def test_pages_render_in_ascending_pdf_page_order_regardless_of_input_order(
    tmp_path: Path,
) -> None:
    findings = [
        _margin_finding(30),
        _margin_finding(5),
        _margin_finding(17),
    ]
    text = _write(findings, tmp_path)
    positions = [text.index(f"PDF PAGE {p}") for p in (5, 17, 30)]
    assert positions == sorted(positions)


def test_multiple_findings_on_same_page_are_grouped_under_one_heading(
    tmp_path: Path,
) -> None:
    findings = [
        _margin_finding(8),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=8,
            message="Missing approval page heading.",
            details={
                "issue_type": "required_heading_missing",
                "expected_heading": "APPROVAL PAGE",
                "confidence": "high",
            },
        ),
    ]
    text = _write(findings, tmp_path)
    assert text.count("PDF PAGE 8") == 1
    heading_index = text.index("PDF PAGE 8")
    assert "Problem 1" in text
    assert "Problem 2" in text
    assert heading_index < text.index("Problem 1") < text.index("Problem 2")


def test_exact_location_field_is_precise_and_page_prefix_free(tmp_path: Path) -> None:
    text = _write([_margin_finding(8)], tmp_path)
    assert "Exact location: left margin" in text
    # The page reference is already in the "PDF PAGE 8" heading, so it must not
    # be repeated at the start of the Exact location value.
    assert "Exact location: Page 8" not in text


def test_exact_location_falls_back_when_detector_gives_no_location(tmp_path: Path) -> None:
    finding = AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=None,
        message="Mixed numbering style detected.",
        details={"issue_type": "mixed_numbering_style", "confidence": "medium"},
    )
    text = _write([finding], tmp_path)
    assert "DOCUMENT-WIDE FINDINGS" in text


def test_page_less_findings_appear_after_all_page_sections(tmp_path: Path) -> None:
    findings = [
        _margin_finding(9),
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=None,
            message="Mixed numbering style detected.",
            details={
                "issue_type": "mixed_numbering_style",
                "observed_style": "roman/arabic",
                "confidence": "medium",
            },
        ),
    ]
    text = _write(findings, tmp_path)
    assert text.index("PDF PAGE 9") < text.index("DOCUMENT-WIDE FINDINGS")


def test_repeated_same_page_p036_findings_consolidate_without_dropping_pairs(
    tmp_path: Path,
) -> None:
    pairs = [
        ("1 INTRODUCTION", "Background and Context"),
        ("Background and Context", "1.2 Exoskeletons and Wearable Devices"),
        ("1.2 Exoskeletons and Wearable Devices", "1.3 Research Questions"),
    ]
    findings = [_toc_finding(12, i, prev, nxt) for i, (prev, nxt) in enumerate(pairs)]
    text = _write(findings, tmp_path)

    # One consolidated problem record, not one per occurrence.
    assert text.count("Problem 1 —") == 1
    assert "Problem 2" not in text
    assert "Affected locations: 3" in text
    for prev, nxt in pairs:
        assert prev in text
        assert nxt in text


def test_repeated_same_page_punctuation_findings_consolidate_without_dropping_entries(
    tmp_path: Path,
) -> None:
    findings = [
        _lof_punctuation_finding(15, entry_index=3, page_entry_index=0),
        _lof_punctuation_finding(15, entry_index=4, page_entry_index=1),
        _lof_punctuation_finding(15, entry_index=5, page_entry_index=2),
        # Unrelated same-page finding: must not be folded into the
        # punctuation group just because it shares a page.
        _margin_finding(15),
    ]
    text = _write(findings, tmp_path)

    assert text.count("PDF PAGE 15") == 1
    assert text.count("List of Figures entry missing terminal punctuation") == 1
    assert "Affected locations: 3" in text
    # Every affected entry is preserved in the numbered list, none dropped.
    assert "1. List of Figures entry 4" in text
    assert "2. List of Figures entry 5" in text
    assert "3. List of Figures entry 6" in text
    # The unrelated margin finding stays a separate problem record, not
    # merged into the punctuation group's "Affected locations" list.
    assert "Problem 1 —" in text
    assert "Problem 2 —" in text
    assert "Problem 3" not in text
    margin_start = text.index("Left margin boundary violation")
    margin_end = text.index("Public rule reference: P011", margin_start)
    assert "Affected locations" not in text[margin_start:margin_end]


def test_p013_routine_candidates_excluded_from_headline_problem_count(tmp_path: Path) -> None:
    findings = [
        _page_number_candidate(1),
        _page_number_candidate(2),
        _page_number_candidate(3),
        _margin_finding(4),
    ]
    text = _write(findings, tmp_path)
    assert "1 problem requiring review." in text
    assert "PDF PAGE 1" not in text
    assert "PDF PAGE 2" not in text
    assert "PDF PAGE 3" not in text
    assert "PDF PAGE 4" in text


def test_headline_distinguishes_problems_from_affected_locations(tmp_path: Path) -> None:
    pairs = [(f"entry {i} heading", f"entry {i + 1} heading") for i in range(4)]
    findings = [_toc_finding(12, i, prev, nxt) for i, (prev, nxt) in enumerate(pairs)]
    text = _write(findings, tmp_path)
    assert "1 problem requiring review, representing 4 affected locations." in text


def test_no_duplicated_suggested_fix_label(tmp_path: Path) -> None:
    findings = [_toc_finding(12, 0, "1 INTRODUCTION", "Background and Context")]
    text = _write(findings, tmp_path)
    assert "Suggested fix: | Suggested fix:" not in text
    assert text.count("How to fix it:") == 1


def test_no_truncated_ellipsis_in_student_facing_text(tmp_path: Path) -> None:
    # P025 has no issue-specific or Ester-authored remediation override in most
    # cases, so its suggested fix falls back to the rule-JSON remediation text,
    # which is exactly the path that used to get silently cut off at ~200
    # characters with a trailing "...".
    finding = AuditFinding(
        rule_id="P025",
        severity=Severity.WARNING,
        page=3,
        message="Front matter structure issue.",
        details={"issue_type": "frontmatter_structure_issue", "confidence": "medium"},
    )
    text = _write([finding], tmp_path)
    assert "..." not in text
    assert "…" not in text


def test_no_private_q_rule_ids_or_absolute_paths(tmp_path: Path) -> None:
    finding = _margin_finding(8, absolute_path="/home/student/Documents/thesis-final-v9.tex")
    text = _write([finding], tmp_path)
    assert "Q123" not in text
    assert "/home/student" not in text
    assert "thesis-final-v9.tex" not in text


def test_output_is_valid_utf8_plain_text(tmp_path: Path) -> None:
    findings = [
        _margin_finding(8),
        _toc_finding(12, 0, "1 INTRODUCTION", "Background and Context"),
    ]
    output_path = tmp_path / "report.txt"
    write_text_report(findings, _metadata(), output_path)
    raw = output_path.read_bytes()
    # Must decode cleanly as UTF-8 (raises UnicodeDecodeError otherwise).
    decoded = raw.decode("utf-8")
    assert decoded.strip()


def test_manuscript_page_shown_when_available_from_any_finding_on_that_page(
    tmp_path: Path,
) -> None:
    findings = [
        _margin_finding(8),
        _page_number_candidate(8, label="v"),
    ]
    text = _write(findings, tmp_path)
    assert "PDF PAGE 8" in text
    assert "Manuscript page: v" in text


def test_manuscript_page_line_omitted_when_not_determined(tmp_path: Path) -> None:
    text = _write([_margin_finding(8)], tmp_path)
    lines = text.splitlines()
    heading_index = lines.index("PDF PAGE 8")
    # The line right after the "PDF PAGE 8" heading is either "Manuscript page:
    # ..." or the closing "====" separator -- never anything else -- so when no
    # manuscript label was available it must be the separator, not the line.
    assert not lines[heading_index + 1].startswith("Manuscript page:")


def test_public_rule_reference_uses_injected_mapping(tmp_path: Path) -> None:
    def fake_reference(rule_id: str, **_: object) -> str:
        return f"CUSTOM-{rule_id}"

    output_path = tmp_path / "report.txt"
    write_text_report(
        [_margin_finding(8)],
        _metadata(),
        output_path,
        public_rule_reference_id=fake_reference,
    )
    text = output_path.read_text(encoding="utf-8")
    assert "Public rule reference: CUSTOM-P011" in text


def test_no_finding_produces_no_problems_message(tmp_path: Path) -> None:
    text = _write([], tmp_path)
    assert "No student-facing formatting problems were detected." in text


def test_confidence_label_is_title_case(tmp_path: Path) -> None:
    text = _write([_margin_finding(8)], tmp_path)
    assert "Confidence: Medium" in text
