"""Conservative inter-entry spacing checks for TOC/List pages (P036).

Partial heuristic PDF coverage for Q057, Q067, and Q077.

Ester's 2026-09-14 clarification is the authoritative policy this module
implements: "The TOC must be double spaced except for titles that run
longer than one line in which case these titles must be single spaced."
That is, spacing is a property of the relationship between two adjacent
*physical lines*, and it means something different depending on whether
those two lines belong to the same logical entry (a wrapped title's own
continuation -- expected single spaced) or to two different, consecutive
entries (expected double spaced). See
``docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md`` for the
forensic measurement (on the real Praneeth PDF) that this model is based
on: a genuinely double-spaced entry pair advances by *exactly* 2x the
page's own single-line pitch (baseline-to-baseline), never by 2x the
nominal font size -- the previous bbox-gap/font-size model conflated the
two and measured real double spacing at ~1.19x, below its own 1.4x
threshold, on effectively every double-spaced TOC in the corpus (not
merely on Praneeth), which was the actual root cause of all 12
Ester-reviewed false positives.
"""

from __future__ import annotations

import re
import statistics

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import _clean_text, detect_toc_like_pages
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import (
    _collect_entry_region_lines,
    _estimate_line_height,
    _has_intervening_page_number_line,
    _is_wrap_continuation_pair,
    _looks_like_new_entry_start_given_previous,
)
from njit_auditor.toc_list_student_preview import (
    gap_bbox_between_boxes,
    sanitize_toc_list_entry_preview,
)

# Required ratio of the inter-entry line PITCH (baseline-to-baseline, i.e.
# ``next_line.bbox.y0 - previous_line.bbox.y0``) to the page's own local
# single-line pitch. Genuine double spacing means the entry-to-entry pitch
# is ~2.0x the single-line pitch, by definition (double spacing doubles
# the line advance); genuine single/tight spacing measures ~1.0x-1.2x.
# 1.6 sits with a comfortable margin below the true-double value (2.0) and
# above the true-single value (~1.2) -- confirmed against the real, mixed
# corpus in docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md,
# where every genuinely double-spaced pair measured >= 1.9 and every
# genuinely single/tight pair measured <= 1.2 under this model, leaving a
# wide unused margin around 1.6. This is a ratio of pitch to pitch (a
# spacing-mode discriminator), not a ratio of points to font size, so it
# is expected to generalize across fonts/documents where the old
# font-size-normalized threshold did not.
MIN_INTER_ENTRY_GAP_RATIO = 1.6

# Only used as a fallback when a page has no same-entry wrapped-title line
# pairs to locally calibrate a single-line pitch from (see
# ``_local_single_line_pitch_pt``). 1.15 is a standard single-line-spacing
# leading factor relative to nominal font size; it is not load-bearing for
# any page that has at least one multi-line entry, which is the common
# case for TOC pages long enough to trigger this rule at all.
SINGLE_LINE_PITCH_FALLBACK_MULTIPLIER = 1.15
FALLBACK_LINE_HEIGHT_PT = 12.0

ISSUE_TYPE_BY_SECTION = {
    "table_of_contents": "toc_inter_entry_spacing_too_tight",
    "list_of_tables": "lot_inter_entry_spacing_too_tight",
    "list_of_figures": "lof_inter_entry_spacing_too_tight",
}

SOURCE_Q_RULE_IDS_BY_SECTION = {
    "table_of_contents": "Q057",
    "list_of_tables": "Q067",
    "list_of_figures": "Q077",
}


def _is_entry_boundary(
    previous: PdfTextLine,
    line: PdfTextLine,
    page_type: str,
) -> bool:
    """Return True when *line* begins a new logical TOC/List entry.

    ``_is_wrap_continuation_pair`` is tuned for P032's conservative "only
    check a gap when we are SURE these two lines are the same wrapped
    entry" purpose -- a False return there is a safe default to skip
    checking, not proof the two lines belong to different entries. Treating
    that negation directly as an entry boundary over-splits any entry whose
    wrapped continuation uses a hanging indent (continuation lines indented
    under the entry text rather than under its leading number), which is
    common in this corpus and shifts x0 by more than
    ``INDENT_CLUSTER_TOLERANCE_PT``. That over-split then makes each
    entry's own internal single-line-height wrap gap look like an
    unusually tight gap BETWEEN two entries. Require positive evidence of a
    new entry start instead (numbered "N.N"/Chapter/Appendix line, or a
    dot-leader entry line) so only genuinely separate entries are split.
    """
    if _is_wrap_continuation_pair(previous, line, page_type):
        return False
    return _looks_like_new_entry_start_given_previous(previous, _clean_text(line.text))


def _group_lines_into_entries(
    lines: list[PdfTextLine],
    page_type: str,
) -> list[list[PdfTextLine]]:
    if not lines:
        return []

    entries: list[list[PdfTextLine]] = [[lines[0]]]
    for line in lines[1:]:
        previous = entries[-1][-1]
        if _is_entry_boundary(previous, line, page_type):
            entries.append([line])
            continue
        entries[-1].append(line)
    return entries


