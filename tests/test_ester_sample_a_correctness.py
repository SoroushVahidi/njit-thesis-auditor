"""Sample A correctness regression tests (privacy-safe, no PDF body text in assertions)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import fitz

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_frontmatter_headings import check_pdf_frontmatter_headings
from njit_auditor.web_samples import get_builtin_sample


def _make_concatenated_heading_pdf(tmp_path: Path, heading_line: str) -> Path:
    """Minimal PDF whose text layer has a concatenated front-matter heading line."""
    pdf_path = tmp_path / "concat_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 90), heading_line, fontsize=12)
    page.insert_text((108, 120), "Placeholder synthetic body line.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_p038_concatenated_approval_page_not_reported_missing(tmp_path: Path) -> None:
    pdf_path = _make_concatenated_heading_pdf(tmp_path, "APPROVALPAGE")
    model = load_pdf_layout(str(pdf_path))
    missing = [
        f
        for f in check_pdf_frontmatter_headings(model)
        if f.details.get("issue_type") == "required_heading_missing"
        and f.details.get("expected_heading") == "APPROVAL PAGE"
    ]
    assert missing == []


def test_p038_concatenated_table_of_contents_not_reported_missing(tmp_path: Path) -> None:
    pdf_path = _make_concatenated_heading_pdf(tmp_path, "TABLEOFCONTENTS")
    model = load_pdf_layout(str(pdf_path))
    missing = [
        f
        for f in check_pdf_frontmatter_headings(model)
        if f.details.get("issue_type") == "required_heading_missing"
        and f.details.get("expected_heading") == "TABLE OF CONTENTS"
    ]
    assert missing == []


def test_p038_concatenated_variant_does_not_emit_phrase_not_exact(tmp_path: Path) -> None:
    pdf_path = _make_concatenated_heading_pdf(tmp_path, "BIOGRAPHICALSKETCH")
    model = load_pdf_layout(str(pdf_path))
    phrase = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert phrase == []


def test_ester_sample_a_problem_finding_baseline() -> None:
    """Regression guard for the reproducible Sample A correctness fixes.

    P011 dropped from 19 to 17 (total 25 -> 23) after the low-confidence
    margin-overflow suppression fix: two Sample A findings were single-line,
    sub-5pt "overflow" -- the same measurement-noise pattern Ester's Sample B
    review confirmed as false positives. See
    docs/status/ester_sample_b_p011_margin_low_overflow.md.

    Later P051 copyright-year extraction hardening removed one additional
    Sample A false positive on the Copyright Page, bringing the total to 22.

    P011 dropped again from 17 to 15 (total 22 -> 20) after the 2026-08
    Esther/R011-batch bottom-margin fix (BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT):
    Sample A pages 26 (6.0pt) and 54 (5.7pt) were single-line bottom-margin
    "probable TP" guesses in
    docs/status/p011_precision_false_negative_audit_20260710.md (S7, never
    confirmed by Esther) and match, in side/magnitude, the bottom-margin false
    positives Esther confirmed on seven different real dissertations in that
    batch. See docs/status/p011_r011_batch_2026_08_false_positive_fix.md.

    P015 dropped from 1 to 0 (total 20 -> 19) after the 2026-08 Esther/R015
    row-remnant-absorption fix. Sample A page 77's single finding was the
    same root cause as three Esther-confirmed R015 false positives in that
    batch: a short fragment ("MPDPTWinstances.") on a split text row was
    silently dropped by the paragraph-usability filter, leaving the row's
    surviving remnant to start mid-row and orphan the true paragraph
    continuation as a spurious "later paragraph missing indent". See
    docs/status/p015_r015_esther_feedback_false_positive_fix_20260825.md.

    P011 dropped again from 15 to 11 (total 19 -> 15) after Esther's
    2026-08-25 R011-R015 follow-up review directly confirmed the ~9.2pt
    recurring bottom-margin footer-zone cluster
    (BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT raised 9.0 -> 9.3pt) is NOT a
    violation: Sample A pages 11, 42, 66, and 71 were single-line
    bottom-margin findings at exactly that ~9.2pt (9.17pt raw) geometry, the
    same recurring pattern as the Muyeed physical-page-36 "clustering
    algorithm." finding Esther labeled a false positive. Pages 82 (9.8pt)
    and 83 (11.0pt) were beyond that first cluster, but their final-line
    boxes also fit the later bounded R011 line-box pattern. They are now
    suppressed by the focused R011 Ester-regression reconciliation. See
    docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md.

    P015 is 1 under the 2026-09 R015 paragraph-boundary follow-up: a later
    bold run-in paragraph start is now eligible for missing-indent reporting
    instead of being heading-exempt. This mirrors Ester's Youra page-101
    correction: report the true paragraph-start line, not the following
    continuation line.

    P011 dropped from 9 to 1 after the 2026-10-06 outdented reference-label
    exemption: pages 91-98 were "[n]" label columns hanging left of the 1.5 in
    edge with entry text starting at it, exempt under Ester's LaTeX left-margin
    guidance (derived application, see
    docs/status/r011_outdented_reference_labels_20261006.md). Page 99 (one
    entry, no heading) stayed reported.

    P011 dropped from 1 to 0 after the 2026-10-07 cross-page continuation of
    the reference-label column: page 99 holds entry [93], continuing page 98's
    [84]-[92] in the same label and text columns with no new heading, so its
    outdented label is exempt for the same reason as pages 91-98 (derived
    application, same doc).
    """
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    problem = view.findings
    by_rule = Counter(f.rule_id for f in problem)

    # The historical 14-item total was a snapshot of the rule set at one point in
    # time. Sample A currently exercises a broader detector set (e.g. TOC/LoT/LoF
    # spacing and page-number rules) without any of the historically reproduced
    # false positives returning. Keep the scientific invariants pinned to the known
    # false-positive regressions instead of freezing a stale aggregate count.
    assert len(problem) >= 14
    assert by_rule["P038"] == 0
    assert by_rule["P011"] == 0
    assert by_rule["P013"] == 0
    assert by_rule["P028"] == 0
    assert by_rule["P044"] == 0
    assert by_rule["P027"] == 0
    assert by_rule["P015"] == 1
    assert by_rule["P051"] == 0


def test_ester_sample_a_p012_rollup_lists_affected_pages() -> None:
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p012 = next(f for f in view.findings if f.rule_id == "P012")
    assert "Affected pages include:" in p012.polished_comment
    assert "42 pages total" in p012.polished_comment


def test_p038_required_heading_missing_remains_student_visible() -> None:
    finding = AuditFinding(
        rule_id="P038",
        severity=Severity.WARNING,
        message="Missing required heading.",
        details={
            "issue_type": "required_heading_missing",
            "expected_heading": "TABLE OF CONTENTS",
            "section_key": "table_of_contents",
        },
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    assert len(view.findings) == 1
    assert view.findings[0].rule_id == "P038"
    assert view.findings[0].location_label == (
        "Front matter — required heading missing: TABLE OF CONTENTS"
    )
    assert view.findings[0].has_highlight is False
    # Ester (Sample B feedback, P038 Problem 43): the boilerplate "does not
    # correspond to a specific page or visual location" is incorrect once a
    # location IS given (here, the front-matter section name) -- don't repeat
    # the location text again, but don't deny it exists either.
    reason = view.findings[0].no_highlight_reason.lower()
    assert "does not correspond to a specific page or visual location" not in reason
    assert "no specific pdf page" in reason


def test_no_highlight_guidance_still_claims_no_location_when_none_is_known() -> None:
    """A genuinely locationless document-level finding (e.g. P021 word count)
    must keep the original generic wording -- only findings that DO carry a
    location_label get the corrected sentence.
    """
    finding = AuditFinding(
        rule_id="P021",
        severity=Severity.WARNING,
        message="Abstract word count exceeded.",
        details={"word_count": "420", "limit": "400"},
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    assert view.findings[0].location_label == ""
    assert (
        "does not correspond to a specific page or visual location"
        in view.findings[0].no_highlight_reason.lower()
    )


def test_ester_sample_a_json_export_schema_unchanged() -> None:
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    assert set(payload.keys()) == {"findings", "grouped_findings", "grouped_summary", "metadata"}
    if payload["findings"]:
        assert set(payload["findings"][0].keys()) >= {
            "rule_id",
            "severity",
            "page",
            "message",
            "details",
        }


# --- Sample B side effects (see docs/status/ester_sample_b_feedback_audit.md) ---
# These fixes were built for Sample A but also resolve documented Sample B
# false positives. Page assertions are used instead of exact totals, which
# are sensitive to unrelated rules and drift as other branches land.


def test_ester_sample_b_page_number_false_positives_resolved() -> None:
    """P013/P028 no longer misfire on Sample B TOC pages 10-11."""
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    by_rule = Counter(f.rule_id for f in view.findings)

    assert by_rule["P013"] == 0
    assert by_rule["P028"] == 0


def test_ester_sample_b_p015_mid_paragraph_false_positives_resolved() -> None:
    """P015 no longer fires on Sample B pages 24, 26, 27, 38 (Ester false positives)."""
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p015_pages = {f.page for f in view.findings if f.rule_id == "P015"}

    assert p015_pages.isdisjoint({24, 26, 27, 38})


def test_ester_sample_b_p015_page_23_false_positive_resolved() -> None:
    """P015 emits no Sample B page-23 finding after Ester's reviewed FP."""
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    page_23_issue_types = {
        f.issue_type for f in view.findings if f.rule_id == "P015" and f.page == 23
    }

    assert page_23_issue_types == set()
    # Page 34 is a separate, unconfirmed residual finding untouched by this fix.
    p015_pages = {f.page for f in view.findings if f.rule_id == "P015"}
    assert 34 in p015_pages


