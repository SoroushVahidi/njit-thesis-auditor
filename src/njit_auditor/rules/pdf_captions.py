"""Heuristic figure/table caption and title formatting checks for PDF text lines."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine
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
TERMINAL_PUNCT_RE = re.compile(r"[.!?]$")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")

MIN_CAPTION_BODY_LEN = 14
MIN_WORDS_FOR_CASE_CHECK = 6
MAX_PREVIEW_LEN = 80


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


def _normalized_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _collect_page_lines(page: PdfPage) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        lines.extend(block.lines)
    return lines


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
        for line in _collect_page_lines(page):
            clean = normalize_caption_text(line.text)
            if not clean or _is_page_number_line(clean):
                continue
            match = CAPTION_START_RE.match(clean)
            if not match:
                continue
            body = normalize_caption_text(match.group("body"))
            if len(body) < MIN_CAPTION_BODY_LEN:
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

        findings.append(
            AuditFinding(
                rule_id="P017",
                severity=Severity.WARNING,
                page=caption.page_number,
                message=message,
                details={
                    "page_number": str(caption.page_number),
                    "caption_type": caption.caption_type,
                    "issue_type": issue_type,
                    "line_preview": _line_preview(caption.raw_text),
                    "confidence": confidence,
                },
            )
        )

    return findings
