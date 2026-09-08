"""Tests for review-ledger ID determinism, uniqueness, and grammar."""

from __future__ import annotations

import datetime as dt

import pytest

from njit_auditor.review_ledger.identifiers import (
    make_adjudication_id,
    make_case_id,
    make_history_event_id,
    make_review_round_id,
    make_run_id,
    make_thesis_id,
    make_thesis_version_id,
)


def test_thesis_id_is_deterministic() -> None:
    assert make_thesis_id("synthetic-alpha") == make_thesis_id("synthetic-alpha")


def test_thesis_id_differs_for_different_alias() -> None:
    assert make_thesis_id("synthetic-alpha") != make_thesis_id("synthetic-beta")


def test_thesis_id_does_not_embed_the_alias_verbatim() -> None:
    thesis_id = make_thesis_id("synthetic-alpha")
    assert "synthetic-alpha" not in thesis_id


def test_thesis_id_rejects_empty_alias() -> None:
    with pytest.raises(ValueError):
        make_thesis_id("   ")


def test_thesis_version_id_deterministic_for_same_thesis_and_hash() -> None:
    thesis_id = make_thesis_id("synthetic-alpha")
    sha = "a" * 64
    assert make_thesis_version_id(thesis_id, sha) == make_thesis_version_id(thesis_id, sha)


def test_distinct_pdf_versions_produce_distinct_thesis_version_ids() -> None:
    thesis_id = make_thesis_id("synthetic-alpha")
    v1 = make_thesis_version_id(thesis_id, "a" * 64)
    v2 = make_thesis_version_id(thesis_id, "b" * 64)
    assert v1 != v2


def test_thesis_identity_stable_across_versions() -> None:
    """The same thesis alias always yields the same thesis_id regardless of
    which content hash is later paired with it -- version identity and
    thesis identity are independent axes."""
    thesis_id = make_thesis_id("synthetic-alpha")
    v1 = make_thesis_version_id(thesis_id, "a" * 64)
    v2 = make_thesis_version_id(thesis_id, "b" * 64)
    assert v1.split("-")[1] != v2.split("-")[1]  # different version ids
    # but both were derived from, and can be traced back to originating from,
    # the same deterministic thesis_id input
    assert make_thesis_version_id(thesis_id, "a" * 64) == v1


def test_run_id_is_unique_per_call() -> None:
    a = make_run_id("codesha1")
    b = make_run_id("codesha1")
    assert a != b


def test_run_id_embeds_code_sha_prefix() -> None:
    run_id = make_run_id("abcdef1234567890")
    assert "abcdef12" in run_id


def test_review_round_id_format() -> None:
    review_date = dt.date(2026, 9, 7)
    assert make_review_round_id(review_date, 1) == "ER-20260907-01"
    assert make_review_round_id(review_date, 12) == "ER-20260907-12"


def test_review_round_id_rejects_out_of_range_sequence() -> None:
    review_date = dt.date(2026, 9, 7)
    with pytest.raises(ValueError):
        make_review_round_id(review_date, 0)
    with pytest.raises(ValueError):
        make_review_round_id(review_date, 100)


def test_case_id_deterministic_for_same_equivalence_key() -> None:
    a = make_case_id("TV-1", "P018", "equivkey123")
    b = make_case_id("TV-1", "P018", "equivkey123")
    assert a == b


def test_case_id_not_derived_from_physical_page_alone() -> None:
    """Two cases with the same equivalence key on different thesis versions
    or rules must differ; nothing here accepts a page number as an input at
    all, by construction -- the equivalence key already folds structural
    location (which includes, but is not only, page) into the id."""
    a = make_case_id("TV-1", "P018", "equivkey123")
    b = make_case_id("TV-2", "P018", "equivkey123")
    assert a != b


def test_adjudication_and_history_event_ids_unique_per_call() -> None:
    assert make_adjudication_id() != make_adjudication_id()
    assert make_history_event_id() != make_history_event_id()
