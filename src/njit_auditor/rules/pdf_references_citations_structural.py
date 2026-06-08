"""Conservative references/citations structural checks (P064).

Heuristic PDF coverage for the NJIT references section (no direct Q-rule, with
analogy to Q028/Q029 from the Biographical Sketch section):

  A. references_section_heading_not_detected — no REFERENCES, BIBLIOGRAPHY,
     WORKS CITED, or LITERATURE CITED heading found in body pages of a document
     long enough to require a references section (≥5 body pages).

  B. references_entry_indentation_inconsistent — within the detected references
     section, multi-line entry candidates exhibit mixed hanging-indent patterns
     (some with a significant indent delta, some without) rather than a consistent
     style.  Gate: ≥5 entry candidates AND ≥3 multi-line entry candidates.

  C. references_entry_spacing_inconsistent — within the detected references
     section, inter-entry vertical gaps are highly irregular (≥20% of gaps are
     outliers differing by >2× the median AND the absolute range from median to
     max outlier exceeds the threshold).  Gate: ≥5 entry candidates.

Guideline basis:
  - Self-Assessment Sheet p.4: "The references are consistently formatted and
    follow a style that is agreed upon with your advisor."
  - Formatting Guidelines para 138: "Section heading 'References' in the document
    body."
  - Front Matter Lorem Ipsum p.9: REFERENCES in TOC at body-section level.
  - Q028/Q029 analogy: Bio Sketch entries use hanging indent and inter-entry
    spacing — applied conservatively to the main References section.

No direct Q-rule addresses the references section; checks A/B/C are justified
via the guideline text and the Q028/Q029 Bio Sketch analogy.

P064 does NOT check:
  - Citation style compliance (APA, IEEE, ACM, MLA, Chicago) — advisor-dependent.
  - Reference entry content: author names, journal titles, DOIs, URLs.
  - In-text citation markers in body paragraphs.
  - Completeness: every in-text citation has a corresponding entry.
  - BibTeX/TeX source citation consistency.

Privacy: all findings contain ONLY geometric/structural metadata — page numbers,
counts, x-coordinates, gap values, confidence strings.  No reference entry text,
citation text, author names, article or book titles, DOI strings, URL strings,
label/ref keys, or any other dissertation content appears in any finding field.

Conservative skip conditions:
  - No body pages detected.
  - No recognized references heading AND document has fewer than 5 body pages.
  - Fewer than 3 multi-line entry candidates → skip check B.
  - Fewer than 5 entry candidates → skip checks B and C.
  - Image-only or flattened pages (no text-layer blocks).
  - High x-coordinate variance on references section lines (std dev > 50 pt).
  - References section too short (<2 pages AND <5 entries).
  - Mixed multi-column layout detected (≥3 distinct left-margin clusters).
"""

from __future__ import annotations

import re
import statistics

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RULE_ID = "P064"

# Accepted heading keywords (normalized, case-insensitive).
_HEADING_KEYWORDS: tuple[str, ...] = (
    "REFERENCES",
    "BIBLIOGRAPHY",
    "WORKS CITED",
    "LITERATURE CITED",
)

# Heading type enum strings for the heading_type finding field.
_HEADING_TYPE_MAP: dict[str, str] = {
    "REFERENCES": "REFERENCES",
    "BIBLIOGRAPHY": "BIBLIOGRAPHY",
    "WORKS CITED": "WORKS_CITED",
    "LITERATURE CITED": "LITERATURE_CITED",
}

# Maximum length (chars) of a recognized references-section heading line.
_MAX_HEADING_LEN = 60

# Body chapter/appendix pattern — used to find body start page and section ends.
_CHAPTER_APPENDIX_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+", re.IGNORECASE)

# Minimum body pages needed before heading absence is flagged.
_MIN_BODY_PAGES_FOR_HEADING_CHECK = 5

# Minimum line length to be a reference entry candidate (chars).
_MIN_ENTRY_LINE_LEN = 20

# Minimum number of entries required to run check B (indentation).
_MIN_ENTRIES_FOR_INDENT_CHECK = 5

# Minimum number of multi-line entries required to run check B.
_MIN_MULTILINE_FOR_INDENT_CHECK = 3

# Minimum number of entries required to run check C (spacing).
_MIN_ENTRIES_FOR_SPACING_CHECK = 5

# Maximum y0-to-y0 gap (line pitch, points) for grouping lines within one entry.
# Lines whose y0 baseline is within this distance of the previous line's y0 are
# considered part of the same entry.  A gap larger than this starts a new entry.
# Typical body font (12pt) line spacing is ~14-16pt (y0-to-y0); entry separators
# are usually at least one blank line (≥24pt y0-to-y0 gap).
_INTRA_ENTRY_Y0_GAP_PT = 20.0

