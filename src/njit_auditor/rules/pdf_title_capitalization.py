"""Heuristic title-case capitalization checks for PDF title-like and heading-like text.

Scope: title-like lines only — Level 2 headings (bold, title case expected per NJIT
guidelines) and List of Tables entries.
Not applied to body paragraphs, Level 3+ sentence-case headings, figure captions,
references pages, or all-caps front-matter labels.

Source: NJIT Thesis and Dissertation Formatting Guidelines; Titles Examples Level 1–5.
  - Level 1 (chapter): ALL CAPS bold centered — already checked by P014.
  - Level 2 (X.x): Title Case bold — checked by P020.
  - Level 3–5: Sentence case — NOT checked by P020 (sentence case is expected).
  - Table titles: Title Case — checked by P017/P024.
  - Figure descriptions: Sentence case — NOT checked by P020.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median

from njit_auditor.digital_commons_wrapper import (
    detect_digital_commons_wrapper_pages,
    without_wrapper_pages,
)
from njit_auditor.highlight_targeting import (
    estimate_word_bbox_in_line_bbox,
    format_optional_bbox_detail,
    word_bbox_in_line,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_body_spacing import _line_in_bands, _table_band_ranges
from njit_auditor.rules.pdf_captions import (
    CAPTION_START_RE,
    detect_caption_lines,
    normalize_caption_candidate_text,
)
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

# NJIT/Esther title-case minor words: articles, conjunctions, and prepositions.
# Source: Titles Examples Level 1–5 and Thesis Formatting Guidelines — "Each word
# is capitalized except for articles, prepositions and conjunctions." Unlike APA's
# common "4+ letter words are major" shortcut, NJIT does not exempt long
# prepositions (e.g. "with", "from", "between") from the lowercase-minor rule.
MINOR_WORDS: frozenset[str] = frozenset(
    [
        # articles
        "a",
        "an",
        "the",
        # coordinating conjunctions
        "and",
        "but",
        "or",
        "for",
        "nor",
        "as",
        "yet",
        "so",
        # common prepositions (including 4+ letters)
        "at",
        "by",
        "in",
        "of",
        "on",
        "per",
        "to",
        "up",
        "via",
        "with",
        "from",
        "into",
        "onto",
        "upon",
        "over",
        "under",
        "about",
        "above",
        "across",
        "after",
        "against",
        "along",
        "among",
        "around",
        "before",
        "behind",
        "below",
        "beneath",
        "beside",
        "between",
        "beyond",
        "during",
        "except",
        "inside",
        "outside",
        "through",
        "throughout",
        "toward",
        "towards",
        "underneath",
        "until",
        "within",
        "without",
        "versus",
        "vs",
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

# Patterns that identify a page as a Title Page or Approval Page template.
# If any line on a page matches, the page is skipped from generic P020 bold-heading
# checks — those pages contain NJIT institutional boilerplate, not body headings.
_TEMPLATE_PAGE_MARKER_RE = re.compile(
    r"submitted\s+to\s+the\s+faculty|"
    r"in\s+partial\s+fulfillment|"
    r"in\s+fulfillment\s+of\s+the\s+requirements|"
    r"for\s+the\s+degree\s+of|"
    r"^approval\s+page$",
    re.IGNORECASE,
)

# All-caps acronym: 2+ uppercase letters (PDF, AI, MRI, NJIT, CAD, SDF, …).
_ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9]{1,}$")

# Words to skip: contain digits, Greek chars, or math/equation notation.
_SKIP_WORD_RE = re.compile(r"[0-9Α-ω+*/=<>^\\{}[\]()]")

# Subtitle separators that trigger capitalization of the following word.
_SUBTITLE_SEP_RE = re.compile(r"[:–—]|--+")
# Text allowed between a subtitle separator and the word it capitalizes.
_SEP_LEAD_IN_RE = re.compile(r"[\s\"'“‘(\[]*")

# Word token: letter-started run, optionally joined by single hyphens.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'À-ɏ]*(?:-[A-Za-z][A-Za-z'À-ɏ]*)*")

# A bold line that is *only* a Level 3+ section number (e.g. "3.4.3"), on its own
# line, immediately followed by the bold heading text. When the number and text
# are split across two lines like this, neither P020's generic bold-heading path
# nor P027's same-line numbered-heading regex can see the number prefix attached
# to the heading text — so this pattern is P020's own signal to recognize the
# following line as a Level 3+ (sentence-case) heading and exclude it, per this
# module's documented scope (Level 3+ is not checked by P020).
_LEVEL3PLUS_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+){2,4}$")
_LEVEL2_NUMBER_ONLY_RE = re.compile(r"^\d+\.\d+$")
_SAME_LINE_LEVEL2_HEADING_RE = re.compile(r"^\d+\.\d+\s+\S")

# Same-line Level 3+ numbered heading (3–5 numeric components), after optional
# reconstruction of a missing space between the number and the title text.
# Level 3–5 use sentence case, so they are out of P020 title-case scope.
_SAME_LINE_LEVEL3PLUS_HEADING_RE = re.compile(
    r"^\d+(?:\.\d+){2,4}\s+\S"
)
_LIST_MARKER_PREFIX_RE = re.compile(r"^[A-Za-z][.)]\s+")

# PDF extraction sometimes concatenates the section number span with the title
# span when the visual space is missing from the text layer, e.g.
# "3.3.9.4Robustness to input variations." Insert that boundary when a dotted
# section number is immediately followed by a letter-started title token.
_SECTION_NUMBER_GLUE_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+){1,4})(?P<body>[A-Za-z].*)$"
)

# Statistical / mathematical notation must never be forced to title case.
# Comparison and (in)equality operators that mark a variable=value expression.
_STAT_OPERATOR_RE = re.compile(r"[=<>≤≥±≈~∼]")
# Common statistical variable / table-header abbreviations (case-insensitive).
# These are notation, not English words, so title-case rules do not apply.
_STAT_ABBREVIATIONS: frozenset[str] = frozenset(
    {
        "n",
        "p",
        "r",
        "r2",
        "r²",
        "b",
        "se",
        "sd",
        "df",
        "t",
        "f",
        "m",
        "ci",
    }
)

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


def normalize_numbered_heading_text(text: str) -> str:
    """Normalize heading text and repair glued section-number prefixes.

    Some PDFs extract ``3.3.9.4Robustness…`` without the visual space between the
    number span and the title span. Restore that boundary so level classification
    and student-facing previews quote the heading accurately.
    """
    clean = normalize_title_text(text)
    glued = _SECTION_NUMBER_GLUE_RE.match(clean)
    if glued is None:
        return clean
    return f"{glued.group('num')} {glued.group('body')}"


def _is_same_line_level3plus_heading(text: str) -> bool:
    """Return True for same-line Level 3–5 numbered headings (sentence case)."""
    return bool(_SAME_LINE_LEVEL3PLUS_HEADING_RE.match(text))


def _is_same_line_level2_heading(text: str) -> bool:
    """Return True for same-line Level 2 numbered headings (title case)."""
    return bool(_SAME_LINE_LEVEL2_HEADING_RE.match(text))


def tokenize_title_words(text: str) -> list[str]:
    """Return alphabetic word tokens from title text."""
    return _WORD_RE.findall(text)


def is_minor_word(word: str) -> bool:
    """Return True if the word is an NJIT title-case minor word (article/conj/prep)."""
    return word.lower() in MINOR_WORDS


def looks_like_acronym(word: str) -> bool:
    """Return True if the word looks like an all-caps acronym (PDF, AI, NJIT…)."""
    return bool(_ACRONYM_RE.match(word))


def _should_skip_word(word: str) -> bool:
    """Return True if the word contains math/digit/equation notation — skip it."""
    return bool(_SKIP_WORD_RE.search(word))


def _is_digit_adjacent_unit_token(text: str, start: int, end: int) -> bool:
    """Return True for letter fragments glued to digits (``10k``, ``5k``, ``H2``).

    ``_WORD_RE`` only matches alphabetic runs, so ``10k`` yields a bare ``k``
    token. That fragment is a numeric unit/suffix, not an English title word.
    """
    if start > 0 and text[start - 1].isdigit():
        return True
    if end < len(text) and text[end].isdigit():
        return True
    return False


def _words_with_sep_info(text: str) -> list[tuple[str, bool, int, int]]:
    """
    Return (word, after_subtitle_sep, start, end) tuples for each word token.

    after_subtitle_sep is True when a subtitle separator (colon, em/en dash,
    double-hyphen) appears in the gap between the previous word and this word
    and only whitespace, opening quotes, or opening brackets follow it. A symbol
    or number after the separator (": # of", ": 3 of") is itself the first word
    of the subtitle, so the following word keeps its normal case rule.
    start/end are the token's character offsets within *text*, so callers can
    inspect the surrounding context (e.g. statistical notation) without doing
    unsafe substring searches.
    """
    result: list[tuple[str, bool, int, int]] = []
    last_end = 0
    after_sep = False
    for m in _WORD_RE.finditer(text):
        gap = text[last_end : m.start()]
        separators = list(_SUBTITLE_SEP_RE.finditer(gap))
        if separators and _SEP_LEAD_IN_RE.fullmatch(gap[separators[-1].end() :]):
            after_sep = True
        result.append((m.group(), after_sep, m.start(), m.end()))
        after_sep = False
        last_end = m.end()
    return result


def _is_statistical_notation_word(text: str, word: str, start: int, end: int) -> bool:
    """Return True when *word* is a statistical/mathematical notation token.

    Title/heading capitalization checks must not require statistical variables,
    formula symbols, or table-column abbreviations to follow English title case.
    This covers compact notation such as ``(n = 97)``, ``(p < .001)``,
    ``(r = 0.22)``, ``adjusted R² = 0.673``, ``B = 0.65``, and bare
    table-header abbreviations like ``SE``, ``df``, ``t``, and ``F``.

    A token qualifies when either:
      * it matches a known statistical abbreviation (case-insensitive), or
      * it is a single letter adjacent to a comparison/assignment operator or
        wrapped as a parenthesized ``(x = ...)`` style variable marker.
    """
    if word.casefold() in _STAT_ABBREVIATIONS:
        return True
    if len(word) != 1:
        return False
    # Single-letter variable next to an operator/comparator (p < .001, r = 0.22).
    window = text[max(0, start - 6) : min(len(text), end + 10)]
    if _STAT_OPERATOR_RE.search(window):
        return True
    # Parenthesized compact variable marker, e.g. "(n = 97)" or "(p)".
    left = text[:start].rstrip()
    right = text[end:].lstrip()
    return bool(
        left.endswith("(")
        and right
        and (right[0].isdigit() or right[0] in ".=<>≤≥±≈~∼)")
    )


_HYPHEN_CHARS = "-‐‑‒–—"


def _has_recent_hyphen_before(text: str, start: int) -> bool:
    """True when only extraction whitespace separates this word from a hyphen."""
    prefix = text[:start].rstrip()
    return bool(prefix) and prefix[-1] in _HYPHEN_CHARS


def _corrected_preview(
    check_text: str, line_preview: str, issues: list[dict[str, str]]
) -> str:
    """Return *line_preview* with every flagged word in *issues* corrected.

    Issue positions index the word tokens of *check_text*; the preview must be
    a prefix of it. Returns "" when the correction cannot be placed safely.
    """
    if not line_preview or not check_text.startswith(line_preview):
        return ""
    words = _words_with_sep_info(check_text)
    corrected = list(check_text)
    for issue in issues:
        try:
            word, _sep, start, end = words[int(issue["position"])]
        except (KeyError, ValueError, IndexError):
            return ""
        if word != issue["word"] or len(issue["expected"]) != end - start:
            return ""
        corrected[start:end] = issue["expected"]
    return "".join(corrected)[: len(line_preview)]


def check_apa_title_case_phrase(
    text: str, *, skip_hyphenated_fragments: bool = False
) -> list[dict[str, str]]:
    """
    Check NJIT/APA title case for a phrase.

    Returns list of issue dicts: {word, position, reason, confidence, expected}.
    An empty list means no issues detected.

    Conservative: skips hyphenated words, all-caps acronyms, and words with
    digits or special characters. When requested, also skips alphabetic
    fragments following a hyphen, which can be produced when a PDF extractor
    drops a non-Latin prefix from a scientific term. Only flags clear
    under-capitalization.
    Does not flag over-capitalization (e.g. 'The' in the middle).
    """
    words_with_info = _words_with_sep_info(text)
    if len(words_with_info) < MIN_WORDS_FOR_TITLE_CHECK:
        return []

    issues: list[dict[str, str]] = []

    for idx, (word, after_sep, start, end) in enumerate(words_with_info):
        is_first = idx == 0

        # Skip math/digit/equation tokens.
        if _should_skip_word(word):
            continue

        # A non-Latin hyphenated prefix (for example, a Greek letter in a
        # scientific name) may be omitted by the word tokenizer, leaving only
        # the suffix as an apparent standalone English word. This opt-in is
        # used by P024's List of Tables path; P020 keeps its existing behavior.
        if skip_hyphenated_fragments and _has_recent_hyphen_before(text, start):
            continue

        # Skip letter fragments glued to digits (10k / 5k / 1k).
        if _is_digit_adjacent_unit_token(text, start, end):
            continue

        # Skip statistical/math notation (n, p, r, R², B, SE, t, F, df, …).
        # These are variables/abbreviations, not English words, so title-case
        # capitalization rules do not apply to them.
        if _is_statistical_notation_word(text, word, start, end):
            continue

        # Preserve all-caps acronyms — never flag these.
        if looks_like_acronym(word):
            continue

        # Hyphenated words: conservative — skip entirely.
        if "-" in word:
            continue

        # NJIT/Esther: capitalize the first word, words after subtitle separators,
        # and major words. Articles/prepositions/conjunctions stay lowercase even
        # when they happen to be the final token (no APA-style last-word override).
        should_be_capitalized = (
            is_first or after_sep or not is_minor_word(word.lower())
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


def _is_template_frontmatter_page(page: PdfPage) -> bool:
    """Return True when a page contains NJIT title-page or approval-page boilerplate.

    Such pages must not be subject to generic body-heading title-case checks (P020)
    because their text is institutional template language, not manuscript headings.
    A single strong-signal pattern match on any line is sufficient.
    """
    for block in page.text_blocks:
        for line in block.lines:
            clean = normalize_title_text(line.text)
            if _TEMPLATE_PAGE_MARKER_RE.search(clean):
                return True
    return False


def _is_prose_paragraph_line(text: str) -> bool:
    """Return True when text looks like a body-paragraph fragment rather than a heading.

    Catches cases where wrapper-page paragraph text slips through detection:
    three or more commas, multiple mid-sentence periods, or a dangling end
    punctuation (comma/semicolon) all indicate body prose rather than headings.
    """
    if text.count(",") >= 3:
        return True
    if text.count(". ") >= 2:
        return True
    stripped = text.rstrip()
    if stripped.endswith(",") or stripped.endswith(";"):
        return True
    return False


def _starts_with_minor_word(text: str) -> bool:
    """True when the first alphabetic token is a title-case minor word.

    Level 2 titles and table titles capitalize the first word, so a bold line
    that begins with ``and`` / ``in`` / ``of`` is typically a wrapped continuation
    of a multi-line heading, not a standalone title-case target.
    """
    words = tokenize_title_words(text)
    return bool(words) and is_minor_word(words[0])


def _has_same_baseline_run_in_body(page: PdfPage, line: PdfTextLine) -> bool:
    """Return True when non-bold text continues on the same baseline to the right.

    NJIT Level 4 headings are run-in: sentence-case heading, then body text on the
    same line. PyMuPDF often emits that as a bold line plus a separate non-bold
    line sharing the baseline. Those are not Level 2 title-case targets for P020.
    """
    y_tol = 2.0
    for block in page.text_blocks:
        for other in block.lines:
            if other is line:
                continue
            if abs(other.bbox.y0 - line.bbox.y0) > y_tol:
                continue
            if other.bbox.x0 + 0.5 < line.bbox.x1:
                continue
            other_text = normalize_title_text(other.text)
            if not other_text or _is_page_number_line(other_text):
                continue
            if _spans_bold_reason(other) is None:
                return True
    return False


def detect_pdf_title_like_lines(pdf_document: PdfDocument) -> list[TitleLikeLine]:
    """
    Detect title-like lines for NJIT title-case checking.

    Includes:
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
    wrapper_pages = detect_digital_commons_wrapper_pages(pdf_document)
    working_doc = without_wrapper_pages(pdf_document, wrapper_pages)
    results: list[TitleLikeLine] = []

    table_caption_bboxes_by_page: dict[int, list[BBox]] = {}
    for caption in detect_caption_lines(working_doc):
        if caption.caption_type == "table" and caption.bbox is not None:
            table_caption_bboxes_by_page.setdefault(caption.page_number, []).append(caption.bbox)

    body_size = _estimate_document_body_size(working_doc)

    # Bold heading-like lines (Level 2 and similar title-case headings).
    for page in working_doc.pages:
        page_ctx = _page_context_type(page)
        if page_ctx in {"references", "toc"}:
            continue
        if _is_template_frontmatter_page(page):
            continue  # Title/Approval Page boilerplate — not subject to generic P020
        all_lines = [line for block in page.text_blocks for line in block.lines]
        table_bands = _table_band_ranges(
            table_caption_bboxes_by_page.get(page.page_number, []),
            all_lines,
            body_size,
        )
        prev_numbered_heading_level: int | None = None
        numbered_heading_block_y1: float | None = None
        for block in page.text_blocks:
            for line in block.lines:
                clean = normalize_numbered_heading_text(line.text)
                if not clean:
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if _is_page_number_line(clean):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if _is_frontmatter_allcaps_label(clean):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if len(clean) > MAX_HEADING_LINE_LEN:
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if CAPTION_START_RE.match(normalize_caption_candidate_text(clean)):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue  # already covered by caption detection above
                if _LIST_MARKER_PREFIX_RE.match(clean):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if _is_prose_paragraph_line(clean):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue  # prose body text, not a heading
                if _is_same_line_level3plus_heading(clean):
                    # Level 3–5 numbered headings use sentence case (P027), not
                    # Title Case. Keep the number-only split-line state machine
                    # from also treating a following bold line as L2 title case.
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                # NJIT Level 4/5 headings end with a period and use sentence case.
                # Level 2 titles and table titles do not. A bold line that already
                # ends with '.' is therefore out of P020 title-case scope (it may
                # be an unnumbered/run-in Level 4–5 heading or a bolded phrase).
                if clean.endswith(".") and not clean.endswith("..."):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if _has_same_baseline_run_in_body(page, line):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if _line_in_bands(line, table_bands):
                    prev_numbered_heading_level = None
                    numbered_heading_block_y1 = None
                    continue
                if _starts_with_minor_word(clean):
                    # Wrapped continuation ("and …"); if still inside a numbered
                    # heading block, keep the block open for further wraps.
                    if not (
                        prev_numbered_heading_level is not None
                        and numbered_heading_block_y1 is not None
                        and (line.bbox.y0 - numbered_heading_block_y1)
                        <= max(8.0, (line.bbox.y1 - line.bbox.y0) * 1.3)
                    ):
                        prev_numbered_heading_level = None
                        numbered_heading_block_y1 = None
                    else:
                        numbered_heading_block_y1 = line.bbox.y1
                    continue

                detection_reason = _spans_bold_reason(line)
                if detection_reason is None and len(clean) <= _MAX_FONT_SIZE_FALLBACK_LINE_LEN:
                    # Font-size fallback: treat as heading-like if significantly larger than body.
                    # Only apply for short lines to avoid catching body paragraphs.
                    if _is_font_size_heading(line, body_size):
                        detection_reason = "font_size_heading_fallback"

                is_level2_number = detection_reason is not None and bool(
                    _LEVEL2_NUMBER_ONLY_RE.match(clean)
                )
                is_level3plus_number = detection_reason is not None and bool(
                    _LEVEL3PLUS_NUMBER_ONLY_RE.match(clean)
                )

                if is_level2_number:
                    prev_numbered_heading_level = 2
                    numbered_heading_block_y1 = line.bbox.y1
                    continue

                if is_level3plus_number:
                    prev_numbered_heading_level = 3
                    numbered_heading_block_y1 = line.bbox.y1
                    continue

                if prev_numbered_heading_level is not None and detection_reason is not None:
                    # Bold line(s) for a numbered heading whose number lives on a
                    # previous line. Level 2 is in P020 scope; Level 3+ is sentence
                    # case and remains out of scope.
                    if numbered_heading_block_y1 is None or (
                        line.bbox.y0 - numbered_heading_block_y1
                    ) <= max(8.0, (line.bbox.y1 - line.bbox.y0) * 1.3):
                        numbered_heading_block_y1 = line.bbox.y1
                        if prev_numbered_heading_level != 2:
                            continue
                    else:
                        prev_numbered_heading_level = None
                        numbered_heading_block_y1 = None

                if detection_reason is not None and (
                    _is_same_line_level2_heading(clean)
                    or prev_numbered_heading_level == 2
                ):
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

                prev_numbered_heading_level = None
                numbered_heading_block_y1 = None

    return results


