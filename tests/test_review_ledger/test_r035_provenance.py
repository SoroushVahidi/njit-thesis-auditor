"""R035 known cases carry only direct Ester adjudications (live R035 sheet)."""

from __future__ import annotations

from njit_auditor.review_ledger.importers.known_cases import (
    KNOWN_ADJUDICATION_SUPERSESSIONS,
    KNOWN_HISTORICAL_CASES,
)
from njit_auditor.review_ledger.models import AdjudicationVerdict


def _p035_cases():
    return [c for c in KNOWN_HISTORICAL_CASES if c.internal_rule_id == "P035"]


def test_r035_direct_cases_are_exactly_anthony_p60_and_praneeth_p29() -> None:
    keys = sorted(
        (c.document_short_name, c.physical_page, c.issue_type, c.verdict)
        for c in _p035_cases()
    )
    assert keys == [
        ("Anthony", 60, "table_body_not_centered", AdjudicationVerdict.FALSE_POSITIVE),
        ("Praneeth", 29, "figure_body_not_centered", AdjudicationVerdict.FALSE_POSITIVE),
    ]


def test_engineering_only_praneeth_pages_are_not_ester_adjudications() -> None:
    # p72: engineering-found text-fallback bug, never sent to Ester.
    # p67: excluded by authority reuse (material equivalence to p29), not reviewed.
    pages = {c.physical_page for c in _p035_cases() if c.document_short_name == "Praneeth"}
    assert pages.isdisjoint({67, 69, 72, 100})
    assert not any(
        s.case.internal_rule_id == "P035" for s in KNOWN_ADJUDICATION_SUPERSESSIONS
    )


def test_known_case_identities_are_unique() -> None:
    keys = [
        (c.document_short_name, c.internal_rule_id, c.issue_type, c.physical_page,
         c.structural_location)
        for c in KNOWN_HISTORICAL_CASES
    ]
    assert len(keys) == len(set(keys))
