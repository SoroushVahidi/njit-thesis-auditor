"""Shared front-matter heading gate resolver for P069 and dependent rules.

Provides relaxed but conservative canonical heading resolution for section
localization gates used by P041, P044–P047, P065–P068, and TOC/list detection.
P014 style checks remain on strict ``find_named_frontmatter_headings()`` only.
"""

from __future__ import annotations

from dataclasses import dataclass

from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import (
    BOLD_FONT_HINT_RE,
    EXPECTED_HEADINGS,
    HeadingMatch,
    _line_centering,
    _visible_text_bbox,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT
from njit_auditor.rules.pdf_page_numbering_regime import _classify_pages
from njit_auditor.rules.pdf_toc_alignment import (
    TRAILING_PUNCT_RE,
    _normalize_toc_heading_variant,
)

# Curated variant spellings → canonical expected phrase (shared with P038).
FRONTMATTER_HEADING_VARIANTS: dict[str, str] = {
    "ACKNOWLEDGMENTS": "ACKNOWLEDGEMENTS",
}

GATE_CANONICAL_HEADINGS: tuple[str, ...] = EXPECTED_HEADINGS + ("DEDICATION",)
_GATE_CANONICAL_SET = frozenset(GATE_CANONICAL_HEADINGS)

_MAX_GATE_LINE_CHARS = 40
_MAX_GATE_LINE_TOKENS = 6


@dataclass(frozen=True)
class GateHeadingMatch(HeadingMatch):
    """Named front-matter heading resolved through the P069 gate."""

    match_path: str
    match_confidence: str


def _is_bold_line(line: PdfTextLine) -> bool:
    if any(span.bold for span in line.spans):
        return True
    return any(BOLD_FONT_HINT_RE.search(span.font or "") for span in line.spans)


def passes_standalone_line_gate(text: str) -> bool:
    """Return True when *text* looks like a standalone heading line, not prose."""
    normalized = normalize_heading_text(text)
    if not normalized:
        return False
    gate_line = TRAILING_PUNCT_RE.sub("", normalized).strip()
    if not gate_line:
        return False
    if len(gate_line) > _MAX_GATE_LINE_CHARS:
        return False
    if len(gate_line.split()) > _MAX_GATE_LINE_TOKENS:
        return False
    if gate_line.endswith(".") or gate_line.endswith("?"):
        return False
    return True


def resolve_gate_heading_from_line(text: str) -> tuple[str, str, str] | None:
    """Resolve a text line to ``(canonical_heading, match_path, match_confidence)``."""
    if not passes_standalone_line_gate(text):
        return None

    raw_upper = normalize_heading_text(text).upper()
    punct_stripped = TRAILING_PUNCT_RE.sub("", raw_upper).strip()
    continued_norm = _normalize_toc_heading_variant(text)

    if raw_upper in _GATE_CANONICAL_SET:
        return raw_upper, "exact", "high"
    if punct_stripped in _GATE_CANONICAL_SET and punct_stripped != raw_upper:
        return punct_stripped, "variant_map", "medium"
    canonical = FRONTMATTER_HEADING_VARIANTS.get(raw_upper)
    if canonical is not None:
        return canonical, "variant_map", "medium"
    canonical = FRONTMATTER_HEADING_VARIANTS.get(punct_stripped)
    if canonical is not None:
        return canonical, "variant_map", "medium"
    if continued_norm in _GATE_CANONICAL_SET and continued_norm not in {
        raw_upper,
        punct_stripped,
    }:
        return continued_norm, "continued_suffix", "medium"
    return None


def line_resolves_to_gate_heading(text: str, heading: str) -> bool:
    """Return True when *text* resolves to the requested canonical *heading*."""
    resolved = resolve_gate_heading_from_line(text)
    return resolved is not None and resolved[0] == heading


def _eligible_page_numbers(
    pdf_document: PdfDocument,
    *,
    max_scan_pages: int | None,
) -> set[int]:
    regions, _has_front = _classify_pages(pdf_document)
    eligible: set[int] = set()
    for page in pdf_document.pages:
        pn = page.page_number
        if max_scan_pages is not None and pn > max_scan_pages:
            continue
        region = regions.get(pn, "ambiguous")
        if region in {"front_matter", "ambiguous"}:
            eligible.add(pn)
    return eligible


def find_frontmatter_headings_for_gates(
    pdf_document: PdfDocument,
    *,
    max_scan_pages: int | None = None,
) -> list[GateHeadingMatch]:
    """Return gate-resolved front-matter headings with layout flags."""
    if not pdf_document.pages:
        return []

    eligible_pages = _eligible_page_numbers(pdf_document, max_scan_pages=max_scan_pages)
    if not eligible_pages:
        return []

    matches: list[GateHeadingMatch] = []
    for page in pdf_document.pages:
        if page.page_number not in eligible_pages:
            continue
        text_area_x0 = LEFT_MARGIN_PT
        text_area_x1 = page.width - RIGHT_MARGIN_PT
        for block in page.text_blocks:
            for line in block.lines:
                resolved = resolve_gate_heading_from_line(line.text)
                if resolved is None:
                    continue
                canonical, match_path, match_confidence = resolved
                normalized = normalize_heading_text(line.text)
                centered, center_offset, centering_confidence = _line_centering(
                    line, text_area_x0, text_area_x1
                )
                text_area_center = (text_area_x0 + text_area_x1) / 2.0
                matches.append(
                    GateHeadingMatch(
                        heading=canonical,
                        page_number=page.page_number,
                        centered=centered,
                        near_top=line.bbox.y0 <= 2.0 * 72.0,
                        bold=_is_bold_line(line),
                        all_caps=(normalized == normalized.upper()),
                        bbox=_visible_text_bbox(line),
                        center_offset_pt=center_offset,
                        centering_confidence=centering_confidence,
                        text_area_center_pt=text_area_center,
                        match_path=match_path,
                        match_confidence=match_confidence,
                    )
                )
    return matches


def find_gate_matches_for_heading(
    pdf_document: PdfDocument,
    heading: str,
    *,
    max_scan_pages: int | None = None,
) -> list[GateHeadingMatch]:
    """Return gate matches for a single canonical *heading* label."""
    return [
        match
        for match in find_frontmatter_headings_for_gates(
            pdf_document, max_scan_pages=max_scan_pages
        )
        if match.heading == heading
    ]


def find_gate_heading_page_and_y(
    pdf_document: PdfDocument,
    heading: str,
    *,
    max_scan_pages: int | None = None,
    require_unique: bool = True,
) -> tuple[PdfPage, float] | None:
    """Return ``(page, heading_bottom_y)`` for a gate-resolved *heading*."""
    matches = find_gate_matches_for_heading(
        pdf_document, heading, max_scan_pages=max_scan_pages
    )
    if require_unique and len(matches) != 1:
        return None
    if not require_unique and not matches:
        return None

    target_page = matches[0].page_number
    for page in pdf_document.pages:
        if page.page_number != target_page:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                if line_resolves_to_gate_heading(line.text, heading):
                    return page, line.bbox.y1
    return None