def _classify_entry_level(text: str, page_type: str) -> str:
    """Classify the hierarchical level/kind of a TOC/List entry line."""
    cleaned = _clean_text(text)
    if page_type == "list_of_tables":
        return "table_entry"
    if page_type == "list_of_figures":
        return "figure_entry"

    normalized = cleaned.upper()
    if normalized.startswith("CHAPTER") or normalized.startswith("APPENDIX"):
        return "toc_level_1"
    if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+", cleaned):
        return "toc_level_3"
    if re.match(r"^[0-9]+\.[0-9]+", cleaned):
        return "toc_level_2"
    if re.match(r"^[0-9]+\s", cleaned):
        return "toc_level_1"
    if re.match(r"^[IVXLCDM]+\s", cleaned):
        return "toc_level_1"

    words = [w for w in re.split(r"[.\s\d]+", normalized) if w]
    if words:
        first_word = words[0]
        if first_word in ("REFERENCES", "BIBLIOGRAPHY", "VITA", "GLOSSARY", "INDEX"):
            return "toc_level_1"

    return "unknown"


_TOC_LEVEL_DEPTH = {"toc_level_1": 1, "toc_level_2": 2, "toc_level_3": 3}


def _is_exempt_structural_transition(prev_level: str, next_level: str) -> bool:
    """Return True for a transition exempt from tight-spacing detection
    because it borders a structural row (a chapter/appendix/top-level
    heading), not an ordinary peer-to-peer entry gap.

    Two exempt shapes, both confirmed against real Ester-reviewed cases
    (see docs/evaluation/ESTER_FEEDBACK_MIGRATION.md, P036/Anthony p12 and
    the R036 email/sheet policy: "the relevant spacing transitions
    involve structural rows such as chapter or appendix headings, and the
    auditor should allow appropriate flexibility rather than treating
    them like ordinary peer entries"):

    1. *prev* is a heading (or any entry) immediately followed by its own
       first, more deeply nested child entry (``prev_depth < next_depth``)
       -- a parent-to-first-child transition.
    2. *next* is itself a top-level structural row (``toc_level_1`` --
       CHAPTER/APPENDIX/REFERENCES/etc., see ``_classify_entry_level``)
       and *prev* is at a strictly deeper level -- finishing a nested
       subsection and entering a new top-level section (e.g. "3.5
       Conclusion" -> "APPENDIX", the reviewed Anthony p12 case: a
       level-2 entry finishing right before an APPENDIX heading). A
       top-level-to-top-level peer pair (e.g. "Chapter 3" -> "Chapter 4")
       is deliberately NOT covered by this shape -- ``prev_level`` must
       differ from ``toc_level_1``, or two chapter headings back-to-back
       would wrongly become exempt as "ordinary peer entries", which is
       exactly what Ester's policy says should stay checked.

    A same-depth peer pair (e.g. "1.1" -> "1.2") or a pair that merely
    finishes a nested subsection and returns to an ordinary (non-level-1)
    peer (e.g. "1.2.3" -> "1.3") is deliberately NOT exempted by shape 2 --
    only entering a genuine top-level structural row is. Broadening this
    further without further reviewed evidence would risk silently
    suppressing genuine spacing defects across the corpus. Pairs
    involving an unclassifiable ("unknown") entry are never exempt.
    """
    if next_level == "toc_level_1" and prev_level != "toc_level_1":
        return True
    prev_depth = _TOC_LEVEL_DEPTH.get(prev_level)
    next_depth = _TOC_LEVEL_DEPTH.get(next_level)
    if prev_depth is None or next_depth is None:
        return False
    return prev_depth < next_depth


# Ratio boundary (of the same pitch/pitch measure as MIN_INTER_ENTRY_GAP_RATIO)
# below which an under-spaced pair is triaged "high" rather than "medium": a
# ratio at or below this is close to the ~1.0-1.2x single-line-pitch range,
# i.e. no meaningfully extra spacing was added between entries at all.
HIGH_TRIAGE_RATIO_CEILING = 1.3


def _triage_tier(gap_ratio: float) -> str:
    if gap_ratio < HIGH_TRIAGE_RATIO_CEILING:
        return "high"
    if gap_ratio < MIN_INTER_ENTRY_GAP_RATIO:
        return "medium"
    return "low"


