"""Abstract page checks for MVP."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_loader import read_page_text
from njit_auditor.rules.page_numbers import detect_page_number_candidates

FORBIDDEN_WORD_RE = re.compile(r"\b(paper|papers|article|articles)\b", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"\b(i|me|my|mine|we|us|our|ours)\b", re.IGNORECASE)


def find_forbidden_abstract_words(text: str) -> list[str]:
    """Return forbidden standalone words found in abstract text."""
    return sorted({m.group(0).lower() for m in FORBIDDEN_WORD_RE.finditer(text)})


def find_first_person_pronouns(text: str) -> list[str]:
    """Return first-person pronouns found in abstract text."""
    return sorted({m.group(0).lower() for m in FIRST_PERSON_RE.finditer(text)})


def run_abstract_checks(pdf_path: str) -> list[AuditFinding]:
    """Treat page 1 as abstract for this MVP and run simple local checks."""
    findings: list[AuditFinding] = []
    abstract_page_index = 0

    text = read_page_text(pdf_path, abstract_page_index)
    if not text.strip():
        return [
            AuditFinding(
                rule_id="abstract",
                severity=Severity.WARNING,
                page=1,
                message="Page 1 is empty or unreadable; abstract checks were limited.",
            )
        ]

    abstract_page_candidates = [
        c for c in detect_page_number_candidates(pdf_path) if c.page_index == abstract_page_index
    ]
    if abstract_page_candidates:
        findings.append(
            AuditFinding(
                rule_id="abstract_page_number",
                severity=Severity.FAIL,
                page=1,
                message="Abstract page appears to contain a visible page number.",
            )
        )
    else:
        findings.append(
            AuditFinding(
                rule_id="abstract_page_number",
                severity=Severity.PASS,
                page=1,
                message="No visible abstract page number candidate detected.",
            )
        )

    forbidden = find_forbidden_abstract_words(text)
    if forbidden:
        findings.append(
            AuditFinding(
                rule_id="abstract_forbidden_terms",
                severity=Severity.FAIL,
                page=1,
                message="Abstract contains forbidden terms.",
                details={"terms": ", ".join(forbidden)},
            )
        )
    else:
        findings.append(
            AuditFinding(
                rule_id="abstract_forbidden_terms",
                severity=Severity.PASS,
                page=1,
                message="No forbidden abstract terms found.",
            )
        )

    pronouns = find_first_person_pronouns(text)
    if pronouns:
        findings.append(
            AuditFinding(
                rule_id="abstract_first_person",
                severity=Severity.FAIL,
                page=1,
                message="Abstract contains first-person pronouns.",
                details={"pronouns": ", ".join(pronouns)},
            )
        )
    else:
        findings.append(
            AuditFinding(
                rule_id="abstract_first_person",
                severity=Severity.PASS,
                page=1,
                message="No first-person pronouns found in abstract text.",
            )
        )

    # TODO: implement coordinate-based first paragraph indentation check using text block geometry.
    findings.append(
        AuditFinding(
            rule_id="abstract_indentation",
            severity=Severity.WARNING,
            page=1,
            message="First paragraph indentation check is a placeholder in this MVP.",
        )
    )

    return findings
