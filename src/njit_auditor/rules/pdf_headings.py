"""Heuristic named front-matter heading checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT

INCH_TO_PT = 72.0
TOP_ZONE_PT = 2.0 * INCH_TO_PT
CENTER_TOLERANCE_PT = 18.0
BORDERLINE_CENTER_TOLERANCE_PT = 26.0

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

# Chapter/appendix heading patterns used to locate the start of the body region.
_CHAPTER_HEADING_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+", re.IGNORECASE)
# Fallback: "CHAPTER" or "APPENDIX" alone on its own line (split-heading layout).
_CHAPTER_STANDALONE_RE = re.compile(r"^(CHAPTER|APPENDIX)\s*$", re.IGNORECASE)


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
    line: PdfTextLine, text_area_x0: float, text_area_x1: float
) -> tuple[bool, float, str]:
    bbox = _visible_text_bbox(line)
    line_center = (bbox.x0 + bbox.x1) / 2.0
    text_area_center = (text_area_x0 + text_area_x1) / 2.0
    offset = abs(line_center - text_area_center)
    if offset <= CENTER_TOLERANCE_PT:
        return True, offset, "high"
    if offset <= BORDERLINE_CENTER_TOLERANCE_PT:
        return False, offset, "borderline"
    return False, offset, "high"


def _line_centered(line: PdfTextLine, text_area_x0: float, text_area_x1: float) -> bool:
    centered, _, _ = _line_centering(line, text_area_x0, text_area_x1)
    return centered


def find_body_start_page(pdf_doc: PdfDocument) -> int | None:
    """Return the page number of the first CHAPTER/APPENDIX heading, or None.

    Handles two layouts:
    * "CHAPTER 1 INTRODUCTION" on a single line — matched by _CHAPTER_HEADING_RE.
    * "CHAPTER" alone on one line with the number on the next — matched by
      _CHAPTER_STANDALONE_RE (split-heading layout common in some templates).
    """
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if _CHAPTER_HEADING_RE.match(clean) or _CHAPTER_STANDALONE_RE.match(clean):
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

                centered, center_offset, centering_confidence = _line_centering(
                    line, text_area_x0, text_area_x1
                )
                text_area_center = (text_area_x0 + text_area_x1) / 2.0
                matches.append(
                    HeadingMatch(
                        heading=normalized_upper,
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
