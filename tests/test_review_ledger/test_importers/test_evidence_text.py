"""Tests for the evidence-block text parser."""

from __future__ import annotations

from njit_auditor.review_ledger.importers.evidence_text import parse_evidence_block


def test_no_finding_sentinel() -> None:
    block = parse_evidence_block("No current auditor R018 finding.")
    assert block.no_finding is True
    assert block.physical_page is None


def test_parses_structured_block() -> None:
    text = (
        "Physical PDF page: 14\n"
        "Printed/document page: xii\n"
        "Location: body text\n"
        "Affected content:\n"
        '  1. "some excerpt"\n'
        "Possible violation: This entry's indent does not match peers.\n"
        "Measured amount: Not applicable for this rule\n"
        "Auditor confidence: MEDIUM"
    )
    block = parse_evidence_block(text)
    assert block.no_finding is False
    assert block.physical_page == 14
    assert block.printed_page == "xii"
    assert block.location == "body text"
    assert block.message == "This entry's indent does not match peers."
    assert block.measured_amount == "Not applicable for this rule"
    assert block.confidence == "MEDIUM"


def test_unparseable_text_returns_all_none() -> None:
    block = parse_evidence_block("some unrelated free text")
    assert block.no_finding is False
    assert block.physical_page is None
    assert block.message is None


def test_non_integer_physical_page_is_none_not_a_crash() -> None:
    text = "Physical PDF page: N/A\nPrinted/document page: --\nLocation: front matter\n"
    block = parse_evidence_block(text)
    assert block.physical_page is None
    assert block.location == "front matter"
