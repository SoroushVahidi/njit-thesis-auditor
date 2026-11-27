"""Heuristic figure/table caption and title formatting checks for PDF text lines."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

TOC_LIKE_HEADINGS = {
    "TABLE OF CONTENTS",
}
LIST_OF_TABLES_HEADINGS = {
    "LIST OF TABLES",
}
LIST_OF_FIGURES_HEADINGS = {
    "LIST OF FIGURES",
}
REFERENCES_LIKE_HEADINGS = {
    "REFERENCES",
    "BIBLIOGRAPHY",
    "WORKS CITED",
}

CAPTION_START_RE = re.compile(
    r"^\s*(?P<label>figure|fig\.|table)\s+(?P<number>[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)"
    r"(?:[.)])?\s+(?P<body>.+)$",
    re.IGNORECASE,
)
CAPTION_NUMBER_PREFIX_RE = re.compile(
    r"^\s*(?P<label>figure|fig\.|table)\s+(?P<number>[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)"
    r"(?:[.)])?",
    re.IGNORECASE,
)
TERMINAL_PUNCT_RE = re.compile(r"[.!?]$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")
EMBEDDED_SENTENCE_RE = re.compile(r"[.!?]\s+[A-Z]")

MIN_CAPTION_BODY_LEN = 14
MIN_WORDS_FOR_CASE_CHECK = 6
MAX_PREVIEW_LEN = 80
SAME_MARGIN_TOLERANCE_PT = 2.0
MAX_PARAGRAPH_GAP_RATIO = 1.2
CAPTION_CONTINUATION_LEFT_TOLERANCE_PT = 12.0
MAX_CAPTION_CONTINUATION_PITCH_RATIO = 1.35

CAPTION_NOTE_START_RE = re.compile(
    r"^(?:source|sources|note|notes|adapted from|reprinted from|"
    r"all photographs were sourced|photographs? (?:by|courtesy)|"
    r"images? (?:by|courtesy)|data source)\b",
    re.IGNORECASE,
)

# Q-rule IDs for P017 findings per Ester's YES/NO audit matrix.
# Keyed by (page_context, issue_type). Body-context findings have no direct Q-rule
# (Q074/Q075 are LoF-specific; Q065 is LoT-specific).
_P017_Q_RULE_MAP: dict[tuple[str, str], str] = {
    ("list_of_tables", "unexpected_terminal_period"): "Q065",
    ("list_of_figures", "missing_terminal_punctuation"): "Q075",
}


class CaptionLine:
    """Normalized caption-like line with page and context metadata."""

    def __init__(
        self,
        page_number: int,
        raw_text: str,
        caption_type: str,
        caption_body: str,
        context: str,
        bbox: BBox | None = None,
    ) -> None:
        self.page_number = page_number
        self.raw_text = raw_text
        self.caption_type = caption_type
        self.caption_body = caption_body
        self.context = context
        self.bbox = bbox


def normalize_caption_text(text: str) -> str:
    """Collapse whitespace and trim caption-like text."""

    return " ".join(text.strip().split())


def normalize_caption_candidate_text(text: str) -> str:
    """Normalize a candidate line for caption-start parsing only.

    Some PDFs extract a real caption start without the visual space between the
    figure/table number and the first caption word, e.g. ``Figure 4.1Caption``.
    Insert that missing boundary only when the line already looks like a
    caption-number prefix and the immediately following character starts an
    uppercase word, so ordinary prose references such as ``Figure 4.1 shows``
    or ``Figure 4.1shows`` do not broaden into caption matches.
    """

    clean = normalize_caption_text(text)
    if CAPTION_START_RE.match(clean):
        return clean
    prefix = CAPTION_NUMBER_PREFIX_RE.match(clean)
    if prefix is None:
        return clean
    end = prefix.end()
    if end >= len(clean):
        return clean
    next_char = clean[end]
    if not next_char.isalpha() or not next_char.isupper():
        return clean
    return f"{clean[:end]} {clean[end:]}"


def _normalized_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _collect_page_lines(page: PdfPage) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        lines.extend(block.lines)
    return lines


def _reading_order_page_lines(page: PdfPage) -> list[PdfTextLine]:
    return sorted(_collect_page_lines(page), key=lambda line: line.bbox.y0)


def _page_context(page: PdfPage) -> str:
    headings = {_normalized_heading(line) for line in _collect_page_lines(page)}
    if headings.intersection(TOC_LIKE_HEADINGS):
        return "toc"
    if headings.intersection(LIST_OF_TABLES_HEADINGS):
        return "list_of_tables"
    if headings.intersection(LIST_OF_FIGURES_HEADINGS):
        return "list_of_figures"
    if headings.intersection(REFERENCES_LIKE_HEADINGS):
        return "references"
    return "body"


def _is_page_number_line(text: str) -> bool:
    return bool(text and PAGE_NUM_RE.match(text))


def _line_preview(text: str) -> str:
    return text[:MAX_PREVIEW_LEN]


def _caption_end_preview(text: str) -> str:
    clean = normalize_caption_text(text)
    if len(clean) <= MAX_PREVIEW_LEN:
        return clean
    return clean[-MAX_PREVIEW_LEN:]


def _terminal_punctuation(text: str) -> bool:
    return bool(TERMINAL_PUNCT_RE.search(text))


def has_terminal_caption_punctuation(text: str) -> bool:
    """Recognize a terminal mark immediately inside closing quotation marks."""
    return _terminal_punctuation(text.rstrip().rstrip("\"'”’"))


def _starts_new_caption(text: str) -> bool:
    clean = normalize_caption_candidate_text(text)
    match = CAPTION_START_RE.match(clean)
    return bool(match and not _has_mixed_number_segment(match.group("number")))


def _has_mixed_number_segment(number: str) -> bool:
    """True for inline subfigure references such as ``3.2d`` or ``4a``.

    The caption parser supports both Arabic and Roman numerals, but a single
    segment that combines digits and Roman letters is ordinarily a subfigure or
    subtable reference inside prose, not a standalone caption number.
    """

    for segment in re.split(r"[.\-]", number):
        has_digit = any(char.isdigit() for char in segment)
        has_alpha = any(char.isalpha() for char in segment)
        if has_digit and has_alpha:
            return True
    return False


def _starts_caption_note(text: str) -> bool:
    return bool(CAPTION_NOTE_START_RE.match(normalize_caption_text(text)))


def _reads_as_prose_sentence(caption_body: str) -> bool:
    """True when the body already contains a full sentence followed by another.

    This legacy page-local guard cannot distinguish a multi-sentence caption
    from a paragraph opening with a figure reference without further layout
    evidence. The opt-in logical-caption path may recover a cross-page panel
    description only with a corroborating graphic and continuation structure.
    Other prose-reference exclusions remain unchanged.
    """

    return bool(EMBEDDED_SENTENCE_RE.search(caption_body))


_PROSE_AFTER_TABLE_REF_RE = re.compile(
    r"^(?:The|A|An|This|These|Those)\b.+\b(?:is|are|was|were|has|have|had|"
    r"suggests|shows|compares|presents|indicates|demonstrates|reports)\b",
    re.IGNORECASE,
)


def _reads_as_prose_after_float_reference(caption_body: str) -> bool:
    """True when a Table/Figure body reads as a continuing prose sentence.

    Pattern: ``Table 3.2. The corresponding … is experimentally determined…``
    — determiner-led clause with a finite verb. Real table titles are short
    noun phrases in title case, not full declarative sentences.
    """

    return bool(_PROSE_AFTER_TABLE_REF_RE.search(caption_body))


def _starts_with_lowercase_word(text: str) -> bool:
    for char in text:
        if char.isalpha():
            return char.islower()
    return False


def _next_line_is_paragraph_continuation(
    caption_body: str,
    lines: list[PdfTextLine],
    index: int,
) -> bool:
    """True when the next line on the page reads as the same flowing sentence.

    A real caption is a standalone element: what follows it is either the
    actual figure/table body (a different left edge, often a much larger
    gap than ordinary single-line spacing) or a clear structural break, not
    an unbroken, same-margin, lowercase-starting continuation of the
    candidate line itself. A body sentence that merely opens by referencing
    a figure or table number, by contrast, wraps onto the next line exactly
    like any other sentence in the surrounding paragraph. Because a genuine
    caption still ordinarily starts its own title/sentence with a capitalized
    word after the number, treat this as paragraph flow only when the
    candidate's own body already looks like ordinary running prose.
    """

    if index + 1 >= len(lines):
        return False
    if not _starts_with_lowercase_word(caption_body):
        return False
    current = lines[index]
    following = lines[index + 1]
    next_text = normalize_caption_text(following.text)
    if not next_text or not _starts_with_lowercase_word(next_text):
        return False
    same_left_edge = abs(following.bbox.x0 - current.bbox.x0) < SAME_MARGIN_TOLERANCE_PT
    line_height = current.bbox.y1 - current.bbox.y0
    if not same_left_edge or line_height <= 0:
        return False
    gap_below = following.bbox.y0 - current.bbox.y1
    return gap_below <= line_height * MAX_PARAGRAPH_GAP_RATIO


def _is_caption_continuation_line(
    previous: PdfTextLine,
    following: PdfTextLine,
) -> bool:
    clean = normalize_caption_text(following.text)
    if not clean or _is_page_number_line(clean):
        return False
    if _starts_new_caption(clean) or _starts_caption_note(clean):
        return False
    if abs(following.bbox.x0 - previous.bbox.x0) > CAPTION_CONTINUATION_LEFT_TOLERANCE_PT:
        return False
    pitch = following.bbox.y0 - previous.bbox.y0
    if pitch <= 0:
        return False
    line_height = max(previous.bbox.height, following.bbox.height, 1.0)
    return pitch <= line_height * MAX_CAPTION_CONTINUATION_PITCH_RATIO


def _group_caption_text(
    block_lines: list[PdfTextLine],
    index: int,
    first_body: str,
) -> tuple[str, str]:
    raw_parts = [normalize_caption_text(block_lines[index].text)]
    body_parts = [first_body]
    previous = block_lines[index]
    for following in block_lines[index + 1 :]:
        clean = normalize_caption_text(following.text)
        if not _is_caption_continuation_line(previous, following):
            break
        raw_parts.append(clean)
        body_parts.append(clean)
        previous = following
    return (
        normalize_caption_text(" ".join(raw_parts)),
        normalize_caption_text(" ".join(body_parts)),
    )


def _likely_title_case_issue(caption_body: str) -> bool:
    words = WORD_RE.findall(caption_body)
    if len(words) < MIN_WORDS_FOR_CASE_CHECK:
        return False
    content_words = [w for w in words if len(w) > 3]
    if len(content_words) < 4:
        return False
    lowercase_count = sum(1 for word in content_words if word[0].islower())
    return (lowercase_count / len(content_words)) >= 0.6


def _likely_sentence_case_issue(caption_body: str) -> bool:
    words = WORD_RE.findall(caption_body)
    if len(words) < MIN_WORDS_FOR_CASE_CHECK:
        return False
    later_words = [w for w in words[1:] if len(w) > 2]
    if len(later_words) < 4:
        return False
    capitalized_count = sum(1 for word in later_words if word[0].isupper())
    return (capitalized_count / len(later_words)) >= 0.6


def detect_caption_lines(pdf_document: PdfDocument) -> list[CaptionLine]:
    """Detect figure/table caption-like lines and attach context."""

    candidates: list[CaptionLine] = []
    for page in pdf_document.pages:
        context = _page_context(page)
        page_lines = _reading_order_page_lines(page)
        page_line_ids = {id(line): index for index, line in enumerate(page_lines)}
        for block in page.text_blocks:
            block_lines = sorted(block.lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
            for block_index, line in enumerate(block_lines):
                index = page_line_ids.get(id(line))
                if index is None:
                    continue
                clean = normalize_caption_text(line.text)
                if not clean or _is_page_number_line(clean):
                    continue
                candidate_text = normalize_caption_candidate_text(clean)
                match = CAPTION_START_RE.match(candidate_text)
                if not match:
                    continue
                if _has_mixed_number_segment(match.group("number")):
                    continue
                body = normalize_caption_text(match.group("body"))
                if len(body) < MIN_CAPTION_BODY_LEN:
                    continue
                # Both table titles (title case) and figure descriptions (sentence case)
                # capitalize the first word of the body. A lowercase-starting body after
                # "Table/Figure N.N" is almost always an inline cross-reference in prose
                # ("Table 3.1 compares…"), not a standalone caption/title. Same-margin
                # continuation alone is not reliable when the first line's extracted
                # left edge differs from the wrapped paragraph.
                if _starts_with_lowercase_word(body):
                    continue
                if _reads_as_prose_sentence(body):
                    continue
                if _reads_as_prose_after_float_reference(body):
                    continue
                if _next_line_is_paragraph_continuation(body, page_lines, index):
                    continue
                raw_text, caption_body = _group_caption_text(block_lines, block_index, body)
                label = match.group("label").lower()
                caption_type = "table" if label == "table" else "figure"
                candidates.append(
                    CaptionLine(
                        page_number=page.page_number,
                        raw_text=raw_text,
                        caption_type=caption_type,
                        caption_body=caption_body,
                        context=context,
                        bbox=line.bbox,
                    )
                )

    return candidates


def check_pdf_captions(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit conservative P017 caption punctuation, capitalization and spacing warnings."""

    findings: list[AuditFinding] = []

    from njit_auditor.rules.pdf_caption_continuations import (
        LogicalCaption,
        detect_logical_caption_lines,
        locate_page_caption_end,
    )
    from njit_auditor.rules.pdf_caption_spacing import check_page_caption_spacing

    pages = {page.page_number: page for page in pdf_document.pages}
    quoted_list_rows: set[tuple[int, float, float]] | None = None
    for caption in detect_logical_caption_lines(pdf_document):
        if caption.context in {"toc", "references"}:
            continue

        issue_type: str | None = None
        confidence = "medium"
        message = ""
        terminal_text = caption.caption_body
        end_lines: tuple[PdfTextLine, ...] = ()
        end_is_resolved = True
        if caption.context == "body" and not isinstance(caption, LogicalCaption):
            end = locate_page_caption_end(pages[caption.page_number], caption)
            if end is not None:
                terminal_text = normalize_caption_text(end.lines[-1].text)
                end_is_resolved = end.resolved
                end_lines = end.lines
                spacing = check_page_caption_spacing(caption, end)
                if spacing is not None:
                    findings.append(spacing)

        if caption.context == "list_of_tables" and caption.caption_type == "table":
            if caption.caption_body.endswith("."):
                issue_type = "unexpected_terminal_period"
                confidence = "high"
                message = (
                    "Table title entry in List of Tables appears to end with an "
                    "unexpected period."
                )
        elif caption.context == "list_of_figures" and caption.caption_type == "figure":
            if not has_terminal_caption_punctuation(caption.caption_body):
                if quoted_list_rows is None:
                    from njit_auditor.rules.pdf_lof_terminal_punctuation import (
                        quoted_lof_terminal_rows,
                    )

                    quoted_list_rows = quoted_lof_terminal_rows(pdf_document)
                box = caption.bbox
                if box is not None and (
                    caption.page_number, round(box.x0, 1), round(box.y0, 1)
                ) in quoted_list_rows:
                    continue
                issue_type = "missing_terminal_punctuation"
                confidence = "medium"
                message = (
                    "Figure entry in List of Figures appears to be missing terminal "
                    "punctuation."
                )
            # List of Figures capitalization is owned by P024 (R024E). Ester's
            # 2026-11-09 feedback requires sentence case; keep that check
            # in P024 to avoid duplicate List of Figures findings.
        elif caption.context == "body":
            if caption.caption_type == "figure":
                if end_is_resolved and not has_terminal_caption_punctuation(terminal_text):
                    issue_type = "missing_terminal_punctuation"
                    confidence = "high"
                    message = "Figure caption appears to be missing terminal punctuation."
                elif (
                    has_terminal_caption_punctuation(caption.caption_body)
                    and _likely_sentence_case_issue(caption.caption_body)
                ):
                    issue_type = "possible_sentence_case_issue"
                    confidence = "low"
                    message = "Figure caption may not follow likely sentence-case style."
            elif caption.caption_type == "table":
                if end_is_resolved and terminal_text.endswith(".."):
                    issue_type = "unexpected_terminal_period"
                    confidence = "high"
                    message = (
                        "Table title/caption appears to contain an obvious punctuation "
                        "problem."
                    )
                elif _likely_title_case_issue(caption.caption_body):
                    issue_type = "possible_title_case_issue"
                    confidence = "low"
                    message = "Table title/caption may not follow likely title-case style."

        if (
            caption.context == "body"
            and caption.caption_type == "table"
            and issue_type != "unexpected_terminal_period"
            and end_is_resolved
            and terminal_text.endswith(".")
        ):
            # Table titles do not end in a period (Ester, Sample B feedback);
            # report it alongside any capitalization issue on the same title.
            findings.append(
                _caption_finding(
                    caption,
                    "unexpected_terminal_period",
                    "medium",
                    "Table title appears to end with a period; table titles do not end "
                    "with a period.",
                    end_lines=end_lines,
                )
            )

        if issue_type is None:
            continue

        findings.append(
            _caption_finding(caption, issue_type, confidence, message, end_lines=end_lines)
        )

    return findings


