"""Hand-transcribed, case-level historical Ester adjudications.

Two source shapes, both hand-transcribed (this module does not parse
either programmatically -- treat it as a curated, reviewable data table):

1. Prose in dated ``docs/status/*.md`` files (the R018/R024/R035/R085
   cases, and the R011/R015 follow-up round -- these predate having any
   populated sheet export on this machine).
2. ``data/evaluation/private/ester_sheet_exports/audito_feedback_20260901.xlsx``
   (gitignored, private -- a 2026-09-01 export of the live Ester feedback
   Google Sheet, spreadsheet id ``1ZM7nJcw5KI5YGUkJBdE6hJyT7Y0Le-g1O1jiIb5RfBI``,
   located on this machine outside the repo and copied into the private
   evaluation area for this migration). This is the *initial* per-rule
   review round -- structurally and chronologically distinct from the
   R011/R015 follow-up round in (1): both are kept as separate
   ``KnownHistoricalCase`` entries even where the same rule and document
   recur, because they are genuinely different cases (different pages --
   see e.g. R011 Muyeed's initial page 19 vs. the follow-up's page 36).
   The export's own populated rows only go through R033 plus a handful of
   later rules (R035/R036 Anthony+Praneeth, sourced with their exact page
   numbers from the export, but whose ``Comment``/verdict column was
   still blank in this snapshot -- their FALSE_POSITIVE verdict here
   comes from a direct, dated relay of the live sheet, not from this
   file; see each entry's ``source_reference``). R055 and most of R037
   onward were not yet populated in this export at all and are not
   represented here -- see ``docs/evaluation/ESTER_FEEDBACK_MIGRATION.md``
   for the full accounting of what is and is not covered.

   R019's six reviewed cases (all "FALSE POSITIVE:") were added to the
   live sheet after this 2026-09-01 export was taken (the sheet's Drive
   ``modifiedTime`` is 2026-09-04) and were checked directly against the
   live sheet on 2026-09-08 -- see ``docs/status/r019_ester_sheet_authority_20260908.md``,
   which also records the full diff against this cached export confirming
   R019 is the only rule with new case-level verdicts since 2026-09-01
   (R035/R036's comment cells were also filled in by that point, but their
   verdicts already match what a prior 2026-09-07 direct check had
   recorded; R015's Youra comment gained an extra sentence that does not
   change its verdict).

Every finding's page/issue_type here was independently re-verified
against a real run of the current auditor on the real private PDF as
part of this migration (not merely transcribed and trusted) -- several
entries' exact ``issue_type`` (see ``ground_truth.qualify_issue_type``)
exists specifically because that verification surfaced a real ambiguity
(the same page carrying more than one same-rule finding) that a naive
transcription would have gotten wrong.

Do NOT add an entry here without a citable source and a page number/
structural fact actually stated in that source (or independently
reproducible against the real corpus, as every entry below was).
"""

from __future__ import annotations

from dataclasses import dataclass

from njit_auditor.review_ledger.models import AdjudicationVerdict

_SHEET_EXPORT_REF = "data/evaluation/private/ester_sheet_exports/audito_feedback_20260901.xlsx"
# The export's capture date, used as a documented upper bound on when each
# of its populated verdicts was actually recorded -- the sheet does not
# retain per-cell edit timestamps, and no earlier reference to most of
# these specific rows exists in this repository.
_SHEET_EXPORT_DATE = "2026-09-01"


@dataclass(frozen=True)
class KnownHistoricalCase:
    document_short_name: str
    internal_rule_id: str
    issue_type: str
    # None for a genuinely document-level finding (e.g. P019's
    # mixed_numbering_style, which the auditor itself reports with no page
    # -- see pdf_page_numbers.py) -- never a placeholder for "page unknown".
    physical_page: int | None
    structural_location: str
    volatile_detail: str
    summary: str
    verdict: AdjudicationVerdict
    reviewer_comment: str
    source_reference: str
    decided_at: str
    anchor_x: float | None = None
    anchor_y: float | None = None
    structural_role: str | None = None
    locator_source_reference: str | None = None