# Minimum gap (points) between entries (inter-entry gap) for baseline detection.
_MIN_INTER_ENTRY_GAP_PT = 2.0

# Hanging-indent significant threshold: continuation lines must differ by this
# many points from the first line to be considered a "hanging indent" present.
_HANGING_INDENT_THRESHOLD_PT = 10.0

# Standard deviation threshold for indent deltas: if std dev exceeds this value,
# emit an inconsistency finding.
_INDENT_STDEV_THRESHOLD_PT = 12.0

# Fraction of outlier gaps that triggers a spacing inconsistency finding.
_OUTLIER_GAP_FRACTION = 0.20

# Minimum absolute difference from median gap for an outlier to matter (points).
_OUTLIER_GAP_ABS_THRESHOLD_PT = 15.0

# X-coordinate standard deviation threshold for "noisy geometry" skip.
_HIGH_X_VARIANCE_THRESHOLD_PT = 50.0

# Number of distinct left-margin x clusters that indicate two-column layout.
_MULTICOLUMN_CLUSTER_COUNT = 3

# Minimum references section pages to run sub-checks (otherwise too short).
_MIN_SECTION_PAGES_FOR_SUBCHECKS = 1  # at least 1 page with entries
_MIN_ENTRIES_FOR_SECTION_NONEMPTY = 2  # skip if barely any entries

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_body_start_page(pdf_doc: PdfDocument) -> int | None:
    """Return the first page number where a CHAPTER or APPENDIX body heading is found."""
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if _CHAPTER_APPENDIX_RE.match(clean):
                    return page.page_number
    return None


def _normalized_heading(text: str) -> str:
    """Normalize text for heading comparison: strip, collapse whitespace, upper-case."""
    return " ".join(text.strip().split()).upper()


def _is_references_heading(line: PdfTextLine) -> str | None:
    """Return the normalized heading keyword if this line is a references heading, else None.

    A line qualifies if:
    - Its normalized text exactly matches (or starts with, for WORKS CITED etc.)
      one of the accepted heading keywords.
    - It is short enough (< _MAX_HEADING_LEN chars) to be a standalone heading,
      not a body sentence containing "references".
    - It does not look like a numbered/lettered section heading prefix (e.g.,
      "3.1 References" — avoid matching numbered subsection headings in body).
    """
    clean = _normalized_heading(line.text)
    if len(clean) > _MAX_HEADING_LEN:
        return None
    # Reject lines that begin with a digit (numbered section headings like "3. References")
    if clean and clean[0].isdigit():
        return None
    # Reject lines that look like inline citations: "[1]", "(Author, 2023)"
    if clean.startswith("[") or clean.startswith("("):
        return None
    for keyword in _HEADING_KEYWORDS:
        if clean == keyword:
            return keyword
        # Allow trailing colon: "REFERENCES:" accepted.
        if clean == keyword + ":":
            return keyword
    return None


def _find_references_heading(
    pdf_doc: PdfDocument, body_start: int
) -> tuple[int, str] | None:
    """Return (page_number, heading_keyword) for the first references heading found.

    Scans body pages only.  Returns None if no heading is found.
    """
    for page in pdf_doc.pages:
        if page.page_number < body_start:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                kw = _is_references_heading(line)
                if kw is not None:
                    return page.page_number, kw
    return None


def _count_body_pages(pdf_doc: PdfDocument, body_start: int) -> int:
    """Count pages in body (at or after body_start)."""
    return sum(1 for p in pdf_doc.pages if p.page_number >= body_start)


def _collect_references_section_pages(
    pdf_doc: PdfDocument,
    heading_page: int,
) -> list[PdfPage]:
    """Return the list of pages that belong to the references section.

    Start: heading_page.
    End: the page before the next major structural heading (all-caps CHAPTER /
    APPENDIX line), or the last page of the document, whichever comes first.
    """
    in_section = False
    section_pages: list[PdfPage] = []

    for page in pdf_doc.pages:
        if page.page_number == heading_page:
            in_section = True

        if not in_section:
            continue

        if page.page_number > heading_page:
            # Check if a new major structural heading starts on this page.
            for block in page.text_blocks:
                for line in block.lines:
                    clean = " ".join(line.text.strip().split()).upper()
                    if _CHAPTER_APPENDIX_RE.match(clean):
                        # New chapter/appendix starts — end references section.
                        return section_pages

        section_pages.append(page)

    return section_pages


