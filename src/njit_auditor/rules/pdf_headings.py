"""Heuristic named front-matter heading checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT

INCH_TO_PT = 72.0
TOP_ZONE_PT = 2.0 * INCH_TO_PT
# Heading centering tolerances (points from text-area center).
CENTER_SUPPRESS_THRESHOLD_PT = 6.0
CENTER_REVIEW_MAX_THRESHOLD_PT = 12.0
CENTER_MEDIUM_MAX_THRESHOLD_PT = 36.0
# Legacy aliases kept for tests/docs that referenced the old pass window.
CENTER_TOLERANCE_PT = CENTER_SUPPRESS_THRESHOLD_PT
BORDERLINE_CENTER_TOLERANCE_PT = CENTER_REVIEW_MAX_THRESHOLD_PT

EXPECTED_HEADINGS: tuple[str, ...] = (
    "ABSTRACT",
    "APPROVAL PAGE",
    "BIOGRAPHICAL SKETCH",
    "ACKNOWLEDGEMENTS",
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
)

BOLD_FONT_HINT_RE = re.compile(r"(bold|black|heavy|semibold)", re.IGNORECASE)

# Q-rule IDs for each named front-matter heading (per Ester's YES/NO audit matrix).
# Q013=Approval Page, Q021=Biographical Sketch, Q036=Acknowledgements,
# Q047=TOC, Q061=List of Tables, Q070=List of Figures.
_HEADING_Q_RULE_MAP: dict[str, str] = {
    "APPROVAL PAGE": "Q013",
    "BIOGRAPHICAL SKETCH": "Q021",
    "ACKNOWLEDGEMENTS": "Q036",
    "TABLE OF CONTENTS": "Q047",
    "LIST OF TABLES": "Q061",
    "LIST OF FIGURES": "Q070",
}

# Chapter/appendix heading patterns used to locate the start of the body region.
# All three patterns are intentionally case-SENSITIVE: NJIT requires ALL CAPS headings.
# Title-case "Chapter" in TOC column headers and body sentences ("Chapter 3 discusses...")
# must not be treated as body-chapter headings.

# "CHAPTER 1 INTRODUCTION" or "APPENDIX A" — space-separated, ALL CAPS.
_CHAPTER_HEADING_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+")
# Fallback for PDFs where the space between "CHAPTER" and "1" is a whitespace-only span
# that pdf_layout.py strips (line 83: `if not text.strip(): continue`), causing PyMuPDF
# to join them as "CHAPTER1". Only ALL-CAPS versions match.
_CHAPTER_HEADING_MASHED_RE = re.compile(r"^(CHAPTER|APPENDIX)[\dA-Z]+")
# Fallback: "CHAPTER" or "APPENDIX" alone on its own line (split-heading layout).
_CHAPTER_STANDALONE_RE = re.compile(r"^(CHAPTER|APPENDIX)\s*$")
# Four or more consecutive dots indicate a TOC dotted leader ("........ 1").
# Lines matching this pattern are TOC entries, not real chapter headings.
_TOC_LEADER_RE = re.compile(r"\.{4,}")


@dataclass(frozen=True)
class HeadingCenteringMetrics:
    passes: bool
    heading_center_x: float
    text_area_center_x: float
    signed_offset_pt: float
    abs_offset_pt: float
    direction: str
    suppress_threshold_pt: float
    review_threshold_pt: float
    medium_threshold_pt: float
    finding_confidence: str
    centering_confidence: str


@dataclass(frozen=True)
class HeadingMatch:
    heading: str
    page_number: int
    centered: bool
    near_top: bool
    bold: bool
    all_caps: bool
    bbox: BBox
    center_offset_pt: float
    centering_confidence: str
    text_area_center_pt: float
    heading_center_x: float
    signed_center_offset_pt: float
    center_offset_direction: str


def normalize_heading_text(text: str) -> str:
    """Normalize heading text for deterministic matching."""

    return " ".join(text.replace("\u00a0", " ").strip().split())


def _is_bold_line(line: PdfTextLine) -> bool:
    if any(span.bold for span in line.spans):
        return True
    return any(BOLD_FONT_HINT_RE.search(span.font or "") for span in line.spans)


def _visible_text_bbox(line: PdfTextLine) -> BBox:
    if not line.spans:
        return line.bbox
    return BBox(
        x0=min(span.bbox.x0 for span in line.spans),
        y0=min(span.bbox.y0 for span in line.spans),
        x1=max(span.bbox.x1 for span in line.spans),
        y1=max(span.bbox.y1 for span in line.spans),
    )


def _heading_centering_metrics(
    line: PdfTextLine, text_area_x0: float, text_area_x1: float
) -> HeadingCenteringMetrics:
    bbox = _visible_text_bbox(line)
    heading_center_x = (bbox.x0 + bbox.x1) / 2.0
    text_area_center_x = (text_area_x0 + text_area_x1) / 2.0
    signed_offset_pt = heading_center_x - text_area_center_x
    abs_offset_pt = abs(signed_offset_pt)
    if signed_offset_pt < 0:
        direction = "left"
    elif signed_offset_pt > 0:
        direction = "right"
    else:
        direction = ""

    if abs_offset_pt <= CENTER_SUPPRESS_THRESHOLD_PT:
        return HeadingCenteringMetrics(
            passes=True,
            heading_center_x=heading_center_x,
            text_area_center_x=text_area_center_x,
            signed_offset_pt=signed_offset_pt,
            abs_offset_pt=abs_offset_pt,
            direction=direction,
            suppress_threshold_pt=CENTER_SUPPRESS_THRESHOLD_PT,
            review_threshold_pt=CENTER_REVIEW_MAX_THRESHOLD_PT,
            medium_threshold_pt=CENTER_MEDIUM_MAX_THRESHOLD_PT,
            finding_confidence="",
            centering_confidence="high",
        )

    if abs_offset_pt <= CENTER_REVIEW_MAX_THRESHOLD_PT:
        finding_confidence = "review needed"
        centering_confidence = "borderline"
    elif abs_offset_pt <= CENTER_MEDIUM_MAX_THRESHOLD_PT:
        finding_confidence = "medium"
        centering_confidence = "medium"
    else:
        finding_confidence = "high"
        centering_confidence = "high"

    return HeadingCenteringMetrics(
        passes=False,
        heading_center_x=heading_center_x,
        text_area_center_x=text_area_center_x,
        signed_offset_pt=signed_offset_pt,
        abs_offset_pt=abs_offset_pt,
        direction=direction,
        suppress_threshold_pt=CENTER_SUPPRESS_THRESHOLD_PT,
        review_threshold_pt=CENTER_REVIEW_MAX_THRESHOLD_PT,
        medium_threshold_pt=CENTER_MEDIUM_MAX_THRESHOLD_PT,
        finding_confidence=finding_confidence,
        centering_confidence=centering_confidence,
    )


def _line_centering(
    line: PdfTextLine, text_area_x0: float, text_area_x1: float
) -> tuple[bool, float, str]:
    metrics = _heading_centering_metrics(line, text_area_x0, text_area_x1)
    return metrics.passes, metrics.abs_offset_pt, metrics.centering_confidence


def _line_centered(line: PdfTextLine, text_area_x0: float, text_area_x1: float) -> bool:
    centered, _, _ = _line_centering(line, text_area_x0, text_area_x1)
    return centered


def find_body_start_page(pdf_doc: PdfDocument) -> int | None:
    """Return the page number of the first CHAPTER/APPENDIX heading, or None.

    Handles three ALL-CAPS layouts (all patterns are case-sensitive):
    * "CHAPTER 1 INTRODUCTION" on a single line — _CHAPTER_HEADING_RE.
    * "CHAPTER1" (mashed) — _CHAPTER_HEADING_MASHED_RE handles PDFs where the
      inter-word space is a whitespace-only span filtered out by pdf_layout.py.
    * "CHAPTER" alone on one line with the number on the next — _CHAPTER_STANDALONE_RE
      (split-heading layout common in some templates).

    Named front-matter pages (TABLE OF CONTENTS, LIST OF TABLES, LIST OF FIGURES,
    etc.) are always skipped, even when they contain ALL-CAPS text that matches the
    chapter-heading patterns.  Common examples that would otherwise trigger a false
    body-start:
    * "CHAPTER" or "CHAPTER 1" used as a TOC column header on the TOC page.
    * Full TOC entries such as "CHAPTER 1 INTRODUCTION ........ 1".
    """
    # Named front-matter pages: "CHAPTER"/"APPENDIX" alone on one line is a common
    # TOC column-header layout ("CHAPTER    PAGE") — skip the standalone match on
    # those pages, but still allow the full "CHAPTER 1 ..." pattern to fire so
    # that pages carrying BOTH a named FM heading and a real chapter heading are
    # classified correctly.
    fm_page_numbers: frozenset[int] = frozenset(
        m.page_number for m in find_named_frontmatter_headings(pdf_doc)
    )
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if _TOC_LEADER_RE.search(clean):
                    continue  # dotted leader → TOC entry, not a chapter heading
                if _CHAPTER_HEADING_RE.match(clean) or _CHAPTER_HEADING_MASHED_RE.match(clean):
                    return page.page_number
                # "CHAPTER" alone could be a TOC column header — skip on named FM pages.
                if _CHAPTER_STANDALONE_RE.match(clean) and page.page_number not in fm_page_numbers:
                    return page.page_number
    return None


def find_named_frontmatter_headings(pdf_document: PdfDocument) -> list[HeadingMatch]:
    """Return detected named front-matter headings with derived layout/style flags."""

    matches: list[HeadingMatch] = []
    expected_set = set(EXPECTED_HEADINGS)

    for page in pdf_document.pages:
        text_area_x0 = LEFT_MARGIN_PT
        text_area_x1 = page.width - RIGHT_MARGIN_PT
        for block in page.text_blocks:
            for line in block.lines:
                raw_text = line.text.strip()
                normalized = normalize_heading_text(raw_text)
                normalized_upper = normalized.upper()
                if normalized_upper not in expected_set:
                    continue

                metrics = _heading_centering_metrics(line, text_area_x0, text_area_x1)
                matches.append(
                    HeadingMatch(
                        heading=normalized_upper,
                        page_number=page.page_number,
                        centered=metrics.passes,
                        near_top=line.bbox.y0 <= TOP_ZONE_PT,
                        bold=_is_bold_line(line),
                        all_caps=(normalized == normalized_upper),
                        bbox=_visible_text_bbox(line),
                        center_offset_pt=metrics.abs_offset_pt,
                        centering_confidence=metrics.centering_confidence,
                        text_area_center_pt=metrics.text_area_center_x,
                        heading_center_x=metrics.heading_center_x,
                        signed_center_offset_pt=metrics.signed_offset_pt,
                        center_offset_direction=metrics.direction,
                    )
                )

    return matches


def _centering_finding_details(match: HeadingMatch) -> dict[str, str]:
    metrics = _heading_centering_metrics_from_match(match)
    details = {
        "heading_text": match.heading,
        "heading_center_x": f"{match.heading_center_x:.1f}",
        "text_area_center_x": f"{match.text_area_center_pt:.1f}",
        "center_offset_pt": f"{match.center_offset_pt:.1f}",
        "center_offset_direction": match.center_offset_direction,
        "centering_threshold_points": f"{CENTER_SUPPRESS_THRESHOLD_PT:.1f}",
        "centering_review_threshold_points": f"{CENTER_REVIEW_MAX_THRESHOLD_PT:.1f}",
        "centering_medium_threshold_points": f"{CENTER_MEDIUM_MAX_THRESHOLD_PT:.1f}",
    }
    if metrics.finding_confidence:
        details["confidence"] = metrics.finding_confidence
        details["triage_tier"] = (
            "review" if metrics.finding_confidence == "review needed" else "check"
        )
    return details


def _heading_centering_metrics_from_match(match: HeadingMatch) -> HeadingCenteringMetrics:
    if match.center_offset_pt <= CENTER_SUPPRESS_THRESHOLD_PT:
        finding_confidence = ""
        centering_confidence = "high"
    elif match.center_offset_pt <= CENTER_REVIEW_MAX_THRESHOLD_PT:
        finding_confidence = "review needed"
        centering_confidence = "borderline"
    elif match.center_offset_pt <= CENTER_MEDIUM_MAX_THRESHOLD_PT:
        finding_confidence = "medium"
        centering_confidence = "medium"
    else:
        finding_confidence = "high"
        centering_confidence = "high"
    return HeadingCenteringMetrics(
        passes=match.centered,
        heading_center_x=match.heading_center_x,
        text_area_center_x=match.text_area_center_pt,
        signed_offset_pt=match.signed_center_offset_pt,
        abs_offset_pt=match.center_offset_pt,
        direction=match.center_offset_direction,
        suppress_threshold_pt=CENTER_SUPPRESS_THRESHOLD_PT,
        review_threshold_pt=CENTER_REVIEW_MAX_THRESHOLD_PT,
        medium_threshold_pt=CENTER_MEDIUM_MAX_THRESHOLD_PT,
        finding_confidence=finding_confidence,
        centering_confidence=centering_confidence,
    )


def check_named_frontmatter_headings(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P014 warnings when detected named front-matter headings fail heuristics."""

    findings: list[AuditFinding] = []
    for match in find_named_frontmatter_headings(pdf_document):
        if match.centered and match.near_top and match.bold and match.all_caps:
            continue

        failures: list[str] = []
        if not match.centered:
            failures.append("not centered")
        if not match.near_top:
            failures.append("not near top")
        if not match.bold:
            failures.append("not bold")
        if not match.all_caps:
            failures.append("not all caps")

        issue_type = "frontmatter_heading_layout_issue"
        if not match.centered and match.near_top and match.bold and match.all_caps:
            issue_type = "frontmatter_heading_not_centered"

        q_rule_id = _HEADING_Q_RULE_MAP.get(match.heading, "")
        finding_details: dict[str, str] = {
            "heading": match.heading,
            "page_number": str(match.page_number),
            "issue_type": issue_type,
            "source_q_rule_id": q_rule_id,
            "centered": str(match.centered),
            "near_top": str(match.near_top),
            "bold": str(match.bold),
            "all_caps": str(match.all_caps),
            "center_offset_pt": f"{match.center_offset_pt:.1f}",
            "centering_confidence": match.centering_confidence,
            "text_area_center_pt": f"{match.text_area_center_pt:.1f}",
            "bbox": format_bbox_detail(match.bbox),
            "suggested_fix": (
                "Center the front-matter heading within the text area."
                if issue_type == "frontmatter_heading_not_centered"
                else (
                    "Place named front-matter headings centered near the top "
                    "in bold all-caps."
                )
            ),
        }
        if issue_type == "frontmatter_heading_not_centered":
            finding_details.update(_centering_finding_details(match))
        findings.append(
            AuditFinding(
                rule_id="P014",
                severity=Severity.WARNING,
                page=match.page_number,
                message=(
                    f"Named front-matter heading '{match.heading}' may violate layout/style "
                    f"heuristics: {', '.join(failures)}."
                ),
                details=finding_details,
            )
        )

    return findings