KNOWN_HISTORICAL_CASES: tuple[KnownHistoricalCase, ...] = (
    # -- R011/P011: follow-up round (docs/status/*, 2026-08-31) ------------------
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:bottom_margin",
        physical_page=36,
        structural_location="bottom_margin:paragraph_trailing_line:follow_up",
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
        issue_type="margin_boundary_violation:right_margin",
        physical_page=88,
        structural_location="right_margin:reference_entry:follow_up",
        volatile_detail="worst_overflow_pt=18.0",
        summary="Right-margin overflow, Weng Cho Chew reference-list entry.",
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment=(
            "Ester: correct, report it, via the shared R011-R015 Follow-up sheet."
        ),
        source_reference="docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md",
        decided_at="2026-08-31",
    ),
    # -- R011/P011: initial round (sheet export, page differs from follow-up) ----
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:bottom_margin",
        physical_page=42,
        structural_location="bottom_margin:body_text:initial_round",
        volatile_detail="template=latex",
        summary="Bottom-margin overflow, body text.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive -- this dissertation was written using LaTeX "
            "and the margins of the template are set up this way; she does not "
            "ask students to make this correction."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:right_margin",
        physical_page=48,
        structural_location="right_margin:body_text:initial_round",
        volatile_detail="template=word",
        summary="Right-margin overflow, body text.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive -- this dissertation was written in Word.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:bottom_margin",
        physical_page=19,
        structural_location="bottom_margin:body_text:initial_round",
        volatile_detail="template=latex",
        summary="Bottom-margin overflow, body text.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive -- this dissertation was written using LaTeX "
            "and the margins of the template are set up this way."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Philip",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:bottom_margin",
        physical_page=55,
        structural_location="bottom_margin:displayed_equation:initial_round",
        volatile_detail="template=latex",
        summary="Bottom-margin overflow, displayed-equation lines.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive -- this dissertation was written using LaTeX "
            "and the margins of the template are set up this way."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:right_margin",
        physical_page=56,
        structural_location="right_margin:methods_body_text:initial_round",
        volatile_detail="worst_overflow_pt=3.0",
        summary="Right-margin overflow, methods-section body text.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Sebastian",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:bottom_margin",
        physical_page=16,
        structural_location="bottom_margin:body_text:initial_round",
        volatile_detail="template=word",
        summary="Bottom-margin overflow, body text.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive -- this dissertation was written in Word.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Patrick",
        internal_rule_id="P011",
        issue_type="margin_boundary_violation:right_margin",
        physical_page=87,
        structural_location="right_margin:reference_entry:initial_round",
        volatile_detail="location=reference_list",
        summary="Right-margin overflow, reference-list entries.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R015/P015: follow-up round --------------------------------------------
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P015",
        issue_type="missing_later_indent",
        physical_page=101,
        structural_location="body_paragraph:run_in_bold_phrase:follow_up",
        volatile_detail="misread_paragraph_start=true",
        summary="Paragraph-start misread as a continuation line after a bold run-in phrase.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester clarified the actual paragraph begins with the preceding bold "
            "run-in phrase; the flagged line is ordinary continuation text."
        ),
        source_reference="docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md",
        decided_at="2026-08-31",
        anchor_x=108.4,
        anchor_y=376.1,
        structural_role="paragraph_continuation",
        locator_source_reference=(
            "docs/evaluation/ester_feedback/next_targeted_followup_after_r011_r015_20260825.md"
        ),
    ),
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P015",
        issue_type="missing_later_indent",
        physical_page=101,
        structural_location="body_paragraph:run_in_bold_phrase:paragraph_start:follow_up",
        volatile_detail="",
        summary="Later paragraph starts at a bold run-in phrase without its expected indent.",
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment=(
            "Ester confirmed that the missing-indent violation is at the bold "
            "run-in paragraph start above the previously flagged continuation line."
        ),
        source_reference="docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md",
        decided_at="2026-08-31",
        anchor_x=108.4,
        anchor_y=352.2,
        structural_role="paragraph_start",
        locator_source_reference="docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md",
    ),
    # -- R015/P015: initial round (different pages from the follow-up case) ----
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P015",
        issue_type="missing_later_indent",
        physical_page=86,
        structural_location="body_paragraph:near_page_center:initial_round",
        volatile_detail="",
        summary="Later paragraph appears to be missing expected first-line indentation.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P015",
        issue_type="unexpected_indent_on_continuation_line",
        physical_page=144,
        structural_location="body_paragraph:after_displayed_equation:initial_round",
        volatile_detail="",
        summary=(
            "Line continuing the previous sentence after a displayed equation "
            "has a paragraph-style indent."
        ),
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Philip",
        internal_rule_id="P015",
        issue_type="unexpected_indent_on_continuation_line",
        physical_page=17,
        structural_location="body_paragraph:after_displayed_equation:initial_round",
        volatile_detail="",
        summary=(
            "Line continuing the previous sentence after a displayed equation "
            "has a paragraph-style indent."
        ),
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R016/P016 ---------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P016",
        issue_type="excessive_paragraph_gap",
        physical_page=1,
        structural_location="page_1:paragraph_group_spacing",
        volatile_detail="",
        summary="Detected excessive blank space likely between paragraph groups.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P016",
        issue_type="excessive_paragraph_gap",
        physical_page=1,
        structural_location="page_1:paragraph_group_spacing",
        volatile_detail="",
        summary="Detected excessive blank space likely between paragraph groups.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P016",
        issue_type="excessive_line_gap",
        physical_page=1,
        structural_location="page_1:adjacent_line_spacing",
        volatile_detail="",
        summary="Detected excessive vertical spacing between adjacent text lines.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R017/P017 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P017",
        issue_type="missing_terminal_punctuation",
        physical_page=47,
        structural_location="figure_caption:near_page_center",
        volatile_detail="",
        summary="Figure caption appears to be missing terminal punctuation.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive -- the figure is not missing punctuation; the "
            "auditor appears to be looking only at the first line of the description."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P017",
        issue_type="missing_terminal_punctuation",
        physical_page=28,
        structural_location="figure_caption:near_page_center",
        volatile_detail="",
        summary="Figure caption appears to be missing terminal punctuation.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive -- same reasoning as Anthony's case.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Sebastian",
        internal_rule_id="P017",
        issue_type="missing_terminal_punctuation",
        physical_page=19,
        structural_location="figure_caption:near_page_center",
        volatile_detail="",
        summary="Figure caption appears to be missing terminal punctuation.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive -- same reasoning as Anthony's case.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R018/P018 (live sheet, checked directly, 2026-09-07) --------------------
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
    # -- R019/P019 (live sheet, checked directly, 2026-09-08) --------------------
    # Document-level finding (no physical page -- see pdf_page_numbers.py's
    # "mixed dominant style across document" check, which reports page=None
    # by design). All six reviewed cases are explicit "FALSE POSITIVE:" --
    # unambiguous per the migration's verdict-normalization rule A, not a
    # "CORRECT, but..." case needing NEEDS_CLARIFICATION treatment.
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (same policy guidance as Philip's R019 case: "
            "the auditor should treat the page with the literal 'CHAPTER 1' "
            "heading as Arabic page 1, and the 'Approval Page' as Roman iv, "
            "with sequential Roman numerals in between)."
        ),
        source_reference="docs/status/r019_ester_sheet_authority_20260908.md",
        decided_at="2026-09-08",
    ),
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (same policy guidance as Philip's R019 case)."
        ),
        source_reference="docs/status/r019_ester_sheet_authority_20260908.md",
        decided_at="2026-09-08",
    ),
    KnownHistoricalCase(
        document_short_name="Philip",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive. Policy guidance: can the auditor treat the "
            "page beginning with the literal 'CHAPTER 1' heading as Arabic page "
            "1, and the page beginning 'Approval Page' as Roman numeral iv, "
            "with Roman numerals applied sequentially in between and stopping "
            "once 'CHAPTER 1' appears at the top of a page?"
        ),
        source_reference="docs/status/r019_ester_sheet_authority_20260908.md",
        decided_at="2026-09-08",
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (same policy guidance as Philip's R019 case)."
        ),
        source_reference="docs/status/r019_ester_sheet_authority_20260908.md",
        decided_at="2026-09-08",
    ),
    KnownHistoricalCase(
        document_short_name="Sebastian",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (same policy guidance as Philip's R019 case)."
        ),
        source_reference="docs/status/r019_ester_sheet_authority_20260908.md",
        decided_at="2026-09-08",
    ),
    KnownHistoricalCase(
        document_short_name="Patrick",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        # Nuanced record like R028's Patrick case: Ester explicitly wrote
        # "FALSE POSITIVE:" here (unambiguous, unlike R028's "CORRECT: but"
        # phrasing), so this migrates as a plain FALSE_POSITIVE, not
        # NEEDS_CLARIFICATION. She additionally names the same underlying
        # defect as R028/R085: the missing literal "CHAPTER 1" heading. That
        # root cause is already migrated as Patrick's P085 TRUE_VIOLATION
        # case below; recorded here as context, not a second verdict.
        reviewer_comment=(
            'Ester: "FALSE POSITIVE: This case is a little different: There is '
            'an error on page 1: the student did not add the CHAPTER 1 header '
            'and instead wrote introduction." -- root cause is P085 (missing '
            "CHAPTER 1 heading), not P019; see Patrick's P085 case."
        ),
        source_reference="docs/status/r019_ester_sheet_authority_20260908.md",
        decided_at="2026-09-08",
    ),
    # -- R020/P020 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        physical_page=19,
        structural_location="title_like_text:near_page_center",
        volatile_detail="word=neutral",
        summary="Possible title capitalization issue: 'neutral' may need to be capitalized.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false -- this title is in sentence case and is fine as-is.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        physical_page=180,
        structural_location="title_like_text:top_of_page",
        volatile_detail="word=vs",
        summary="Possible title capitalization issue: 'vs' may need to be capitalized.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false -- 'vs' is a preposition and should be lowercase.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Philip",
        internal_rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        physical_page=3,
        structural_location="title_like_text:body_text",
        volatile_detail="word=and",
        summary="Possible title capitalization issue: 'and' may need to be capitalized.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- conjunctions (for, and, nor, but, or, yet, so), "
            "prepositions, and articles are always lowercase in titles."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P020",
        issue_type="possible_title_capitalization_issue",
        physical_page=20,
        structural_location="title_like_text:top_of_page",
        volatile_detail="word=need",
        summary="Possible title capitalization issue: 'need' may need to be capitalized.",
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment="Ester: correct.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R023/P023 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Youra",
        internal_rule_id="P023",
        issue_type="possible_body_text_not_double_spaced",
        physical_page=102,
        structural_location="body_text:figure_description",
        volatile_detail="",
        summary="Body text appears under-spaced (figure description region).",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- single space in the figure description, then a "
            "blank line, then double-spaced text is correct."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P023",
        issue_type="possible_body_text_not_double_spaced",
        physical_page=55,
        structural_location="body_text:figure_description",
        volatile_detail="",
        summary="Body text appears under-spaced (figure description region).",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- single space in the figure description, then a "
            "blank line, then double-spaced text is correct."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Muyeed",
        internal_rule_id="P023",
        issue_type="possible_body_text_not_double_spaced",
        physical_page=32,
        structural_location="body_text:bullet_list",
        volatile_detail="",
        summary="Body text appears under-spaced (bullet-list region).",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- bullet points are single-spaced within the bullet "
            "and maintain double spacing between them."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Philip",
        internal_rule_id="P023",
        issue_type="possible_body_text_not_double_spaced",
        physical_page=51,
        structural_location="body_text:bullet_list",
        volatile_detail="",
        summary="Body text appears under-spaced (bullet-list region).",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- bullet points are single-spaced within the bullet "
            "and maintain double spacing between them."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R024/P024 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P024",
        issue_type="list_of_figures_sentence_case:Neotropical",
        physical_page=14,
        structural_location="list_of_figures:parenthetical_proper_noun_list",
        volatile_detail="capitalized_terms=species_names",
        summary=(
            "Capitalized words in a parenthetical species-name list flagged as a "
            "sentence-case issue."
        ),
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- the capitalized words are proper nouns (names of "
            "snake species)."
        ),
        source_reference="docs/status/r018_r024_ester_sheet_authority_20260907.md",
        decided_at="2026-09-07",
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P024",
        issue_type="list_of_tables_title_case:casein",
        physical_page=14,
        structural_location="list_of_tables:hyphenated_fragment",
        volatile_detail="word=casein",
        summary=(
            "List of Tables entry may have title-case issue: 'casein' may need "
            "to be capitalized."
        ),
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- the word following a hyphen is not supposed to be "
            "capitalized in this construction (a non-Latin hyphenated prefix, "
            "e.g. a Greek letter, was dropped by PDF text extraction)."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R026/P026 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P026",
        issue_type="possible_body_font_size_issue",
        physical_page=35,
        structural_location="body_text:figure_source_credit",
        volatile_detail="",
        summary="Body text may not use the required 12pt font size.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false -- sources are in 10pt size under the figure description.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R027/P027 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P027",
        issue_type="level4_sentence_case_or_punctuation_issue",
        physical_page=69,
        structural_location="level4_heading:wrapped_across_lines",
        volatile_detail="",
        summary="Level 4 heading may be missing a required terminal period.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive -- the period is there, but the auditor does "
            "not recognize that this title ends on the second line."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R028/P028 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Philip",
        internal_rule_id="P028",
        issue_type="roman_number_on_body_page",
        physical_page=12,
        structural_location="page_footer:page_number_regime",
        volatile_detail="",
        summary="Page-number candidate does not match the expected regime for that region.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false positive.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Patrick",
        internal_rule_id="P028",
        issue_type="arabic_number_on_frontmatter_page",
        physical_page=13,
        structural_location="page_footer:page_number_regime",
        volatile_detail="",
        summary="Page-number candidate does not match the expected regime for that region.",
        # Nuanced record, not a simple TRUE_VIOLATION -- see module docstring
        # and docs/evaluation/ESTER_FEEDBACK_MIGRATION.md: Ester marked this
        # "CORRECT" but explained the real error is the missing literal
        # "CHAPTER 1" heading (the student forgot it), not the page number
        # itself. That is Patrick's R085 case, migrated separately as a
        # TRUE_VIOLATION and confirmed still detected. Forcing P028 itself to
        # keep reporting this would be wrong now that responsibility for the
        # actual defect sits with P085 -- recorded as NEEDS_CLARIFICATION so
        # it is preserved and visible without being scored as a P028 case.
        # Superseded by FALSE_POSITIVE in KNOWN_ADJUDICATION_SUPERSESSIONS
        # below (2026-10-06), from Ester's own explanation; this first
        # migrated verdict stays as history.
        verdict=AdjudicationVerdict.NEEDS_CLARIFICATION,
        reviewer_comment=(
            'Ester: "CORRECT: but we need to talk about this. the auditor has '
            "detected that this should not be page 1. Page one starts at "
            "CHAPTER 1: this is a case where the student forgot to add the "
            "title CHAPTER 1. The real error is not the page number but the "
            'absence of the header \\"CHAPTER 1\\"." -- root cause is R085, '
            "not R028; see Patrick's R085 case."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R030/P030 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P030",
        issue_type="missing_continued_heading",
        physical_page=11,
        structural_location="table_of_contents:continuation_page",
        volatile_detail="",
        summary="Multi-page TOC continuation page appears to be missing a continued heading.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment='Ester: false -- the "(Continued)" text is there.',
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P030",
        issue_type="missing_continued_heading",
        physical_page=12,
        structural_location="table_of_contents:continuation_page",
        volatile_detail="",
        summary="Multi-page TOC continuation page appears to be missing a continued heading.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="Ester: false -- same reasoning as Anthony's case.",
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R033/P033 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P033",
        issue_type="frontmatter_title_mismatch",
        physical_page=6,
        structural_location="frontmatter:title_consistency",
        volatile_detail="",
        summary="Dissertation title text may be inconsistent across front-matter pages.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false -- checked this student's Abstract, Title page, and "
            "Approval page; the title is consistent."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R035/P035 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P035",
        issue_type="table_body_not_centered",
        physical_page=60,
        structural_location="table:inferred_body_block",
        volatile_detail="",
        summary="Inferred table body block may not be centered within the text area.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (landscape/geometry context; live feedback "
            "sheet, page confirmed from the 2026-09-01 export)."
        ),
        source_reference="docs/status/r035_praneeth_text_fallback_fix_20260907.md",
        decided_at="2026-09-07",
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P035",
        issue_type="figure_body_not_centered",
        physical_page=29,
        structural_location="figure:inferred_body_block",
        volatile_detail="",
        summary="Inferred figure body block may not be centered within the text area.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: the figure is centered (live feedback sheet; page confirmed "
            "from the 2026-09-01 export -- consistent with this page no longer "
            "appearing among Praneeth's current P035 findings, see "
            "docs/status/r035_praneeth_text_fallback_fix_20260907.md)."
        ),
        source_reference="docs/status/r035_praneeth_text_fallback_fix_20260907.md",
        decided_at="2026-09-07",
    ),
    # Praneeth p72 is intentionally absent: it was an engineering-found
    # text-fallback geometry bug (fixed in 6facf49), never sent to Ester, and
    # has no reviewer verdict in the live R035 sheet -- see
    # docs/status/r035_praneeth_text_fallback_fix_20260907.md.
    # -- R036/P036 -----------------------------------------------------------------
    KnownHistoricalCase(
        document_short_name="Anthony",
        internal_rule_id="P036",
        issue_type="toc_inter_entry_spacing_too_tight",
        physical_page=12,
        structural_location="table_of_contents:entry_pair_spacing",
        volatile_detail="gap_ratio=1.08",
        summary="Consecutive TOC entries appear to have insufficient inter-entry vertical spacing.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (live feedback sheet, page and measured "
            "gap ratio confirmed)."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    KnownHistoricalCase(
        document_short_name="Praneeth",
        internal_rule_id="P036",
        issue_type="toc_inter_entry_spacing_too_tight",
        physical_page=11,
        structural_location="table_of_contents:entry_pair_spacing",
        volatile_detail="gap_ratio=1.19",
        summary="Consecutive TOC entries appear to have insufficient inter-entry vertical spacing.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Ester: false positive (live feedback sheet, page and measured "
            "gap ratio confirmed)."
        ),
        source_reference=_SHEET_EXPORT_REF,
        decided_at=_SHEET_EXPORT_DATE,
    ),
    # -- R085/P085 -----------------------------------------------------------------
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