def _is_usable_entry_line(line: PdfTextLine) -> bool:
    """Return True if this line is a usable reference-entry candidate."""
    clean = " ".join(line.text.strip().split())
    if len(clean) < _MIN_ENTRY_LINE_LEN:
        return False
    # Skip likely page-number lines (short all-digit or roman numeral).
    if re.match(r"^[\d]+$", clean):
        return False
    # Must have some alphabetic content.
    alpha_count = sum(ch.isalpha() for ch in clean)
    return alpha_count >= 8


def _collect_lines_from_section(
    section_pages: list[PdfPage],
    heading_page: int,
    heading_kw: str,
) -> list[PdfTextLine]:
    """Collect all usable text lines from the references section pages.

    Skips the heading line itself on the first page.
    Returns lines sorted by (page_number, y0) order.
    """
    all_lines: list[PdfTextLine] = []
    heading_skipped = False

    for page in section_pages:
        page_lines: list[PdfTextLine] = []
        for block in page.text_blocks:
            for line in block.lines:
                # Skip the section heading line itself.
                if not heading_skipped and page.page_number == heading_page:
                    kw = _is_references_heading(line)
                    if kw is not None:
                        heading_skipped = True
                        continue
                if _is_usable_entry_line(line):
                    page_lines.append(line)
        # Sort within page by top y-coordinate.
        page_lines.sort(key=lambda ln: (ln.bbox.y0, ln.bbox.x0))
        all_lines.extend(page_lines)

    return all_lines


def _group_entries(lines: list[PdfTextLine]) -> list[list[PdfTextLine]]:
    """Group lines into entry candidates using line-pitch (y0-to-y0) heuristic.

    Lines whose y0 baseline is within _INTRA_ENTRY_Y0_GAP_PT of the previous
    line's y0 are continuation lines of the same entry.  A y0-to-y0 gap larger
    than this threshold signals a new entry starts.

    Using y0-to-y0 rather than y1-to-y0 avoids false groupings caused by
    overlapping bboxes that PyMuPDF reports for tightly-spaced text runs.
    """
    if not lines:
        return []

    groups: list[list[PdfTextLine]] = [[lines[0]]]
    for line in lines[1:]:
        prev_y0 = groups[-1][-1].bbox.y0
        y0_gap = line.bbox.y0 - prev_y0
        if y0_gap <= _INTRA_ENTRY_Y0_GAP_PT:
            groups[-1].append(line)
        else:
            groups.append([line])

    return groups


def _compute_x_variance(lines: list[PdfTextLine]) -> float:
    """Return standard deviation of x0 coordinates across all lines."""
    if len(lines) < 2:
        return 0.0
    x0s = [line.bbox.x0 for line in lines]
    return statistics.stdev(x0s)


def _detect_multicolumn(lines: list[PdfTextLine]) -> bool:
    """Return True if lines appear to span multiple text columns.

    A simple heuristic: cluster distinct x0 values.  If there are ≥3 distinct
    clusters separated by more than 40 points, assume multi-column layout.
    """
    if len(lines) < 4:
        return False
    x0s = sorted(set(round(line.bbox.x0 / 10) * 10 for line in lines))
    clusters: list[float] = []
    for x in x0s:
        if not clusters or x - clusters[-1] > 40:
            clusters.append(x)
    return len(clusters) >= _MULTICOLUMN_CLUSTER_COUNT


# ---------------------------------------------------------------------------
# Check A: References heading detection
# ---------------------------------------------------------------------------


def _check_heading(
    pdf_doc: PdfDocument,
    body_start: int,
    body_page_count: int,
) -> tuple[AuditFinding | None, int | None, str | None]:
    """Run heading check.  Returns (finding_or_None, heading_page_or_None, heading_kw_or_None).

    If the heading is found, finding is None (no problem) and heading details are returned.
    If the heading is not found and the document is long enough, a finding is emitted.
    If the document is too short to expect a references section, returns (None, None, None).
    """
    heading_result = _find_references_heading(pdf_doc, body_start)

    if heading_result is not None:
        heading_page, heading_kw = heading_result
        return None, heading_page, heading_kw

    # No heading found.
    if body_page_count < _MIN_BODY_PAGES_FOR_HEADING_CHECK:
        # Short document — skip; may not need a references section.
        return None, None, None

    # Long document with no recognized heading — emit finding.
    finding = AuditFinding(
        rule_id=_RULE_ID,
        severity=Severity.WARNING,
        page=body_start,
        message=(
            "No references section heading (REFERENCES, BIBLIOGRAPHY, WORKS CITED, or "
            "LITERATURE CITED) was detected in the body pages of this document. "
            "NJIT guidelines require a references section; its absence is a structural error."
        ),
        details={
            "issue_type": "references_section_heading_not_detected",
            "body_start_page": str(body_start),
            "body_page_count": str(body_page_count),
            "heading_type": "None",
            "confidence": "medium",
            "triage_tier": "medium",
            "source_q_rule_basis": "Self-Assessment Sheet p.4; Formatting Guidelines para 138",
        },
    )
    return finding, None, None


