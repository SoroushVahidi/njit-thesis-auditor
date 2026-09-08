"""Tests for case fingerprinting: SAME / EQUIVALENT / NEW classification."""

from __future__ import annotations

import pytest

from njit_auditor.review_ledger.fingerprint import (
    classify_against_known,
    compute_case_fingerprint,
)


def _fp(**overrides: object) -> object:
    base = {
        "thesis_version_id": "TV-1",
        "internal_rule_id": "P018",
        "issue_type": "inconsistent_leader_dots",
        "physical_page": 11,
        "structural_location": "table_of_contents:entry_index=1",
        "volatile_detail": "center_delta_pt=0",
    }
    base.update(overrides)
    return compute_case_fingerprint(**base)  # type: ignore[arg-type]


def test_identical_inputs_produce_identical_fingerprint() -> None:
    a = _fp()
    b = _fp()
    assert a.exact_fingerprint == b.exact_fingerprint
    assert a.equivalence_key == b.equivalence_key


def test_rejects_empty_stable_fields() -> None:
    with pytest.raises(ValueError):
        compute_case_fingerprint(
            thesis_version_id="",
            internal_rule_id="P018",
            issue_type="x",
            physical_page=1,
            structural_location="loc",
        )
    with pytest.raises(ValueError):
        compute_case_fingerprint(
            thesis_version_id="TV-1",
            internal_rule_id="P018",
            issue_type="x",
            physical_page=1,
            structural_location="",
        )


def test_minor_volatile_detail_change_is_equivalent_not_new() -> None:
    """A tiny bbox/measurement change (same page, same rule, same
    structural slot) must classify as EQUIVALENT, not a brand-new case."""
    original = _fp(volatile_detail="center_delta_pt=0")
    reran = _fp(volatile_detail="center_delta_pt=1.4")
    assert original.exact_fingerprint != reran.exact_fingerprint
    assert original.equivalence_key == reran.equivalence_key
    assert classify_against_known(reran, [original]) == "EQUIVALENT"


def test_identical_rerun_classifies_as_same() -> None:
    original = _fp()
    identical = _fp()
    assert classify_against_known(identical, [original]) == "SAME"


def test_different_page_is_a_new_case() -> None:
    original = _fp(physical_page=11)
    other_page = _fp(physical_page=12, structural_location="table_of_contents:entry_index=2")
    assert classify_against_known(other_page, [original]) == "NEW"


def test_different_structural_location_on_same_page_is_a_new_case() -> None:
    """Two distinct violations on the same page must not collide into one
    case just because the page number matches."""
    entry_one = _fp(structural_location="table_of_contents:entry_index=1")
    entry_two = _fp(structural_location="table_of_contents:entry_index=2")
    assert classify_against_known(entry_two, [entry_one]) == "NEW"


def test_different_rule_is_a_new_case() -> None:
    original = _fp(internal_rule_id="P018")
    other_rule = _fp(internal_rule_id="P024")
    assert classify_against_known(other_rule, [original]) == "NEW"


def test_different_thesis_version_is_a_new_case() -> None:
    """A finding on a later thesis version is never automatically treated
    as the same case as one from an earlier version, even with otherwise
    identical structural attributes -- version identity is part of the
    stable key."""
    v1 = _fp(thesis_version_id="TV-1")
    v2 = _fp(thesis_version_id="TV-2")
    assert classify_against_known(v2, [v1]) == "NEW"


def test_classify_against_empty_known_list_is_new() -> None:
    assert classify_against_known(_fp(), []) == "NEW"


def test_exact_fingerprint_never_reveals_stable_key_order_leniency() -> None:
    """Sanity: swapping two structurally-different inputs must not
    accidentally produce a matching digest (guards against a naive
    concatenation bug where e.g. rule_id='P0' + issue_type='18...' could
    collide with rule_id='P018' + issue_type='...')."""
    a = compute_case_fingerprint(
        thesis_version_id="TV-1",
        internal_rule_id="P0",
        issue_type="18x",
        physical_page=1,
        structural_location="loc",
    )
    b = compute_case_fingerprint(
        thesis_version_id="TV-1",
        internal_rule_id="P018",
        issue_type="x",
        physical_page=1,
        structural_location="loc",
    )
    assert a.equivalence_key != b.equivalence_key
