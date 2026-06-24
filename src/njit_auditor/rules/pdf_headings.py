"""Heuristic named front-matter heading checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT

INCH_TO_PT = 72.0
TOP_ZONE_PT = 2.0 * INCH_TO_PT
CENTER_TOLERANCE_PT = 12.0

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


@dataclass(frozen=True)
class HeadingMatch:
    heading: str
    page_number: int
    centered: bool
    near_top: bool
    bold: bool
    all_caps: bool
    bbox: BBox


def normalize_heading_text(text: str) -> str:
    """Normalize heading text for deterministic matching."""

    return " ".join(text.replace("\u00a0", " ").strip().split())


def _is_bold_line(line: PdfTextLine) -> bool:
    if any(span.bold for span in line.spans):
        return True
    return any(BOLD_FONT_HINT_RE.search(span.font or "") for span in line.spans)


def _line_centered(line: PdfTextLine, text_area_x0: float, text_area_x1: float) -> bool:
    line_center = (line.bbox.x0 + line.bbox.x1) / 2.0
    text_area_center = (text_area_x0 + text_area_x1) / 2.0
    return abs(line_center - text_area_center) <= CENTER_TOLERANCE_PT


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

                matches.append(
                    HeadingMatch(
                        heading=normalized_upper,
                        page_number=page.page_number,
                        centered=_line_centered(line, text_area_x0, text_area_x1),
                        near_top=line.bbox.y0 <= TOP_ZONE_PT,
                        bold=_is_bold_line(line),
                        all_caps=(normalized == normalized_upper),
                        bbox=line.bbox,
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
                    "centered": str(match.centered),
                    "near_top": str(match.near_top),
                    "bold": str(match.bold),
                    "all_caps": str(match.all_caps),
                    "bbox": format_bbox_detail(match.bbox),
                    "suggested_fix": (
                        "Place named front-matter headings centered near the top in bold all-caps."
                    ),
                },
            )
        )

    return findings
