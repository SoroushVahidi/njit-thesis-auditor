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
"""

from __future__ import annotations

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
