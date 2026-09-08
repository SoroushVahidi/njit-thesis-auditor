"""Hand-transcribed, case-level historical Ester adjudications.

Unlike ``authority_matrix.py`` (rule-level policy, machine-parsed from a
structured JSON snapshot) and ``xlsx_packages.py`` (found nothing to
import -- see its module docstring), the well-documented *case-level*
historical decisions in this repository exist only as prose in dated
``docs/status/*.md`` files. Each entry below was read and transcribed by
hand from exactly the cited document, cross-checked against a real run of
the current auditor against the real private PDF (see
``docs/evaluation/ESTER_FEEDBACK_MIGRATION.md`` for how each was
verified) -- this module does not parse those markdown files
programmatically; treat it as a curated, reviewable data table, not a
generic importer.

Two cases with real historical detail but insufficient confidence to
pin to a specific current page/instance are deliberately **not** listed
here (R024's Praneeth hyphenated-fragment case, and R035's Anthony
landscape-geometry case -- both real, both already resolved as *policy*
via the authority-matrix/matrix-delta path, neither confidently
re-locatable as one specific current case). Listing a page number for
either would be fabrication; leaving them out and noting it in the
migration report is the honest choice for this pass.

Do NOT add an entry here without a citable source document and a page
number/structural fact actually stated in that document (or independently
reproducible against the real corpus, as every entry below was).
"""

from __future__ import annotations

from dataclasses import dataclass

from njit_auditor.review_ledger.models import AdjudicationVerdict


@dataclass(frozen=True)
class KnownHistoricalCase:
    document_short_name: str
    internal_rule_id: str
    issue_type: str
    physical_page: int
    structural_location: str
    volatile_detail: str
    summary: str
    verdict: AdjudicationVerdict
    reviewer_comment: str
    source_reference: str
    decided_at: str


KNOWN_HISTORICAL_CASES: tuple[KnownHistoricalCase, ...] = (
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation",
        physical_page=36,
        structural_location="bottom_margin:paragraph_trailing_line",
        volatile_detail="worst_overflow_pt=9.2",
        summary="Bottom-margin overflow at the ~9.2pt boundary cluster.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: not a violation, via the shared R011-R015 Follow-up sheet."
        ),
        source_reference="docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md",
        decided_at="2026-08-31",
    ),
    KnownHistoricalCase(
        document_short_name="Patrick",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation",
        physical_page=88,
        structural_location="right_margin:reference_entry",
        volatile_detail="worst_overflow_pt=18.0",
        summary="Right-margin overflow, Weng Cho Chew reference-list entry.",
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment=(
            "Ester: correct, report it, via the shared R011-R015 Follow-up sheet."
        ),
        source_reference="docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md",
        decided_at="2026-08-31",
    ),
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P015",
        issue_type="missing_later_indent",
        physical_page=101,
        structural_location="body_paragraph:run_in_bold_phrase",
        volatile_detail="misread_paragraph_start=true",
        summary="Paragraph-start misread as a continuation line after a bold run-in phrase.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester clarified the actual paragraph begins with the preceding bold "
            "run-in phrase; the flagged line is ordinary continuation text."
        ),
        source_reference="docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md",
        decided_at="2026-08-31",
    ),
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P018",
        issue_type="inconsistent_hierarchy_indent",
        physical_page=14,
        structural_location="list_of_figures:wrapped_entry_hanging_indent",
        volatile_detail="worst_delta_pt=unspecified",
        summary="TOC/List entry's left indent does not match same-level peers.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive (live feedback sheet, checked directly).",
        source_reference="docs/status/r018_r024_ester_sheet_authority_20260907.md",
        decided_at="2026-09-07",
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P018",
        issue_type="inconsistent_leader_dots",
        physical_page=11,
        structural_location="table_of_contents:section_1_1_area",
        volatile_detail="worst_entry_area=section_1_1",
        summary="TOC entries show inconsistent visible leader-dot usage (Section 1.1 area).",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (live feedback sheet, checked directly). Ester "
            "additionally asked whether sections 1.3.3/1.3.4/1.3.5 are caught -- "
            "recorded separately as policy/question context, not a second verdict "
            "(see docs/status/r018_r024_ester_sheet_authority_20260907.md)."
        ),
        source_reference="docs/status/r018_r024_ester_sheet_authority_20260907.md",
        decided_at="2026-09-07",
    ),
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P024",
        issue_type="list_of_figures_sentence_case",
        physical_page=14,
        structural_location="list_of_figures:parenthetical_proper_noun_list",
        volatile_detail="capitalized_terms=species_names",
        summary=(
            "Capitalized words in a parenthetical species-name list flagged as a "
            "sentence-case issue."
        ),
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive -- capitalized words are proper nouns/species names."
        ),
        source_reference="docs/status/r018_r024_ester_sheet_authority_20260907.md",
        decided_at="2026-09-07",
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P035",
        issue_type="figure_body_not_centered",
        physical_page=72,
        structural_location="figure:text_fallback_body_proxy",
        volatile_detail="center_delta_pt=114.3",
        summary=(
            "Figure-centering measured against a text-fragment fallback body, not "
            "the actual image."
        ),
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: the figure is centered.",
        source_reference="docs/status/r035_praneeth_text_fallback_fix_20260907.md",
        decided_at="2026-09-07",
    ),
    KnownHistoricalCase(
        document_short_name="Patrick",
        internal_rule_id="P085",
        issue_type="missing_first_chapter_one_heading",
        physical_page=13,
        structural_location="body_chapter:first_heading",
        volatile_detail="observed_heading=INTRODUCTION",
        summary=(
            "First body-chapter heading reads 'INTRODUCTION' instead of the "
            "required literal 'CHAPTER 1'."
        ),
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment=(
            "Ester: the first body heading must be the literal 'CHAPTER 1'; "
            "'INTRODUCTION' in that position is an error."
        ),
        source_reference="docs/status/patrick_chapter1_rule_gap_20260902.md",
        decided_at="2026-09-02",
    ),
)
