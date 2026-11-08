"""Conservative Biographical Sketch publication entry checks (P045).

Entries must not be numbered. Ester, 2026-10-06: "The list of publications on
this page MUST NOT BE NUMBERED" -- they are not references, so they keep the
References citation format but drop the number in front. An entry that starts
with a list label ("[1]", "(1)", "1.", "1)") is reported. This check needs no
entry segmentation, so a single numbered entry is enough.

Partial heuristic PDF coverage for Q028 ("Is each entry in Publications and
Presentations single-spaced with a blank line between entries?"):
  - wrapped lines within one publication/presentation entry are single-spaced;
  - consecutive entries are separated by a blank line.

Q029 (hanging indent) is not enforced. Ester confirmed on 2026-10-05 that a
hanging indent is not mandatory: entries without one are acceptable. Hanging
geometry is still read, but only to tell where one entry ends and the next
begins; its absence is never reported.

Only the Publications/Presentations section of the BIOGRAPHICAL SKETCH page is
inspected (education bullets belong to P047). Entries are separated by visible
entry labels ("[1]", "(2)", "3.") when present, otherwise by hanging-indent
geometry; a section whose entries cannot be separated is skipped. Does not
read or quote publication text, author names, citation content, or
biographical prose. Does not duplicate P015 (general indentation), P043
(Acknowledgements), P044 (Abstract), P047 (education bullets), or P067
(publication ordering).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median as _median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_frontmatter_heading_gate import find_gate_heading_page_and_y

HANGING_THRESHOLD_PT = 12.0
MAX_PARA_GAP_PT = 14.0
MIN_TEXT_LEN = 20
_HEADING_LABEL = "BIOGRAPHICAL SKETCH"
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)

# Rows whose top edges are this close belong to one visual line (LaTeX can
# split a justified line into many fragments).
_ROW_Y_TOLERANCE_PT = 2.0
# A row starting within this distance of the section's left edge is flush.
_FLUSH_TOLERANCE_PT = 3.0
# Within one entry, a line pitch (top-to-top step) above this multiple of the
# font size is wider than single spacing. Single-spaced Word and LaTeX entries
# measure about 1.15-1.2x the font size; double spacing is about 2x.
WITHIN_ENTRY_MAX_PITCH_RATIO = 1.6
# A blank line between entries makes the step from one entry's last line to
# the next entry's first line at least this multiple of the within-entry pitch
# (observed 1.66-2.0x with a blank line, 1.0x without one).
BLANK_LINE_MIN_PITCH_RATIO = 1.5

_PUBLICATION_HEADING_KEYS = frozenset(
    {
        "PUBLICATIONS",
        "PRESENTATIONS",
        "PUBLICATIONSANDPRESENTATIONS",
        "PRESENTATIONSANDPUBLICATIONS",
    }
)
_FOOTER_ZONE_PT = 72.0
_MAX_SECTION_LABEL_WORDS = 6
_ENTRY_LABEL_RE = re.compile(r"^\s*(?:\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}[.)])(?:\s|$)")
_BRACKET_LABEL_RE = re.compile(r"^\s*\[\d{1,3}\](?:\s|$)")


def _is_usable_line(line: PdfTextLine) -> bool:
    cleaned = " ".join(line.text.strip().split())
    if len(cleaned) < MIN_TEXT_LEN:
        return False
    if _PAGE_NUM_RE.match(cleaned):
        return False
    alpha_count = sum(ch.isalpha() for ch in cleaned)
    return alpha_count >= 10 and alpha_count / max(len(cleaned), 1) >= 0.45


def _find_biosketch_page_and_heading_y(
    pdf_document: PdfDocument,
) -> tuple[PdfPage, float] | None:
    """Return (page, heading_bottom_y) for the BIOGRAPHICAL SKETCH page, or None."""
    return find_gate_heading_page_and_y(pdf_document, _HEADING_LABEL)


def _lines_below_heading(
    page: PdfPage, heading_bottom_y: float
) -> list[PdfTextLine]:
    lines = []
    for block in page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= heading_bottom_y + 2:
                continue
            if _is_usable_line(line):
                lines.append(line)
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _group_paragraphs(lines: list[PdfTextLine]) -> list[list[PdfTextLine]]:
    if not lines:
        return []
    groups: list[list[PdfTextLine]] = [[lines[0]]]
    for line in lines[1:]:
        gap = line.bbox.y0 - groups[-1][-1].bbox.y1
        if gap <= MAX_PARA_GAP_PT:
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def _has_hanging_indent(block: list[PdfTextLine]) -> bool:
    """Return True if block exhibits hanging-indent pattern (continuations more indented)."""
    if len(block) < 2:
        return False
    first_x0 = block[0].bbox.x0
    rest_x0s = [line.bbox.x0 for line in block[1:]]
    rest_median = _median(rest_x0s)
    return (rest_median - first_x0) >= HANGING_THRESHOLD_PT


@dataclass(frozen=True)
class _Row:
    """One visual line: every extracted fragment sharing a baseline."""

    x0: float
    y0: float
    y1: float
    text: str
    font_size: float
    baseline_y: float | None = None
    x1: float = 0.0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


def _rows_bbox(rows: list[_Row]) -> str:
    """Highlight box covering *rows* (the lines the finding is about)."""
    return format_bbox_detail(
        (
            min(row.x0 for row in rows),
            min(row.y0 for row in rows),
            max(max(row.x1, row.x0) for row in rows),
            max(row.y1 for row in rows),
        )
    )


def _line_step(earlier: _Row, later: _Row) -> float:
    """Return the baseline step between two rows.

    Span origins are the authoritative baseline when available. Without
    origins, retain the prior smaller-edge estimate for synthetic geometry.
    """
    if earlier.baseline_y is not None and later.baseline_y is not None:
        return later.baseline_y - earlier.baseline_y
    return min(later.y0 - earlier.y0, later.y1 - earlier.y1)


def _letters_key(text: str) -> str:
    return "".join(ch for ch in text.upper() if ch.isalpha())


def _rows_for_page(page: PdfPage) -> list[_Row]:
    lines = sorted(
        (line for block in page.text_blocks for line in block.lines if line.text.strip()),
        key=lambda line: (line.bbox.y0, line.bbox.x0),
    )
    clusters: list[list[PdfTextLine]] = []
    for line in lines:
        if clusters and abs(line.bbox.y0 - clusters[-1][0].bbox.y0) <= _ROW_Y_TOLERANCE_PT:
            clusters[-1].append(line)
        else:
            clusters.append([line])
    rows = []
    for cluster in clusters:
        ordered = sorted(cluster, key=lambda line: line.bbox.x0)
        rows.append(
            _Row(
                x0=ordered[0].bbox.x0,
                x1=max(line.bbox.x1 for line in ordered),
                y0=min(line.bbox.y0 for line in ordered),
                y1=max(line.bbox.y1 for line in ordered),
                text=" ".join(" ".join(line.text.split()) for line in ordered),
                font_size=max(
                    (span.size or 0.0 for line in ordered for span in line.spans),
                    default=0.0,
                )
                or max(line.bbox.height for line in ordered),
                baseline_y=(
                    _median(
                        [line.baseline_y for line in ordered if line.baseline_y is not None]
                    )
                    if any(line.baseline_y is not None for line in ordered)
                    else None
                ),
            )
        )
    return rows


def _publication_section_rows(page: PdfPage, heading_bottom_y: float) -> list[_Row]:
    """Rows between the Publications/Presentations label and the next section."""
    rows = [row for row in _rows_for_page(page) if row.y0 > heading_bottom_y + 2]
    start = next(
        (
            index
            for index, row in enumerate(rows)
            if _letters_key(row.text) in _PUBLICATION_HEADING_KEYS
        ),
        None,
    )
    if start is None:
        return []
    heading_x0 = rows[start].x0
    section: list[_Row] = []
    for row in rows[start + 1 :]:
        if row.y0 >= page.height - _FOOTER_ZONE_PT and _PAGE_NUM_RE.match(row.text):
            break
        key = _letters_key(row.text)
        if key in _PUBLICATION_HEADING_KEYS:
            # "Publications:" / "Presentations:" sub-labels inside the section.
            continue
        if _is_section_label(row) and abs(row.x0 - heading_x0) <= _FLUSH_TOLERANCE_PT:
            break
        section.append(row)
    return section


def _is_section_label(row: _Row) -> bool:
    """A short "Label:" row such as another Biographical Sketch heading."""
    return (
        row.text.endswith(":")
        and len(row.text.split()) <= _MAX_SECTION_LABEL_WORDS
        and not any(ch.isdigit() for ch in row.text)
    )


def _split_entries(rows: list[_Row]) -> tuple[list[list[_Row]], str]:
    """Split section rows into entries; return (entries, segmentation method)."""
    left = min((row.x0 for row in rows), default=0.0)
    flush = [row for row in rows if row.x0 <= left + _FLUSH_TOLERANCE_PT]
    indented = [row for row in rows if row.x0 >= left + HANGING_THRESHOLD_PT]
    # Hanging geometry is used only to locate entry boundaries; a missing
    # hanging indent is acceptable (Ester, 2026-10-05).
    hanging_layout = bool(flush) and bool(indented) and (
        len(flush) + len(indented) == len(rows)
    )

    starts: list[bool]
    label_rows = [row for row in rows if _ENTRY_LABEL_RE.match(row.text)]
    if len(label_rows) >= 2:
        method = "entry_labels"
        starts = [bool(_ENTRY_LABEL_RE.match(row.text)) for row in rows]
    elif hanging_layout and len(flush) >= 2:
        method = "hanging_indent"
        starts = [row.x0 <= left + _FLUSH_TOLERANCE_PT for row in rows]
    else:
        return [], ""

    entries: list[list[_Row]] = []
    for row, is_start in zip(rows, starts):
        if is_start:
            entries.append([row])
        elif entries:
            entries[-1].append(row)
    return entries, method


def _numbered_entry_rows(rows: list[_Row]) -> list[_Row]:
    """Rows that open an entry with a list number.

    Only rows at the section's left edge count, so citation-internal numbers
    (years, volumes, pages, DOIs) never qualify: they are not at a row start,
    and four-digit years do not match the label pattern. A bracketed "[n]"
    label is unambiguous on its own; "(n)", "n." and "n)" count when they open
    the section or when at least two rows carry such a label.
    """
    if not rows:
        return []
    left = min(row.x0 for row in rows)
    labelled = [
        row
        for row in rows
        if row.x0 <= left + _FLUSH_TOLERANCE_PT and _ENTRY_LABEL_RE.match(row.text)
    ]
    if len(labelled) >= 2:
        return labelled
    return [
        row for row in labelled if _BRACKET_LABEL_RE.match(row.text) or row is rows[0]
    ]


def _numbering_style(row: _Row) -> str:
    text = row.text.lstrip()
    if text.startswith("["):
        return "bracketed_number"
    if text.startswith("("):
        return "parenthesized_number"
    return "number_with_period" if re.match(r"\d+\.", text) else "number_with_parenthesis"


def check_pdf_biosketch_publication_layout(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P045 warnings for numbered or mis-spaced Bio Sketch publication entries."""
    result = _find_biosketch_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_bottom_y = result
    rows = _publication_section_rows(page, heading_bottom_y)

    findings: list[AuditFinding] = []
    numbered = _numbered_entry_rows(rows)
    if numbered:
        first = numbered[0]
        findings.append(
            AuditFinding(
                rule_id="P045",
                severity=Severity.WARNING,
                page=page.page_number,
                message=(
                    "Publication/presentation entries on the Biographical Sketch page "
                    "are numbered; they must not be numbered."
                ),
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "biosketch_publication_entry_numbered",
                    "numbered_entry_count": str(len(numbered)),
                    "numbering_style": _numbering_style(first),
                    "bbox": format_bbox_detail((first.x0, first.y0, first.x1, first.y1)),
                    "confidence": "high",
                    "triage_tier": "high",
                },
            )
        )

    entries, method = _split_entries(rows)
    if len(entries) < 2 or not any(len(entry) >= 2 for entry in entries):
        return findings

    font_size = _median([row.font_size for row in rows])
    max_within_pitch = WITHIN_ENTRY_MAX_PITCH_RATIO * font_size
    base_details = {
        "page_number": str(page.page_number),
        "entry_count": str(len(entries)),
        "entry_segmentation": method,
        "confidence": "medium",
        "confidence_reason": "publication_segmentation_and_measured_spacing_heuristic",
        "triage_tier": "medium",
        "source_q_rule_id": "Q028",
    }

    # Q028 (first half): wrapped lines inside one entry are single-spaced.
    for entry_index, entry in enumerate(entries):
        pitches = [_line_step(earlier, later) for earlier, later in zip(entry, entry[1:])]
        if pitches and max(pitches) > max_within_pitch:
            return findings + [
                AuditFinding(
                    rule_id="P045",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "Wrapped lines within a publication/presentation entry on the "
                        "Biographical Sketch page do not appear to be single-spaced."
                    ),
                    details={
                        **base_details,
                        "issue_type": "biosketch_publication_wrapped_line_spacing_not_single",
                        "entry_index": str(entry_index),
                        "bbox": _rows_bbox(entry),
                        "observed_line_pitch_points": f"{max(pitches):.1f}",
                        "max_single_spacing_pitch_points": f"{max_within_pitch:.1f}",
                        "font_size_points": f"{font_size:.1f}",
                    },
                )
            ]

    # Q028 (second half): a blank line separates consecutive entries, measured
    # against the entries' own line pitch so it does not depend on font size.
    within_pitches = [
        _line_step(earlier, later)
        for entry in entries
        for earlier, later in zip(entry, entry[1:])
    ]
    required_pitch = BLANK_LINE_MIN_PITCH_RATIO * _median(within_pitches)
    for entry_index, (earlier_entry, later_entry) in enumerate(zip(entries, entries[1:])):
        last_row = earlier_entry[-1]
        pitch = _line_step(last_row, later_entry[0])
        if pitch < required_pitch:
            return findings + [
                AuditFinding(
                    rule_id="P045",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "Consecutive publication entries on the Biographical Sketch page "
                        "appear to lack the required blank line between them."
                    ),
                    details={
                        **base_details,
                        "issue_type": "biosketch_publication_entry_spacing_not_double",
                        "entry_index": str(entry_index),
                        "bbox": _rows_bbox([last_row, later_entry[0]]),
                        "observed_gap_points": f"{pitch - last_row.height:.1f}",
                        "required_gap_points": f"{required_pitch - last_row.height:.1f}",
                    },
                )
            ]
    return findings
