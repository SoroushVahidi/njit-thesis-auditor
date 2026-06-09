"""Conservative Approval Page committee/signature-block structural check (P068).

P072 (infrastructure companion): structural localization fallback when the APPROVAL PAGE
heading is absent from the text layer. Activates only when the heading gate returns 0
matches and exactly 1 front-matter/ambiguous page has sufficient role-label phrases.
No new issue types in v1 — existing P068 types fire when checks reach the page.

Partial heuristic PDF coverage for the Approval Page structural extension of Q013:
committee role labels and signature/date blocks should be present on a detected
APPROVAL PAGE. Q015–Q020 remain manual-only and are not checked.

Does not read or quote committee-member names, honorifics, affiliations,
signature images, or approval-page prose. Findings contain counts and booleans only.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage
from njit_auditor.rules.pdf_frontmatter_heading_gate import (
    _eligible_page_numbers,
    find_gate_matches_for_heading,
)
from njit_auditor.rules.pdf_frontmatter_structure import _lines_below_heading
from njit_auditor.rules.pdf_headings import normalize_heading_text

_APPROVAL_HEADING = "APPROVAL PAGE"
_RULE_ID = "P068"

_MIN_BODY_LINES = 4
_MIN_ROLE_LABELS = 2
_MIN_LINE_CHARS = 3
_ROLE_PREFIX_CHARS = 60

_ADVISOR_ROLE_PHRASES: tuple[str, ...] = (
    "dissertation advisor",
    "doctoral dissertation advisor",
    "major professor",
)

_ROLE_LABEL_PHRASES: tuple[str, ...] = (
    "dissertation advisor",
    "doctoral dissertation advisor",
    "committee member",
    "doctoral committee member",
    "major professor",
    "departmental graduate committee",
)

_DATE_LABEL_RE = re.compile(r"^\s*date\s*:", re.IGNORECASE)
_SIGNATURE_LABEL_RE = re.compile(r"^\s*signature\s*:?", re.IGNORECASE)


def _normalized_line(text: str) -> str:
    return normalize_heading_text(text).lower()


def _usable_body_lines(page: PdfPage) -> list[str]:
    raw_lines = _lines_below_heading(page, _APPROVAL_HEADING)
    return [
        line
        for line in raw_lines
        if len(_normalized_line(line)) >= _MIN_LINE_CHARS
    ]


def _all_usable_lines(page: PdfPage) -> list[str]:
    """Return all usable non-empty lines from a page (no heading boundary required)."""
    return [
        line.text.strip()
        for block in page.text_blocks
        for line in block.lines
        if len(_normalized_line(line.text)) >= _MIN_LINE_CHARS
    ]


def _mostly_single_token_noise(lines: list[str]) -> bool:
    if not lines:
        return True
    single_token = sum(1 for line in lines if len(line.split()) < 2)
    return single_token > len(lines) / 2


def _phrase_in_prefix(line: str, phrase: str) -> bool:
    prefix = _normalized_line(line)[:_ROLE_PREFIX_CHARS]
    return phrase in prefix


def _is_role_label_line(line: str) -> bool:
    return any(_phrase_in_prefix(line, phrase) for phrase in _ROLE_LABEL_PHRASES)


def _advisor_role_present(lines: list[str]) -> bool:
    return any(
        _phrase_in_prefix(line, phrase)
        for line in lines
        for phrase in _ADVISOR_ROLE_PHRASES
    )


def _is_date_label(line: str) -> bool:
    normalized = _normalized_line(line)
    if _DATE_LABEL_RE.match(normalized):
        return True
    return "date:" in normalized[:20]


def _is_signature_label(line: str) -> bool:
    return bool(_SIGNATURE_LABEL_RE.match(_normalized_line(line)))


def _is_signature_blank(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 8:
        return False
    non_space = [char for char in stripped if not char.isspace()]
    if not non_space:
        return False
    fill_chars = sum(1 for char in non_space if char in "_.-")
    return fill_chars / len(non_space) >= 0.7


def _confidence(role_label_count: int, indicator_count: int) -> str:
    if role_label_count >= 3 and indicator_count >= 3:
        return "high"
    if role_label_count >= 2 and indicator_count >= 2:
        return "medium"
    return "low"


def _find_structural_approval_page_candidate(
    pdf_document: PdfDocument,
) -> PdfPage | None:
    """Find an approval-page candidate via role-label pattern when heading is absent.

    Returns the single candidate page when exactly one front-matter/ambiguous page has
    sufficient role-label phrases and body lines. Returns None if 0 or >=2 candidates
    (ambiguous), or if no page passes the structural gate.
    """
    eligible = _eligible_page_numbers(pdf_document, max_scan_pages=None)
    candidates: list[PdfPage] = []
    for page in pdf_document.pages:
        if page.page_number not in eligible:
            continue
        if not page.text_blocks:
            continue
        lines = _all_usable_lines(page)
        if len(lines) < _MIN_BODY_LINES or _mostly_single_token_noise(lines):
            continue
        role_count = sum(1 for line in lines if _is_role_label_line(line))
        if role_count >= _MIN_ROLE_LABELS:
            candidates.append(page)
    return candidates[0] if len(candidates) == 1 else None


def _base_details(
    *,
    page_number: int,
    issue_type: str,
    role_label_count: int,
    advisor_label_present: bool,
    date_label_count: int,
    signature_label_count: int,
    signature_blank_count: int,
    signature_date_indicator_count: int,
    confidence: str,
    detected_via: str = "heading_gate",
) -> dict[str, str]:
    return {
        "page_number": str(page_number),
        "issue_type": issue_type,
        "role_label_count": str(role_label_count),
        "advisor_label_present": "true" if advisor_label_present else "false",
        "date_label_count": str(date_label_count),
        "signature_label_count": str(signature_label_count),
        "signature_blank_count": str(signature_blank_count),
        "signature_date_indicator_count": str(signature_date_indicator_count),
        "confidence": confidence,
        "triage_tier": "medium",
        "source_q_rule_ids": "Q013",
        "detected_via": detected_via,
    }


def _make_finding(
    *,
    page_number: int,
    issue_type: str,
    message: str,
    role_label_count: int,
    advisor_label_present: bool,
    date_label_count: int,
    signature_label_count: int,
    signature_blank_count: int,
    signature_date_indicator_count: int,
    confidence: str,
    detected_via: str = "heading_gate",
) -> AuditFinding:
    return AuditFinding(
        rule_id=_RULE_ID,
        severity=Severity.WARNING,
        page=page_number,
        message=message,
        details=_base_details(
            page_number=page_number,
            issue_type=issue_type,
            role_label_count=role_label_count,
            advisor_label_present=advisor_label_present,
            date_label_count=date_label_count,
            signature_label_count=signature_label_count,
            signature_blank_count=signature_blank_count,
            signature_date_indicator_count=signature_date_indicator_count,
            confidence=confidence,
            detected_via=detected_via,
        ),
    )


def check_pdf_approval_page_committee_blocks(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P068 warnings when approval-page committee blocks look structurally sparse.

    P072: when the heading gate finds 0 matches, tries a structural role-label fallback
    on front-matter/ambiguous pages before giving up. Skips if 0 or >=2 candidates.
    """
    approval_matches = find_gate_matches_for_heading(pdf_document, _APPROVAL_HEADING)

    if len(approval_matches) == 1:
        detected_via = "heading_gate"
        page_number = approval_matches[0].page_number
        page = next(
            (p for p in pdf_document.pages if p.page_number == page_number),
            None,
        )
        if page is None or not page.text_blocks:
            return []
        body_lines = _usable_body_lines(page)
    elif len(approval_matches) == 0:
        candidate = _find_structural_approval_page_candidate(pdf_document)
        if candidate is None:
            return []
        detected_via = "structural_fallback"
        page_number = candidate.page_number
        page = candidate
        body_lines = _all_usable_lines(page)
    else:
        return []

    if len(body_lines) < _MIN_BODY_LINES or _mostly_single_token_noise(body_lines):
        return []

    role_label_count = sum(1 for line in body_lines if _is_role_label_line(line))
    if role_label_count < _MIN_ROLE_LABELS:
        return []

    advisor_label_present = _advisor_role_present(body_lines)
    date_label_count = sum(1 for line in body_lines if _is_date_label(line))
    signature_label_count = sum(1 for line in body_lines if _is_signature_label(line))
    signature_blank_count = sum(1 for line in body_lines if _is_signature_blank(line))
    signature_date_indicator_count = (
        date_label_count + signature_label_count + signature_blank_count
    )
    confidence = _confidence(role_label_count, signature_date_indicator_count)

    findings: list[AuditFinding] = []
    required_indicators = max(2, role_label_count)

    if not advisor_label_present:
        findings.append(
            _make_finding(
                page_number=page_number,
                issue_type="approval_page_advisor_role_label_missing",
                message=(
                    "APPROVAL PAGE detected but no advisor-role template label was found "
                    "among committee block lines."
                ),
                role_label_count=role_label_count,
                advisor_label_present=advisor_label_present,
                date_label_count=date_label_count,
                signature_label_count=signature_label_count,
                signature_blank_count=signature_blank_count,
                signature_date_indicator_count=signature_date_indicator_count,
                confidence=confidence,
                detected_via=detected_via,
            )
        )

    if signature_date_indicator_count < required_indicators:
        findings.append(
            _make_finding(
                page_number=page_number,
                issue_type="approval_page_signature_blocks_sparse",
                message=(
                    "APPROVAL PAGE committee blocks appear sparse: insufficient date/signature "
                    "structural indicators relative to detected role-label count."
                ),
                role_label_count=role_label_count,
                advisor_label_present=advisor_label_present,
                date_label_count=date_label_count,
                signature_label_count=signature_label_count,
                signature_blank_count=signature_blank_count,
                signature_date_indicator_count=signature_date_indicator_count,
                confidence=confidence,
                detected_via=detected_via,
            )
        )

    return findings
