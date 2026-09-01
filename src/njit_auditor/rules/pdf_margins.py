"""Heuristic margin checks for layout-aware PDF text lines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p011_margin_presentation import (
    infer_margin_content_kind,
    infer_page_margin_context,
    margin_suggested_fix,
)
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, _is_top_or_bottom_zone

INCH_TO_PT = 72.0
LEFT_MARGIN_PT = 1.5 * INCH_TO_PT
RIGHT_MARGIN_PT = 1.0 * INCH_TO_PT
TOP_MARGIN_PT = 1.0 * INCH_TO_PT
BOTTOM_MARGIN_PT = 1.0 * INCH_TO_PT
MIN_ARTIFACT_SIZE_PT = 2.0
OVERFLOW_TOLERANCE_PT = 3.0
# Numeric-stability guard only: PDF/PyMuPDF coordinates can land a few
# thousandths of a point above the nominal tolerance (e.g. 3.00006pt) while the
# displayed overflow rounds to 3.0pt and the rendered ink remains in-bounds.
# This does not widen NJIT policy tolerance; it makes the existing 3.0pt cutoff
# behave consistently at floating-point precision boundaries.
OVERFLOW_TOLERANCE_EPSILON_PT = 0.01

# Bottom-margin-specific overflow tolerance (replaces OVERFLOW_TOLERANCE_PT for
# the bottom side only). A fully justified body line that lands last on an
# otherwise full page routinely has its own descent/leading dip a few extra
# points past the nominal 1-inch line -- normal single-line typographic slack,
# not content placed outside the margin. Esther originally confirmed four
# such single/short-line bottom-margin findings -- both Word and LaTeX source
# PDFs, both prose and equation lines -- as false positives at 3.9-8.2pt
# overflow, and the tolerance was set just above that (9.0pt), deliberately
# stopping short of a recurring ~9.2pt footer-zone cluster that a prior audit
# (docs/status/p011_precision_false_negative_audit_20260710.md, S7
# "Uncertain cases") flagged as an open policy question.
#
# Esther has since reviewed that cluster directly (Muyeed physical PDF page
# 36, "clustering algorithm.", MEDIUM confidence, measured 9.17pt raw / 9.2pt
# displayed overflow) via the R011-R015 follow-up sheet and confirmed it is
# NOT a violation -- see
# docs/evaluation/ester_feedback/next_targeted_followup_after_r011_r015_20260825.md.
# Re-auditing the full 8-12pt bottom-margin population across all seven
# private evaluation dissertations (see
# docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md) shows
# this is not an isolated point: raw overflow of ~9.17pt recurs 47 times
# across two independent LaTeX-source dissertations (Muyeed, Philip) on
# prose, equations, table-of-contents dot-leaders, and reference URLs alike
# -- a content-independent geometric constant, not a real placement issue --
# and the population immediately above it (raw 9.05-9.29pt) is followed by a
# clean, empty gap (no findings from 9.30-9.43pt raw) before the next,
# unconfirmed cluster begins (~9.5pt+). The tolerance is raised only enough
# to clear that confirmed cluster and its immediate neighbors up to the
# natural gap, not the next cluster: it remains a narrow, evidence-anchored
# band, not a blanket bottom-margin relaxation. Bottom-margin overflow at or
# beyond ~9.5pt (e.g. Sample A pages 82-83, 9.8-11.0pt) is unaffected and
# still reported.
BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT = 9.3

# Extra right/left-margin overflow tolerance for reference-list entries only
# (added on top of OVERFLOW_TOLERANCE_PT). Bibliography/reference entries
# often contain an unbreakable long citation title, DOI, or foreign-language
# phrase that cannot wrap without altering the citation; Esther confirmed a
# references-list right-margin finding (~6.9pt) as a false positive for
# exactly this reason. Bounded rather than unlimited so a genuinely oversized
# reference-block margin problem -- e.g. the ~24pt hanging-indent left-margin
# violations covered by
# test_numbered_reference_left_margin_overflow_stays_high_confidence_with_correct_wording --
# still gets flagged.
REFERENCES_MARGIN_EXTRA_TOLERANCE_PT = 6.0

# Standard space-glyph advance width as a fraction of font size (~0.25em is a
# near-universal convention across text fonts), used only to correct a
# text-extraction artifact -- see _content_right_edge below.
_SPACE_ADVANCE_EM_FRACTION = 0.25

# Artifact guard: a page/side group with this many lines all below this overflow
# is likely caused by a compressed-PDF coordinate shift rather than a real margin violation.
ARTIFACT_GUARD_MIN_COUNT = 5
ARTIFACT_GUARD_MAX_OVERFLOW_PT = 8.0

# Half-thickness of the drawn margin-boundary guide rectangle. Presentation-only:
# does not affect detection, thresholds, or confidence -- purely how wide the
# guide line is once rendered in the highlighted PDF.
MARGIN_GUIDE_HALF_THICKNESS_PT = 1.5

# Presentation-only minimum width/height for visible overflow aids. Thin actual
# overflow slices are widened only for display, while the raw overflow segment
# geometry stays unchanged in the serialized finding details.
MIN_VISIBLE_OVERFLOW_DIMENSION_PT = 4.0

# Two violating lines on the same side are grouped into one tight highlight
# region only when no other line (violating or not) separates them in the
# page's top-to-bottom reading order. This is presentation-only: it decides
# how many highlight boxes are drawn for an already-decided finding, never
# whether a violation is flagged.
_ADJACENT_LINE_INDEX_GAP = 1


class MarginSide(str, Enum):
    LEFT = "left_margin"
    RIGHT = "right_margin"
    TOP = "top_margin"
    BOTTOM = "bottom_margin"


@dataclass
class LineViolation:
    side: MarginSide
    overflow_pt: float
    line: PdfTextLine
    line_index: int


def _page_text(page: PdfPage) -> str:
    return " ".join(block.text for block in page.text_blocks)


def _margin_side_label_for_fix(side: MarginSide) -> str:
    labels = {
        MarginSide.LEFT: "left margin",
        MarginSide.RIGHT: "right margin",
        MarginSide.TOP: "top margin",
        MarginSide.BOTTOM: "bottom margin",
    }
    return labels.get(side, "required page margin")


def _likely_page_number_text(text: str, y0: float, y1: float, page_height: float) -> bool:
    return _is_top_or_bottom_zone(y0, y1, page_height) and bool(PAGE_NUM_RE.match(text.strip()))


def _content_right_edge(line: PdfTextLine) -> float:
    """Return the line's right edge with a trailing whitespace glyph trimmed off.

    PyMuPDF's line bbox is the union of its spans' boxes, and a span's box
    extends to the full advance width of its last character -- including a
    trailing space that fully justified text commonly ends a line with. That
    space carries no visible ink, so leaving it in inflates the measured right
    edge by roughly one space-glyph width (~0.25em) with nothing actually
    crossing the margin. This walks spans from the end, skipping any that are
    pure whitespace, and trims the trailing whitespace characters off the last
    span that has real content -- so it only ever narrows the measured edge,
    never widens it.
    """
    for span in reversed(line.spans):
        if not span.text.strip():
            continue
        stripped = span.text.rstrip(" \t")
        trailing_ws = len(span.text) - len(stripped)
        if trailing_ws and span.size:
            return span.bbox.x1 - trailing_ws * span.size * _SPACE_ADVANCE_EM_FRACTION
        return span.bbox.x1
    return line.bbox.x1


def _line_violation(
    line: PdfTextLine,
    page_height: float,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
    line_index: int,
) -> LineViolation | None:
    text = line.text.strip()
    if not text:
        return None
    bbox: BBox = line.bbox
    if bbox.width < MIN_ARTIFACT_SIZE_PT or bbox.height < MIN_ARTIFACT_SIZE_PT:
        return None
    if _likely_page_number_text(text, bbox.y0, bbox.y1, page_height):
        return None

    content_x1 = min(bbox.x1, _content_right_edge(line))

    overflow_by_side: dict[MarginSide, float] = {}
    if bbox.x0 < allowed_x0:
        raw = allowed_x0 - bbox.x0
        if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.LEFT] = raw
    if content_x1 > allowed_x1:
        raw = content_x1 - allowed_x1
        if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.RIGHT] = raw
    if bbox.y0 < allowed_y0:
        raw = allowed_y0 - bbox.y0
        if raw > OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.TOP] = raw
    if bbox.y1 > allowed_y1:
        raw = bbox.y1 - allowed_y1
        if raw > BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT + OVERFLOW_TOLERANCE_EPSILON_PT:
            overflow_by_side[MarginSide.BOTTOM] = raw

    if not overflow_by_side:
        return None
    side, overflow = max(overflow_by_side.items(), key=lambda item: item[1])
    return LineViolation(side=side, overflow_pt=overflow, line=line, line_index=line_index)


def _group_confidence(worst_overflow_pt: float, count: int) -> str:
    large_count_ok = (
        count >= ARTIFACT_GUARD_MIN_COUNT and worst_overflow_pt >= ARTIFACT_GUARD_MAX_OVERFLOW_PT
    )
    if worst_overflow_pt >= 12.0 or large_count_ok:
        return "high"
    if worst_overflow_pt >= 5.0 or count >= 2:
        return "medium"
    return "low"


def _union_bbox_of(violations: list[LineViolation]) -> BBox:
    return BBox(
        x0=min(v.line.bbox.x0 for v in violations),
        y0=min(v.line.bbox.y0 for v in violations),
        x1=max(v.line.bbox.x1 for v in violations),
        y1=max(v.line.bbox.y1 for v in violations),
    )


def _group_adjacent_violations(violations: list[LineViolation]) -> list[list[LineViolation]]:
    """Split same-side violations into tight groups with no line between them.

    Presentation-only: groups violating lines for highlight geometry so a
    highlighted PDF shows tight boxes around each cluster of affected lines
    instead of one region spanning unrelated content between separated
    violations. Two violations land in the same group only when their
    position in the page's top-to-bottom line order is consecutive (no other
    line -- violating or not -- separates them); this never changes which
    lines are flagged, only how many highlight boxes are drawn for them.
    """
    ordered = sorted(violations, key=lambda v: v.line_index)
    groups: list[list[LineViolation]] = []
    for violation in ordered:
        if groups and violation.line_index - groups[-1][-1].line_index <= _ADJACENT_LINE_INDEX_GAP:
            groups[-1].append(violation)
        else:
            groups.append([violation])
    return groups


def _margin_boundary_guide_bbox(
    side: MarginSide,
    violations: list[LineViolation],
    *,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> BBox:
    """Return a thin rectangle marking the required margin boundary line.

    Spans only the vertical (for left/right) or horizontal (for top/bottom)
    extent of the affected lines, not the full page, so the guide stays
    contextual to the violation instead of drawing a page-length line.
    """
    thickness = MARGIN_GUIDE_HALF_THICKNESS_PT
    if side in (MarginSide.LEFT, MarginSide.RIGHT):
        y0 = min(v.line.bbox.y0 for v in violations)
        y1 = max(v.line.bbox.y1 for v in violations)
        boundary_x = allowed_x0 if side is MarginSide.LEFT else allowed_x1
        return BBox(x0=boundary_x - thickness, y0=y0, x1=boundary_x + thickness, y1=y1)
    x0 = min(v.line.bbox.x0 for v in violations)
    x1 = max(v.line.bbox.x1 for v in violations)
    boundary_y = allowed_y0 if side is MarginSide.TOP else allowed_y1
    return BBox(x0=x0, y0=boundary_y - thickness, x1=x1, y1=boundary_y + thickness)


def _overflow_segment_bbox(
    side: MarginSide,
    group: list[LineViolation],
    *,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> BBox:
    """Return the sub-rectangle of *group*'s union box that actually crosses
    the margin boundary -- presentation-only geometry derived from the same
    line boxes and boundary already used for detection, never a new measure
    of overflow. Used to render the crossing segment distinctly from the
    rest of the (in-bounds) line in the highlighted PDF.
    """
    full = _union_bbox_of(group)
    if side is MarginSide.RIGHT:
        return BBox(x0=max(full.x0, allowed_x1), y0=full.y0, x1=full.x1, y1=full.y1)
    if side is MarginSide.LEFT:
        return BBox(x0=full.x0, y0=full.y0, x1=min(full.x1, allowed_x0), y1=full.y1)
    if side is MarginSide.BOTTOM:
        return BBox(x0=full.x0, y0=max(full.y0, allowed_y1), x1=full.x1, y1=full.y1)
    return BBox(x0=full.x0, y0=full.y0, x1=full.x1, y1=min(full.y1, allowed_y0))


def _overflow_display_bbox(
    side: MarginSide,
    group: list[LineViolation],
    *,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> BBox:
    """Return a display-friendly version of the overflow slice.

    The underlying overflow segment geometry remains exact; this helper only
    widens very thin slices enough to stay visible in the highlighted PDF.
    """
    segment = _overflow_segment_bbox(
        side,
        group,
        allowed_x0=allowed_x0,
        allowed_y0=allowed_y0,
        allowed_x1=allowed_x1,
        allowed_y1=allowed_y1,
    )
    full = _union_bbox_of(group)
    if side in (MarginSide.LEFT, MarginSide.RIGHT):
        width = segment.width
        if width >= MIN_VISIBLE_OVERFLOW_DIMENSION_PT:
            return segment
        target = min(MIN_VISIBLE_OVERFLOW_DIMENSION_PT, full.width)
        center = (segment.x0 + segment.x1) / 2
        x0 = max(full.x0, center - target / 2)
        x1 = min(full.x1, x0 + target)
        if x1 - x0 < target:
            x0 = max(full.x0, x1 - target)
        return BBox(x0=x0, y0=segment.y0, x1=x1, y1=segment.y1)
    height = segment.height
    if height >= MIN_VISIBLE_OVERFLOW_DIMENSION_PT:
        return segment
    target = min(MIN_VISIBLE_OVERFLOW_DIMENSION_PT, full.height)
    center = (segment.y0 + segment.y1) / 2
    y0 = max(full.y0, center - target / 2)
    y1 = min(full.y1, y0 + target)
    if y1 - y0 < target:
        y0 = max(full.y0, y1 - target)
    return BBox(x0=segment.x0, y0=y0, x1=segment.x1, y1=y1)


def run_pdf_margin_rule(
    pdf_doc: PdfDocument,
    *,
    skip_pages: set[int] | None = None,
) -> list[AuditFinding]:
    """Detect possible text lines outside expected margin rectangle."""

    findings: list[AuditFinding] = []
    skipped = skip_pages or set()
    for page in pdf_doc.pages:
        if page.page_number in skipped:
            continue
        allowed_x0 = LEFT_MARGIN_PT
        allowed_y0 = TOP_MARGIN_PT
        allowed_x1 = page.width - RIGHT_MARGIN_PT
        allowed_y1 = page.height - BOTTOM_MARGIN_PT

        grouped: dict[MarginSide, list[LineViolation]] = {}
        line_index = 0
        for block in page.text_blocks:
            for line in block.lines:
                violation = _line_violation(
                    line, page.height, allowed_x0, allowed_y0, allowed_x1, allowed_y1, line_index
                )
                line_index += 1
                if not violation:
                    continue
                grouped.setdefault(violation.side, []).append(violation)

        for side, violations in grouped.items():
            worst_violation = max(violations, key=lambda v: v.overflow_pt)
            worst = worst_violation.overflow_pt
            count = len(violations)
            # Suppress groups where many lines all barely cross the margin: this pattern
            # indicates a compressed-PDF coordinate shift, not a real margin violation.
            if count >= ARTIFACT_GUARD_MIN_COUNT and worst < ARTIFACT_GUARD_MAX_OVERFLOW_PT:
                continue

            # Collect truncated text previews of all violating lines for student-facing
            # wording, and classify the page/content up front: both the references
            # exception right below and the finding's remediation wording later need
            # the same classification, computed once from the same evidence.
            _MAX_PREVIEW_LEN = 60
            _MAX_PREVIEW_LINES = 5
            line_previews: list[str] = []
            for v in violations[:_MAX_PREVIEW_LINES]:
                txt = v.line.text.strip()
                if txt:
                    line_previews.append(
                        (txt[:_MAX_PREVIEW_LEN] + "…") if len(txt) > _MAX_PREVIEW_LEN else txt
                    )
            page_context = infer_page_margin_context(_page_text(page), line_previews)
            content_kind = infer_margin_content_kind(page_context, line_previews)

            # Reference-list entries often contain an unbreakable long citation
            # title, DOI, or foreign-language phrase that cannot wrap without
            # altering the citation; Esther confirmed a references-list
            # right-margin finding as a false positive for exactly this reason.
            # Bounded (not unlimited) so a genuinely oversized reference-block
            # margin problem -- e.g. the much larger hanging-indent left-margin
            # violations -- still gets flagged.
            if (
                side in (MarginSide.LEFT, MarginSide.RIGHT)
                and content_kind == "references_hanging_indent"
                and worst
                <= OVERFLOW_TOLERANCE_PT
                + REFERENCES_MARGIN_EXTRA_TOLERANCE_PT
                + OVERFLOW_TOLERANCE_EPSILON_PT
            ):
                continue

            confidence = _group_confidence(worst, count)
            # A "low" confidence group is, by construction, a single line whose
            # measured overflow is under the 5pt medium-confidence floor -- text
            # extraction/font-metric rounding noise rather than a real margin
            # violation. Ester's Sample B review confirmed exactly this pattern
            # (single-line, sub-5pt right-margin "overflow") as false positives
            # on several pages while every reviewed medium/high-confidence
            # finding was a real violation. See
            # docs/status/ester_sample_b_p011_margin_low_overflow.md.
            if confidence == "low":
                continue

            # `bbox` stays the union of every violating line's box, unchanged, for
            # backward compatibility with any consumer reading a single box (e.g.
            # the has_highlight availability check). It does not add a new box
            # concept on its own (see docs/status/highlight_quality_improvement_plan.md)
            # and every other field below (worst_overflow_pt, affected_line_count,
            # confidence, side) still reflects the single worst offender exactly
            # as before.
            highlight_bbox = _union_bbox_of(violations)

            # Precise per-region highlight boxes: violating lines are grouped so
            # that only lines with nothing (violating or not) between them share
            # one tight box, instead of one region spanning unrelated content
            # between separated violations.
            adjacent_groups = _group_adjacent_violations(violations)
            highlight_bboxes = [_union_bbox_of(group) for group in adjacent_groups]

            # For each same group, the sub-rectangle that actually crosses the
            # margin boundary -- lets the highlighted PDF draw the crossing
            # segment more strongly than the rest of the (in-bounds) line,
            # instead of highlighting the whole line uniformly.
            overflow_segment_bboxes = [
                _overflow_segment_bbox(
                    side,
                    group,
                    allowed_x0=allowed_x0,
                    allowed_y0=allowed_y0,
                    allowed_x1=allowed_x1,
                    allowed_y1=allowed_y1,
                )
                for group in adjacent_groups
            ]
            overflow_display_bboxes = [
                _overflow_display_bbox(
                    side,
                    group,
                    allowed_x0=allowed_x0,
                    allowed_y0=allowed_y0,
                    allowed_x1=allowed_x1,
                    allowed_y1=allowed_y1,
                )
                for group in adjacent_groups
            ]

            # A thin guide rectangle marking the exact required margin boundary
            # line the content must not cross, scoped to the affected region's
            # extent rather than spanning the full page.
            margin_boundary_bbox = _margin_boundary_guide_bbox(
                side,
                violations,
                allowed_x0=allowed_x0,
                allowed_y0=allowed_y0,
                allowed_x1=allowed_x1,
                allowed_y1=allowed_y1,
            )

            # Tiny, single-line overflows are more likely measurement noise (font
            # metric rounding, a stray descender) than a real violation. This is
            # already reflected in `confidence` ("low"); `triage_tier` stays a
            # constant "informational" for all P011 findings because it is part
            # of build_grouped_findings()'s grouping key (report_outputs.py) —
            # varying it by confidence would split identical margin problems
            # across separate cards purely because occurrences differed in
            # measured overflow.
            finding_details: dict[str, str] = {
                "side": side.value,
                "issue_type": "margin_boundary_violation",
                "worst_overflow_pt": f"{worst:.1f}",
                "affected_line_count": str(count),
                "confidence": confidence,
                "triage_tier": "informational",
                "bbox": format_bbox_detail(highlight_bbox),
                "highlight_bboxes": " | ".join(
                    format_bbox_detail(box) for box in highlight_bboxes
                ),
                "overflow_display_bboxes": " | ".join(
                    format_bbox_detail(box) for box in overflow_display_bboxes
                ),
                "overflow_segment_bboxes": " | ".join(
                    format_bbox_detail(box) for box in overflow_segment_bboxes
                ),
                "margin_boundary_bbox": format_bbox_detail(margin_boundary_bbox),
            }
            if line_previews:
                finding_details["affected_line_texts"] = " | ".join(line_previews)

            finding_details["page_context"] = page_context
            finding_details["margin_content_kind"] = content_kind
            finding_details["suggested_fix"] = margin_suggested_fix(
                page_context=page_context,
                content_kind=content_kind,
                side_label=_margin_side_label_for_fix(side),
            )

            findings.append(
                AuditFinding(
                    rule_id="P011",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        f"Possible text crossing {side.value} by approximately "
                        f"{worst:.1f} pt."
                    ),
                    details=finding_details,
                )
            )

    if findings:
        return findings
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.PASS,
            message="No obvious margin-boundary text violations detected.",
        )
    ]