@dataclass(frozen=True)
class KnownAdjudicationSupersession:
    """A later normalization of one ``KNOWN_HISTORICAL_CASES`` verdict.

    The original adjudication stays in the ledger; migration appends a new
    one that supersedes it (``Adjudication.supersedes_adjudication_id``).
    Only for verdicts that existing, cited authority already settles -- not
    for new reviewer input.
    """

    case: KnownHistoricalCase
    superseded_verdict: AdjudicationVerdict
    verdict: AdjudicationVerdict
    reviewer_comment: str
    source_reference: str
    decided_at: str


def _known_case(document: str, rule_id: str, issue_type: str, page: int) -> KnownHistoricalCase:
    matches = [
        c
        for c in KNOWN_HISTORICAL_CASES
        if (c.document_short_name, c.internal_rule_id, c.issue_type, c.physical_page)
        == (document, rule_id, issue_type, page)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one known case for {document}/{rule_id}/{issue_type}"
            f"@page{page}, found {len(matches)}"
        )
    return matches[0]


KNOWN_ADJUDICATION_SUPERSESSIONS: tuple[KnownAdjudicationSupersession, ...] = (
    # R028 Patrick physical page 13 (printed 1): first migrated as
    # NEEDS_CLARIFICATION because the sheet cell reads "CORRECT: but ...".
    # Ester's own explanation settles it: the page number is not the error,
    # the missing CHAPTER 1 heading is. Her R019 sheet entry for the same
    # page-1 situation is an explicit "FALSE POSITIVE:" with the same
    # explanation, and the 2026-09-02 status record treats it as resolved
    # policy. The missing heading stays Patrick's separate P085
    # TRUE_VIOLATION case.
    KnownAdjudicationSupersession(
        case=_known_case("Patrick", "P028", "arabic_number_on_frontmatter_page", 13),
        superseded_verdict=AdjudicationVerdict.NEEDS_CLARIFICATION,
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=(
            "Verdict normalized 2026-10-06 from Ester's existing comments; no new "
            "reviewer input. R028 sheet: the real error is not the page number but "
            "the absence of the CHAPTER 1 heading. R019 sheet (2026-09-08): the same "
            "page-1 situation marked FALSE POSITIVE with the same explanation. The "
            "page-number finding is not a violation; the missing CHAPTER 1 heading "
            "is Patrick's separate P085 TRUE_VIOLATION case."
        ),
        source_reference="docs/status/r028_patrick_ledger_resolution_20261006.md",
        decided_at="2026-09-08",
    ),
)
