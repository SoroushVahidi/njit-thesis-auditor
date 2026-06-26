"""Heuristic title-case capitalization checks for PDF title-like and heading-like text.

Scope: title-like lines only — Level 2 headings (bold, title case expected per NJIT
guidelines), table title lines, and List of Tables entries.
Not applied to body paragraphs, Level 3+ sentence-case headings, figure captions,
references pages, or all-caps front-matter labels.

Source: NJIT Thesis and Dissertation Formatting Guidelines; Titles Examples Level 1–5.
  - Level 1 (chapter): ALL CAPS bold centered — already checked by P014.
  - Level 2 (X.x): Title Case bold — checked by P020.
  - Level 3–5: Sentence case — NOT checked by P020 (sentence case is expected).
  - Table titles: Title Case — checked by P020.
  - Figure descriptions: Sentence case — NOT checked by P020.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median

from njit_auditor.highlight_targeting import (
    estimate_word_bbox_in_line_bbox,
    format_optional_bbox_detail,
    word_bbox_in_line,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_captions import (
    CAPTION_START_RE,
    detect_caption_lines,
    normalize_caption_candidate_text,
)
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

# APA/NJIT title-case minor words (all ≤3 chars; 4+ letter words are always major).
MINOR_WORDS: frozenset[str] = frozenset(
    [
        "a", "an", "the",
        "and", "but", "or", "for", "nor", "as",
        "at", "by", "in", "of", "on", "per", "to", "up", "via",
    ]
)

# All-caps front-matter labels: ignore entirely for capitalization checking.
FRONTMATTER_ALLCAPS_LABELS: frozenset[str] = frozenset(
    [
        "ABSTRACT",
        "APPROVAL PAGE",
        "BIOGRAPHICAL SKETCH",
        "ACKNOWLEDGEMENTS",
        "ACKNOWLEDGMENTS",
        "TABLE OF CONTENTS",
        "LIST OF TABLES",
        "LIST OF FIGURES",
        "REFERENCES",
        "BIBLIOGRAPHY",
        "WORKS CITED",
    ]
)

_REFERENCES_HEADINGS: frozenset[str] = frozenset(
    ["REFERENCES", "BIBLIOGRAPHY", "WORKS CITED"]
)
_TOC_HEADINGS: frozenset[str] = frozenset(["TABLE OF CONTENTS"])

# All-caps acronym: 2+ uppercase letters (PDF, AI, MRI, NJIT, CAD, SDF, …).
_ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9]{1,}$")

# Words to skip: contain digits, Greek chars, or math/equation notation.
_SKIP_WORD_RE = re.compile(r"[0-9Α-ω+*/=<>^\\{}[\]()]")

# Subtitle separators that trigger capitalization of the following word.
_SUBTITLE_SEP_RE = re.compile(r"[:–—]|--+")

# Word token: letter-started run, optionally joined by single hyphens.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'À-ɏ]*(?:-[A-Za-z][A-Za-z'À-ɏ]*)*")

_BOLD_FONT_HINT_RE = re.compile(r"(bold|black|heavy|semibold|cmbx)", re.IGNORECASE)

MIN_WORDS_FOR_TITLE_CHECK = 3
MAX_HEADING_LINE_LEN = 150
MAX_PREVIEW_LEN = 80
# Font-size fallback: line treated as heading-like if span sizes exceed body by this much.
_FONT_SIZE_HEADING_MARGIN_PT = 2.0
# Maximum line length for font-size fallback headings (shorter = more conservative).
_MAX_FONT_SIZE_FALLBACK_LINE_LEN = 100
# Minimum fraction of spans that must be above the size threshold for fallback to fire.
_MIN_ABOVE_SIZE_FRACTION = 0.70


@dataclass
class TitleLikeLine:
    """A candidate line for title-case checking."""

    page_number: int
    check_text: str   # phrase to check (caption body or full clean heading)
    line_preview: str  # ≤80-char preview of the original line
    source: str        # "caption" | "heading"
    detection_reason: str = field(default="bold_heading")
    bbox: BBox | None = None
    source_line: PdfTextLine | None = None
    # detection_reason values: "bold_heading" | "cmbx_bold_heading" | "font_size_heading_fallback"


def normalize_title_text(text: str) -> str:
    """Collapse whitespace and normalize non-breaking spaces."""
    return " ".join(text.replace(" ", " ").strip().split())


def tokenize_title_words(text: str) -> list[str]:
    """Return alphabetic word tokens from title text."""
    return _WORD_RE.findall(text)


def is_minor_word(word: str) -> bool:
    """Return True if the word is a short NJIT/APA minor word (article/conj/prep)."""
    return word.lower() in MINOR_WORDS


def looks_like_acronym(word: str) -> bool:
    """Return True if the word looks like an all-caps acronym (PDF, AI, NJIT…)."""
    return bool(_ACRONYM_RE.match(word))


def _should_skip_word(word: str) -> bool:
    """Return True if the word contains math/digit/equation notation — skip it."""
    return bool(_SKIP_WORD_RE.search(word))


def _words_with_sep_info(text: str) -> list[tuple[str, bool]]:
    """
    Return (word, after_subtitle_sep) pairs for each word token.

    after_subtitle_sep is True when a subtitle separator (colon, em/en dash,
    double-hyphen) appears in the gap between the previous word and this word.
    """
    result: list[tuple[str, bool]] = []
    last_end = 0
    after_sep = False
    for m in _WORD_RE.finditer(text):
        gap = text[last_end : m.start()]
        if _SUBTITLE_SEP_RE.search(gap):
            after_sep = True
        result.append((m.group(), after_sep))
        after_sep = False
        last_end = m.end()
    return result


def check_apa_title_case_phrase(text: str) -> list[dict[str, str]]:
    """
    Check NJIT/APA title case for a phrase.

    Returns list of issue dicts: {word, position, reason, confidence, expected}.
    An empty list means no issues detected.

    Conservative: skips hyphenated words, all-caps acronyms, and words with
    digits or special characters. Only flags clear under-capitalization.
    Does not flag over-capitalization (e.g. 'The' in the middle).
    """
    words_with_info = _words_with_sep_info(text)
    if len(words_with_info) < MIN_WORDS_FOR_TITLE_CHECK:
        return []

    issues: list[dict[str, str]] = []
    n = len(words_with_info)

    for idx, (word, after_sep) in enumerate(words_with_info):
        is_first = idx == 0
        is_last = idx == n - 1

        # Skip math/digit/equation tokens.
        if _should_skip_word(word):
            continue

        # Preserve all-caps acronyms — never flag these.
        if looks_like_acronym(word):
            continue

        # Hyphenated words: conservative — skip entirely.
        if "-" in word:
            continue

        # Determine whether this word must be capitalized.
        should_be_capitalized = (
            is_first or is_last or after_sep or not is_minor_word(word.lower())
        )

        if should_be_capitalized and word[0].islower():
            if is_first:
                reason = "first_word_requires_capital"
                confidence = "high"
            elif after_sep:
                reason = "word_after_separator_requires_capital"
                confidence = "high"
            else:
                reason = "major_word_requires_capital"
                confidence = "medium"

            issues.append(
                {
                    "word": word,
                    "position": str(idx),
                    "reason": reason,
                    "confidence": confidence,
                    "expected": word[0].upper() + word[1:],
                }
            )

    return issues


def _is_page_number_line(text: str) -> bool:
    return bool(text and PAGE_NUM_RE.match(text))


def _is_frontmatter_allcaps_label(text: str) -> bool:
    return normalize_title_text(text).upper() in FRONTMATTER_ALLCAPS_LABELS


def _normalize_line_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _page_context_type(page: PdfPage) -> str:
    """Return coarse page context: 'references', 'toc', or 'body'."""
    for block in page.text_blocks:
        for line in block.lines:
            h = _normalize_line_heading(line)
            if h in _REFERENCES_HEADINGS:
                return "references"
            if h in _TOC_HEADINGS:
                return "toc"
    return "body"


def _is_math_font(font_name: str) -> bool:
    """Return True for known math/symbol fonts that should not be treated as headings."""
    base = font_name.lower().split("+")[-1]
    return base.startswith(("cmmi", "cmsy", "cmex", "msam", "msbm", "wasy"))


def _spans_bold_reason(line: PdfTextLine) -> str | None:
    """Return detection reason if the line looks bold/heading-like, else None.

    Returns:
        'cmbx_bold_heading' — all non-math spans use CMBX (Computer Modern Bold).
        'bold_heading'      — all non-math spans use another bold font.
        None               — line is not detected as bold/heading-like.
    """
    if not line.spans:
        return None
    candidate_spans = [
        s for s in line.spans if not (s.font and _is_math_font(s.font))
    ]
    if not candidate_spans:
        return None
    all_bold = all(
        s.bold or bool(s.font and _BOLD_FONT_HINT_RE.search(s.font))
        for s in candidate_spans
    )
    if not all_bold:
        return None
    # Distinguish CMBX-based detection from other bold fonts.
    if all(
        s.font and s.font.lower().split("+")[-1].startswith("cmbx")
        for s in candidate_spans
        if s.font
    ):
        return "cmbx_bold_heading"
    return "bold_heading"


def _estimate_document_body_size(pdf_document: PdfDocument) -> float:
    """Estimate the dominant body font size from spans in the document."""
    sizes: list[float] = []
    for page in pdf_document.pages:
        for block in page.text_blocks:
            for line in block.lines:
                for span in line.spans:
                    if span.size and 9.0 <= span.size <= 14.0:
                        sizes.append(span.size)
    return median(sizes) if sizes else 12.0


def _is_font_size_heading(line: PdfTextLine, body_size: float) -> bool:
    """Return True if line looks like a heading based on font size alone.

    Conservative: requires ≥70% of spans to be above body_size + 2pt threshold,
    line must be short and not all-caps.
    """
    if not line.spans:
        return False
    threshold = body_size + _FONT_SIZE_HEADING_MARGIN_PT
    sized_spans = [s for s in line.spans if s.size is not None]
    if not sized_spans:
        return False
    above_count = sum(1 for s in sized_spans if (s.size or 0.0) >= threshold)
    if above_count / len(sized_spans) < _MIN_ABOVE_SIZE_FRACTION:
        return False
    return True


def detect_pdf_title_like_lines(pdf_document: PdfDocument) -> list[TitleLikeLine]:
    """
    Detect title-like lines for NJIT title-case checking.

    Includes:
    - Table caption/title bodies (Level 2 title case expected per NJIT guidelines).
    - List of Tables entries (title case expected).
    - Bold heading-like lines that are not all-caps front-matter labels,
      not page numbers, and not on references or TOC pages.

    Excludes:
    - Normal body paragraphs (not bold).
    - Figure captions (sentence case per NJIT guidelines — not checked).
    - References/bibliography pages.
    - TOC pages.
    - All-caps front-matter labels (ABSTRACT, APPROVAL PAGE, etc.).
    - Lines over 150 characters.
    - Page-number-like lines.
    """
    results: list[TitleLikeLine] = []

    # 1. Table caption/title bodies only (figure captions use sentence case — skip).
    for caption in detect_caption_lines(pdf_document):
        if caption.context in {"references", "toc"}:
            continue
        # NJIT: table titles are title case; figure descriptions are sentence case.
        if caption.caption_type != "table":
            continue
        results.append(
            TitleLikeLine(
                page_number=caption.page_number,
                check_text=caption.caption_body,
                line_preview=caption.raw_text[:MAX_PREVIEW_LEN],
                source="caption",
                bbox=caption.bbox,
            )
        )

    body_size = _estimate_document_body_size(pdf_document)

    # 2. Bold heading-like lines (Level 2 and similar title-case headings).
    for page in pdf_document.pages:
        page_ctx = _page_context_type(page)
        if page_ctx in {"references", "toc"}:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                clean = normalize_title_text(line.text)
                if not clean:
                    continue
                if _is_page_number_line(clean):
                    continue
                if _is_frontmatter_allcaps_label(clean):
                    continue
                if len(clean) > MAX_HEADING_LINE_LEN:
                    continue
                if CAPTION_START_RE.match(normalize_caption_candidate_text(clean)):
                    continue  # already covered by caption detection above

                detection_reason = _spans_bold_reason(line)
                if detection_reason is None and len(clean) <= _MAX_FONT_SIZE_FALLBACK_LINE_LEN:
                    # Font-size fallback: treat as heading-like if significantly larger than body.
                    # Only apply for short lines to avoid catching body paragraphs.
                    if _is_font_size_heading(line, body_size):
                        detection_reason = "font_size_heading_fallback"

                if detection_reason is not None:
                    results.append(
                        TitleLikeLine(
                            page_number=page.page_number,
                            check_text=clean,
                            line_preview=clean[:MAX_PREVIEW_LEN],
                            source="heading",
                            detection_reason=detection_reason,
                            bbox=line.bbox,
                            source_line=line,
                        )
                    )

    return results


def check_pdf_title_capitalization(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit conservative P020 warnings for title-case issues in title-like text.

    One finding per title-like line with at least one clear violation.
    Reports the first (most significant) issue per line to avoid flooding.

    Based on NJIT guidelines: Level 2 headings and table titles use Title Case
    (each word capitalized except short articles, conjunctions, and prepositions).
    """
    findings: list[AuditFinding] = []

    for title_line in detect_pdf_title_like_lines(pdf_document):
        issues = check_apa_title_case_phrase(title_line.check_text)
        if not issues:
            continue

        first_issue = issues[0]
        details: dict[str, str] = {
            "page_number": str(title_line.page_number),
            "issue_type": "possible_title_capitalization_issue",
            "line_preview": title_line.line_preview,
            "expected_or_reason": first_issue["reason"],
            "confidence": first_issue["confidence"],
            "source": title_line.source,
            "detection_reason": title_line.detection_reason,
            # Single offending word and its corrected capitalization, so the
            # student's own report can show exactly what to fix instead of
            # only a violation category (see check_apa_title_case_phrase).
            "flagged_word": first_issue["word"],
            "corrected_word": first_issue["expected"],
        }
        if title_line.bbox is not None:
            details["bbox"] = format_bbox_detail(title_line.bbox)
        token_bbox: BBox | None = None
        if title_line.source_line is not None:
            token_bbox = word_bbox_in_line(title_line.source_line, first_issue["word"])
        if token_bbox is None and title_line.bbox is not None:
            estimated = estimate_word_bbox_in_line_bbox(
                (
                    title_line.bbox.x0,
                    title_line.bbox.y0,
                    title_line.bbox.x1,
                    title_line.bbox.y1,
                ),
                title_line.line_preview,
                first_issue["word"],
            )
            if estimated is not None:
                token_bbox = BBox(
                    x0=estimated[0],
                    y0=estimated[1],
                    x1=estimated[2],
                    y1=estimated[3],
                )
        token_detail = format_optional_bbox_detail(token_bbox)
        if token_detail:
            details["token_bbox"] = token_detail
        findings.append(
            AuditFinding(
                rule_id="P020",
                severity=Severity.WARNING,
                page=title_line.page_number,
                message=(
                    f"Possible title capitalization issue in title-like text: "
                    f"'{first_issue['word']}' may need to be capitalized "
                    f"({first_issue['reason']})."
                ),
                details=details,
            )
        )

    return findings
