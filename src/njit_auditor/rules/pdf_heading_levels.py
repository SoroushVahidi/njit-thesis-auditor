"""Conservative PDF heading-level style checks (P027).

Detects heading-like lines using numbered-section patterns (1.1, 1.1.1, etc.)
and infers expected capitalization/punctuation style from NJIT guidelines.

NJIT expectations (Titles Examples Level 1 to 5.docx):
  Level 1: ALL CAPS, bold, centered  — P014 covers named front-matter; P027 covers body chapters.
  Level 2: Title Case, bold          — supplementary to P020 (adds coverage for non-bold PDFs).
  Level 3: Sentence case, bold       — flagged when title-case-like (≥2 non-first caps words).
  Level 4: Sentence case, period     — flagged when title-case-like or missing terminal period.
  Level 5: Sentence case, period, italic — same checks; italic detection is unreliable.

Q-rule basis: Q051 (Level 3 sentence case).

Does NOT duplicate:
  - P014: named front-matter heading style (ABSTRACT, APPROVAL PAGE, etc.).
  - P020: bold-line title-case checking.
  - P024: TOC/List entry capitalization.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import (
    BOLD_FONT_HINT_RE,
    EXPECTED_HEADINGS,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE
from njit_auditor.rules.pdf_title_capitalization import (
    check_apa_title_case_phrase,
    is_minor_word,
    looks_like_acronym,
)

# Numbered section patterns — most specific first.
_L5_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+\.\d+)\s+(.+)$")
_L4_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\s+(.+)$")
_L3_RE = re.compile(r"^(\d+\.\d+\.\d+)\s+(.+)$")
_L2_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")

# Level 1 body-chapter pattern: "CHAPTER N ..." or "APPENDIX A ...".
_CHAPTER_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+\s*(.*)$")

# Year-in-parens pattern — indicates a reference/citation, not a heading.
_CITATION_RE = re.compile(r"\(\d{4}\)")

# Pages to skip entirely.
_SKIP_HEADINGS: frozenset[str] = frozenset(EXPECTED_HEADINGS) | frozenset(
    ["REFERENCES", "BIBLIOGRAPHY", "WORKS CITED", "DEDICATION", "COPYRIGHT PAGE"]
)
_TOC_LIST_HEADINGS: frozenset[str] = frozenset(
    ["TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES"]
)

_TOP_ZONE_RATIO = 0.15
_MIN_HEADING_TEXT_LEN = 5
_MAX_HEADING_LINE_LEN = 150
_MAX_PREVIEW_LEN = 80
_MIN_ALPHA_RATIO = 0.50
# ≥2 non-first capitalized major words required to call text "title-case-like".
_TITLE_CASE_MAJOR_WORD_MIN = 2


def _in_margin_zone(line: PdfTextLine, page_height: float) -> bool:
    top = page_height * _TOP_ZONE_RATIO
    bottom = page_height * (1.0 - _TOP_ZONE_RATIO)
    return line.bbox.y0 < top or line.bbox.y0 > bottom


def _page_has_any_heading(page: PdfPage, headings: frozenset[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            if normalize_heading_text(line.text).upper() in headings:
                return True
    return False


# A capitalized word directly followed by a number or label ("Theorem 5.2",
# "Part (i)", "Section 3") names a specific item and keeps its capital.
_REFERENCE_LABEL_RE = re.compile(r"^\(?(?:\d+(?:\.\d+)*|[ivxlcdm]+|[IVXLCDM]+|[A-Z])\)?[,.;:]?$")
_BODY_WORD_RE = re.compile(r"(?<![\w.])([A-Za-z][a-z]+)\b")
_PROPER_NOUN_MIN_OCCURRENCES = 2


def _document_proper_nouns(pdf_doc: PdfDocument) -> frozenset[str]:
    """Words the document's body text always capitalizes mid-sentence.

    Level 3-5 headings use sentence case, which still capitalizes proper
    names (Ester: "capitalizing only the first word and proper names"). A word
    written capitalized at least twice mid-sentence in non-bold body text and
    never in lowercase is treated as a proper name (e.g. "Markov").
    """
    capitalized: dict[str, int] = {}
    lowercase: set[str] = set()
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                if _is_bold_line(line):
                    continue
                text = " ".join(join_content_span_texts(line.spans).split())
                for match in _BODY_WORD_RE.finditer(text):
                    word = match.group(1)
                    before = text[: match.start()].rstrip()
                    if not before or before.endswith((".", "?", "!", ":")):
                        continue  # sentence or line start: case says nothing
                    key = word.lower()
                    if word[0].isupper():
                        capitalized[key] = capitalized.get(key, 0) + 1
                    else:
                        lowercase.add(key)
    return frozenset(
        word
        for word, count in capitalized.items()
        if count >= _PROPER_NOUN_MIN_OCCURRENCES and word not in lowercase
    )


def _keeps_capital(words: list[str], index: int, proper_nouns: frozenset[str]) -> bool:
    """True when words[index] is a proper name or a labelled reference."""
    core = words[index].strip(".,;:!?\"'()-[]")
    if core.lower() in proper_nouns:
        return True
    following = words[index + 1] if index + 1 < len(words) else ""
    return bool(_REFERENCE_LABEL_RE.match(following))


def _looks_like_title_case_violation(
    text: str, proper_nouns: frozenset[str] = frozenset()
) -> bool:
    """Return True if text has ≥2 non-first capitalized major words (title-case signal).

    Used to detect sentence-case violations: if a Level 3–5 heading looks like it
    was written in title case, this returns True. Conservative: requires ≥2 such words.
    """
    words = text.split()
    if len(words) < 3:
        return False
    major_caps = 0
    for index, word in enumerate(words[1:], start=1):
        if _keeps_capital(words, index, proper_nouns):
            continue
        clean = word.strip(".,;:!?\"'()-[]")
        if not clean or not clean[0].isupper():
            continue
        if is_minor_word(clean.lower()):
            continue
        if looks_like_acronym(clean):
            continue
        if len(clean) <= 1:
            continue
        major_caps += 1
    return major_caps >= _TITLE_CASE_MAJOR_WORD_MIN


def _is_all_caps_phrase(text: str) -> bool:
    """Return True when ≥80% of alphabetic chars in text are uppercase."""
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return False
    return sum(1 for c in alpha if c.isupper()) / len(alpha) >= 0.80


def _is_bold_line(line: PdfTextLine) -> bool:
    """Return True when the line's text is (mostly) bold.

    Per Titles Examples Level 1 to 5.docx, numbered Level 2-5 headings are all
    bold and stand on their own line — a body sentence that merely starts with
    a decimal-looking number (e.g. a statistic like "68.4 percent...") is
    neither. Requiring bold before treating a numbered-pattern match as a real
    heading candidate is what keeps such sentences from being misclassified.
    """
    if not line.spans:
        return False
    return any(
        span.bold or bool(span.font and BOLD_FONT_HINT_RE.search(span.font))
        for span in line.spans
    )


def _sentence_case_example(
    number_prefix: str, heading_text: str, proper_nouns: frozenset[str] = frozenset()
) -> str:
    """Return a conservative sentence-case rewrite of heading_text, or "" if unsafe.

    Only lowercases simple Title-Case words (single leading capital, rest
    lowercase); acronyms, hyphenated/mixed-case tokens, and numbers are left
    untouched. Returns "" if nothing would change, so callers can skip
    offering a misleading "example" when the safe rewrite is a no-op.
    """
    words = heading_text.split()
    if not words:
        return ""
    rewritten = [words[0]]
    changed = False
    for index, word in enumerate(words[1:], start=1):
        core = word.strip(".,;:!?\"'()-[]")
        if _keeps_capital(words, index, proper_nouns):
            rewritten.append(word)
            continue
        if core and core[0].isupper() and core[1:].islower() and not looks_like_acronym(core):
            lowered = word[0].lower() + word[1:]
            rewritten.append(lowered)
            changed = True
        else:
            rewritten.append(word)
    if not changed:
        return ""
    return f"{number_prefix} {' '.join(rewritten)}"


def _union_bbox(a: BBox, b: BBox) -> BBox:
    return BBox(x0=min(a.x0, b.x0), y0=min(a.y0, b.y0), x1=max(a.x1, b.x1), y1=max(a.y1, b.y1))


# A wrapped heading's second physical line sits immediately below the
# first with no blank line (verified against a real reviewed case: 0.5pt
# gap on a 13.3pt line height, ratio ~0.04). A real corpus PDF can pack a
# heading's wrap *and* the following body paragraph into the same PyMuPDF
# text block when nothing resets block segmentation between them -- e.g.
# a bold amino-acid-sequence line directly below a heading, same block,
# but a full extra line of leading below it (ratio ~1.08 in that case).
# This ratio is what actually distinguishes "still the heading" from
# "next paragraph, coincidentally bold" -- being in the same block is
# necessary but not sufficient.
_MAX_WRAP_LINE_GAP_RATIO = 0.6


def _is_tight_wrap_gap(prev_line: PdfTextLine, next_line: PdfTextLine) -> bool:
    prev_height = max(prev_line.bbox.height, 1.0)
    gap = next_line.bbox.y0 - prev_line.bbox.y1
    return gap <= _MAX_WRAP_LINE_GAP_RATIO * prev_height


def _is_continuation_line(line: PdfTextLine) -> bool:
    """A physical line that continues a wrapped heading onto a new line:
    bold (same requirement as a heading's own first line) and not itself
    the start of a new numbered or chapter/appendix heading. Does not by
    itself check vertical proximity -- see ``_is_tight_wrap_gap``, checked
    separately by the caller against the actual previous line consumed."""
    if not _is_bold_line(line):
        return False
    clean = " ".join(line.text.strip().split())
    if not clean:
        return False
    if any(pattern.match(clean) for pattern in (_L5_RE, _L4_RE, _L3_RE, _L2_RE)):
        return False
    if _CHAPTER_RE.match(clean):
        return False
    if normalize_heading_text(clean).upper() in _SKIP_HEADINGS | _TOC_LIST_HEADINGS:
        return False
    return True


def _gather_wrapped_heading(
    block_lines: list[PdfTextLine], start_index: int, heading_text: str
) -> tuple[str, PdfTextLine]:
    """Numbered NJIT headings (Level 2-5) are a single bold run that can
    wrap across more than one physical PDF line -- e.g. a long Level 4
    heading whose terminal period lands on the second line. Checking only
    the first physical line (the prior behavior) means that period is
    never seen, which is exactly the false positive Ester reported
    (level4_sentence_case_or_punctuation_issue, "the period is there, but
    the auditor does not recognize that this title ends on the second
    line" -- see docs/evaluation/ESTER_FEEDBACK_MIGRATION.md).

    Gather any immediately-following bold, non-heading continuation lines
    that sit tightly below the previous one (``_is_tight_wrap_gap``) and
    append their text, so every downstream check sees the complete
    logical heading. Same PyMuPDF text block is necessary but not
    sufficient on its own -- a real corpus PDF was found (during this
    fix's own verification) to pack a heading's wrap *and* the following
    body paragraph into one block with no other boundary between them, so
    the gap check is what actually stops the merge at the heading's real
    end. Returns the merged text and the last physical line consumed
    (used for the finding's bbox, so a wrapped heading's highlight still
    spans what was actually flagged). For a single-line heading (the
    common case), no continuation line qualifies and this is a no-op:
    merged text and last line both equal the input.
    """
    merged = heading_text
    last_line = block_lines[start_index]
    for line in block_lines[start_index + 1 :]:
        if not _is_continuation_line(line):
            break
        if not _is_tight_wrap_gap(last_line, line):
            break
        continuation = " ".join(line.text.strip().split())
        merged = f"{merged} {continuation}"
        last_line = line
    return merged, last_line


def _is_qualified_heading(text: str) -> bool:
    """Return True when heading text looks like a real heading title (not noise/equations).

    Does NOT check first-character case — lowercase-first may be a formatting error that
    level-specific checks should flag.
    """
    if len(text) < _MIN_HEADING_TEXT_LEN or len(text) > _MAX_HEADING_LINE_LEN:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    if alpha / max(len(text), 1) < _MIN_ALPHA_RATIO:
        return False
    if _CITATION_RE.search(text):
        return False
    return True


def _period_precedes_math_continuation(prefix: str, text: str) -> bool:
    """A dotted abbreviation followed by an expression is not a proven boundary.

    Upright identifiers and function applications can continue a heading after
    an abbreviation. Recognize their syntax, not particular function names.
    Require the complete suffix to have expression syntax: prose containing an
    equation does not undo an otherwise valid bold-to-regular boundary. A hyphen
    inside a word is not a subtraction operator. Without a dotted abbreviation,
    retain the existing terminal-period boundary even for a body formula.
    """
    if re.search(r"[^\W\d]+\.[^\W\d]+\.\s*$", prefix) is None:
        return False
    atom = r"(?:[^\W\d]\w*(?:\([^()]*\))?|\d+(?:\.\d+)?)"
    operand = rf"(?:{atom}\s+)?{atom}"
    operator = r"(?:\s*[+*/=<>^−×÷±≤≥≠]\s*|\s+-\s+)"
    return re.fullmatch(
        rf"\s*{operand}(?:{operator}{operand})+\.?\s*", text
    ) is not None


def _bold_run_in_has_terminal_period(line: PdfTextLine, pattern: re.Pattern[str]) -> bool:
    """Read a run-in heading's period when raw span text omits word spaces."""
    prefix_end = 0
    for span in line.spans:
        # Whitespace has no title/body role, regardless of its font. Only
        # nonblank regular text can end the bold heading run.
        if not span.bold and span.text.strip():
            break
        prefix_end += 1
    bold_spans = line.spans[:prefix_end]
    if not bold_spans or prefix_end == len(line.spans):
        return False
    tail = line.spans[prefix_end:]
    first_tail = next((span for span in tail if span.text.strip()), None)
    if first_tail is None or first_tail.italic:
        return False
    # An italic continuation or a mathematical expression is still heading content,
    # not enough evidence of an ordinary body sentence after the bold title.
    tail_text = join_content_span_texts(tail)
    if not _is_qualified_heading(tail_text) or _period_precedes_math_continuation(
        join_content_span_texts(bold_spans), tail_text
    ):
        return False
    match = pattern.match(" ".join(join_content_span_texts(bold_spans).split()))
    if match is None:
        return False
    title = match.group(2).strip()
    return _is_qualified_heading(title) and title.endswith(".")


def _finding(
    page_number: int,
    issue_type: str,
    inferred_level: str,
    heading_pattern: str,
    message: str,
    expected_or_reason: str,
    line_preview: str,
    confidence: str,
    source_q_rule_id: str = "",
    bbox: BBox | None = None,
) -> AuditFinding:
    details: dict[str, str] = {
        "page_number": str(page_number),
        "issue_type": issue_type,
        "inferred_level": inferred_level,
        "heading_pattern": heading_pattern,
        "expected_or_reason": expected_or_reason,
        "line_preview": line_preview[:_MAX_PREVIEW_LEN],
        "confidence": confidence,
    }
    if source_q_rule_id:
        details["source_q_rule_id"] = source_q_rule_id
    if bbox is not None:
        details["bbox"] = format_bbox_detail(bbox)
    return AuditFinding(
        rule_id="P027",
        severity=Severity.WARNING,
        page=page_number,
        message=message,
        details=details,
    )


def _check_line(
    page: PdfPage,
    block_lines: list[PdfTextLine],
    index: int,
    proper_nouns: frozenset[str] = frozenset(),
) -> list[AuditFinding]:
    line = block_lines[index]
    if _in_margin_zone(line, page.height):
        return []
    clean = " ".join(line.text.strip().split())
    if not clean or PAGE_NUM_RE.match(clean):
        return []
    if normalize_heading_text(clean).upper() in _SKIP_HEADINGS:
        return []
    if len(clean) > _MAX_HEADING_LINE_LEN:
        return []

    preview = clean[:_MAX_PREVIEW_LEN]
    results: list[AuditFinding] = []

    # Try numbered patterns, most-specific first.
    for level, pattern in [(5, _L5_RE), (4, _L4_RE), (3, _L3_RE), (2, _L2_RE)]:
        m = pattern.match(clean)
        if not m:
            continue
        number_prefix, heading_text = m.group(1), m.group(2).strip()
        if not _is_qualified_heading(heading_text):
            break  # matched pattern but text is not heading-like; skip
        if not _is_bold_line(line):
            # A body sentence that merely starts with a decimal-looking number
            # (e.g. "68.4 percent of participants...") matches the numbered
            # pattern but is not a heading — NJIT numbered headings are bold.
            break

        # A wrapped heading's terminal period (or a title-case violation
        # spanning the wrap) can land on a later physical line — see
        # _gather_wrapped_heading's docstring. finding_bbox spans the full
        # heading when it wrapped, or is just the single line otherwise.
        heading_text, last_line = _gather_wrapped_heading(block_lines, index, heading_text)
        if level in (4, 5) and line.spans:
            # Run-in level-4/5 headings can share one physical line with the
            # following ordinary body sentence. Check the bold heading run,
            # not the body text that follows its terminal period.
            bold_prefix = ""
            prefix_end = 0
            for span in line.spans:
                if not span.bold and span.text.strip():
                    break
                bold_prefix += span.text
                prefix_end += 1
            bold_match = pattern.match(" ".join(bold_prefix.split()))
            if (
                bold_match
                and len(bold_prefix) < len(line.text)
                and not _period_precedes_math_continuation(
                    bold_prefix, join_content_span_texts(line.spans[prefix_end:])
                )
            ):
                heading_text = bold_match.group(2).strip()
                last_line = line
        finding_bbox = (
            line.bbox if last_line is line else _union_bbox(line.bbox, last_line.bbox)
        )

        if level == 2:
            issues = check_apa_title_case_phrase(heading_text)
            high_conf = [i for i in issues if i.get("confidence") == "high"]
            if high_conf:
                first = high_conf[0]
                results.append(_finding(
                    page.page_number,
                    issue_type="level2_title_case_issue",
                    inferred_level="2",
                    heading_pattern=number_prefix,
                    message=(
                        f"Level 2 heading on page {page.page_number} may violate "
                        f"title-case style (NJIT: Level 2 = Title Case)."
                    ),
                    expected_or_reason=(
                        f"Title Case; {first.get('reason', '?')} "
                        f"on '{first.get('word', '?')}'"
                    ),
                    line_preview=preview,
                    confidence="medium",
                    bbox=finding_bbox,
                ))

        else:  # level 3, 4, 5
            q_rule = "Q051" if level == 3 else ""
            if _looks_like_title_case_violation(heading_text, proper_nouns):
                example = _sentence_case_example(number_prefix, heading_text, proper_nouns)
                original = f"{number_prefix} {heading_text}"
                if example:
                    # Prefer an exact, safe token-level replacement over a
                    # generic style reminder when one can be computed.
                    message = (
                        f'Change "{original}" to "{example}" '
                        f"(Level {level} heading; NJIT: Level {level} = Sentence case)."
                    )
                else:
                    message = (
                        f"Change this Level {level} heading to sentence case "
                        f"(NJIT: Level {level} = Sentence Case)."
                    )
                finding = _finding(
                    page.page_number,
                    issue_type=f"level{level}_sentence_case_issue",
                    inferred_level=str(level),
                    heading_pattern=number_prefix,
                    message=message,
                    expected_or_reason="Sentence case (only first word capitalized)",
                    line_preview=preview,
                    confidence="medium",
                    source_q_rule_id=q_rule,
                    bbox=finding_bbox,
                )
                if example:
                    finding.details["corrected_example"] = example
                    finding.details["corrected_from"] = original
                results.append(finding)
            # Level 4/5: heading text should end with a period.
            if (
                level in (4, 5)
                and not heading_text.rstrip().endswith(".")
                and not _bold_run_in_has_terminal_period(line, pattern)
            ):
                results.append(_finding(
                    page.page_number,
                    issue_type=f"level{level}_sentence_case_or_punctuation_issue",
                    inferred_level=str(level),
                    heading_pattern=number_prefix,
                    message=(
                        f"Level {level} heading on page {page.page_number} may be "
                        f"missing a required terminal period "
                        f"(NJIT: Level {level} heading ends with a period)."
                    ),
                    expected_or_reason="Heading text should end with a period '.'",
                    line_preview=preview,
                    confidence="low",
                    source_q_rule_id=q_rule,
                    bbox=finding_bbox,
                ))
        break  # apply only the most specific matched level

    else:
        # No numbered pattern matched — check for Level 1 body-chapter headings.
        m1 = _CHAPTER_RE.match(clean)
        if m1:
            title_part = m1.group(2).strip()
            if title_part and len(title_part) >= 3 and not _is_all_caps_phrase(title_part):
                results.append(_finding(
                    page.page_number,
                    issue_type="level1_not_all_caps",
                    inferred_level="1",
                    heading_pattern="CHAPTER/APPENDIX",
                    message=(
                        f"Chapter/Appendix heading on page {page.page_number} title "
                        f"may not be ALL CAPS (NJIT: Level 1 = ALL CAPS)."
                    ),
                    expected_or_reason="ALL CAPS heading title after CHAPTER/APPENDIX N",
                    line_preview=preview,
                    confidence="medium",
                    bbox=line.bbox,
                ))

    return results


def check_pdf_heading_level_styles(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P027 warnings for numbered headings that violate expected level-specific style.

    Conservative: only numbered section headings (1.1, 1.1.1, etc.) are classified.
    Pages with named front-matter headings, TOC/List headings, or references are skipped.
    """
    findings: list[AuditFinding] = []
    proper_nouns = _document_proper_nouns(pdf_doc)
    for page in pdf_doc.pages:
        if _page_has_any_heading(page, _SKIP_HEADINGS):
            continue
        if _page_has_any_heading(page, _TOC_LIST_HEADINGS):
            continue
        merged = _split_number_headings(page)
        for block in page.text_blocks:
            lines = [merged.get(id(line), line) for line in block.lines]
            for index in range(len(lines)):
                findings.extend(_check_line(page, lines, index, proper_nouns))
    return findings


# A bold line holding only a section number ("3.4.3"), with the heading text
# extracted as a separate line on the same baseline to its right.
_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+)+\.?$")
_SPLIT_BASELINE_TOLERANCE_PT = 2.0
_SPLIT_MAX_GAP_PT = 72.0


def _split_number_headings(page: PdfPage) -> dict[int, PdfTextLine]:
    """Map each split heading's title line to one line carrying number + title.

    Some PDFs extract a numbered heading's number and its title as two lines
    (sometimes in different text blocks), so the numbered-heading patterns,
    which need "3.4.3 Title" on one line, never see the heading. Rejoin them
    only when both parts are bold and share a baseline, with the title just
    to the right of the number; the number-only line then matches no pattern
    on its own, so the heading is checked exactly once.
    """
    lines = [line for block in page.text_blocks for line in block.lines]
    numbers = [
        line
        for line in lines
        if _NUMBER_ONLY_RE.match(line.text.strip()) and _is_bold_line(line)
    ]
    merged: dict[int, PdfTextLine] = {}
    for number in numbers:
        candidates = [
            line
            for line in lines
            if line is not number
            and id(line) not in merged
            and _is_bold_line(line)
            and abs(line.bbox.y0 - number.bbox.y0) <= _SPLIT_BASELINE_TOLERANCE_PT
            and abs(line.bbox.y1 - number.bbox.y1) <= _SPLIT_BASELINE_TOLERANCE_PT
            and 0 <= line.bbox.x0 - number.bbox.x1 <= _SPLIT_MAX_GAP_PT
            and line.text.strip()
            and not line.text.strip()[0].isdigit()
        ]
        if not candidates:
            continue
        title = min(candidates, key=lambda line: line.bbox.x0)
        merged[id(title)] = PdfTextLine(
            spans=[*number.spans, *title.spans],
            bbox=_union_bbox(number.bbox, title.bbox),
            # Rebuild word spaces from span geometry: these PDFs often omit
            # whitespace spans, which concatenates the title's words.
            text=f"{number.text.strip()} {join_content_span_texts(title.spans).strip()}",
            line_dir=title.line_dir,
            wmode=title.wmode,
        )
    return merged