def _caption_finding(
    caption: CaptionLine, issue_type: str, confidence: str, message: str,
    *, end_lines: tuple[PdfTextLine, ...] = (),
) -> AuditFinding:
    details = {
        "page_number": str(caption.page_number),
        "caption_type": caption.caption_type,
        "issue_type": issue_type,
        "line_preview": _line_preview(caption.raw_text),
        "caption_end_preview": _caption_end_preview(caption.raw_text),
        "confidence": confidence,
        "source_q_rule_id": _P017_Q_RULE_MAP.get((caption.context, issue_type), ""),
    }
    if issue_type == "unexpected_terminal_period":
        details["caption_context"] = caption.context
        details["suggested_fix"] = (
            "Remove the final period from this List of Tables entry."
            if caption.context == "list_of_tables"
            else "Remove the final period from this table title."
        )
    if issue_type == "missing_terminal_punctuation" and caption.context == "list_of_figures":
        details["caption_context"] = caption.context
        details["suggested_fix"] = "End this List of Figures description with a period."
    if caption.bbox is not None:
        details["bbox"] = format_bbox_detail(caption.bbox)
    if end_lines and issue_type in {"missing_terminal_punctuation", "unexpected_terminal_period"}:
        details["caption_end_preview"] = _caption_end_preview(
            " ".join(line.text for line in end_lines)
        )
        details["line_preview"] = _line_preview(normalize_caption_text(end_lines[-1].text))
        if len(end_lines) > 1:
            details["bbox"] = format_bbox_detail(end_lines[-1].bbox)
    from njit_auditor.rules.pdf_caption_continuations import LogicalCaption

    finding_page = caption.page_number
    if isinstance(caption, LogicalCaption):
        first, last = caption.fragments
        details.update({
            "caption_start_page": str(first.page_number),
            "caption_end_page": str(last.page_number),
            "caption_start_document_page_label": first.document_page_label,
            "caption_end_document_page_label": last.document_page_label,
            "caption_start_bbox": format_bbox_detail(first.bbox),
            "caption_end_bbox": format_bbox_detail(last.bbox),
        })
        if issue_type == "missing_terminal_punctuation":
            finding_page = last.page_number
            details["page_number"] = str(finding_page)
            details["bbox"] = format_bbox_detail(last.lines[-1].bbox)
            details["line_preview"] = _line_preview(last.lines[-1].text.strip())
            details["caption_end_preview"] = _caption_end_preview(
                " ".join(line.text.strip() for line in last.lines)
            )
            details["suggested_fix"] = (
                "Add terminal punctuation at the end of the complete figure description "
                f"on physical PDF page {finding_page}."
            )
            if last.document_page_label:
                details["document_page_label"] = last.document_page_label
                details["document_page_label_confidence"] = "medium"
    return AuditFinding(
        rule_id="P017",
        severity=Severity.WARNING,
        page=finding_page,
        message=message,
        details=details,
    )