# ---------------------------------------------------------------------------
# Check B: Reference-entry indentation consistency
# ---------------------------------------------------------------------------


def _check_indentation(
    entries: list[list[PdfTextLine]],
    heading_page: int,
    section_page_count: int,
    heading_kw: str,
) -> AuditFinding | None:
    """Check whether multi-line reference entries have a consistent hanging-indent pattern.

    Returns a finding if inconsistency is detected, else None.
    """
    entry_count = len(entries)
    multi_line = [e for e in entries if len(e) >= 2]

    if entry_count < _MIN_ENTRIES_FOR_INDENT_CHECK:
        return None
    if len(multi_line) < _MIN_MULTILINE_FOR_INDENT_CHECK:
        return None

    # Compute indent_delta for each multi-line entry.
    deltas: list[float] = []
    first_xs: list[float] = []
    cont_xs: list[float] = []

    for entry in multi_line:
        first_x = entry[0].bbox.x0
        continuation_x0s = [line.bbox.x0 for line in entry[1:]]
        if not continuation_x0s:
            continue
        cont_x = statistics.median(continuation_x0s)
        delta = cont_x - first_x
        deltas.append(delta)
        first_xs.append(first_x)
        cont_xs.append(cont_x)

    if len(deltas) < _MIN_MULTILINE_FOR_INDENT_CHECK:
        return None

    median_delta = statistics.median(deltas)
    stdev_delta = statistics.stdev(deltas) if len(deltas) >= 2 else 0.0

    # If all entries are flush-left (|delta| < threshold for all) → uniform style,
    # possibly IEEE numbered flush-left.  Do not flag uniform flush-left.
    all_flush_left = all(abs(d) < _HANGING_INDENT_THRESHOLD_PT for d in deltas)
    if all_flush_left:
        return None

    # Flag inconsistency when stdev is high enough to show mixed patterns.
    if stdev_delta <= _INDENT_STDEV_THRESHOLD_PT:
        return None

    # Count affected entries: those whose delta differs significantly from median.
    affected = sum(
        1 for d in deltas if abs(d - median_delta) >= _HANGING_INDENT_THRESHOLD_PT
    )

    median_first_x = statistics.median(first_xs) if first_xs else 0.0
    median_cont_x = statistics.median(cont_xs) if cont_xs else 0.0

    finding = AuditFinding(
        rule_id=_RULE_ID,
        severity=Severity.WARNING,
        page=heading_page,
        message=(
            "Reference entries in the references section show inconsistent hanging-indent "
            "formatting. Some entries have continuation lines indented differently from "
            "others, suggesting mixed formatting within the section."
        ),
        details={
            "issue_type": "references_entry_indentation_inconsistent",
            "page_number": str(heading_page),
            "section_page_count": str(section_page_count),
            "entry_candidate_count": str(entry_count),
            "multi_line_entry_count": str(len(multi_line)),
            "affected_entry_count": str(affected),
            "median_indent_px": f"{median_delta:.1f}",
            "indent_inconsistency_score": f"{stdev_delta:.1f}",
            "first_line_x": f"{median_first_x:.1f}",
            "continuation_line_x": f"{median_cont_x:.1f}",
            "heading_type": _HEADING_TYPE_MAP.get(heading_kw, heading_kw),
            "confidence": "medium" if entry_count >= 8 else "low",
            "triage_tier": "medium" if entry_count >= 8 else "low",
            "source_q_rule_basis": "Q028,Q029 analogy; Self-Assessment Sheet p.4",
        },
    )
    return finding


# ---------------------------------------------------------------------------
# Check C: Reference-entry spacing consistency
# ---------------------------------------------------------------------------