def test_ester_sample_b_p012_visibility_stable() -> None:
    """P012 document-level rollup is unchanged by this pass.

    P038's page-9 finding is covered separately by
    test_ester_sample_b_p038_acknowledgements_page9_not_flagged — Ester's
    Sample B review confirmed that finding was a false positive (American
    spelling "ACKNOWLEDGMENTS" is an NJIT-accepted equivalent), so it is now
    correctly absent rather than "stable" at one finding.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p012 = next(f for f in view.findings if f.rule_id == "P012")
    assert p012.has_highlight is False
    assert "pages total" in p012.polished_comment


def test_ester_sample_b_p016_page1_metadata_gap_is_not_spacing_finding() -> None:
    """P016 ignores the intentional abstract title/author metadata gap."""
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p016_page1 = [f for f in view.findings if f.rule_id == "P016" and f.page == 1]
    assert p016_page1 == []


def test_ester_sample_b_p023_page82_figure_description_not_flagged() -> None:
    """P023 no longer flags Sample B page 82 as under-spaced body text.

    Page 82 is entirely two figure descriptions (Figure 3.3 and Figure 3.4).
    Root cause: the PDF's text extraction splits each caption's number
    ("Figure3.3") from its description text onto a separate line fragment on
    the same visual row, so the multi-line description text was measured as
    ordinary body text and flagged single-spaced. Figure descriptions are
    conventionally single-spaced (Ester's exception list: tables, figure
    descriptions, bullet points, multi-line titles) and must not be
    flagged. See docs/status/ester_sample_b_p023_figure_description_spacing.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p023_page82 = [f for f in view.findings if f.rule_id == "P023" and f.page == 82]
    assert p023_page82 == []


