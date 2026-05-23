"""Heuristic page-number candidate detection for layout-model pages."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument

PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)
ROMAN_CHARS_RE = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)
TOP_BOTTOM_ZONE_RATIO = 0.15
POSITION_CENTER_TOLERANCE_PT = 24.0
POSITION_RIGHT_TOLERANCE_PT = 72.0
POSITION_DOMINANT_MISMATCH_THRESHOLD = 2


@dataclass(frozen=True)
class PageNumberCandidate:
    page_number: int
    text: str
    location: str
    line_number_like: str
    number_style: str
    position_type: str
    value: int | None


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
                    )
                )
    return candidates


def run_pdf_page_number_candidates_rule(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P013 findings for candidate page numbers."""

    candidates = detect_page_number_candidates(pdf_doc)
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
            details={"candidate_count": str(len(candidates))},
        )
    ]
    for candidate in candidates:
        findings.append(
            AuditFinding(
                rule_id="P013",
                severity=Severity.WARNING,
                page=candidate.page_number,
                message=(
                    f"Candidate page number '{candidate.text}' found near "
                    f"{candidate.location} margin."
                ),
                details={
                    "location": candidate.location,
                    "suggested_fix": (
                        "Verify placement/format against NJIT page-number requirements."
                    ),
                },
            )
        )
    return findings


def _find_sequence_gap(values_by_page: list[tuple[int, int]]) -> tuple[int, int, int] | None:
    if len(values_by_page) < 3:
        return None
    sorted_items = sorted(values_by_page, key=lambda item: item[0])
    for (prev_page, prev_value), (page, value) in zip(sorted_items, sorted_items[1:]):
        page_step = page - prev_page
        value_step = value - prev_value
        if page_step <= 0:
            continue
        if value_step != page_step:
            return (page, prev_value + page_step, value)
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

    # Missing page number where neighboring pages both have candidates.
    pages_with_candidates = set(by_page.keys())
    for page in range(2, len(pdf_doc.pages)):
        if page in pages_with_candidates:
            continue
        if (page - 1) in pages_with_candidates and (page + 1) in pages_with_candidates:
            findings.append(
                AuditFinding(
                    rule_id="P019",
                    severity=Severity.WARNING,
                    page=page,
                    message="Likely missing visible page number on a sequence page.",
                    details={
                        "page_number": str(page),
                        "issue_type": "missing_page_number",
                        "expected_or_context": "neighbors_have_candidates",
                        "confidence": "medium",
                    },
                )
            )

    # Multiple candidate numbers on a single page.
    for page, page_candidates in by_page.items():
        if len(page_candidates) <= 1:
            continue
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                page=page,
                message="Multiple page-number candidates detected on one page.",
                details={
                    "page_number": str(page),
                    "issue_type": "multiple_page_numbers",
                    "candidate_text": ", ".join(c.text for c in page_candidates[:3]),
                    "confidence": "medium",
                },
            )
        )

    dominant_position = Counter(
        c.position_type for c in candidates if c.position_type != "other"
    ).most_common(1)
    if dominant_position:
        dominant_position_type = dominant_position[0][0]
        for page, page_candidates in by_page.items():
            mismatch_count = sum(
                1 for c in page_candidates if c.position_type != dominant_position_type
            )
            if mismatch_count >= POSITION_DOMINANT_MISMATCH_THRESHOLD:
                findings.append(
                    AuditFinding(
                        rule_id="P019",
                        severity=Severity.WARNING,
                        page=page,
                        message="Page-number position appears inconsistent with dominant pattern.",
                        details={
                            "page_number": str(page),
                            "issue_type": "inconsistent_position",
                            "expected_or_context": f"dominant={dominant_position_type}",
                            "confidence": "medium",
                        },
                    )
                )

    # Mixed style on same page.
    for page, page_candidates in by_page.items():
        styles = {c.number_style for c in page_candidates if c.number_style != "other"}
        if len(styles) > 1:
            findings.append(
                AuditFinding(
                    rule_id="P019",
                    severity=Severity.WARNING,
                    page=page,
                    message="Mixed page-numbering styles detected on one page.",
                    details={
                        "page_number": str(page),
                        "issue_type": "mixed_numbering_style",
                        "expected_or_context": ",".join(sorted(styles)),
                        "confidence": "medium",
                    },
                )
            )

    # Mixed dominant style across document.
    style_counts = Counter(c.number_style for c in candidates if c.number_style != "other")
    if len([s for s in style_counts if style_counts[s] > 0]) > 1:
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                message="Mixed numbering styles detected across candidate page-number regions.",
                details={
                    "page_number": "-",
                    "issue_type": "mixed_numbering_style",
                    "expected_or_context": ",".join(
                        f"{style}:{count}" for style, count in sorted(style_counts.items())
                    ),
                    "confidence": "low",
                },
            )
        )

    arabic_values = [
        (c.page_number, c.value)
        for c in candidates
        if c.number_style == "arabic" and c.value is not None
    ]
    arabic_gap = _find_sequence_gap(
        [(page, value) for page, value in arabic_values if value is not None]
    )
    if arabic_gap:
        page, expected, actual = arabic_gap
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                page=page,
                message="Arabic page-number candidate sequence shows an obvious gap/break.",
                details={
                    "page_number": str(page),
                    "issue_type": "sequence_gap",
                    "expected_or_context": f"expected={expected},actual={actual},style=arabic",
                    "confidence": "medium",
                },
            )
        )

    roman_values = [
        (c.page_number, c.value)
        for c in candidates
        if c.number_style == "roman_lower" and c.value is not None
    ]
    roman_gap = _find_sequence_gap(
        [(page, value) for page, value in roman_values if value is not None]
    )
    if roman_gap:
        page, expected, actual = roman_gap
        findings.append(
            AuditFinding(
                rule_id="P019",
                severity=Severity.WARNING,
                page=page,
                message="Roman page-number candidate sequence shows an obvious gap/break.",
                details={
                    "page_number": str(page),
                    "issue_type": "sequence_gap",
                    "expected_or_context": f"expected={expected},actual={actual},style=roman_lower",
                    "confidence": "medium",
                },
            )
        )

    # Keep output conservative: dedupe by (page, issue_type).
    deduped: dict[tuple[int | None, str], AuditFinding] = {}
    for finding in findings:
        key = (finding.page, finding.details.get("issue_type", ""))
        deduped[key] = finding
    return list(deduped.values())