def _check_spacing(
    entries: list[list[PdfTextLine]],
    heading_page: int,
    section_page_count: int,
    heading_kw: str,
) -> AuditFinding | None:
    """Check whether inter-entry vertical gaps are consistent.

    Returns a finding if irregular spacing is detected, else None.
    """
    entry_count = len(entries)
    if entry_count < _MIN_ENTRIES_FOR_SPACING_CHECK:
        return None

    # Compute inter-entry gaps using y0-to-y0 baseline from last line of entry N
    # to first line of entry N+1.  This avoids false measurements from overlapping
    # bboxes and is robust across PDF extraction variations.
    gaps: list[float] = []
    for i in range(len(entries) - 1):
        last_line_y0 = entries[i][-1].bbox.y0
        next_first_y0 = entries[i + 1][0].bbox.y0
        gap = next_first_y0 - last_line_y0
        if gap >= _MIN_INTER_ENTRY_GAP_PT:
            gaps.append(gap)

    if len(gaps) < 3:
        return None

    median_gap = statistics.median(gaps)
    if median_gap <= 0:
        return None

    # Count outlier gaps: those that are >2× the median.
    outlier_gaps = [g for g in gaps if g > 2.0 * median_gap]
    outlier_count = len(outlier_gaps)
    outlier_fraction = outlier_count / len(gaps)

    if outlier_fraction < _OUTLIER_GAP_FRACTION:
        return None

    # Require a meaningful absolute gap range to avoid noise.
    max_outlier = max(outlier_gaps)
    abs_range = max_outlier - median_gap
    if abs_range < _OUTLIER_GAP_ABS_THRESHOLD_PT:
        return None

    finding = AuditFinding(
        rule_id=_RULE_ID,
        severity=Severity.WARNING,
        page=heading_page,
        message=(
            "Reference entries in the references section show inconsistent inter-entry "
            "vertical spacing. Some entries have significantly larger gaps than others, "
            "suggesting mixed or irregular spacing within the section."
        ),
        details={
            "issue_type": "references_entry_spacing_inconsistent",
            "page_number": str(heading_page),
            "section_page_count": str(section_page_count),
            "entry_candidate_count": str(entry_count),
            "affected_entry_count": str(outlier_count),
            "median_gap_px": f"{median_gap:.1f}",
            "gap_outlier_count": str(outlier_count),
            "heading_type": _HEADING_TYPE_MAP.get(heading_kw, heading_kw),
            "confidence": "medium" if entry_count >= 8 else "low",
            "triage_tier": "medium" if entry_count >= 8 else "low",
            "source_q_rule_basis": "Q028 analogy; Self-Assessment Sheet p.4",
        },
    )
    return finding


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def check_pdf_references_citations_structural(
    pdf_doc: PdfDocument,
) -> list[AuditFinding]:
    """Emit P064 warnings for references/citations structural issues.

    Three conservative checks:
      A. references_section_heading_not_detected — heading absent in long doc.
      B. references_entry_indentation_inconsistent — mixed indent pattern.
      C. references_entry_spacing_inconsistent — irregular inter-entry gaps.

    Returns an empty list when skip conditions apply.
    Privacy: no reference entry text, author names, or citation content in findings.
    """
    if not pdf_doc.pages:
        return []

    body_start = _find_body_start_page(pdf_doc)
    if body_start is None:
        # No body region detected — likely front-matter only or image-only PDF.
        return []

    body_page_count = _count_body_pages(pdf_doc, body_start)

    # --- Check A: Heading detection ---
    heading_finding, heading_page, heading_kw = _check_heading(
        pdf_doc, body_start, body_page_count
    )

    if heading_finding is not None:
        # Heading not found, document long enough to warrant a finding.
        return [heading_finding]

    if heading_page is None:
        # No heading found but document too short to require one — skip silently.
        return []

    # --- Collect references section pages ---
    section_pages = _collect_references_section_pages(pdf_doc, heading_page)
    if not section_pages:
        return []

    section_page_count = len(section_pages)

    # --- Collect and group entry candidates ---
    lines = _collect_lines_from_section(section_pages, heading_page, heading_kw)  # type: ignore[arg-type]

    if not lines:
        # No text-layer content — image-only or flattened pages.
        return []

    # Skip: high x-coordinate variance (noisy geometry).
    x_var = _compute_x_variance(lines)
    if x_var > _HIGH_X_VARIANCE_THRESHOLD_PT:
        return []

    # Skip: multi-column layout detected.
    if _detect_multicolumn(lines):
        return []

    entries = _group_entries(lines)
    entry_count = len(entries)

    # Skip: too few entries to be meaningful.
    if entry_count < _MIN_ENTRIES_FOR_SECTION_NONEMPTY:
        return []

    findings: list[AuditFinding] = []

    # --- Check B: Indentation consistency ---
    indent_finding = _check_indentation(
        entries, heading_page, section_page_count, heading_kw  # type: ignore[arg-type]
    )
    if indent_finding is not None:
        findings.append(indent_finding)

    # --- Check C: Spacing consistency ---
    spacing_finding = _check_spacing(
        entries, heading_page, section_page_count, heading_kw  # type: ignore[arg-type]
    )
    if spacing_finding is not None:
        findings.append(spacing_finding)

    return findings
