"""Additive, privacy-safe locators for historical review cases.

These locators are derived from curated authority records and keyed by the
existing case ID. They do not participate in canonical fingerprints or alter
append-only ledger rows. Coordinates are PDF points on a fixed thesis version.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite

from njit_auditor.review_ledger.fingerprint import compute_case_fingerprint
from njit_auditor.review_ledger.identifiers import make_case_id, make_thesis_id
from njit_auditor.review_ledger.importers.known_cases import (
    KNOWN_HISTORICAL_CASES,
    KnownHistoricalCase,
)

LOCATOR_VERSION = 1


@dataclass(frozen=True)
class CaseLocator:
    case_id: str
    version: int
    source_reference: str
    anchor_x: float | None = None
    anchor_y: float | None = None
    structural_role: str | None = None

    def __post_init__(self) -> None:
        if not self.case_id or not self.source_reference:
            raise ValueError("case locator requires a case ID and source reference")
        if self.version != LOCATOR_VERSION:
            raise ValueError(f"unsupported case locator version: {self.version}")
        for coordinate in (self.anchor_x, self.anchor_y):
            if coordinate is not None and not isfinite(coordinate):
                raise ValueError("case locator coordinates must be finite")


def locators_for_review_cases(
    review_cases: Iterable[dict],
    thesis_id_by_version: Mapping[str, str],
    known_cases: Iterable[KnownHistoricalCase] = KNOWN_HISTORICAL_CASES,
) -> dict[str, CaseLocator]:
    """Resolve curated locators against stored IDs, without changing records.

    Recomputing the existing case ID prevents a similarly described case on
    another thesis version from borrowing this locator. Unlocated legacy cases
    remain readable and simply have no entry in the returned mapping.
    """
    result: dict[str, CaseLocator] = {}
    located = [case for case in known_cases if case.anchor_y is not None]
    for review_case in review_cases:
        version_id = str(review_case["thesis_version_id"])
        thesis_id = thesis_id_by_version[version_id]
        for known in located:
            if (
                thesis_id != make_thesis_id(known.document_short_name)
                or
                review_case["internal_rule_id"] != known.internal_rule_id
                or review_case["issue_type"] != known.issue_type
                or review_case.get("physical_page") != known.physical_page
            ):
                continue
            fingerprint = compute_case_fingerprint(
                thesis_version_id=version_id,
                internal_rule_id=known.internal_rule_id,
                issue_type=known.issue_type,
                physical_page=known.physical_page,
                structural_location=known.structural_location,
                volatile_detail=known.volatile_detail,
            )
            case_id = make_case_id(version_id, known.internal_rule_id, fingerprint.equivalence_key)
            if case_id != review_case["case_id"]:
                continue
            result[case_id] = CaseLocator(
                case_id=case_id,
                version=LOCATOR_VERSION,
                source_reference=known.locator_source_reference or known.source_reference,
                anchor_x=known.anchor_x,
                anchor_y=known.anchor_y,
                structural_role=known.structural_role,
            )
    return result
