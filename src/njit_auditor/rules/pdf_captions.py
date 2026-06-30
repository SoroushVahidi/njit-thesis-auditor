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

# Q-rule IDs for P017 findings per Ester's YES/NO audit matrix.
# Keyed by (page_context, issue_type). Body-context findings have no direct Q-rule
# (Q074/Q075 are LoF-specific; Q065 is LoT-specific).
_P017_Q_RULE_MAP: dict[tuple[str, str], str] = {
    ("list_of_tables", "unexpected_terminal_period"): "Q065",
    ("list_of_figures", "missing_terminal_punctuation"): "Q075",
    ("list_of_figures", "possible_sentence_case_issue"): "Q074",
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


def _terminal_punctuation(text: str) -> bool:
    return bool(TERMINAL_PUNCT_RE.search(text))


def _reads_as_prose_sentence(caption_body: str) -> bool:
    """True when the body already contains a full sentence followed by another.

    A real figure/table caption is a single descriptive title, not a
    multi-sentence narrative. A body paragraph that merely opens by
    referencing a figure or table number (e.g. "Figure 4.1 displays the
    relationship... The points cluster...") matches the same caption-start
    pattern but reads as flowing prose once a sentence boundary appears
    before the end of the line.
    """

    return bool(EMBEDDED_SENTENCE_RE.search(caption_body))


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
        for index, line in enumerate(page_lines):
            clean = normalize_caption_text(line.text)
            if not clean or _is_page_number_line(clean):
                continue
            candidate_text = normalize_caption_candidate_text(clean)
            match = CAPTION_START_RE.match(candidate_text)
            if not match:
                continue
            body = normalize_caption_text(match.group("body"))
            if len(body) < MIN_CAPTION_BODY_LEN:
                continue
            if _reads_as_prose_sentence(body):
                continue
            if _next_line_is_paragraph_continuation(body, page_lines, index):
                continue
            label = match.group("label").lower()
            caption_type = "table" if label == "table" else "figure"
            candidates.append(
                CaptionLine(
                    page_number=page.page_number,
                    raw_text=clean,
                    caption_type=caption_type,
                    caption_body=body,
                    context=context,
                    bbox=line.bbox,
                )
            )

    return candidates


def check_pdf_captions(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit conservative P017 warnings for obvious caption/title formatting issues."""

    findings: list[AuditFinding] = []

    for caption in detect_caption_lines(pdf_document):
        if caption.context in {"toc", "references"}:
            continue

        issue_type: str | None = None
        confidence = "medium"
        message = ""

        if caption.context == "list_of_tables" and caption.caption_type == "table":
            if caption.caption_body.endswith("."):
                issue_type = "unexpected_terminal_period"
                confidence = "high"
                message = (
                    "Table title entry in List of Tables appears to end with an "
                    "unexpected period."
                )
        elif caption.context == "list_of_figures" and caption.caption_type == "figure":
            if not _terminal_punctuation(caption.caption_body):
                issue_type = "missing_terminal_punctuation"
                confidence = "medium"
                message = (
                    "Figure entry in List of Figures appears to be missing terminal "
                    "punctuation."
                )
            elif _likely_sentence_case_issue(caption.caption_body):
                issue_type = "possible_sentence_case_issue"
                confidence = "low"
                message = (
                    "Figure entry in List of Figures may not follow sentence-case style."
                )
        elif caption.context == "body":
            if caption.caption_type == "figure":
                if not _terminal_punctuation(caption.caption_body):
                    issue_type = "missing_terminal_punctuation"
                    confidence = "high"
                    message = "Figure caption appears to be missing terminal punctuation."
                elif _likely_sentence_case_issue(caption.caption_body):
                    issue_type = "possible_sentence_case_issue"
                    confidence = "low"
                    message = "Figure caption may not follow likely sentence-case style."
            elif caption.caption_type == "table":
                if caption.caption_body.endswith(".."):
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

        if issue_type is None:
            continue

        q_rule_id = _P017_Q_RULE_MAP.get((caption.context, issue_type), "")

        details = {
            "page_number": str(caption.page_number),
            "caption_type": caption.caption_type,
            "issue_type": issue_type,
            "line_preview": _line_preview(caption.raw_text),
            "confidence": confidence,
            "source_q_rule_id": q_rule_id,
        }
        if caption.bbox is not None:
            details["bbox"] = format_bbox_detail(caption.bbox)

        findings.append(
            AuditFinding(
                rule_id="P017",
                severity=Severity.WARNING,
                page=caption.page_number,
                message=message,
                details=details,
            )
        )

    return findings
