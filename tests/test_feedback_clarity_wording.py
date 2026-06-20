"""Tests for the "Clarify student-facing feedback wording" pass.

Covers, using synthetic metadata only (no dissertation body text, no LaTeX):

1. P063 — remediation truncation breaks on a word boundary, not mid-word
2. Confidence:/Triage tier: labels no longer appear in polished comments
3. VERIFY_SUFFIX is dropped for bespoke/specific comments, kept for generic ones
4. P036 — missing issue_type_explanations entries are filled in
5. P016 — gap-measurement (largest_gap_pt) enrichment
6. P068 — role/signature count enrichment
7. P014 — names which heading-layout attribute(s) failed
8. P019/page-numbering — implausible sequence values get a safe fallback message
9. P014/P016/P068 — issue_type_explanation and detailed_explanation (the "Read
   explanation" and "More detail" boxes) now match the polished_comment's
   metadata-specific wording instead of falling back to generic boilerplate
10. P032/P056/P066/P067 — zero-coverage rules gain metadata-specific polished
    comments, issue_type_explanations, and detailed_explanations instead of
    falling through to generic catch-all wording
11. P045/P047 — Biosketch publication/bullet spacing rules gain
    metadata-specific polished comments, issue_type_explanations, and
    detailed_explanations instead of falling through to generic catch-all
    wording
"""

from __future__ import annotations

import pytest

from njit_auditor.issue_type_explanations import explain_issue_type
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    VERIFY_SUFFIX,
    _truncate_at_word_boundary,
    build_polished_comment,
    contains_blocked_detail_text,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import (
    _plausible_page_sequence_value,
    build_report_view,
)

# ---------------------------------------------------------------------------
# 1. P063 — word-boundary-aware truncation
# ---------------------------------------------------------------------------


def test_truncate_at_word_boundary_does_not_cut_mid_word() -> None:
    text = (
        "For a single appendix: rename the heading to APPENDIX (remove any letter "
        "suffix). For multiple appendices: ensure each appendix heading uses "
        "APPENDIX A, APPENDIX B, etc. in consecutive alphabetical order."
    )
    truncated = _truncate_at_word_boundary(text, 200)
    assert len(truncated) <= 200
    assert truncated.endswith("...")
    core = truncated[: -len("...")]
    assert not core.endswith(" ")
    # The original text at the same cut point is mid-word ("alphabetical...");
    # the fixed version must stop at a preceding word boundary instead.
    assert not text.startswith(core + "a")
    assert text.startswith(core)


def test_truncate_at_word_boundary_leaves_short_text_untouched() -> None:
    text = "Short remediation text."
    assert _truncate_at_word_boundary(text, 200) == text


def test_p063_remediation_does_not_end_mid_word() -> None:
    comment = build_polished_comment(
        rule_id="P063",
        issue_type="appendix_numbering_inconsistent",
        page=40,
        details={},
    )
    assert "alphabetical..." not in comment
    assert "consecutive..." in comment


# ---------------------------------------------------------------------------
# 2 & 3. Confidence:/Triage tier: removed; VERIFY_SUFFIX trimmed when specific
# ---------------------------------------------------------------------------


def test_confidence_and_triage_labels_never_appear_in_polished_comment() -> None:
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=2,
        details={"side": "left_margin", "confidence": "high", "triage_tier": "medium"},
    )
    assert "Confidence:" not in comment
    assert "Triage tier:" not in comment


def test_verify_suffix_dropped_for_bespoke_issue_template() -> None:
    comment = build_polished_comment(
        rule_id="P016",
        issue_type="excessive_line_gap",
        page=9,
        details={"largest_gap_pt": "30.0"},
    )
    assert VERIFY_SUFFIX not in comment


def test_verify_suffix_kept_for_generic_catch_all_fallback() -> None:
    comment = build_polished_comment(
        rule_id="P999",
        issue_type="totally_unmapped_issue_type",
        page=1,
        details={},
    )
    assert VERIFY_SUFFIX in comment


