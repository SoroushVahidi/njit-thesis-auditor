"""Heuristic named front-matter heading checks for layout-aware PDF text lines."""

# from __future__ import annotations

import re
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT

# Re-export expected headings and helper functions for backward compatibility
EXPECTED_HEADINGS: tuple[str, ...] = (
    "ABSTRACT",
    "APPROVAL PAGE",
    "BIOGRAPHICAL SKETCH",
    "ACKNOWLEDGEMENTS",
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
)

COMPACT_EXPECTED_HEADINGS: dict[str, str] = {
    heading.replace(" ", ""): heading
    for heading in ("TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES")
}

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
# that pdf_layout previously dropped without restoring a geometry-based space, causing
# PyMuPDF to join them as "CHAPTER1". load_pdf_layout now inserts spaces from horizontal
# gaps, but this mashed fallback remains for spans that truly abut with no gap. Only
# ALL-CAPS versions match.
_CHAPTER_HEADING_MASHED_RE = re.compile(r"^(CHAPTER|APPENDIX)[\dA-Z]+")
# Fallback: "CHAPTER" or "APPENDIX" alone on its own line (split-heading layout).
_CHAPTER_STANDALONE_RE = re.compile(r"^(CHAPTER|APPENDIX)\s*$")
# Four or more consecutive dots indicate a TOC dotted leader ("........ 1").
# Lines matching this pattern are TOC entries, not real chapter headings.
_TOC_LEADER_RE = re.compile(r"\.{4,}")

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


def normalize_heading_text(text: str) -> str:
    """Normalize heading text for deterministic matching."""
    return " ".join(text.replace("\u00a0", " ").strip().split())

INCH_TO_PT = 72.0
TOP_ZONE_PT = 2.0 * INCH_TO_PT
CENTER_TOLERANCE_PT = 18.0
BORDERLINE_CENTER_TOLERANCE_PT = 26.0


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


def _line_centering(
    line: PdfTextLine,
    text_area_x0: float,
    text_area_x1: float,
    *,
    page_width: float | None = None,
) -> tuple[bool, float, str]:
    """Return whether *line* is centered within tolerance of a reference midpoint.

    NJIT body margins are asymmetric (1.5" left, 1" right), so the text-area
    midpoint and physical page midpoint differ by 18pt on letter paper. Named
    front-matter headings are often centered on the page face rather than the
    asymmetric text-area box; accept either reference when within tolerance.
    """
    bbox = _visible_text_bbox(line)
    line_center = (bbox.x0 + bbox.x1) / 2.0
    text_area_center = (text_area_x0 + text_area_x1) / 2.0
    offsets = [abs(line_center - text_area_center)]
    if page_width is not None:
        offsets.append(abs(line_center - (page_width / 2.0)))
    offset = min(offsets)
    if offset <= CENTER_TOLERANCE_PT:
        return True, offset, "high"
    if offset <= BORDERLINE_CENTER_TOLERANCE_PT:
        return False, offset, "borderline"
    return False, offset, "high"


def _line_centered(
    line: PdfTextLine,
    text_area_x0: float,
    text_area_x1: float,
    *,
    page_width: float | None = None,
) -> bool:
    centered, _, _ = _line_centering(
        line, text_area_x0, text_area_x1, page_width=page_width
    )
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
                    if page.page_number in fm_page_numbers and not _line_centered(
                        line,
                        LEFT_MARGIN_PT,
                        page.width - RIGHT_MARGIN_PT,
                        page_width=page.width,
                    ):
                        continue
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
                heading = (
                    normalized_upper
                    if normalized_upper in expected_set
                    else COMPACT_EXPECTED_HEADINGS.get(normalized_upper.replace(" ", ""))
                )
                if heading is None:
                    continue

                centered, center_offset, centering_confidence = _line_centering(
                    line, text_area_x0, text_area_x1, page_width=page.width
                )
                text_area_center = (text_area_x0 + text_area_x1) / 2.0
                matches.append(
                    HeadingMatch(
                        heading=heading,
                        page_number=page.page_number,
                        centered=centered,
                        near_top=line.bbox.y0 <= TOP_ZONE_PT,
                        bold=_is_bold_line(line),
                        all_caps=(normalized == normalized_upper),
                        bbox=_visible_text_bbox(line),
                        center_offset_pt=center_offset,
                        centering_confidence=centering_confidence,
                        text_area_center_pt=text_area_center,
                    )
                )
    return matches


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
        findings.append(
            AuditFinding(
                rule_id="P014",
                severity=Severity.WARNING,
                page=match.page_number,
                message=(
                    f"Named front-matter heading '{match.heading}' may violate layout/style "
                    f"heuristics: {', '.join(failures)}."
                ),
                details={
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
                        "Place named front-matter headings centered near the top in bold all-caps."
                    ),
                },
            )
        )
    return findings