"""Parser for the auditor's own evidence-block text format.

``scripts/ester_batch/build_rule_package.py`` renders each candidate
finding for an Ester review package as a fixed-shape text block (see
``_structured_block`` there):

    Physical PDF page: 14
    Printed/document page: xii
    Location: body text
    Affected content:
      1. "..."
    Possible violation: <message>
    Measured amount: <value>
    Auditor confidence: MEDIUM

The same shape appears in both the ``.xlsx`` packages' second column and
``docs/evaluation/ester_feedback/live_sheet_pending_content.json``. This
module parses it back into structured fields so an importer can recover
page/confidence/message without re-deriving them, and without ever needing
the private "Affected content" excerpt itself for identity purposes.

A row reading exactly ``"No current auditor Rxxx finding."`` parses to
``EvidenceBlock(no_finding=True, ...)`` -- this is a statement about what
was sent for review, never a verdict; callers must not treat it as an
adjudication.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NO_FINDING_RE = re.compile(r"^No current auditor \S+ finding\.$")
_FIELD_RE = re.compile(
    r"Physical PDF page:\s*(?P<physical_page>[^\n]*)\n"
    r"Printed/document page:\s*(?P<printed_page>[^\n]*)\n"
    r"Location:\s*(?P<location>[^\n]*)\n",
)
_VIOLATION_RE = re.compile(r"Possible violation:\s*(?P<message>[^\n]*)")
_MEASURED_RE = re.compile(r"Measured amount:\s*(?P<measured>[^\n]*)")
_CONFIDENCE_RE = re.compile(r"Auditor confidence:\s*(?P<confidence>[^\n]*)")


@dataclass(frozen=True)
class EvidenceBlock:
    no_finding: bool
    physical_page: int | None
    printed_page: str | None
    location: str | None
    message: str | None
    measured_amount: str | None
    confidence: str | None


def parse_evidence_block(text: str) -> EvidenceBlock:
    """Parse one document's evidence-block text for one rule.

    Returns an ``EvidenceBlock`` with every field ``None`` (and
    ``no_finding=False``) if the text does not match either the
    "no finding" sentinel or the structured block shape -- callers should
    treat that as "unparseable", not as a finding or a non-finding.
    """
    stripped = text.strip()
    if _NO_FINDING_RE.match(stripped):
        return EvidenceBlock(
            no_finding=True,
            physical_page=None,
            printed_page=None,
            location=None,
            message=None,
            measured_amount=None,
            confidence=None,
        )

    field_match = _FIELD_RE.search(text)
    if field_match is None:
        return EvidenceBlock(
            no_finding=False,
            physical_page=None,
            printed_page=None,
            location=None,
            message=None,
            measured_amount=None,
            confidence=None,
        )

    physical_page_raw = field_match.group("physical_page").strip()
    physical_page: int | None
    try:
        physical_page = int(physical_page_raw)
    except ValueError:
        physical_page = None

    violation_match = _VIOLATION_RE.search(text)
    measured_match = _MEASURED_RE.search(text)
    confidence_match = _CONFIDENCE_RE.search(text)

    return EvidenceBlock(
        no_finding=False,
        physical_page=physical_page,
        printed_page=field_match.group("printed_page").strip() or None,
        location=field_match.group("location").strip() or None,
        message=violation_match.group("message").strip() if violation_match else None,
        measured_amount=measured_match.group("measured").strip() if measured_match else None,
        confidence=confidence_match.group("confidence").strip() if confidence_match else None,
    )
