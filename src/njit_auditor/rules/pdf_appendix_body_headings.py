"""Conservative body-page appendix heading label checks (P063).

Heuristic PDF coverage for Q058/Q059 (body-page extension):
  - Q058: If the document has only one appendix, its body heading must be
    "APPENDIX" followed by a title (no letter suffix).
  - Q059: If the document has multiple appendices, each body heading must be
    "APPENDIX <letter>" (e.g. APPENDIX A, APPENDIX B, ...).

Guideline source (Self-Assessment Sheet, page 4):
  "If there is one appendix it is called APPENDIX; if there are multiple
  appendices, they are named APPENDIX A, B, C + the appendix title.
  Appendices titles are in all caps both in the text and in the TOC."

Companion to P042 (TOC-side appendix format check, Q058/Q059). P042 checks
the Table of Contents entries; P063 checks the body-page headings.

Conservative gates:
  - Requires a structurally supported APPENDIX heading on a body page.
  - Excludes named front matter, TOC/list pages and reference entries.
  - Uses heading text, separation and typography to distinguish new headings
    from prose and wrapped lines.
  - Single-appendix case: the heading must be exactly "APPENDIX" with no
    trailing letter (A–Z), OR must be "APPENDIX" optionally followed by a
    title that is NOT a single letter.  A bare letter suffix triggers a
    warning: single-appendix docs should NOT use "APPENDIX A".
  - Multi-appendix case: each heading must use "APPENDIX <letter>" format.
    Missing letter suffix triggers a warning.
  - Letter sequence is checked for continuity from A: gaps or repeats are
    flagged (e.g. APPENDIX A, APPENDIX C skipping B).
  - Issue types:
      * "single_appendix_uses_letter_label" — one appendix found but heading
        uses APPENDIX A/B/... format (not required per Q058)
      * "multiple_appendix_missing_letter" — multiple appendices found but
        at least one heading lacks a letter identifier (required per Q059)
      * "appendix_letter_sequence_gap" — letter identifiers are non-
        consecutive (e.g., A, C with no B)
      * "appendix_letter_sequence_repeat" — same letter used on more than one
        appendix heading

Privacy: findings contain only structural metadata — heading count, letter
labels (A, B, C...) as structural identifiers, page number. No body text,
section titles, dissertation content, or author names are included.

Does NOT duplicate:
  - P042: TOC appendix entry format (Q058/Q059 TOC side).
  - P038: required front-matter heading presence.
  - P014: front-matter named heading layout/style.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_appendix_subsections import check_appendix_subsections
from njit_auditor.rules.pdf_frontmatter_heading_gate import resolve_gate_heading_from_line
from njit_auditor.rules.pdf_heading_levels import _is_tight_wrap_gap, _union_bbox
from njit_auditor.rules.pdf_headings import (
    CENTER_TOLERANCE_PT,
    _is_bold_line,
    _line_centered,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT, TOP_MARGIN_PT
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE
from njit_auditor.rules.pdf_references_citations_structural import (
    _page_heading as _references_page_heading,
)
from njit_auditor.rules.pdf_title_capitalization import MINOR_WORDS
from njit_auditor.rules.pdf_toc_alignment import (
    HEADING_SUFFIX_RE,
    RIGHT_COLUMN_MIN_X_OFFSET_PT,
    SAME_BASELINE_Y_TOLERANCE_PT,
    _right_edge_page_number_span,
    detect_toc_like_pages,
)

# Matches a line starting with APPENDIX (case-insensitive), possibly followed by
# a letter identifier and/or title text.
_APPENDIX_LINE_RE = re.compile(r"^APPENDIX\b", re.IGNORECASE)

# Use a standalone letter token. A.1 is a subsection number, not an appendix label.
_APPENDIX_WITH_LETTER_RE = re.compile(r"^APPENDIX\s+([A-Z])(?=$|[\s:\-–—])", re.IGNORECASE)
_SUBSECTION_AFTER_APPENDIX_RE = re.compile(r"^APPENDIX\s+(?:[A-Z]?\.\d|\d)", re.IGNORECASE)
_TOC_LEADERS_RE = re.compile(r"[.·]{2,}|…|[-–—_]{4,}")
_OTHER_FRONT_MATTER = frozenset({
    "COPYRIGHT PAGE", "TITLE PAGE", "LIST OF SYMBOLS", "LIST OF ABBREVIATIONS",
})

_RULE_ID = "P063"
_SOURCE_Q_RULE_IDS = ("Q058", "Q059")


def _heading_text(line: PdfTextLine, *, bold: bool) -> str | None:
    text = normalize_heading_text(line.text)
    prefix = _APPENDIX_WITH_LETTER_RE.match(text) or _APPENDIX_LINE_RE.match(text)
    if (
        prefix is None
        or text.endswith((".", "!", "?", ";"))
        or HEADING_SUFFIX_RE.search(text)
        or _SUBSECTION_AFTER_APPENDIX_RE.match(text)
        or _TOC_LEADERS_RE.search(text)
    ):
        return None
    title = text[prefix.end():].strip(" :–—-")
    if title and not title[0].isupper():
        return None
    # A full-width paragraph can appear centered. Regular text must also read like a title.
    if not bold and any(
        word[0].islower() and word not in MINOR_WORDS for word in title.split()
    ):
        return None
    return text.upper()


def _has_folio_peer(line: PdfTextLine, folios: list[PdfTextLine]) -> bool:
    """Recognize TOC rows whose folio was extracted as a separate text line."""
    if _right_edge_page_number_span(line) is not None:
        return True
    baseline = line.baseline_y if line.baseline_y is not None else line.bbox.y0
    for folio in folios:
        folio_y = folio.baseline_y if folio.baseline_y is not None else folio.bbox.y0
        if (
            folio.bbox.x0 >= line.bbox.x0 + RIGHT_COLUMN_MIN_X_OFFSET_PT
            and abs(folio_y - baseline) <= SAME_BASELINE_Y_TOLERANCE_PT
        ):
            return True
    return False


def _is_upper_folio(line: PdfTextLine, page_width: float) -> bool:
    """Recognize an isolated number in an upper-margin folio position."""
    if line.bbox.y1 > TOP_MARGIN_PT or not PAGE_NUM_RE.fullmatch(line.text.strip()):
        return False
    right_edge = page_width - RIGHT_MARGIN_PT
    return (
        _line_centered(line, LEFT_MARGIN_PT, right_edge, page_width=page_width)
        or abs(line.bbox.x1 - right_edge) <= CENTER_TOLERANCE_PT
    )


def _is_wrapped_letter(previous: PdfTextLine, following: PdfTextLine) -> bool:
    if not (
        re.fullmatch(r"[A-Z]", following.text.strip())
        and _is_bold_line(previous)
        and _is_bold_line(following)
        and previous.bbox.y0 < following.bbox.y0
        and _is_tight_wrap_gap(previous, following)
    ):
        return False
    a, b = previous.bbox, following.bbox
    return (
        abs(a.x0 - b.x0) <= CENTER_TOLERANCE_PT
        or abs((a.x0 + a.x1 - b.x0 - b.x1) / 2) <= CENTER_TOLERANCE_PT
    )


def _collect_appendix_headings(pdf_doc: PdfDocument) -> list[tuple[int, str, BBox]]:
    """Return the physical page, label text and source box of each supported heading."""
    list_pages = {c.page.page_number for c in detect_toc_like_pages(pdf_doc)}
    headings: list[tuple[int, str, BBox]] = []
    in_references = False
    for page in pdf_doc.pages:
        if page.page_number in list_pages:
            continue
        lines = sorted(
            (line for block in page.text_blocks for line in block.lines if line.text.strip()),
            key=lambda line: (line.bbox.y0, line.bbox.x0),
        )
        if any(
            resolve_gate_heading_from_line(line.text) is not None
            or HEADING_SUFFIX_RE.sub("", normalize_heading_text(line.text)).upper()
            in _OTHER_FRONT_MATTER
            for line in lines
        ):
            continue
        if _references_page_heading(page) is not None:
            in_references = True
            continue

        folios = [line for line in lines if PAGE_NUM_RE.fullmatch(line.text.strip())]
        for index, line in enumerate(lines):
            if not _APPENDIX_LINE_RE.match(line.text.lstrip()):
                continue
            previous = lines[index - 1] if index else None
            following = lines[index + 1] if index + 1 < len(lines) else None
            if previous is not None and _is_tight_wrap_gap(previous, line):
                continue
            bold = _is_bold_line(line)
            styled = bold or _line_centered(
                line, LEFT_MARGIN_PT, page.width - RIGHT_MARGIN_PT, page_width=page.width,
            )
            # Mid-page headings need visual evidence. Within a References run,
            # only a styled opening heading can establish a new appendix.
            if not styled and (previous is not None or in_references):
                continue
            # An isolated upper folio can precede the heading without sharing its row.
            if in_references and previous is not None and (
                index != 1 or not _is_upper_folio(previous, page.width)
            ):
                continue
            text = _heading_text(line, bold=bold)
            if text is None or _has_folio_peer(line, folios):
                continue
            bbox = line.bbox
            if text == "APPENDIX" and following is not None and _is_wrapped_letter(line, following):
                text = f"{text} {following.text.strip()}"
                bbox = _union_bbox(bbox, following.bbox)
            elif not styled and following is not None and _is_tight_wrap_gap(line, following):
                continue  # An unstyled line in a dense paragraph is ambiguous.
            headings.append((page.page_number, text, bbox))
            in_references = False

    return headings


def _extract_letter(heading: str) -> str | None:
    """Return the letter suffix from an APPENDIX heading, or None if absent."""
    m = _APPENDIX_WITH_LETTER_RE.match(heading)
    if m:
        return m.group(1).upper()
    return None


def check_pdf_appendix_body_headings(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P063 warnings for appendix labels and missing subsection prefixes.

    Conservative gates:
    - No findings if no body region is detected (image-only / front-matter-only PDFs).
    - No findings if no APPENDIX headings are found in the body region.
    - Single appendix: warn if heading uses a letter suffix (APPENDIX A) per Q058.
    - Multiple appendices: warn if any heading lacks a letter suffix per Q059.
    - Warn if letter identifiers are non-consecutive or repeated.
    """
    headings = _collect_appendix_headings(pdf_doc)
    if not headings:
        return []

    findings: list[AuditFinding] = []
    n = len(headings)

    if n == 1:
        page_num, heading, bbox = headings[0]
        letter = _extract_letter(heading)
        if letter is not None:
            # Single appendix uses a letter suffix — not required per Q058.
            findings.append(
                AuditFinding(
                    rule_id=_RULE_ID,
                    severity=Severity.WARNING,
                    page=page_num,
                    message=(
                        f"Single appendix body heading on page {page_num} uses a letter "
                        f"identifier ('{letter}'). NJIT guidelines require a single "
                        f"appendix to be labeled APPENDIX without a letter suffix."
                    ),
                    details={
                        "issue_type": "single_appendix_uses_letter_label",
                        "page": str(page_num),
                        "appendix_count": "1",
                        "letter_found": letter,
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q058",
                        "bbox": format_bbox_detail(bbox),
                    },
                )
            )
    else:
        # Multiple appendices: each must use APPENDIX <letter> format.
        letters: list[str | None] = []
        for page_num, heading, bbox in headings:
            letter = _extract_letter(heading)
            letters.append(letter)
            if letter is None:
                findings.append(
                    AuditFinding(
                        rule_id=_RULE_ID,
                        severity=Severity.WARNING,
                        page=page_num,
                        message=(
                            f"Multiple-appendix body heading on page {page_num} does not "
                            "include a letter identifier. NJIT guidelines require "
                            f"multiple appendices to be labeled APPENDIX A, APPENDIX B, etc."
                        ),
                        details={
                            "issue_type": "multiple_appendix_missing_letter",
                            "page": str(page_num),
                            "appendix_count": str(n),
                            "triage_tier": "medium",
                            "source_q_rule_id": "Q059",
                            "bbox": format_bbox_detail(bbox),
                        },
                    )
                )

        # Check letter sequence only when all headings have letters.
        resolved = [ltr for ltr in letters if ltr is not None]
        if len(resolved) == n:
            # Check for repeated letters.
            seen_letters: set[str] = set()
            for idx, (page_num, _, bbox) in enumerate(headings):
                letter = resolved[idx]
                if letter in seen_letters:
                    findings.append(
                        AuditFinding(
                            rule_id=_RULE_ID,
                            severity=Severity.WARNING,
                            page=page_num,
                            message=(
                                f"Appendix body heading on page {page_num} repeats the "
                                f"letter identifier '{letter}'. Each appendix must use a "
                                "unique letter (A, B, C ...) per NJIT guidelines."
                            ),
                            details={
                                "issue_type": "appendix_letter_sequence_repeat",
                                "page": str(page_num),
                                "appendix_count": str(n),
                                "letter_repeated": letter,
                                "triage_tier": "medium",
                                "source_q_rule_id": "Q059",
                                "bbox": format_bbox_detail(bbox),
                            },
                        )
                    )
                seen_letters.add(letter)

            # Check for non-consecutive sequence (gaps).
            # Expected: A, B, C, D, ... in order.
            if not findings:  # Only check gaps when no repeat found.
                expected_letters = [chr(ord("A") + i) for i in range(n)]
                for idx, (page_num, _, bbox) in enumerate(headings):
                    actual = resolved[idx]
                    expected = expected_letters[idx]
                    if actual != expected:
                        findings.append(
                            AuditFinding(
                                rule_id=_RULE_ID,
                                severity=Severity.WARNING,
                                page=page_num,
                                message=(
                                    f"Appendix body heading letter sequence is non-consecutive "
                                    f"on page {page_num}: expected '{expected}' at position "
                                    f"{idx + 1} but found '{actual}'. NJIT guidelines "
                                    "require consecutive letter labels (A, B, C ...)."
                                ),
                                details={
                                    "issue_type": "appendix_letter_sequence_gap",
                                    "page": str(page_num),
                                    "appendix_count": str(n),
                                    "expected_letter": expected,
                                    "found_letter": actual,
                                    "sequence_position": str(idx + 1),
                                    "triage_tier": "medium",
                                    "source_q_rule_id": "Q059",
                                    "bbox": format_bbox_detail(bbox),
                                },
                            )
                        )
                        break  # Report only the first gap.

    findings.extend(check_appendix_subsections(
        pdf_doc, [(page, _extract_letter(text), bbox) for page, text, bbox in headings],
    ))
    return findings
