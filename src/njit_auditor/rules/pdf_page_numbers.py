"""Heuristic page-number candidate detection for layout-model pages."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail

PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)
ROMAN_CHARS_RE = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)
DECIMAL_SECTION_NUMBER_RE = re.compile(r"\d+\.\d+")
LONG_NUMERIC_ID_RE = re.compile(r"^\d{5,}$")
TOP_BOTTOM_ZONE_RATIO = 0.15
POSITION_CENTER_TOLERANCE_PT = 24.0
POSITION_RIGHT_TOLERANCE_PT = 72.0
POSITION_DOMINANT_MISMATCH_THRESHOLD = 2
MAX_PLAUSIBLE_ARABIC_PAGE_NUMBER = 9999
MAX_ARABIC_PAGE_NUMBER_DIGITS = 4
_POSITION_SCORE = {
    "bottom_center": 4,
    "bottom_right": 3,
    "top_center": 2,
    "top_right": 2,
    "other": 0,
}
_STYLE_SCORE = {"arabic": 2, "roman_lower": 2, "roman_upper": 2, "other": 0}

# (triage_tier, p019_triage_category, triage_reason)
_P019_TRIAGE_MAP: dict[str, tuple[str, str, str]] = {
    "sequence_gap": (
        "high",
        "high_signal_sequence_gap",
        "numeric page sequence gap; manual review recommended",
    ),
    "missing_page_number": (
        "high",
        "high_signal_missing_page_number",
        "expected page number missing; manual review recommended",
    ),
    "mixed_numbering_style": (
        "medium",
        "mixed_numbering_manual_review",
        "mixed Roman/Arabic style; boundary detection not available; manual review recommended",
    ),
    "multiple_page_numbers": (
        "medium",
        "multiple_page_numbers_manual_review",
        "multiple page-number candidates detected; may be real or artifact-driven",
    ),
    "inconsistent_position": (
        "low",
        "position_inconsistency_artifact_suspected",
        "page-number position inconsistency is often artifact-driven; "
        "manual spot check recommended",
    ),
}


@dataclass(frozen=True)
class PageNumberCandidate:
    page_number: int
    text: str
    location: str
    line_number_like: str
    number_style: str
    position_type: str
    value: int | None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class _SequenceCandidate:
    page_number: int
    value: int
    text: str
    number_style: str
    bbox: tuple[float, float, float, float] | None = None


def _is_top_or_bottom_zone(
    y0: float, y1: float, page_height: float, zone_ratio: float = TOP_BOTTOM_ZONE_RATIO
) -> bool:
    top_limit = page_height * zone_ratio
    bottom_limit = page_height * (1.0 - zone_ratio)
    return y1 <= top_limit or y0 >= bottom_limit


def _normalize_candidate_text(text: str) -> str:
    clean = text.strip()
    clean = clean.strip("[]()")
    clean = clean.rstrip(".")
    return clean


def _roman_to_int(text: str) -> int | None:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    s = text.upper()
    if not s or not ROMAN_CHARS_RE.match(s):
        return None
    total = 0
    prev = 0
    for ch in reversed(s):
        current = values.get(ch)
        if current is None:
            return None
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    return total if total > 0 else None


def _classify_style_and_value(text: str) -> tuple[str, int | None]:
    normalized = _normalize_candidate_text(text)
    if normalized.isdigit():
        return "arabic", int(normalized)
    if ROMAN_CHARS_RE.match(normalized):
        value = _roman_to_int(normalized)
        if value is None:
            return "other", None
        if normalized.islower():
            return "roman_lower", value
        if normalized.isupper():
            return "roman_upper", value
    return "other", None


def _classify_position_type(
    x0: float, x1: float, y1: float, page_width: float, page_height: float
) -> str:
    top = y1 <= page_height * TOP_BOTTOM_ZONE_RATIO
    line_center = (x0 + x1) / 2.0
    page_center = page_width / 2.0
    near_center = abs(line_center - page_center) <= POSITION_CENTER_TOLERANCE_PT
    near_right = abs(x1 - page_width) <= POSITION_RIGHT_TOLERANCE_PT

    if top and near_center:
        return "top_center"
    if top and near_right:
        return "top_right"
    if (not top) and near_center:
        return "bottom_center"
    if (not top) and near_right:
        return "bottom_right"
    return "other"


def detect_page_number_candidates(pdf_doc: PdfDocument) -> list[PageNumberCandidate]:
    """Return page-number candidate objects with style/position metadata."""

    candidates: list[PageNumberCandidate] = []
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            if not _is_top_or_bottom_zone(block.bbox.y0, block.bbox.y1, page.height):
                continue
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if not clean or not PAGE_NUM_RE.match(clean):
                    continue
                location = "top" if line.bbox.y1 <= page.height * 0.15 else "bottom"
                number_style, value = _classify_style_and_value(clean)
                position_type = _classify_position_type(
                    line.bbox.x0, line.bbox.x1, line.bbox.y1, page.width, page.height
                )
                candidates.append(
                    PageNumberCandidate(
                        page_number=page.page_number,
                        text=clean,
                        location=location,
                        line_number_like=str(page.page_number),
                        number_style=number_style,
                        position_type=position_type,
                        value=value,
                        bbox=(line.bbox.x0, line.bbox.y0, line.bbox.x1, line.bbox.y1),
                    )
                )
    return candidates


def _candidate_rank(candidate: PageNumberCandidate) -> tuple[int, int, int]:
    return (
        _POSITION_SCORE.get(candidate.position_type, 0),
        _STYLE_SCORE.get(candidate.number_style, 0),
        len(candidate.text.strip()),
    )


def _looks_like_decimal_section_number(text: str) -> bool:
    normalized = _normalize_candidate_text(text)
    return bool(DECIMAL_SECTION_NUMBER_RE.search(normalized))


def is_plausible_page_number_candidate(candidate: PageNumberCandidate) -> bool:
    """Return True when a margin-zone token looks like a printed page number."""
    normalized = _normalize_candidate_text(candidate.text)
    if _looks_like_decimal_section_number(candidate.text):
        return False
    if candidate.number_style == "other":
        return False
    if candidate.position_type == "other":
        return False
    if candidate.number_style == "arabic" and candidate.value is not None:
        if candidate.value > MAX_PLAUSIBLE_ARABIC_PAGE_NUMBER:
            return False
        if len(normalized) > MAX_ARABIC_PAGE_NUMBER_DIGITS:
            return False
        if LONG_NUMERIC_ID_RE.match(normalized):
            return False
    return candidate.number_style in {"arabic", "roman_lower", "roman_upper"}


def _plausible_candidates(candidates: list[PageNumberCandidate]) -> list[PageNumberCandidate]:
    return [candidate for candidate in candidates if is_plausible_page_number_candidate(candidate)]


def _filter_toc_column_candidates(
    plausible: list[PageNumberCandidate],
    *,
    page_is_front_matter: bool,
) -> list[PageNumberCandidate]:
    """Remove arabic bottom-right candidates on front-matter pages that already have
    a roman bottom-center candidate.

    On front-matter pages, the correct printed page number is a roman numeral at
    bottom-center. Arabic numbers at bottom-right on those pages are almost always
    TOC/list destination page references (the right-aligned page-number column of
    the TOC), not a second printed page number. This guard is conservative: it only
    fires when a roman bottom-center IS present, so it cannot suppress a real arabic
    front-matter page number that appears without a competing roman candidate.
    """
    if not page_is_front_matter:
        return plausible
    has_roman_bottom_center = any(
        c.number_style in ("roman_lower", "roman_upper") and c.position_type == "bottom_center"
        for c in plausible
    )
    if not has_roman_bottom_center:
        return plausible
    return [
        c for c in plausible
        if not (c.number_style == "arabic" and c.position_type == "bottom_right")
    ]


def _front_matter_pages_for_toc_filter(pdf_doc: PdfDocument) -> set[int]:
    # Imported lazily to avoid a circular import:
    # pdf_page_numbers → pdf_headings → pdf_margins → pdf_page_numbers.
    from njit_auditor.rules.pdf_headings import find_body_start_page  # noqa: PLC0415

    body_start = find_body_start_page(pdf_doc)
    if body_start is None:
        return set()
    return {page.page_number for page in pdf_doc.pages if page.page_number < body_start}


def _primary_plausible_candidate(
    candidates: list[PageNumberCandidate],
) -> PageNumberCandidate | None:
    plausible = _plausible_candidates(candidates)
    if not plausible:
        return None
    return max(plausible, key=_candidate_rank)


_MIN_DOMINANT_LOCATION_SAMPLE = 10
_MIN_DOMINANT_LOCATION_RATIO = 0.9


def _dominant_location(
    filtered_by_page: dict[int, list[PageNumberCandidate]],
) -> str | None:
    """Return "top" or "bottom" when one location overwhelmingly dominates the
    document's plausible page-number candidates, else None.

    Requires both a minimum sample size and a strong majority so this never fires
    on small or ambiguous documents (short PDFs, synthetic tests) — only on
    documents with an unmistakable, page-numbering-wide pattern.
    """
    all_plausible = [c for candidates in filtered_by_page.values() for c in candidates]
    if len(all_plausible) < _MIN_DOMINANT_LOCATION_SAMPLE:
        return None
    location, count = Counter(c.location for c in all_plausible).most_common(1)[0]
    if count / len(all_plausible) < _MIN_DOMINANT_LOCATION_RATIO:
        return None
    return location


def _filter_secondary_location_noise(
    plausible: list[PageNumberCandidate],
    dominant_location: str | None,
) -> list[PageNumberCandidate]:
    """Drop candidates outside the document's dominant page-number location when a
    dominant-location candidate is already present on the same page.

    Handles reprinted/embedded material (e.g. a published paper reproduced as a
    dissertation chapter) that carries its own original page numbering at the
    opposite edge of the page from where the manuscript's real page numbers are
    printed. That secondary token is not a second real page number, so it should
    not force a "multiple_page_numbers" review — the manuscript's own printed
    page number (at the document's dominant location) is unambiguous.

    Never fires when both candidates share the same location (e.g. bottom-center
    + bottom-right on one page), which remains a genuine multiple-candidate case,
    and never fires when *every* candidate on the page is already non-dominant
    (nothing to prefer over anything else).
    """
    if dominant_location is None:
        return plausible
    dominant_here = [c for c in plausible if c.location == dominant_location]
    if not dominant_here or len(dominant_here) == len(plausible):
        return plausible
    return dominant_here


def _format_candidate_tokens(candidates: list[PageNumberCandidate]) -> str:
    return "; ".join(f"{_position_label(c.position_type)}: {c.text}" for c in candidates)


def _style_transition_pages(
    filtered_by_page: dict[int, list[PageNumberCandidate]],
) -> list[tuple[int, str, int, str]]:
    """Return every (previous_page, previous_style, page, new_style) point where
    the document's primary page-number style changes from one page with a
    plausible candidate to the next. This turns a generic "mixed styles
    detected across the document" claim into the exact pages responsible,
    when the underlying per-page style data already makes that identifiable.
    """
    per_page_style: list[tuple[int, str]] = []
    for page in sorted(filtered_by_page):
        primary = _primary_plausible_candidate(filtered_by_page[page])
        if primary is None or primary.number_style == "other":
            continue
        per_page_style.append((page, primary.number_style))

    transitions: list[tuple[int, str, int, str]] = []
    for (prev_page, prev_style), (page, style) in zip(per_page_style, per_page_style[1:]):
        if style != prev_style:
            transitions.append((prev_page, prev_style, page, style))
    return transitions


def _primary_sequence_values(
    by_page: dict[int, list[PageNumberCandidate]],
    *,
    number_style: str,
) -> list[_SequenceCandidate]:
    values: list[_SequenceCandidate] = []
    for page in sorted(by_page):
        primary = _primary_plausible_candidate(by_page[page])
        if primary is None or primary.number_style != number_style or primary.value is None:
            continue
        values.append(
            _SequenceCandidate(
                page_number=page,
                value=primary.value,
                text=primary.text,
                number_style=primary.number_style,
                bbox=primary.bbox,
            )
        )
    return values


def _sequence_neighbors(
    values_by_page: list[_SequenceCandidate], page: int
) -> tuple[str, str, str, str]:
    """Return (previous_page, previous_value, next_page, next_value) as strings,
    so wording can name the exact neighboring pages, not just their values --
    e.g. "changed from 'viii' on page 8 to '10' on page 9" instead of only
    naming the values with no page attached.
    """
    sorted_items = sorted(values_by_page, key=lambda item: item.page_number)
    previous_page = ""
    previous_value = ""
    next_page = ""
    next_value = ""
    for index, current in enumerate(sorted_items):
        if current.page_number != page:
            continue
        if index > 0:
            prev = sorted_items[index - 1]
            previous_page = str(prev.page_number)
            previous_value = prev.text
        if index + 1 < len(sorted_items):
            next_item = sorted_items[index + 1]
            next_page = str(next_item.page_number)
            next_value = next_item.text
        break
    return previous_page, previous_value, next_page, next_value


def _int_to_roman_lower(value: int) -> str:
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["m", "cm", "d", "cd", "c", "xc", "l", "xl", "x", "ix", "v", "iv", "i"]
    result: list[str] = []
    for amount, symbol in zip(vals, syms):
        while value >= amount:
            result.append(symbol)
            value -= amount
    return "".join(result)


def _format_expected_sequence_value(number_style: str, value: int) -> str:
    if number_style == "roman_lower":
        return _int_to_roman_lower(value)
    if number_style == "roman_upper":
        return _int_to_roman_lower(value).upper()
    return str(value)


def _document_label_details(candidate: PageNumberCandidate | _SequenceCandidate) -> dict[str, str]:
    details = {
        "pdf_page": str(candidate.page_number),
        "document_page_label": candidate.text,
        "document_page_label_style": candidate.number_style,
        "document_page_label_confidence": "medium",
    }
    if candidate.bbox is not None:
        details["document_page_label_bbox"] = format_bbox_detail(candidate.bbox)
    return details


def _candidate_confidence(candidate: PageNumberCandidate) -> str:
    if candidate.position_type in {"bottom_center", "bottom_right"} and candidate.number_style in {
        "arabic",
        "roman_lower",
        "roman_upper",
    }:
        return "medium"
    if candidate.position_type in {"top_center", "top_right"} and candidate.number_style in {
        "arabic",
        "roman_lower",
        "roman_upper",
    }:
        return "medium"
    return "low"


def _position_label(position_type: str) -> str:
    labels = {
        "bottom_center": "bottom center",
        "bottom_right": "bottom right",
        "top_center": "top center",
        "top_right": "top right",
        "other": "an unexpected location",
    }
    return labels.get(position_type, "an unexpected location")


def _style_label(number_style: str) -> str:
    labels = {
        "arabic": "Arabic numerals",
        "roman_lower": "lowercase Roman numerals",
        "roman_upper": "uppercase Roman numerals",
        "other": "an unexpected style",
    }
    return labels.get(number_style, "an unexpected style")


def run_pdf_page_number_candidates_rule(
    pdf_doc: PdfDocument,
    *,
    skip_pages: set[int] | None = None,
) -> list[AuditFinding]:
    """Emit P013 findings for candidate page numbers."""

    skipped = skip_pages or set()
    candidates = [
        candidate
        for candidate in detect_page_number_candidates(pdf_doc)
        if candidate.page_number not in skipped
    ]
    if not candidates:
        return [
            AuditFinding(
                rule_id="P013",
                severity=Severity.PASS,
                message="No page-number candidates detected in top/bottom margin zones.",
            )
        ]

    findings: list[AuditFinding] = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            message="Detected possible page-number candidates for manual NJIT rule verification.",
            details={
                "issue_type": "p013_document_overview",
                "candidate_count": str(len(candidates)),
                "triage_tier": "informational",
            },
        )
    ]
    candidates_by_page: dict[int, list[PageNumberCandidate]] = {}
    for candidate in candidates:
        candidates_by_page.setdefault(candidate.page_number, []).append(candidate)
    front_matter_pages = _front_matter_pages_for_toc_filter(pdf_doc)

    # Per-page filtered plausible candidates (TOC column noise suppressed in front
    # matter). Computed for every page up front so the document-wide dominant
    # page-number location can be established before filtering any single page —
    # see _filter_secondary_location_noise for why this must match P019's logic.
    filtered_by_page: dict[int, list[PageNumberCandidate]] = {
        pg: _filter_toc_column_candidates(
            _plausible_candidates(pc),
            page_is_front_matter=(pg in front_matter_pages),
        )
        for pg, pc in candidates_by_page.items()
    }
    dominant_location = _dominant_location(filtered_by_page)

    for page in sorted(candidates_by_page):
        plausible = _filter_secondary_location_noise(
            filtered_by_page[page], dominant_location
        )
        if not plausible:
            # Every token in the margin zone on this page is implausible (e.g. a
            # long numeric ID, protocol number, or decimal section number) --
            # nothing here actually looks like a printed page number, so this
            # page has no P013 candidate to report.
            continue
        primary = max(plausible, key=_candidate_rank)
        distinct_texts = sorted({c.text for c in plausible})
        sample_text = ", ".join(distinct_texts[:3])
        if len(distinct_texts) > 3:
            sample_text += ", ..."
        details: dict[str, str] = {
            "issue_type": "page_number_candidate",
            "location": primary.location,
            "position_type": primary.position_type,
            "candidate_position_label": _position_label(primary.position_type),
            "number_style": primary.number_style,
            "candidate_style_label": _style_label(primary.number_style),
            "candidate_count_on_page": str(len(plausible)),
            "candidate_sample": sample_text,
            "observed_summary": f"{primary.position_type}/{primary.number_style}",
            "confidence": _candidate_confidence(primary),
            "triage_tier": "informational",
            "suggested_fix": (
                "Verify placement/format against NJIT page-number requirements."
            ),
        }
        details.update(_document_label_details(primary))
        if primary.bbox is not None:
            details["bbox"] = format_bbox_detail(primary.bbox)
        findings.append(
            AuditFinding(
                rule_id="P013",
                severity=Severity.WARNING,
                page=page,
                message=f"Page has {len(plausible)} page-number-like candidate(s).",
                details=details,
            )
        )
    return findings


def _find_sequence_gap(
    values_by_page: list[_SequenceCandidate],
) -> tuple[_SequenceCandidate, int, int] | None:
    if len(values_by_page) < 3:
        return None
    sorted_items = sorted(values_by_page, key=lambda item: item.page_number)
    for prev, current in zip(sorted_items, sorted_items[1:]):
        page_step = current.page_number - prev.page_number
        value_step = current.value - prev.value
        if page_step <= 0:
            continue
        if value_step != page_step:
            return (current, prev.value + page_step, current.value)
    return None


def check_pdf_page_number_sequence(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit conservative P019 warnings for page-number sequence/style issues."""

    candidates = detect_page_number_candidates(pdf_doc)
    if not candidates:
        return []

    findings: list[AuditFinding] = []
    by_page: dict[int, list[PageNumberCandidate]] = {}
    for candidate in candidates:
        by_page.setdefault(candidate.page_number, []).append(candidate)

    # Determine front-matter pages so that TOC/list destination numbers at bottom-right
    # are not confused with the real printed page number (roman, bottom-center).
    # Imported here to avoid a circular import:
    # pdf_page_numbers → pdf_headings → pdf_margins → pdf_page_numbers.
    front_matter_pages = _front_matter_pages_for_toc_filter(pdf_doc)

    # Per-page filtered plausible candidates (TOC column noise suppressed in front matter).
    filtered_by_page: dict[int, list[PageNumberCandidate]] = {
        pg: _filter_toc_column_candidates(
            _plausible_candidates(pc),
            page_is_front_matter=(pg in front_matter_pages),
        )
        for pg, pc in by_page.items()
    }

    pages_with_plausible_primary: set[int] = set()
    for page, page_candidates in by_page.items():
        if _primary_plausible_candidate(page_candidates) is not None:
            pages_with_plausible_primary.add(page)

    # Missing page number where neighboring pages both have plausible candidates.
    for page in range(2, len(pdf_doc.pages)):
        if page in pages_with_plausible_primary:
            continue
        if (page - 1) in pages_with_plausible_primary and (
            page + 1
        ) in pages_with_plausible_primary:
            findings.append(
                AuditFinding(
                    rule_id="P019",
                    severity=Severity.WARNING,
                    page=page,
                    message="Likely missing visible page number on a sequence page.",
                    details={
                        "page_number": str(page),
                        "issue_type": "missing_page_number",
                        "expected_or_context": "neighbors_have_plausible_candidates",
                        "confidence": "medium",
                    },
                )
            )

    # Multiple plausible page-number candidates on a single page (TOC noise filtered,
    # and secondary-location noise like an embedded reprint's own page numbers filtered).
    dominant_location = _dominant_location(filtered_by_page)
    for page, raw_plausible in filtered_by_page.items():
        plausible = _filter_secondary_location_noise(raw_plausible, dominant_location)
        if len(plausible) <= 1:
            continue
        candidate_tokens = _format_candidate_tokens(plausible)
        multiple_details: dict[str, str] = {
            "page_number": str(page),
            "issue_type": "multiple_page_numbers",
            "candidate_text": ", ".join(c.text for c in plausible[:3]),
            "candidate_tokens": candidate_tokens,
            "candidate_sample": ", ".join(c.text for c in plausible[:3]),
            "plausible_candidate_count": str(len(plausible)),
            "confidence": "medium",
        }
        primary = _primary_plausible_candidate(plausible)
        if primary is not None:
            multiple_details.update(_document_label_details(primary))
        if primary is not None and primary.bbox is not None:
            multiple_details["bbox"] = format_bbox_detail(primary.bbox)
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                page=page,
                message="Multiple plausible page-number candidates detected on one page.",
                details=multiple_details,
            )
        )

    # Compute dominant position and per-page inconsistency using filtered candidates.
    all_filtered_plausible = [c for cs in filtered_by_page.values() for c in cs]
    dominant_position = Counter(
        c.position_type for c in all_filtered_plausible if c.position_type != "other"
    ).most_common(1)
    if dominant_position:
        dominant_position_type = dominant_position[0][0]
        for page, plausible in filtered_by_page.items():
            mismatched_candidates = [
                c for c in plausible if c.position_type != dominant_position_type
            ]
            mismatch_count = len(mismatched_candidates)
            observed_positions = sorted(
                {_position_label(c.position_type) for c in mismatched_candidates}
            )
            if mismatch_count >= POSITION_DOMINANT_MISMATCH_THRESHOLD:
                inconsistent_details: dict[str, str] = {
                    "page_number": str(page),
                    "issue_type": "inconsistent_position",
                    "expected_or_context": f"dominant={dominant_position_type}",
                    "observed_location": (
                        ", ".join(observed_positions)
                        if observed_positions
                        else _position_label(dominant_position_type)
                    ),
                    "expected_position": _position_label(dominant_position_type),
                    "confidence": "medium",
                }
                mismatch_bbox = mismatched_candidates[0].bbox
                inconsistent_details.update(
                    _document_label_details(mismatched_candidates[0])
                )
                if mismatch_bbox is not None:
                    inconsistent_details["bbox"] = format_bbox_detail(mismatch_bbox)
                findings.append(
                    AuditFinding(
                        rule_id="P019",
                        severity=Severity.WARNING,
                        page=page,
                        message="Page-number position appears inconsistent with dominant pattern.",
                        details=inconsistent_details,
                    )
                )

    # Mixed style on same page (TOC noise filtered).
    for page, plausible in filtered_by_page.items():
        styles = {c.number_style for c in plausible if c.number_style != "other"}
        if len(styles) > 1:
            observed_style_labels = sorted(_style_label(style) for style in styles)
            mixed_style_details: dict[str, str] = {
                "page_number": str(page),
                "issue_type": "mixed_numbering_style",
                "expected_or_context": ",".join(sorted(styles)),
                "observed_style": ", ".join(observed_style_labels),
                "expected_style": "one consistent page-numbering style",
                "confidence": "medium",
            }
            # This page already has 2+ plausible candidates with different
            # styles in scope (that is what triggered this finding) -- the
            # highest-ranked one is the token most likely to be the actual
            # printed page number, so it is the right one to highlight
            # (mirrors the same precedent used for inconsistent_position and
            # multiple_page_numbers above).
            mixed_style_primary = max(plausible, key=_candidate_rank)
            mixed_style_details.update(_document_label_details(mixed_style_primary))
            if mixed_style_primary.bbox is not None:
                mixed_style_details["bbox"] = format_bbox_detail(mixed_style_primary.bbox)
            findings.append(
                AuditFinding(
                    rule_id="P019",
                    severity=Severity.WARNING,
                    page=page,
                    message="Mixed page-numbering styles detected on one page.",
                    details=mixed_style_details,
                )
            )

    # Mixed dominant style across document (TOC noise filtered).
    style_counts = Counter(
        c.number_style for c in all_filtered_plausible if c.number_style != "other"
    )
    if len([s for s in style_counts if style_counts[s] > 0]) > 1:
        observed_style_labels = sorted(_style_label(style) for style in style_counts)
        document_mixed_details: dict[str, str] = {
            "page_number": "-",
            "issue_type": "mixed_numbering_style",
            "expected_or_context": ",".join(
                f"{style}:{count}" for style, count in sorted(style_counts.items())
            ),
            "observed_style": ", ".join(observed_style_labels),
            "expected_style": "one consistent page-numbering style per numbering section",
            "confidence": "low",
        }
        transitions = _style_transition_pages(filtered_by_page)
        if transitions:
            document_mixed_details["transition_pages"] = ";".join(
                f"{prev_page}:{prev_style}->{page:d}:{new_style}"
                for prev_page, prev_style, page, new_style in transitions
            )
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                message="Mixed numbering styles detected across candidate page-number regions.",
                details=document_mixed_details,
            )
        )

    arabic_values = _primary_sequence_values(by_page, number_style="arabic")
    arabic_gap = _find_sequence_gap(arabic_values)
    if arabic_gap:
        current, expected, actual = arabic_gap
        page = current.page_number
        if (
            expected <= MAX_PLAUSIBLE_ARABIC_PAGE_NUMBER
            and actual <= MAX_PLAUSIBLE_ARABIC_PAGE_NUMBER
        ):
            previous_page, previous_value, next_page, next_value = _sequence_neighbors(
                arabic_values, page
            )
            sequence_details: dict[str, str] = {
                "page_number": str(page),
                "issue_type": "sequence_gap",
                "expected_or_context": f"expected={expected},actual={actual},style=arabic",
                "observed_sequence": str(actual),
                "expected_sequence": str(expected),
                "previous_sequence_value": previous_value,
                "next_sequence_value": next_value,
                "previous_sequence_page": previous_page,
                "next_sequence_page": next_page,
                "sequence_confidence": "medium",
                "confidence": "medium",
            }
            sequence_details.update(_document_label_details(current))
            if current.bbox is not None:
                sequence_details["bbox"] = format_bbox_detail(current.bbox)
            findings.append(
                AuditFinding(
                    rule_id="P019",
                    severity=Severity.WARNING,
                    page=page,
                    message="Arabic page-number candidate sequence shows an obvious gap/break.",
                    details=sequence_details,
                )
            )

    roman_values = _primary_sequence_values(by_page, number_style="roman_lower")
    roman_gap = _find_sequence_gap(roman_values)
    if roman_gap:
        current, expected, actual = roman_gap
        page = current.page_number
        # P029 owns front-matter lowercase-Roman sequence defects. Suppress the
        # generic P019 duplicate only when this physical page is confidently in
        # front matter; P019 still handles Roman sequence breaks outside that scope.
        if page in front_matter_pages:
            roman_gap = None
    if roman_gap:
        current, expected, actual = roman_gap
        page = current.page_number
        previous_page, previous_value, next_page, next_value = _sequence_neighbors(
            roman_values, page
        )
        expected_text = _format_expected_sequence_value(current.number_style, expected)
        roman_sequence_details: dict[str, str] = {
            "page_number": str(page),
            "issue_type": "sequence_gap",
            "expected_or_context": f"expected={expected},actual={actual},style=roman_lower",
            "observed_sequence": current.text,
            "expected_sequence": expected_text,
            "observed_value": str(actual),
            "expected_value": str(expected),
            "previous_sequence_value": previous_value,
            "next_sequence_value": next_value,
            "previous_sequence_page": previous_page,
            "next_sequence_page": next_page,
            "sequence_confidence": "medium",
            "confidence": "medium",
        }
        roman_sequence_details.update(_document_label_details(current))
        if current.bbox is not None:
            roman_sequence_details["bbox"] = format_bbox_detail(current.bbox)
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                page=page,
                message="Roman page-number candidate sequence shows an obvious gap/break.",
                details=roman_sequence_details,
            )
        )

    # Keep output conservative: dedupe by (page, issue_type).
    deduped: dict[tuple[int | None, str], AuditFinding] = {}
    for finding in findings:
        key = (finding.page, finding.details.get("issue_type", ""))
        deduped[key] = finding

    result: list[AuditFinding] = []
    for finding in deduped.values():
        issue_type = finding.details.get("issue_type", "")
        triage = _P019_TRIAGE_MAP.get(issue_type)
        if triage:
            tier, category, reason = triage
            new_details = dict(finding.details)
            new_details["triage_tier"] = tier
            new_details["p019_triage_category"] = category
            new_details["triage_reason"] = reason
            result.append(finding.model_copy(update={"details": new_details}))
        else:
            result.append(finding)
    return result