def _internal_wrap_pitches_by_role(
    entries: list[list[PdfTextLine]], page_type: str
) -> tuple[list[float], list[float]]:
    """Bucket every wrapped-title's own internal (same-entry, consecutive-
    physical-line) baseline-to-baseline pitch into ``(heading_pitches,
    entry_pitches)``, split by the structural role of the entry it came
    from (a top-level ``toc_level_1`` heading such as "3 ULTRAFAST
    MICRODROPLET DIGESTION..." vs an ordinary numbered sub-entry).

    A page can legitimately use a different single-line pitch for its
    top-level headings than for its ordinary entries even at the *same*
    font size (confirmed on the real Praneeth PDF, page 12: both measure
    12pt, but a wrapped chapter heading's own two physical lines advance
    by 20.6pt while an ordinary wrapped sub-entry advances by 13.8pt --
    see docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md).
    A single page-wide pitch blindly mixes these two populations and can
    land on the wrong one depending on which happens to have more
    same-page samples. Splitting by role and picking the bucket matching
    the specific transition being checked (see
    ``_local_single_line_pitch_pt``) avoids that.
    """
    heading_pitches: list[float] = []
    entry_pitches: list[float] = []
    for entry in entries:
        if len(entry) < 2:
            continue
        level = _classify_entry_level(entry[0].text, page_type)
        bucket = heading_pitches if level == "toc_level_1" else entry_pitches
        for first, second in zip(entry, entry[1:]):
            pitch = second.bbox.y0 - first.bbox.y0
            if pitch > 0:
                bucket.append(pitch)
    return heading_pitches, entry_pitches


def _local_single_line_pitch_pt(
    prev_level: str,
    heading_pitches: list[float],
    entry_pitches: list[float],
    fallback_line_height: float,
) -> float:
    """Return the single-line pitch to compare an inter-entry gap against:
    the median same-role internal wrap pitch (preferring the bucket
    matching *prev_level*, i.e. the entry the gap is measured FROM), else
    the other role's bucket, else a font-size-based fallback when the page
    has no multi-line entries to calibrate from at all.
    """
    preferred, other = (
        (heading_pitches, entry_pitches)
        if prev_level == "toc_level_1"
        else (entry_pitches, heading_pitches)
    )
    for bucket in (preferred, other):
        if bucket:
            return statistics.median(bucket)
    return fallback_line_height * SINGLE_LINE_PITCH_FALLBACK_MULTIPLIER


def check_pdf_toc_list_entry_spacing(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P036 warnings when consecutive TOC/List entries appear too tightly spaced."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        lines = _collect_entry_region_lines(context)
        entries = _group_lines_into_entries(lines, context.page_type)
        if len(entries) < 2:
            continue

        issue_type = ISSUE_TYPE_BY_SECTION.get(context.page_type)
        if issue_type is None:
            continue

        page_fallback_height = _estimate_line_height(lines[0], lines[0]) or FALLBACK_LINE_HEIGHT_PT
        heading_pitches, entry_pitches = _internal_wrap_pitches_by_role(entries, context.page_type)

        for pair_index, (previous_entry, next_entry) in enumerate(zip(entries, entries[1:])):
            last_line = previous_entry[-1]
            first_line = next_entry[0]
            if _has_intervening_page_number_line(context, last_line, first_line):
                continue

            prev_level = _classify_entry_level(previous_entry[0].text, context.page_type)
            next_level = _classify_entry_level(next_entry[0].text, context.page_type)
            if _is_exempt_structural_transition(prev_level, next_level):
                continue

            pitch_pt = first_line.bbox.y0 - last_line.bbox.y0
            if pitch_pt <= 0:
                continue

            local_single_line_pitch = _local_single_line_pitch_pt(
                prev_level, heading_pitches, entry_pitches, page_fallback_height
            )
            if local_single_line_pitch <= 0:
                continue

            gap_ratio = pitch_pt / local_single_line_pitch
            if gap_ratio >= MIN_INTER_ENTRY_GAP_RATIO:
                continue

            required_gap_pt = local_single_line_pitch * MIN_INTER_ENTRY_GAP_RATIO
            triage_tier = _triage_tier(gap_ratio)

            previous_preview = sanitize_toc_list_entry_preview(last_line.text)
            next_preview = sanitize_toc_list_entry_preview(first_line.text)
            gap_bbox = gap_bbox_between_boxes(last_line.bbox, first_line.bbox)
            details: dict[str, str] = {
                "page_number": str(context.page.page_number),
                "section_type": context.page_type,
                "issue_type": issue_type,
                "entry_pair_index": str(pair_index),
                "gap_points": f"{pitch_pt:.1f}",
                "required_gap_points": f"{required_gap_pt:.1f}",
                "local_single_line_pitch_points": f"{local_single_line_pitch:.1f}",
                "gap_ratio": f"{gap_ratio:.2f}",
                "triage_tier": triage_tier,
                "source_q_rule_ids": SOURCE_Q_RULE_IDS_BY_SECTION[context.page_type],
            }
            if previous_preview:
                details["previous_entry_preview"] = previous_preview
            if next_preview:
                details["next_entry_preview"] = next_preview
            if gap_bbox is not None:
                details["bbox"] = format_bbox_detail(gap_bbox)

            findings.append(
                AuditFinding(
                    rule_id="P036",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "Consecutive TOC/List entries appear to have insufficient "
                        "inter-entry vertical spacing."
                    ),
                    details=details,
                )
            )

    return findings
