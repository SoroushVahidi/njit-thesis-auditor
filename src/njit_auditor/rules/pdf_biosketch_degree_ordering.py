"""Conservative Biographical Sketch degree-ordering check (P066).

Partial heuristic PDF coverage for Q025:
  - Q025: are postgraduate degrees listed from most recent to oldest?

Q023 (no birthplace/date of birth) and Q024 (no work experience) are explicitly
out of scope — both require reading and understanding biographical content, which
is not automatable without NLP and would violate the project privacy model.

The "NJIT first" sub-requirement of Q025 is also out of scope for v1: identifying
which entry refers to NJIT requires recognising institution name text.

Detection strategy: extract 4-digit year tokens from short candidate lines in the
education zone (below the BIOGRAPHICAL SKETCH heading, above any detectable
Publications/Presentations sub-section boundary). If year tokens extracted from
those lines are not in non-increasing order (most recent first), emit
biosketch_degree_order_suspicious.

No bio-sketch text, degree names, institution names, or biographical prose is
stored or reproduced in findings. Findings contain only counts, year integers,
and structural metadata.

Biographical Sketch page only. Does not duplicate P038 (heading presence),
P045 (publication hanging indent/spacing), or P047 (bullet single-spacing).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_frontmatter_heading_gate import find_gate_heading_page_and_y

# ---------------------------------------------------------------------------
# Module-level constants (exported for tests)
# ---------------------------------------------------------------------------

_HEADING_LABEL = "BIOGRAPHICAL SKETCH"
_YEAR_RE = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)
_EDUCATION_SECTION_LABELS = frozenset(
    {"EDUCATION", "GRADUATEEDUCATION", "UNDERGRADUATEANDGRADUATEEDUCATION"}
)
# Matches the boundary word in any spacing/heading form: singular or plural
# ("Publication"/"Publications"/"Presentation"/"Presentations"), qualified or
# prefixed headings ("Selected Publications"), and compact PDF-extracted
# labels where whitespace between words is dropped entirely
# ("PublicationsAndPresentations", "PresentationsAndPublications"). Matched
# against the compact (letters-only, uppercased) form of a line, so ordinary
# spacing differences never matter.
_PUBLICATION_LABEL_RE = re.compile(r"PUBLICATIONS?|PRESENTATIONS?")

_MAX_DEGREE_LINE_CHARS = 120
_MIN_ALPHA_CHARS = 3
_MIN_YEAR_CANDIDATES = 3
_MIN_YEAR_GAP = 2


def _find_biosketch_page_and_heading_y(
    pdf_document: PdfDocument,
) -> tuple[PdfPage, float] | None:
    """Return (page, heading_bottom_y) for the unique BIOGRAPHICAL SKETCH page."""
    return find_gate_heading_page_and_y(pdf_document, _HEADING_LABEL)


def _find_publications_boundary_y(
    page: PdfPage, heading_y: float
) -> float | None:
    """Return the y0 of the first Publications/Presentations sub-section line."""
    lines_below: list[tuple[float, str]] = []
    for block in page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= heading_y + 2:
                continue
            lines_below.append((line.bbox.y0, line.text.strip()))
    lines_below.sort(key=lambda t: t[0])
    for y0, text in lines_below:
        if _PUBLICATION_LABEL_RE.search(_compact_section_label(text)):
            return y0
    return None


def _compact_section_label(text: str) -> str:
    """Normalize section labels, including PDF text with spaces dropped."""
    return re.sub(r"[^A-Z]", "", text.upper())


def _find_education_boundary_y(page: PdfPage, heading_y: float) -> float | None:
    """Return the bottom of the education-section heading, if detectable."""
    lines_below = [
        line
        for block in page.text_blocks
        for line in block.lines
        if line.bbox.y0 > heading_y + 2
    ]
    lines_below.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
    for line in lines_below:
        text = " ".join(line.text.strip().split())
        if _compact_section_label(text) in _EDUCATION_SECTION_LABELS:
            return line.bbox.y1
    return None


def _is_education_candidate(line: PdfTextLine) -> bool:
    """Return True if a line looks like an education-entry candidate.

    Criteria:
    - Not too long to be prose or a full publication citation
    - Contains some alpha characters
    - Not a bare page-number token
    - Contains exactly one year-like token
    """
    text = " ".join(line.text.strip().split())
    if len(text) > _MAX_DEGREE_LINE_CHARS:
        return False
    if _PAGE_NUM_RE.match(text):
        return False
    alpha_count = sum(ch.isalpha() for ch in text)
    if alpha_count < _MIN_ALPHA_CHARS:
        return False
    years = _YEAR_RE.findall(text)
    return len(years) == 1


def _extract_year(line: PdfTextLine) -> int:
    """Extract the single year from a candidate line."""
    years = _YEAR_RE.findall(line.text)
    return int(years[0])


def check_pdf_biosketch_degree_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit a P066 warning when bio-sketch degree years are not in most-recent-first order.

    Returns an empty list when any skip condition applies.
    """
    result = _find_biosketch_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_y = result
    if not page.text_blocks:
        return []

    education_boundary_y = _find_education_boundary_y(page, heading_y)
    if education_boundary_y is None:
        return []

    pub_boundary_y = _find_publications_boundary_y(page, heading_y)

    # Collect education-zone candidate lines: below heading, above publications boundary.
    candidates: list[PdfTextLine] = []
    for block in page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= education_boundary_y + 2:
                continue
            if pub_boundary_y is not None and line.bbox.y0 >= pub_boundary_y:
                continue
            if _is_education_candidate(line):
                candidates.append(line)

    candidates.sort(key=lambda ln: (ln.bbox.y0, ln.bbox.x0))

    if len(candidates) < _MIN_YEAR_CANDIDATES:
        return []

    years = [_extract_year(ln) for ln in candidates]

    # Skip if all years are equal — ordering cannot be determined.
    if len(set(years)) < 2:
        return []

    # Count inversions: later-listed year > earlier-listed year by > _MIN_YEAR_GAP.
    inversion_count = 0
    first_inversion_index = -1
    for i in range(len(years) - 1):
        if years[i + 1] - years[i] > _MIN_YEAR_GAP:
            inversion_count += 1
            if first_inversion_index < 0:
                first_inversion_index = i

    if inversion_count == 0:
        return []

    return [
        AuditFinding(
            rule_id="P066",
            severity=Severity.WARNING,
            page=page.page_number,
            message=(
                "Biographical Sketch degree entries may not be listed in most-recent-first "
                "order. NJIT guidelines require postgraduate degrees listed from most "
                "recent to oldest."
            ),
            details={
                "issue_type": "biosketch_degree_order_suspicious",
                "page": str(page.page_number),
                "year_candidate_count": str(len(years)),
                "first_candidate_year": str(years[0]),
                "last_candidate_year": str(years[-1]),
                "inversion_count": str(inversion_count),
                "first_inversion_index": str(first_inversion_index),
                "expected_order": "descending",
                "confidence": "medium",
                "triage_tier": "low",
                "source_q_rule_ids": "Q025",
            },
        )
    ]
