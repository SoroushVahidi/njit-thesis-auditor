"""Tests for corpus registration (Thesis/ThesisVersion from real file bytes).

Uses small synthetic byte content written to tmp_path -- never a real
dissertation PDF -- since only SHA-256 identity behavior is under test.
"""

from __future__ import annotations

from pathlib import Path

from njit_auditor.review_ledger.importers.thesis_registry import (
    CORPUS_DOCUMENTS,
    register_corpus,
    sha256_of_file,
)
from njit_auditor.review_ledger.store import EsterReviewLedger


def _write_all_corpus_files(private_dir: Path, *, content_by_name: dict[str, bytes]) -> None:
    private_dir.mkdir(parents=True, exist_ok=True)
    for _short_name, filename in CORPUS_DOCUMENTS:
        content = content_by_name.get(filename, b"synthetic placeholder content")
        (private_dir / filename).write_bytes(content)


def test_sha256_of_file_matches_hashlib(tmp_path: Path) -> None:
    import hashlib

    path = tmp_path / "sample.bin"
    path.write_bytes(b"some synthetic content")
    assert sha256_of_file(path) == hashlib.sha256(b"some synthetic content").hexdigest()


def test_register_corpus_creates_thesis_and_version_for_available_files(tmp_path: Path) -> None:
    private_dir = tmp_path / "private"
    _write_all_corpus_files(private_dir, content_by_name={})
    ledger = EsterReviewLedger(tmp_path / "ledger")

    registered = register_corpus(
        ledger, first_seen_at="2026-01-01T00:00:00+00:00", private_data_dir=private_dir
    )

    assert len(registered) == len(CORPUS_DOCUMENTS)
    assert all(doc.available for doc in registered)
    assert len(ledger.theses.all()) == len(CORPUS_DOCUMENTS)
    assert len(ledger.thesis_versions.all()) == len(CORPUS_DOCUMENTS)


def test_missing_pdf_is_reported_unavailable_without_a_version_row(tmp_path: Path) -> None:
    private_dir = tmp_path / "private"
    private_dir.mkdir(parents=True)
    # Deliberately write only the first corpus file, leave the rest missing.
    first_short_name, first_filename = CORPUS_DOCUMENTS[0]
    (private_dir / first_filename).write_bytes(b"only this one exists")
    ledger = EsterReviewLedger(tmp_path / "ledger")

    registered = register_corpus(
        ledger, first_seen_at="2026-01-01T00:00:00+00:00", private_data_dir=private_dir
    )

    available = [d for d in registered if d.available]
    unavailable = [d for d in registered if not d.available]
    assert len(available) == 1
    assert available[0].short_name == first_short_name
    assert len(unavailable) == len(CORPUS_DOCUMENTS) - 1
    # A Thesis row exists for every document (identity doesn't require the
    # PDF); a ThesisVersion row exists only for the one with real bytes.
    assert len(ledger.theses.all()) == len(CORPUS_DOCUMENTS)
    assert len(ledger.thesis_versions.all()) == 1


def test_distinct_content_produces_distinct_version_but_same_thesis(tmp_path: Path) -> None:
    private_dir = tmp_path / "private"
    _write_all_corpus_files(private_dir, content_by_name={})
    ledger = EsterReviewLedger(tmp_path / "ledger")
    first_pass = register_corpus(
        ledger, first_seen_at="2026-01-01T00:00:00+00:00", private_data_dir=private_dir
    )
    first_by_name = {d.short_name: d for d in first_pass}

    # Simulate a later, revised submission: change one document's bytes.
    short_name, filename = CORPUS_DOCUMENTS[0]
    (private_dir / filename).write_bytes(b"a revised submission's bytes")
    second_pass = register_corpus(
        ledger, first_seen_at="2026-02-01T00:00:00+00:00", private_data_dir=private_dir
    )
    second_by_name = {d.short_name: d for d in second_pass}

    assert first_by_name[short_name].thesis_id == second_by_name[short_name].thesis_id
    assert (
        first_by_name[short_name].thesis_version_id
        != second_by_name[short_name].thesis_version_id
    )
    # Both versions persist -- the earlier one was never deleted.
    assert len(ledger.thesis_versions.all()) == len(CORPUS_DOCUMENTS) + 1


def test_register_corpus_is_idempotent(tmp_path: Path) -> None:
    private_dir = tmp_path / "private"
    _write_all_corpus_files(private_dir, content_by_name={})
    ledger = EsterReviewLedger(tmp_path / "ledger")
    register_corpus(ledger, first_seen_at="2026-01-01T00:00:00+00:00", private_data_dir=private_dir)
    register_corpus(ledger, first_seen_at="2026-01-01T00:00:00+00:00", private_data_dir=private_dir)
    assert len(ledger.theses.all()) == len(CORPUS_DOCUMENTS)
    assert len(ledger.thesis_versions.all()) == len(CORPUS_DOCUMENTS)
