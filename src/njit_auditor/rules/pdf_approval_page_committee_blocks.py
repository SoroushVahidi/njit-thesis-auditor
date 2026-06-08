"""Conservative Approval Page committee/signature-block structural check (P068).

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
from njit_auditor.rules.pdf_frontmatter_heading_gate import find_gate_matches_for_heading
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
        ),
    )


def check_pdf_approval_page_committee_blocks(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P068 warnings when approval-page committee blocks look structurally sparse."""
    approval_matches = find_gate_matches_for_heading(pdf_document, _APPROVAL_HEADING)
    if len(approval_matches) != 1:
        return []

    page_number = approval_matches[0].page_number
    page = next(
        (candidate for candidate in pdf_document.pages if candidate.page_number == page_number),
        None,
    )
    if page is None or not page.text_blocks:
        return []

    body_lines = _usable_body_lines(page)
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
            )
        )

    return findings