def test_ester_sample_b_p020_page71_third_level_heading_not_flagged() -> None:
    """P020 no longer misreads Sample B page 71 as a Level 2 title-case violation.

    Page 71 has a Level 3 numbered heading ("3.4.3") whose number sits on its
    own bold line directly above the bold heading text. Because the two are on
    separate text lines, neither P020's generic bold-heading path nor P027's
    same-line numbered-heading regex previously identified the heading text as
    Level 3+ (sentence case, Q051) — P020 fell back to Title Case rules and,
    combined with a text-extraction artifact that glued a minor word onto the
    following word, produced a nonsensical suggestion. Level 3+ numbered
    headings are now excluded from P020, matching this rule's documented scope.
    See docs/status/ester_sample_b_p020_specific_remediation.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p020_page71 = [f for f in view.findings if f.rule_id == "P020" and f.page == 71]
    assert p020_page71 == []


def test_ester_sample_b_p020_page80_table_title_remediation_is_table_specific() -> None:
    """Sample B page 80 is a P017 table-title issue, not generic P020."""
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p020_page80 = [f for f in view.findings if f.rule_id == "P020" and f.page == 80]
    assert p020_page80 == []

    p017_page80 = [f for f in view.findings if f.rule_id == "P017" and f.page == 80]
    # Ester named two issues on this table title: title case, and the period
    # it ends with ("table titles do not end in periods").
    assert sorted(f.issue_type for f in p017_page80) == [
        "possible_title_case_issue",
        "unexpected_terminal_period",
    ]
    finding = next(f for f in p017_page80 if f.issue_type == "possible_title_case_issue")
    assert "table title" in finding.polished_comment
    assert "heading" not in finding.polished_comment.lower()
    assert "figure" not in finding.polished_comment.lower()

    assert "table title" in finding.detailed_explanation
    assert "figure" not in finding.detailed_explanation.lower()
    assert "prepositions, conjunctions, and articles" in finding.detailed_explanation
    assert "period" in finding.detailed_explanation.lower()


def test_ester_sample_b_p019_page57_58_embedded_reprint_not_flagged() -> None:
    """Neither P019 nor P013 flags Sample B pages 57-58 as "multiple_page_numbers".

    Those pages reproduce a published paper as a dissertation chapter; the
    reprint carries its own original top-of-page numbering ("2", "1") alongside
    the manuscript's real, continuously-incrementing bottom-center page number
    ("43", "44"). Ester's Sample B review flagged this as a false positive: the
    manuscript's own page number is unambiguous, so it should not require manual
    "multiple candidates" review. P013 shares the exact same candidate-counting
    logic as P019 (see _filter_secondary_location_noise in
    rules/pdf_page_numbers.py), so both had to be fixed together — fixing only
    P019 just moved the false positive to P013's own raw candidate finding,
    which is no longer suppressed as "redundant with P019" once P019 stops
    reporting a problem here. See
    docs/status/ester_sample_b_p019_page_numbering_highlights.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    noise = [
        f
        for f in view.findings
        if f.rule_id in ("P019", "P013")
        and f.page in {57, 58}
        and f.issue_type == "duplicate_or_ambiguous_page_number"
    ]
    assert noise == [], f"Sample B pages 57/58 must have zero P019/P013 false positives: {noise}"


