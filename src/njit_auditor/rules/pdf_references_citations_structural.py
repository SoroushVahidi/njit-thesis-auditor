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

OS-009 adds page-local spacing compliance checks with entry boundaries anchored
by sequential labels or repeated hanging indentation, independently of gaps.
The November 9, 2026 reviewer feedback specifies single spacing within each
reference and double spacing between references. Guidelines para 139 retain
advisor/discipline citation-style choice; no exact point-pitch standard is stated.
Only clear single-like separators calibrated by measured internal wraps and
clear double-like internal gaps with reliable font evidence are reported.
Ambiguous boundaries, page-crossing gaps and intermediate pitches abstain.
Existing indentation and irregularity thresholds remain unchanged.

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
  - No body anchor in a short document; long documents use a unique heading fallback.
  - No recognized references heading AND document has fewer than 5 body pages.
  - Fewer than 3 multi-line entry candidates → skip check B.
  - Fewer than 5 entry candidates → skip checks B and C.
  - Image-only or flattened pages (no text-layer blocks).
  - High x-coordinate variance on references section lines (std dev > 50 pt).
  - References section too short (<2 pages AND <5 entries).
  - Mixed multi-column layout detected (≥3 distinct left-margin clusters).
"""

from __future__ import annotations

import math
import re
import statistics

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine

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
_COLLAPSED_CHAPTER_APPENDIX_RE = re.compile(
    r"^(CHAPTER|APPENDIX)([IVXLC\d]+)$",
    re.IGNORECASE,
)
_TOC_LEADER_RE = re.compile(r"\.{2,}|\s{2,}[\dIVXLC]+$", re.IGNORECASE)

# P071 localization: body heading should appear in the upper third of the page.
_BODY_HEADING_MAX_Y_FRAC = 0.33
_TAIL_HEADING_MAX_Y_FRAC = 0.5
_MAX_BODY_HEADING_LEN = 80

# P071 tail-scan window for back-matter references heading fallback.
_TAIL_SCAN_MAX_PAGES = 30
_TAIL_SCAN_MIN_DOC_PAGES = 20

# P071 cluster-based x-variance (dominant entry-indent band).
_CLUSTER_X_TOLERANCE_PT = 12.0

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


def _collapsed_heading_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip()).upper()


def _matches_chapter_appendix_heading(text: str) -> bool:
    clean = " ".join(text.strip().split())
    if _CHAPTER_APPENDIX_RE.match(clean):
        return True
    return bool(_COLLAPSED_CHAPTER_APPENDIX_RE.match(_collapsed_heading_text(text)))


def _is_standalone_body_heading_line(line: PdfTextLine, page: PdfPage) -> bool:
    clean = " ".join(line.text.strip().split())
    if len(clean) > _MAX_BODY_HEADING_LEN:
        return False
    if page.height <= 0:
        return True
    return line.bbox.y0 <= page.height * _BODY_HEADING_MAX_Y_FRAC


def _is_tail_heading_line(line: PdfTextLine, page: PdfPage) -> bool:
    clean = " ".join(line.text.strip().split())
    if len(clean) > _MAX_HEADING_LEN:
        return False
    if page.height <= 0:
        return True
    return line.bbox.y0 <= page.height * _TAIL_HEADING_MAX_Y_FRAC


def _find_body_start_page(pdf_doc: PdfDocument) -> int | None:
    """Return the first page number where a CHAPTER or APPENDIX body heading is found."""
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if _matches_chapter_appendix_heading(clean) and _is_standalone_body_heading_line(
                    line, page
                ):
                    return page.page_number
    return None


def _tail_scan_start_page(page_count: int) -> int:
    window = min(_TAIL_SCAN_MAX_PAGES, math.ceil(page_count * 0.25))
    return max(1, page_count - window + 1)


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
    raw = line.text
    # Some Word PDFs retain a small numeric field beside the visible bold
    # heading. Recover only a separate, smaller span touching that heading;
    # never strip a same-size chapter/subsection number from arbitrary text.
    spans = [span for span in line.spans if span.text.strip()]
    if len(spans) >= 2 and spans[0].text.strip().isdigit():
        prefix, rest = spans[0], spans[1:]
        if (
            prefix.size
            and all(s.size and s.size >= prefix.size * 1.4 for s in rest)
            and all(s.bold for s in rest)
            and -2 <= rest[0].bbox.x0 - prefix.bbox.x1 <= 2
        ):
            raw = "".join(s.text for s in rest)
    if _TOC_LEADER_RE.search(raw):
        return None
    clean = _normalized_heading(raw)
    if len(clean) > _MAX_HEADING_LEN:
        return None
    # Reject lines that begin with a digit (numbered section headings like "3. References")
    if clean and clean[0].isdigit():
        return None
    # Reject lines that look like inline citations: "[1]", "(Author, 2023)"
    if clean.startswith("[") or clean.startswith("("):
        return None
    for keyword in _HEADING_KEYWORDS:
        # Letter-spaced and span-fragmented headings retain the same identity.
        if _collapsed_heading_text(clean).removesuffix(":") == _collapsed_heading_text(keyword):
            return keyword
    return None


def _line_y(line: PdfTextLine) -> float:
    return line.baseline_y if line.baseline_y is not None else line.bbox.y0


def _join_row(lines: list[PdfTextLine]) -> PdfTextLine | None:
    """Join disjoint fragments on one baseline; overlapping extraction abstains."""
    ordered = sorted(lines, key=lambda line: line.bbox.x0)
    if any(a.bbox.x1 > b.bbox.x0 + 2 for a, b in zip(ordered, ordered[1:])):
        return None
    for a, b in zip(ordered, ordered[1:]):
        size = max((span.size or 0 for row in (a, b) for span in row.spans), default=0)
        if (
            any(c.isalpha() for c in a.text)
            and any(c.isalpha() for c in b.text)
            and b.bbox.x0 - a.bbox.x1 > 3 * size
        ):
            # Distant text columns are not fragments of one reference row.
            return None
    first = ordered[0]
    return first.model_copy(
        update={
            "text": " ".join(line.text for line in ordered),
            "spans": [span for line in ordered for span in line.spans],
            "bbox": BBox(
                x0=first.bbox.x0,
                y0=min(line.bbox.y0 for line in ordered),
                x1=max(line.bbox.x1 for line in ordered),
                y1=max(line.bbox.y1 for line in ordered),
            ),
        }
    )


def _page_heading(page: PdfPage) -> tuple[PdfTextLine, str] | None:
    lines = [line for block in page.text_blocks for line in block.lines if line.text.strip()]
    if any(
        _collapsed_heading_text(line.text).startswith("TABLEOFCONTENTS")
        for line in lines
        if _is_tail_heading_line(line, page)
    ):
        return None
    for line in lines:
        if not _is_tail_heading_line(line, page):
            continue
        peers = [other for other in lines if abs(_line_y(other) - _line_y(line)) <= 2]
        row = _join_row(peers)
        if row is None:
            continue
        keyword = _is_references_heading(row)
        if keyword is not None:
            size = max((s.size or 0 for s in row.spans), default=0)
            if any(2 < abs(_line_y(other) - _line_y(row)) < size * 1.5 for other in lines):
                continue
            return row, keyword
    return None


def _find_references_heading_forward(
    pdf_doc: PdfDocument, body_start: int
) -> tuple[int, str] | None:
    """Return (page_number, heading_keyword) scanning forward from body_start."""
    for page in pdf_doc.pages:
        if page.page_number < body_start:
            continue
        heading = _page_heading(page)
        if heading is not None:
            return page.page_number, heading[1]
    return None


def _find_references_heading_tail(pdf_doc: PdfDocument) -> tuple[int, str] | None:
    """Conservative back-matter tail scan for a standalone references heading."""
    page_count = len(pdf_doc.pages)
    if page_count < _TAIL_SCAN_MIN_DOC_PAGES:
        return None

    tail_start = _tail_scan_start_page(page_count)
    matches: list[tuple[int, str]] = []
    for page in pdf_doc.pages:
        if page.page_number < tail_start:
            continue
        heading = _page_heading(page)
        if heading is not None:
            matches.append((page.page_number, heading[1]))

    if len(matches) != 1:
        return None
    return matches[0]


def _localize_references_heading(
    pdf_doc: PdfDocument,
    body_start: int | None,
) -> tuple[int, str] | None:
    """Scan all body pages, or require a unique document-wide heading without a body anchor."""
    if body_start is not None:
        forward = _find_references_heading_forward(pdf_doc, body_start)
        if forward is not None:
            return forward
        return _find_references_heading_tail(pdf_doc)

    if len(pdf_doc.pages) < _TAIL_SCAN_MIN_DOC_PAGES:
        return None
    matches = [
        (page.page_number, heading[1])
        for page in pdf_doc.pages
        if (heading := _page_heading(page)) is not None
    ]
    return matches[0] if len(matches) == 1 else None


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
                    clean = " ".join(line.text.strip().split())
                    if (
                        _matches_chapter_appendix_heading(clean)
                        and _is_standalone_body_heading_line(line, page)
                        and not _TOC_LEADER_RE.search(clean)
                        and (
                            clean == clean.upper()
                            or clean.split()[0] in {"CHAPTER", "APPENDIX"}
                            or all(span.bold for span in line.spans if span.text.strip())
                        )
                    ):
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


def _group_entries(
    lines: list[PdfTextLine],
    line_pages: dict[int, int] | None = None,
) -> list[list[PdfTextLine]]:
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
        same_page = line_pages is None or line_pages[id(line)] == line_pages[id(groups[-1][-1])]
        if same_page and y0_gap <= _INTRA_ENTRY_Y0_GAP_PT:
            groups[-1].append(line)
        else:
            groups.append([line])

    return groups


def _cluster_lines_by_x0(lines: list[PdfTextLine]) -> list[list[PdfTextLine]]:
    if not lines:
        return []
    sorted_lines = sorted(lines, key=lambda line: line.bbox.x0)
    clusters: list[list[PdfTextLine]] = [[sorted_lines[0]]]
    for line in sorted_lines[1:]:
        if abs(line.bbox.x0 - clusters[-1][-1].bbox.x0) <= _CLUSTER_X_TOLERANCE_PT:
            clusters[-1].append(line)
        else:
            clusters.append([line])
    return clusters


def _dominant_entry_cluster(lines: list[PdfTextLine]) -> list[PdfTextLine]:
    """Return lines in the largest left-margin cluster (P071 noise filter)."""
    clusters = _cluster_lines_by_x0(lines)
    if not clusters:
        return []
    return max(clusters, key=len)


def _compute_x_variance(lines: list[PdfTextLine]) -> float:
    """Return standard deviation of x0 on the dominant entry cluster (P071)."""
    cluster = _dominant_entry_cluster(lines)
    if len(cluster) < 2:
        return 0.0
    x0s = [line.bbox.x0 for line in cluster]
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
    body_start: int | None,
    body_page_count: int,
) -> tuple[AuditFinding | None, int | None, str | None]:
    """Run heading check.  Returns (finding_or_None, heading_page_or_None, heading_kw_or_None).

    If the heading is found, finding is None (no problem) and heading details are returned.
    If the heading is not found and the document is long enough, a finding is emitted.
    If the document is too short to expect a references section, returns (None, None, None).
    """
    heading_result = _localize_references_heading(pdf_doc, body_start)

    if heading_result is not None:
        heading_page, heading_kw = heading_result
        return None, heading_page, heading_kw

    # No heading found.
    if body_page_count < _MIN_BODY_PAGES_FOR_HEADING_CHECK:
        # Short document — skip; may not need a references section.
        return None, None, None

    # Long document with no recognized heading — emit finding.
    absence_page = (
        body_start if body_start is not None else _tail_scan_start_page(len(pdf_doc.pages))
    )
    finding = AuditFinding(
        rule_id=_RULE_ID,
        severity=Severity.WARNING,
        page=absence_page,
        message=(
            "No references section heading (REFERENCES, BIBLIOGRAPHY, WORKS CITED, or "
            "LITERATURE CITED) was detected in the body pages of this document. "
            "NJIT guidelines require a references section; its absence is a structural error."
        ),
        details={
            "issue_type": "references_section_heading_not_detected",
            "body_start_page": str(absence_page),
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
    affected = sum(1 for d in deltas if abs(d - median_delta) >= _HANGING_INDENT_THRESHOLD_PT)

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
    line_pages: dict[int, int] | None = None,
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
        if (
            line_pages is not None
            and line_pages[id(entries[i][-1])] != line_pages[id(entries[i + 1][0])]
        ):
            continue
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


# OS-009 compliance checks use boundaries independent of vertical spacing.
# The reviewer specifies single-within/double-between; these evidence bands
# deliberately report only clear single-like separators / double-like wraps.
# They are not an NJIT point-size standard or a change to P023/R036 thresholds.
_NUMBERED_ENTRY_RE = re.compile(r"^\s*(?:\[(\d+)\]|\((\d+)\)|(\d+)\.)\s+\S")
_SINGLE_PITCH_FONT_MIN = 0.9
_SINGLE_PITCH_FONT_MAX = 1.35
_DOUBLE_PITCH_FONT_MIN = 1.8
_DOUBLE_PITCH_FONT_MAX = 2.6


def _reference_rows(page: PdfPage, heading_page: int) -> list[PdfTextLine]:
    heading = _page_heading(page)
    if page.page_number == heading_page and heading is None:
        return []
    lower = heading[0].bbox.y1 if heading is not None else page.height * 0.08
    # Keep short continuation lines and detached numeric labels. Discard only
    # empty text and the page's header/footer region, never by paragraph length.
    lines = sorted(
        [
            line
            for block in page.text_blocks
            for line in block.lines
            if line.text.strip() and lower < line.bbox.y0 < page.height * 0.92
        ],
        key=lambda line: (_line_y(line), line.bbox.x0),
    )
    rows: list[list[PdfTextLine]] = []
    for line in lines:
        if rows and abs(_line_y(line) - _line_y(rows[-1][0])) <= 2:
            rows[-1].append(line)
        else:
            rows.append([line])
    merged = [_join_row(row) for row in rows]
    if any(row is None for row in merged):
        return []
    return [row for row in merged if row is not None]


def _anchored_entries(rows: list[PdfTextLine]) -> tuple[list[list[PdfTextLine]], str]:
    """Recognize sequential labels or repeated hanging indents, never by gap.

    Page-leading unanchored text may continue an entry from the previous page;
    it is excluded. No measured pair crosses a physical page boundary.
    """
    markers = [
        (i, match)
        for i, row in enumerate(rows)
        if (match := _NUMBERED_ENTRY_RE.match(row.text)) is not None
    ]
    starts: list[int]
    if markers:
        label_x = min(rows[i].bbox.x0 for i, _ in markers)
        # A year or numeric identifier on an indented wrapped line is not a
        # new entry. Only the leftmost label column may establish boundaries.
        if any(2 < rows[i].bbox.x0 - label_x < _HANGING_INDENT_THRESHOLD_PT for i, _ in markers):
            return [], ""
        markers = [(i, match) for i, match in markers if rows[i].bbox.x0 <= label_x + 2]
        if len(markers) < _MIN_ENTRIES_FOR_SPACING_CHECK:
            return [], ""
        numbers = [int(next(value for value in match.groups() if value)) for _, match in markers]
        if any(b != a + 1 for a, b in zip(numbers, numbers[1:])):
            return [], ""
        starts = [i for i, _ in markers]
        xs = [rows[i].bbox.x0 for i in starts]
        if max(xs) - min(xs) > 2:
            return [], ""
        mode = "sequential_numeric_labels"
    else:
        # Citation text is deliberately not parsed as author/year syntax.
        # Require two tight indentation bands, recurring complete multiline
        # entries, and no other left margins before using unnumbered geometry.
        clusters = _cluster_lines_by_x0(rows)
        if len(clusters) != 2:
            return [], ""
        left, right = clusters
        if any(
            max(r.bbox.x0 for r in band) - min(r.bbox.x0 for r in band) > 2 for band in clusters
        ):
            return [], ""
        delta = right[0].bbox.x0 - left[0].bbox.x0
        if not _HANGING_INDENT_THRESHOLD_PT <= delta <= _HIGH_X_VARIANCE_THRESHOLD_PT:
            return [], ""
        starts = [i for i, row in enumerate(rows) if abs(row.bbox.x0 - left[0].bbox.x0) <= 2]
        mode = "repeated_hanging_indent"
    if len(starts) < _MIN_ENTRIES_FOR_SPACING_CHECK:
        return [], ""
    entries = [rows[start:end] for start, end in zip(starts, starts[1:] + [len(rows)])]
    if any(not _is_usable_entry_line(entry[0]) for entry in entries):
        return [], ""
    if mode == "repeated_hanging_indent" and any(len(entry) < 2 for entry in entries):
        return [], ""
    # A numbered wrapped line cannot precede its own label column.
    if any(line.bbox.x0 < entry[0].bbox.x0 - 2 for entry in entries for line in entry[1:]):
        return [], ""
    return entries, mode


def _row_font_size(line: PdfTextLine) -> float | None:
    sizes = [
        span.size
        for span in line.spans
        if span.size and any(character.isalpha() for character in span.text)
    ]
    if not sizes:
        # Short numeric/URL continuations still need measured font metadata.
        sizes = [span.size for span in line.spans if span.size and span.text.strip()]
    return statistics.median(sizes) if sizes else None


def _measured_pair(a: PdfTextLine, b: PdfTextLine) -> tuple[float, float] | None:
    a_size, b_size = _row_font_size(a), _row_font_size(b)
    if not a_size or not b_size or max(a_size, b_size) / min(a_size, b_size) > 1.1:
        return None
    size = (a_size + b_size) / 2
    if any(line.bbox.height > 1.6 * size for line in (a, b)):
        return None
    # Use actual baselines when both are measured; otherwise compare like y0s.
    pitch = (
        b.baseline_y - a.baseline_y
        if a.baseline_y is not None and b.baseline_y is not None
        else b.bbox.y0 - a.bbox.y0
    )
    if pitch <= 2:
        return None
    return pitch, size


def _check_spacing_pattern(
    section_pages: list[PdfPage], heading_page: int, heading_kw: str
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for page in section_pages:
        rows = _reference_rows(page, heading_page)
        if _detect_multicolumn(rows):
            continue
        entries, mode = _anchored_entries(rows)
        if not entries:
            continue
        internal = [
            pair
            for entry in entries
            for a, b in zip(entry, entry[1:])
            if (pair := _measured_pair(a, b)) is not None
        ]
        if len(internal) < _MIN_MULTILINE_FOR_INDENT_CHECK:
            continue
        single = [
            pitch
            for pitch, size in internal
            if _SINGLE_PITCH_FONT_MIN <= pitch / size <= _SINGLE_PITCH_FONT_MAX
        ]
        large = [
            pitch
            for pitch, size in internal
            if _DOUBLE_PITCH_FONT_MIN <= pitch / size <= _DOUBLE_PITCH_FONT_MAX
        ]
        common = {
            "page_number": str(page.page_number),
            "references_start_page": str(heading_page),
            "entry_candidate_count": str(len(entries)),
            "boundary_evidence": mode,
            "heading_type": _HEADING_TYPE_MAP[heading_kw],
            "confidence": "medium",
            "triage_tier": "medium",
            "source_q_rule_basis": "References spacing reviewer guidance 2026-11-09; "
            "Formatting Guidelines para 139 (citation-style flexibility)",
            "suggested_fix": "Use single spacing within each reference and double spacing "
            "between consecutive references. Keep the citation style agreed "
            "with your advisor.",
        }
        if len(large) >= 2:
            findings.append(
                AuditFinding(
                    rule_id=_RULE_ID,
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message="Reference entries contain line gaps consistent with double spacing. "
                    "Use single spacing within each reference and double spacing "
                    "between entries.",
                    details={
                        **common,
                        "issue_type": "references_entry_not_single_spaced",
                        "affected_gap_count": str(len(large)),
                        "median_internal_pitch_pt": f"{statistics.median(large):.1f}",
                    },
                )
            )
        if len(single) < _MIN_MULTILINE_FOR_INDENT_CHECK:
            continue
        single_pitch = statistics.median(single)
        # Local wrap evidence must itself be coherent; never calibrate from
        # uniformly double-spaced wraps or blend incompatible font populations.
        if max(single) - min(single) > single_pitch * 0.15:
            continue
        between = [
            pair
            for a, b in zip(entries, entries[1:])
            if (pair := _measured_pair(a[-1], b[0])) is not None
        ]
        tight = [
            pitch
            for pitch, size in between
            if _SINGLE_PITCH_FONT_MIN <= pitch / size <= _SINGLE_PITCH_FONT_MAX
            and pitch <= single_pitch * 1.25
        ]
        if len(tight) >= 3:
            findings.append(
                AuditFinding(
                    rule_id=_RULE_ID,
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message="Consecutive reference entries have gaps close to the measured "
                    "single-line spacing within entries. Use double spacing between references "
                    "while keeping each reference single-spaced internally.",
                    details={
                        **common,
                        "issue_type": "references_inter_entry_spacing_too_tight",
                        "affected_gap_count": str(len(tight)),
                        "measured_inter_entry_gap_count": str(len(between)),
                        "single_line_pitch_pt": f"{single_pitch:.1f}",
                        "median_inter_entry_pitch_pt": f"{statistics.median(tight):.1f}",
                    },
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def check_pdf_references_citations_structural(
    pdf_doc: PdfDocument,
) -> list[AuditFinding]:
    """Emit P064 warnings for references/citations structural issues.

    Structural checks plus page-local spacing compliance:
      A. references_section_heading_not_detected — heading absent in long doc.
      B. references_entry_indentation_inconsistent — mixed indent pattern.
      C. references_entry_spacing_inconsistent — irregular inter-entry gaps.
      D. references_entry_not_single_spaced — supported double-like internal gaps.
      E. references_inter_entry_spacing_too_tight — supported single-like separators.

    Returns an empty list when skip conditions apply.
    Privacy: no reference entry text, author names, or citation content in findings.
    """
    if not pdf_doc.pages:
        return []

    page_count = len(pdf_doc.pages)
    body_start = _find_body_start_page(pdf_doc)
    if body_start is not None:
        body_page_count = _count_body_pages(pdf_doc, body_start)
    elif page_count >= _TAIL_SCAN_MIN_DOC_PAGES:
        tail_start = _tail_scan_start_page(page_count)
        body_page_count = page_count - tail_start + 1
    else:
        return []

    # --- Check A: Heading detection (P071 localization wired in _check_heading) ---
    heading_finding, heading_page, heading_kw = _check_heading(pdf_doc, body_start, body_page_count)

    if heading_finding is not None:
        # Heading not found, document long enough to warrant a finding.
        return [heading_finding]

    if heading_page is None or heading_kw is None:
        # No heading found but document too short to require one — skip silently.
        return []

    # --- Collect references section pages ---
    section_pages = _collect_references_section_pages(pdf_doc, heading_page)
    if not section_pages:
        return []

    section_page_count = len(section_pages)

    findings = _check_spacing_pattern(section_pages, heading_page, heading_kw)

    # --- Collect and group entry candidates ---
    lines = _collect_lines_from_section(section_pages, heading_page, heading_kw)

    if not lines:
        # No text-layer content — image-only or flattened pages.
        return []

    # P071: cluster-based x-variance skip (annotation outliers); entry checks use all lines.
    x_var = _compute_x_variance(lines)
    if x_var > _HIGH_X_VARIANCE_THRESHOLD_PT:
        return []

    # Skip: multi-column layout detected.
    if _detect_multicolumn(lines):
        return []

    line_pages = {
        id(line): page.page_number
        for page in section_pages
        for block in page.text_blocks
        for line in block.lines
    }
    entries = _group_entries(lines, line_pages)
    entry_count = len(entries)

    # Skip: too few entries to be meaningful.
    if entry_count < _MIN_ENTRIES_FOR_SECTION_NONEMPTY:
        return findings

    # --- Check B: Indentation consistency ---
    indent_finding = _check_indentation(
        entries,
        heading_page,
        section_page_count,
        heading_kw,
    )
    if indent_finding is not None:
        findings.append(indent_finding)

    # --- Check C: Spacing consistency ---
    spacing_finding = _check_spacing(
        entries,
        heading_page,
        section_page_count,
        heading_kw,
        line_pages,
    )
    if spacing_finding is not None:
        findings.append(spacing_finding)

    return findings


def references_section_page_numbers(pdf_doc: PdfDocument) -> frozenset[int]:
    """Return the page numbers that belong to the References/Bibliography section.

    Reuses this module's heading localization and section-span logic so other
    rules (e.g. P023 body double-spacing) can exclude the entire references
    section — including continuation pages that do not repeat the heading —
    rather than only the single page carrying the heading. Returns an empty set
    when no references section can be confidently located.
    """
    if not pdf_doc.pages:
        return frozenset()
    body_start = _find_body_start_page(pdf_doc)
    located = _localize_references_heading(pdf_doc, body_start)
    if located is None:
        return frozenset()
    heading_page, _ = located
    section_pages = _collect_references_section_pages(pdf_doc, heading_page)
    return frozenset(page.page_number for page in section_pages)