# ---------------------------------------------------------------------------
# 4. P036 — missing issue_type_explanations entries
# ---------------------------------------------------------------------------


def test_p036_toc_lot_lof_explanations_are_specific() -> None:
    for issue_type, expected_phrase in (
        ("toc_inter_entry_spacing_too_tight", "Table of Contents"),
        ("lot_inter_entry_spacing_too_tight", "List of Tables"),
        ("lof_inter_entry_spacing_too_tight", "List of Figures"),
    ):
        text = explain_issue_type("P036", issue_type)
        assert expected_phrase in text
        assert "was flagged by an automated check" not in text


# ---------------------------------------------------------------------------
# 5. P016 — gap-measurement enrichment
# ---------------------------------------------------------------------------


def test_p016_comment_includes_gap_measurement_when_available() -> None:
    comment = build_polished_comment(
        rule_id="P016",
        issue_type="excessive_paragraph_gap",
        page=22,
        details={"largest_gap_pt": "41.3"},
    )
    assert "41.3pt" in comment


def test_p016_heading_gap_comment_includes_measurement() -> None:
    findings = [
        AuditFinding(
            rule_id="P016",
            severity=Severity.WARNING,
            page=6,
            message="Suspicious heading gap.",
            details={
                "issue_type": "suspicious_heading_blank_gap",
                "largest_gap_pt": "55.0",
                "affected_gap_count": "1",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P016")
    assert "55.0pt" in fv.polished_comment


# ---------------------------------------------------------------------------
# 6. P068 — role/signature count enrichment
# ---------------------------------------------------------------------------


def test_p068_advisor_missing_includes_role_label_count() -> None:
    comment = build_polished_comment(
        rule_id="P068",
        issue_type="approval_page_advisor_role_label_missing",
        page=3,
        details={"role_label_count": "3"},
    )
    assert "3 committee role label" in comment
    assert "advisor role label" in comment


def test_p068_signature_sparse_includes_counts_and_required() -> None:
    comment = build_polished_comment(
        rule_id="P068",
        issue_type="approval_page_signature_blocks_sparse",
        page=3,
        details={"role_label_count": "4", "signature_date_indicator_count": "2"},
    )
    assert "2 signature/date line" in comment
    assert "4 committee role label" in comment
    assert "at least 4 are expected" in comment


def test_p068_signature_sparse_required_floor_is_two() -> None:
    comment = build_polished_comment(
        rule_id="P068",
        issue_type="approval_page_signature_blocks_sparse",
        page=3,
        details={"role_label_count": "1", "signature_date_indicator_count": "0"},
    )
    assert "at least 2 are expected" in comment


# ---------------------------------------------------------------------------
# 7. P014 — names which heading-layout attribute(s) failed
# ---------------------------------------------------------------------------


def _p014_finding(*, page: int = 5, **attrs: str) -> AuditFinding:
    details = {
        "heading": "ACKNOWLEDGEMENTS",
        "centered": "True",
        "near_top": "True",
        "bold": "True",
        "all_caps": "True",
        "suggested_fix": (
            "Place named front-matter headings centered near the top in bold all-caps."
        ),
    }
    details.update(attrs)
    return AuditFinding(
        rule_id="P014",
        severity=Severity.WARNING,
        page=page,
        message="Named heading formatting issue.",
        details=details,
    )


def test_p014_names_single_failed_attribute() -> None:
    findings = [_p014_finding(bold="False")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert "not bold" in fv.polished_comment
    assert "not centered" not in fv.polished_comment
    assert "not near the top" not in fv.polished_comment
    assert "make this heading bold" in fv.suggested_fix.lower()


def test_p014_names_multiple_failed_attributes() -> None:
    findings = [_p014_finding(centered="False", all_caps="False")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert "not centered" in fv.polished_comment
    assert "not in all capital letters" in fv.polished_comment
    assert "not bold" not in fv.polished_comment


def test_p014_includes_heading_name() -> None:
    findings = [_p014_finding(bold="False")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert "ACKNOWLEDGEMENTS" in fv.polished_comment


def test_p014_comment_never_quotes_blocked_detail_text() -> None:
    forbidden = "a long confidential dissertation sentence nobody should see"
    findings = [
        _p014_finding(bold="False", line_preview=forbidden, observed_summary=forbidden)
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert forbidden not in fv.polished_comment
    assert contains_blocked_detail_text(fv.polished_comment, findings[0].details) is False


# ---------------------------------------------------------------------------
# 8. P019/page-numbering — implausible sequence values get a safe fallback
# ---------------------------------------------------------------------------


def test_plausible_page_sequence_value_accepts_normal_numbers() -> None:
    assert _plausible_page_sequence_value("42") is True
    assert _plausible_page_sequence_value("0") is True
    assert _plausible_page_sequence_value("9999") is True


def test_plausible_page_sequence_value_rejects_absurd_numbers() -> None:
    assert _plausible_page_sequence_value("2503052525") is False
    assert _plausible_page_sequence_value("10000") is False


def test_plausible_page_sequence_value_leaves_non_numeric_alone() -> None:
    # Roman numerals and placeholder text are not int-parseable; the guard
    # must not affect that existing, already-correct behavior.
    assert _plausible_page_sequence_value("viii") is True
    assert _plausible_page_sequence_value("the detected value") is True


def _p019_sequence_finding(*, observed: str, expected: str, page: int = 7) -> AuditFinding:
    return AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=page,
        message="Page number sequence issue.",
        details={
            "issue_type": "sequence_gap",
            "observed_sequence": observed,
            "expected_sequence": expected,
        },
    )


def test_implausible_sequence_uses_safe_fallback_message() -> None:
    findings = [_p019_sequence_finding(observed="2503052525", expected="27")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P019")
    assert "2503052525" not in fv.polished_comment
    assert "looks inconsistent" in fv.polished_comment
    assert "manually check the nearby page numbers" in fv.polished_comment


def test_plausible_sequence_keeps_real_numbers_visible() -> None:
    findings = [_p019_sequence_finding(observed="27", expected="28")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P019")
    assert "Observed: 27" in fv.polished_comment
    assert "Expected: 28" in fv.polished_comment


def test_roman_numeral_sequence_is_unaffected_by_plausibility_guard() -> None:
    findings = [_p019_sequence_finding(observed="ix", expected="viii")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P019")
    assert "Observed: ix" in fv.polished_comment
    assert "Expected: viii" in fv.polished_comment


# ---------------------------------------------------------------------------
# 9. P014/P016/P068 — issue_type_explanation and detailed_explanation now
#    match the polished_comment's metadata-specific wording
# ---------------------------------------------------------------------------


def test_p014_issue_type_explanation_names_failed_attribute() -> None:
    findings = [_p014_finding(bold="False")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert "not bold" in fv.issue_type_explanation
    assert "was flagged by an automated check" not in fv.issue_type_explanation


def test_p014_detailed_explanation_names_failed_attribute() -> None:
    findings = [_p014_finding(centered="False")]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert "not centered" in fv.detailed_explanation


def test_p014_explanations_never_quote_blocked_detail_text() -> None:
    forbidden = "a long confidential dissertation sentence nobody should see"
    findings = [
        _p014_finding(bold="False", line_preview=forbidden, observed_summary=forbidden)
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert forbidden not in fv.issue_type_explanation
    assert forbidden not in fv.detailed_explanation


def test_p014_issue_type_explanation_degrades_gracefully_without_details() -> None:
    text = explain_issue_type("P014", "")
    assert "does not match njit's expected layout/style" in text.lower()


def test_p016_issue_type_explanation_includes_gap_measurement() -> None:
    findings = [
        AuditFinding(
            rule_id="P016",
            severity=Severity.WARNING,
            page=6,
            message="Excessive line gap.",
            details={"issue_type": "excessive_line_gap", "largest_gap_pt": "37.5"},
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P016")
    assert "37.5pt" in fv.issue_type_explanation
    assert "37.5pt" in fv.detailed_explanation


def test_p068_issue_type_explanation_includes_counts() -> None:
    findings = [
        AuditFinding(
            rule_id="P068",
            severity=Severity.WARNING,
            page=3,
            message="Sparse signature blocks.",
            details={
                "issue_type": "approval_page_signature_blocks_sparse",
                "role_label_count": "4",
                "signature_date_indicator_count": "2",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P068")
    assert "4 committee role label" in fv.issue_type_explanation
    assert "2 signature/date line" in fv.detailed_explanation


def test_explain_issue_type_details_param_is_optional_and_backward_compatible() -> None:
    # Existing call sites across the codebase call explain_issue_type without
    # `details`; this must keep working for non-P014/P016/P068 rule_ids.
    text = explain_issue_type("P012", "pdf_annotation_detected")
    assert "annotation" in text.lower()


# ---------------------------------------------------------------------------
# 10. P032/P056/P066/P067 — zero-coverage quick-win explanations
# ---------------------------------------------------------------------------


def test_p032_comment_includes_entry_kind_and_gap_measurements() -> None:
    comment = build_polished_comment(
        rule_id="P032",
        issue_type="wrapped_entry_internal_spacing",
        page=12,
        details={
            "entry_kind": "toc_level_2",
            "observed_gap_pt": "24.5",
            "expected_max_gap_pt": "20.4",
        },
    )
    assert "Table of Contents entry" in comment
    assert "24.5pt" in comment
    assert "20.4pt" in comment
    assert "was flagged by an automated check" not in comment


def test_p032_issue_type_explanation_and_detailed_explanation_match() -> None:
    findings = [
        AuditFinding(
            rule_id="P032",
            severity=Severity.WARNING,
            page=12,
            message="Wrapped entry spacing issue.",
            details={
                "issue_type": "wrapped_entry_internal_spacing",
                "entry_kind": "table_entry",
                "observed_gap_pt": "30.0",
                "expected_max_gap_pt": "18.0",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P032")
    assert "List of Tables entry" in fv.issue_type_explanation
    assert "30.0pt" in fv.issue_type_explanation
    assert "List of Tables entry" in fv.detailed_explanation
    assert "30.0pt" in fv.detailed_explanation
    assert "was flagged by an automated check" not in fv.issue_type_explanation


@pytest.mark.parametrize(
    ("issue_type", "section_type", "list_label", "entry_noun"),
    [
        ("lot_mixed_numbering_format", "list_of_tables", "List of Tables", "Table"),
        ("lof_mixed_numbering_format", "list_of_figures", "List of Figures", "Figure"),
    ],
)
def test_p056_comment_includes_format_counts_and_dominant_format(
    issue_type: str, section_type: str, list_label: str, entry_noun: str
) -> None:
    comment = build_polished_comment(
        rule_id="P056",
        issue_type=issue_type,
        page=14,
        details={
            "section_type": section_type,
            "format_counts": "chapter_based:3,sequential:2",
            "dominant_format": "chapter_based",
        },
    )
    assert list_label in comment
    assert "3 chapter-based" in comment
    assert "2 sequential" in comment
    assert f"{entry_noun} 1.2" in comment
    assert f"{entry_noun} 3" in comment
    assert "was flagged by an automated check" not in comment


def test_p056_issue_type_explanation_and_detailed_explanation_match() -> None:
    findings = [
        AuditFinding(
            rule_id="P056",
            severity=Severity.WARNING,
            page=16,
            message="Mixed LoF numbering format.",
            details={
                "issue_type": "lof_mixed_numbering_format",
                "section_type": "list_of_figures",
                "format_counts": "chapter_based:2,sequential:2",
                "dominant_format": "sequential",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P056")
    assert "List of Figures" in fv.issue_type_explanation
    assert "2 chapter-based" in fv.issue_type_explanation
    assert "2 sequential" in fv.issue_type_explanation
    assert "List of Figures" in fv.detailed_explanation


def test_p066_comment_describes_year_inversion_direction() -> None:
    comment = build_polished_comment(
        rule_id="P066",
        issue_type="biosketch_degree_order_suspicious",
        page=180,
        details={
            "first_candidate_year": "2015",
            "last_candidate_year": "2020",
            "inversion_count": "1",
        },
    )
    assert "2015" in comment
    assert "2020" in comment
    assert "1 place" in comment
    assert "most recent to oldest" in comment
    # Direction matters: a later-listed entry being *more recent* is the
    # violation, since NJIT requires descending (most-recent-first) order.
    assert "later-listed entry's year is more recent" in comment
    assert "was flagged by an automated check" not in comment


def test_p066_issue_type_explanation_and_detailed_explanation_match() -> None:
    findings = [
        AuditFinding(
            rule_id="P066",
            severity=Severity.WARNING,
            page=180,
            message="Biosketch degree order suspicious.",
            details={
                "issue_type": "biosketch_degree_order_suspicious",
                "first_candidate_year": "2010",
                "last_candidate_year": "2022",
                "inversion_count": "2",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P066")
    assert "2 places" in fv.issue_type_explanation
    assert "2010" in fv.issue_type_explanation
    assert "2022" in fv.detailed_explanation


def test_p067_comment_describes_year_inversion_direction() -> None:
    comment = build_polished_comment(
        rule_id="P067",
        issue_type="biosketch_publication_order_suspicious",
        page=182,
        details={
            "first_entry_year": "2018",
            "last_entry_year": "2023",
            "inversion_count": "2",
        },
    )
    assert "2018" in comment
    assert "2023" in comment
    assert "2 places" in comment
    assert "most recent to oldest" in comment
    assert "later-listed entry's year is more recent" in comment
    assert "was flagged by an automated check" not in comment


def test_p067_uses_top_level_page_when_details_have_no_page_key() -> None:
    # P067's details dict never has a "page"/"page_number" key (unlike most
    # other detectors); the page must still come through via the finding's
    # top-level `page` field, not from details.
    findings = [
        AuditFinding(
            rule_id="P067",
            severity=Severity.WARNING,
            page=182,
            message="Biosketch publication order suspicious.",
            details={
                "issue_type": "biosketch_publication_order_suspicious",
                "first_entry_year": "2019",
                "last_entry_year": "2021",
                "inversion_count": "1",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P067")
    assert fv.page == 182
    assert "page 182" in fv.polished_comment
    assert "1 place" in fv.issue_type_explanation
    assert "2019" in fv.detailed_explanation
    assert "2021" in fv.detailed_explanation


# ---------------------------------------------------------------------------
# 11. P045/P047 — Biosketch publication/bullet spacing explanations
# ---------------------------------------------------------------------------


def test_p045_hanging_indent_comment_includes_block_count_and_threshold() -> None:
    comment = build_polished_comment(
        rule_id="P045",
        issue_type="biosketch_publication_missing_hanging_indent",
        page=44,
        details={
            "multi_line_block_count": "3",
            "hanging_indent_threshold_points": "12.0",
        },
    )
    assert "hanging indentation" in comment
    assert "3 multi-line entries checked" in comment
    assert "12.0pt" in comment
    assert "Biographical Sketch" in comment
    assert "was flagged by an automated check" not in comment


def test_p045_entry_spacing_comment_includes_gap_measurements() -> None:
    comment = build_polished_comment(
        rule_id="P045",
        issue_type="biosketch_publication_entry_spacing_not_double",
        page=44,
        details={
            "observed_gap_points": "9.5",
            "required_gap_points": "20.0",
        },
    )
    assert "9.5pt" in comment
    assert "20.0pt" in comment
    assert "Biographical Sketch" in comment
    assert "was flagged by an automated check" not in comment


def test_p047_bullet_spacing_comment_includes_gap_measurements_and_block_index() -> None:
    comment = build_polished_comment(
        rule_id="P047",
        issue_type="biosketch_bullet_section_not_single_spaced",
        page=45,
        details={
            "observed_gap_points": "18.0",
            "required_max_gap_points": "12.0",
            "block_index": "2",
        },
    )
    assert "bullet block 3" in comment
    assert "18.0pt" in comment
    assert "12.0pt" in comment
    assert "Biographical Sketch" in comment
    assert "was flagged by an automated check" not in comment


def test_p047_bullet_spacing_comment_degrades_gracefully_without_block_index() -> None:
    comment = build_polished_comment(
        rule_id="P047",
        issue_type="biosketch_bullet_section_not_single_spaced",
        page=45,
        details={
            "observed_gap_points": "18.0",
            "required_max_gap_points": "12.0",
        },
    )
    assert "a bullet/list block" in comment
    assert "was flagged by an automated check" not in comment


def test_p045_hanging_indent_issue_type_explanation_and_detailed_explanation_match() -> None:
    findings = [
        AuditFinding(
            rule_id="P045",
            severity=Severity.WARNING,
            page=44,
            message="Biographical Sketch page has no publication entries with hanging indent.",
            details={
                "issue_type": "biosketch_publication_missing_hanging_indent",
                "multi_line_block_count": "4",
                "hanging_indent_threshold_points": "12.0",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P045")
    assert "4 multi-line entries checked" in fv.issue_type_explanation
    assert "12.0pt" in fv.issue_type_explanation
    assert "hanging indentation" in fv.detailed_explanation
    assert "was flagged by an automated check" not in fv.issue_type_explanation
    assert "automated formatting check" not in fv.detailed_explanation


def test_p045_entry_spacing_issue_type_explanation_and_detailed_explanation_match() -> None:
    findings = [
        AuditFinding(
            rule_id="P045",
            severity=Severity.WARNING,
            page=44,
            message="Consecutive publication entries lack the required blank line.",
            details={
                "issue_type": "biosketch_publication_entry_spacing_not_double",
                "observed_gap_points": "11.0",
                "required_gap_points": "20.0",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P045")
    assert "11.0pt" in fv.issue_type_explanation
    assert "20.0pt" in fv.issue_type_explanation
    assert "11.0pt" in fv.detailed_explanation
    assert "was flagged by an automated check" not in fv.issue_type_explanation
    assert "automated formatting check" not in fv.detailed_explanation


def test_p047_issue_type_explanation_and_detailed_explanation_match() -> None:
    findings = [
        AuditFinding(
            rule_id="P047",
            severity=Severity.WARNING,
            page=45,
            message="A bullet or list block has an unexpectedly large line gap.",
            details={
                "issue_type": "biosketch_bullet_section_not_single_spaced",
                "observed_gap_points": "16.0",
                "required_max_gap_points": "12.0",
                "block_index": "0",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P047")
    assert "bullet block 1" in fv.issue_type_explanation
    assert "16.0pt" in fv.issue_type_explanation
    assert "Bullet block 1" in fv.detailed_explanation
    assert "was flagged by an automated check" not in fv.issue_type_explanation
    assert "automated formatting check" not in fv.detailed_explanation


def test_p045_and_p047_wording_never_leak_unrelated_detail_text() -> None:
    forbidden = "Jane Q. Researcher, 'A Confidential Study of Private Bullet Content'"
    p045_comment = build_polished_comment(
        rule_id="P045",
        issue_type="biosketch_publication_missing_hanging_indent",
        page=44,
        details={
            "multi_line_block_count": "3",
            "hanging_indent_threshold_points": "12.0",
            "unrelated_text_field": forbidden,
        },
    )
    p047_comment = build_polished_comment(
        rule_id="P047",
        issue_type="biosketch_bullet_section_not_single_spaced",
        page=45,
        details={
            "observed_gap_points": "18.0",
            "required_max_gap_points": "12.0",
            "block_index": "1",
            "unrelated_text_field": forbidden,
        },
    )
    for comment in (p045_comment, p047_comment):
        assert forbidden not in comment
        assert "/home/" not in comment
        assert "Traceback" not in comment
        assert ".tex" not in comment
        assert "\\begin" not in comment