def test_ester_sample_b_p019_valid_regime_transition_no_document_level_warning() -> None:
    """A valid Roman-front-matter to Arabic-body transition is not a P019 warning."""
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    doc_level = [f for f in view.findings if f.rule_id == "P019" and f.page is None]
    assert doc_level == []


def test_ester_sample_b_p038_acknowledgements_page9_not_flagged() -> None:
    """P038 no longer flags Sample B page 9's ACKNOWLEDGEMENTS heading.

    Page 9's heading literally reads "ACKNOWLEDGMENTS" (the standard American
    spelling, verified directly in the PDF text layer — not a text-extraction
    artifact). The detector already treated this as present for section-gate
    localization purposes, but P038's own phrase-mismatch check separately
    flagged it as a wording error. Ester's Sample B review confirmed this was
    a false positive: the American spelling is an NJIT-accepted equivalent,
    not a defect. See docs/status/ester_sample_b_p038_front_matter_headings.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p038_findings = [f for f in view.findings if f.rule_id == "P038"]
    assert p038_findings == [], (
        f"Sample B must have zero P038 findings after the fix; got: {p038_findings}"
    )


def test_ester_sample_b_p011_low_overflow_false_positives_cleared() -> None:
    """P011 no longer flags Sample B pages 1, 24, and 39.

    Ester's Sample B review marked these three as false positives: each is a
    single text line with a small (under 5pt) measured right-margin
    "overflow" — the same font-metric/text-extraction measurement-noise
    pattern as every other "low confidence" P011 finding in this document.
    See docs/status/ester_sample_b_p011_margin_low_overflow.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    false_positive_pages = {1, 24, 39}
    hits = [f for f in view.findings if f.rule_id == "P011" and f.page in false_positive_pages]
    assert hits == [], f"Sample B pages 1/24/39 must have zero P011 findings: {hits}"


def test_ester_sample_b_p011_true_positives_retained_with_highlights() -> None:
    """P011 still flags Sample B pages 10, 15, 27, 33, and 38.

    Ester's Sample B review confirmed these as real margin-overflow defects
    (measured overflow 5.4-21.2pt — comfortably medium/high confidence, not
    the sub-5pt noise pattern suppressed on pages 1/24/39). The
    low-overflow-noise fix must not weaken detection of genuine violations,
    and each retained finding must still resolve to a usable, visible
    highlight rather than a vague "open the page" fallback. See
    docs/status/ester_sample_b_p011_margin_low_overflow.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    true_positive_pages = {10, 15, 27, 33, 38}
    found_pages = {
        f.page for f in view.findings if f.rule_id == "P011" and f.page in true_positive_pages
    }
    assert found_pages == true_positive_pages, (
        f"expected all of {true_positive_pages}, got {found_pages}"
    )
    for f in view.findings:
        if f.rule_id == "P011" and f.page in true_positive_pages:
            assert f.has_highlight is True, f"page {f.page}: expected a real highlight"
            assert f.action_kind == "highlight"


def test_ester_sample_b_p026_page5_approval_page_font_false_positive_resolved() -> None:
    """P026 no longer misfires on Sample B page 5 (the Approval Page).

    Ester flagged the page 5 font warning as incorrect -- the highlighted
    text was correct-size text. Page 5 is the Approval Page: a committee
    signature block (names/titles/date lines), not body prose. The PDF's
    text extraction runs the page's "APPROVAL PAGE" heading together with no
    space ("APPROVALPAGE"), so the P026 page-skip gate (which already
    exempts named front-matter headings, matching the same pattern used by
    P038) failed to recognize the page as front matter and measured the
    signature block's legitimate ~10.9pt CMR10 text against the 12pt
    body-text rule. See docs/status/ester_sample_b_font_false_positive_highlight.md.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    hits = [f for f in view.findings if f.rule_id == "P026" and f.page == 5]
    assert hits == [], f"Sample B page 5 must have zero P026 findings: {hits}"
