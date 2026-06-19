"""Heuristic body font compliance check (P026).

Conservative: emits one warning per (page, issue_type) only when a majority of
ordinary body-text spans on that page show the same font issue.

Checks:
  A. Font size: body text should be approximately 12pt (±1pt, i.e. 11.0–13.0pt).
  B. Font family: body text should use Times New Roman or an accepted equivalent.

Accepted font families (no warning):
  - Times New Roman and variants: Times-Roman, TimesNewRoman, TimesNewRomanPSMT,
    TimesNewRomanPS, etc.
  - Near-equivalent serifs: NimbusRomNo9L, TeX Gyre Termes, Liberation Serif,
    FreeSerif, STIX, STIXGeneral, etc.
  - Embedded subset variants: e.g., ABCDEF+TimesNewRomanPSMT (prefix stripped).

Computer Modern (LaTeX default):
  - CMR, CMBX, CMTI, Latin Modern (LMRoman, LMBX) — flagged as non-Times.
  - Common in LaTeX dissertations; may or may not be accepted by department.

Math/symbol fonts (CMR variants CMM/CMY, MSAM, MSBM, Symbol, ZapfDingbats):
  - Skipped — not body text.

Sources:
  - Thesis and Dissertation Formatting Guidelines (WIP).docx: Times New Roman 12pt
  - Self-Self Assessment Sheet.pdf: explicit font size/family checklist item
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextSpan, format_bbox_detail
from njit_auditor.rules.pdf_headings import EXPECTED_HEADINGS, normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

# Mirror the top/bottom zone ratio used by P013/P023.
_TOP_ZONE_RATIO = 0.15

# Body-text line quality filters (mirrors P023 thresholds).
_MIN_LINE_LEN = 30
_MIN_ALPHA_COUNT = 15

# Font size compliance.
EXPECTED_BODY_SIZE_PT = 12.0
BODY_SIZE_TOLERANCE_PT = 1.0  # accept spans in [11.0, 13.0] pt

# Per-span bounds: skip obvious non-body spans.
_SPAN_MIN_SIZE = 8.0
_SPAN_MAX_SIZE = 16.0

# Conservative warning thresholds: require both count AND fraction.
_MIN_CANDIDATE_SPANS = 5
_MIN_VIOLATION_COUNT = 5
_MIN_VIOLATION_FRACTION = 0.50

# Embedded subset prefix pattern (e.g., "ABCDEF+TimesNewRomanPSMT").
_SUBSET_PREFIX_RE = re.compile(r"^[A-Z]{6}\+")

# Caption and bullet markers (mirrors P023).
_CAPTION_PREFIX_RE = re.compile(r"^(figure|table)\s+[\divxlcdm]+[.:)]?\s+", re.IGNORECASE)
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s+")

# Named headings used for page-skip and line-skip decisions.
_NAMED_HEADINGS: frozenset[str] = frozenset(EXPECTED_HEADINGS) | frozenset(
    ["REFERENCES", "BIBLIOGRAPHY", "WORKS CITED", "DEDICATION", "COPYRIGHT PAGE"]
)

# Accepted font substrings (lowercased, separators removed) — no warning if matched.
_TIMES_ACCEPTS: list[str] = [
    "times",
    "nimbusrom",
    "texgyretermes",
    "liberationserif",
    "freeserif",
    "stixgeneral",
    "stix",
]

# Computer Modern / Latin Modern prefixes (lowercased, separators removed).
_CM_PREFIXES: list[str] = ["cmr", "cmbx", "cmti", "cmsl", "cmb", "lmroman", "lmbx"]

# Math / symbol font substrings — spans with these are skipped for family checks.
_MATH_FONT_PATTERNS: list[str] = ["cmmi", "cmsy", "cmex", "msam", "msbm", "wasy", "symbol", "zapf"]


def _normalize_font(name: str) -> str:
    """Strip embedded-subset prefix and normalize to lowercase, no separators."""
    stripped = _SUBSET_PREFIX_RE.sub("", name)
    return stripped.lower().replace("-", "").replace(" ", "").replace("_", "")


def classify_font(font_name: str | None) -> str:
    """Classify a PDF font name into 'times', 'computer_modern', 'math', or 'other'.

    Returns 'unknown' when font_name is None or empty.
    Accepted (no warning): 'times', 'math', 'unknown'.
    """
    if not font_name:
        return "unknown"
    norm = _normalize_font(font_name)
    if any(p in norm for p in _MATH_FONT_PATTERNS):
        return "math"
    if any(p in norm for p in _TIMES_ACCEPTS):
        return "times"
    if any(norm.startswith(p) for p in _CM_PREFIXES):
        return "computer_modern"
    return "other"


def _page_has_named_heading(page: PdfPage, headings: frozenset[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            if normalize_heading_text(line.text).upper() in headings:
                return True
    return False


def _collect_body_spans(page: PdfPage) -> list[PdfTextSpan]:
    """Extract candidate body-text spans from a page.

    Excludes margin zones, named headings, page-number lines, captions,
    bullets, very short lines, and low-alpha-density lines.
    """
    top_limit = page.height * _TOP_ZONE_RATIO
    bottom_limit = page.height * (1.0 - _TOP_ZONE_RATIO)
    result: list[PdfTextSpan] = []

    for block in page.text_blocks:
        if block.bbox.y1 <= top_limit or block.bbox.y0 >= bottom_limit:
            continue
        for line in block.lines:
            if line.bbox.y0 < top_limit or line.bbox.y0 > bottom_limit:
                continue
            if normalize_heading_text(line.text).upper() in _NAMED_HEADINGS:
                continue
            clean = " ".join(line.text.strip().split())
            if not clean:
                continue
            if PAGE_NUM_RE.match(clean):
                continue
            if _CAPTION_PREFIX_RE.match(clean):
                continue
            if _BULLET_PREFIX_RE.match(clean):
                continue
            if len(clean) < _MIN_LINE_LEN:
                continue
            alpha_count = sum(ch.isalpha() for ch in clean)
            if alpha_count < _MIN_ALPHA_COUNT:
                continue
            for span in line.spans:
                if span.size is None or span.size <= 0:
                    continue
                if span.size < _SPAN_MIN_SIZE or span.size > _SPAN_MAX_SIZE:
                    continue
                result.append(span)

    return result


def check_pdf_font_compliance(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P026 warnings for body-text pages with repeated font-size or font-family issues.

    One finding per (page, issue_type). Requires both ≥5 violating spans AND ≥50%
    of body-candidate spans on the page to show the same issue.
    """
    findings: list[AuditFinding] = []

    for page in pdf_doc.pages:
        if _page_has_named_heading(page, _NAMED_HEADINGS):
            continue

        body_spans = _collect_body_spans(page)
        if len(body_spans) < _MIN_CANDIDATE_SPANS:
            continue

        # ---- A. Font-size check ----
        size_violations = [
            s for s in body_spans
            if s.size is not None and abs(s.size - EXPECTED_BODY_SIZE_PT) > BODY_SIZE_TOLERANCE_PT
        ]
        if (
            len(size_violations) >= _MIN_VIOLATION_COUNT
            and len(size_violations) / len(body_spans) >= _MIN_VIOLATION_FRACTION
        ):
            observed_sizes = sorted(
                {round(s.size, 1) for s in size_violations if s.size is not None}
            )
            findings.append(
                AuditFinding(
                    rule_id="P026",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        f"Body text on page {page.page_number} may not use 12pt font size "
                        f"(NJIT guidelines require Times New Roman 12pt)."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "possible_body_font_size_issue",
                        "expected": "12pt (±1pt tolerance: 11.0–13.0pt)",
                        "observed_summary": ", ".join(f"{sz}pt" for sz in observed_sizes[:5]),
                        "affected_span_count": str(len(size_violations)),
                        "candidate_count": str(len(body_spans)),
                        "confidence": "medium",
                        "triage_tier": "informational",
                        "bbox": format_bbox_detail(size_violations[0].bbox),
                        "suggested_fix": (
                            "Set body text font size to 12pt throughout the document "
                            "(LaTeX: \\normalsize in a 12pt document class; "
                            "Word: select body text and set font size to 12)."
                        ),
                    },
                )
            )

        # ---- B. Font-family check ----
        named_spans = [s for s in body_spans if s.font]
        if len(named_spans) < _MIN_CANDIDATE_SPANS:
            continue

        family_violations = [
            s for s in named_spans
            if classify_font(s.font) not in ("times", "unknown", "math")
        ]
        if (
            len(family_violations) >= _MIN_VIOLATION_COUNT
            and len(family_violations) / len(named_spans) >= _MIN_VIOLATION_FRACTION
        ):
            observed_fonts = sorted({s.font for s in family_violations if s.font})
            findings.append(
                AuditFinding(
                    rule_id="P026",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        f"Body text on page {page.page_number} may not use Times New Roman "
                        f"(NJIT guidelines require Times New Roman 12pt)."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "possible_body_font_family_issue",
                        "expected": "Times New Roman or accepted equivalent",
                        "observed_summary": ", ".join(observed_fonts[:4]),
                        "affected_span_count": str(len(family_violations)),
                        "candidate_count": str(len(named_spans)),
                        "confidence": "medium",
                        "triage_tier": "informational",
                        "bbox": format_bbox_detail(family_violations[0].bbox),
                        "suggested_fix": (
                            "Set body text font to Times New Roman 12pt throughout the document "
                            "(LaTeX: use \\usepackage{mathptmx} or \\usepackage{times}; "
                            "Word: set paragraph font to Times New Roman)."
                        ),
                    },
                )
            )

    return findings