def check_pdf_title_capitalization(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit conservative P020 warnings for title-case issues in title-like text.

    One finding per title-like line with at least one clear violation.
    Reports the first (most significant) issue per line to avoid flooding.

    Based on NJIT guidelines: Level 2 headings use Title Case
    (each word capitalized except short articles, conjunctions, and prepositions).
    """
    findings: list[AuditFinding] = []

    for title_line in detect_pdf_title_like_lines(pdf_document):
        check_text = title_line.check_text
        line_preview = title_line.line_preview
        # Glued PDF extractions (dropped whitespace spans) can invent false
        # "major words" such as ``andPerformance``. If geometry-aware span
        # joining yields a phrase with no title-case issue, suppress the
        # finding. When *both* glued and rebuilt still have issues, prefer the
        # rebuilt phrase so the flagged word matches visible text (e.g. ``power``
        # instead of ``inpowersystems``). Do not emit *new* findings that appear
        # only after joining — that would expand P020 onto previously invisible
        # sentence-case headings whose level/policy is Esther-dependent.
        if title_line.source == "heading" and title_line.source_line is not None:
            rebuilt = normalize_numbered_heading_text(
                join_content_span_texts(title_line.source_line.spans)
            )
            if rebuilt and rebuilt != check_text:
                glued_issues = check_apa_title_case_phrase(check_text)
                rebuilt_issues = check_apa_title_case_phrase(rebuilt)
                if glued_issues and not rebuilt_issues:
                    continue
                if glued_issues and rebuilt_issues:
                    check_text = rebuilt
                    line_preview = rebuilt[:MAX_PREVIEW_LEN]
        issues = check_apa_title_case_phrase(check_text)
        if not issues:
            continue

        first_issue = issues[0]
        details: dict[str, str] = {
            "page_number": str(title_line.page_number),
            "issue_type": "possible_title_capitalization_issue",
            "line_preview": line_preview,
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
        corrected_preview = _corrected_preview(check_text, line_preview, issues)
        if corrected_preview:
            # Every flagged word corrected, so a suggested rewrite of the
            # title is itself in title case (not just its first problem word).
            details["corrected_title_preview"] = corrected_preview
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
                line_preview,
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
