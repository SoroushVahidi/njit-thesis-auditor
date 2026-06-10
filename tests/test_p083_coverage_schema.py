"""Schema and aggregate-consistency tests for data/processed/ef_comment_coverage.json (P083)."""

from __future__ import annotations

import json
from pathlib import Path

COVERAGE_PATH = Path("data/processed/ef_comment_coverage.json")

VALID_TAXONOMY_CLASSES = {"SIM", "SIP", "SMI", "SBL", "SEM", "PRF", "AMB"}
VALID_SOURCE_TYPES = {"extracted_docx", "estimated_from_evaluation_notes"}
VALID_CONFIDENCES = {"high", "medium", "low"}
REQUIRED_ROW_KEYS = {
    "comment_id",
    "doc_alias",
    "source_type",
    "comment_category",
    "comment_summary",
    "page",
    "taxonomy_class",
    "matched_rule_ids",
    "taxonomy_confidence",
    "gap_note",
}


def _load() -> dict:
    with COVERAGE_PATH.open() as fh:
        return json.load(fh)


def test_coverage_schema_and_row_fields() -> None:
    data = _load()
    assert data["schema_version"] == 1
    assert "privacy_policy" in data
    privacy = data["privacy_policy"]
    assert privacy["no_raw_reviewer_text"] is True
    assert privacy["no_student_names"] is True
    assert privacy["no_private_file_paths"] is True
    assert privacy["no_dissertation_body_text"] is True

    rows = data["coverage"]
    assert isinstance(rows, list)
    assert len(rows) > 0

    seen_ids: set[str] = set()
    for i, row in enumerate(rows):
        missing = REQUIRED_ROW_KEYS - row.keys()
        assert not missing, f"Row {i} missing keys: {missing}"

        cid = row["comment_id"]
        assert isinstance(cid, str) and len(cid) == 12, (
            f"Row {i}: comment_id must be 12-char string"
        )
        assert cid not in seen_ids, f"Duplicate comment_id {cid!r} at row {i}"
        seen_ids.add(cid)

        assert row["doc_alias"] and "/" not in row["doc_alias"], (
            f"Row {i}: doc_alias must not contain path separators"
        )
        assert row["source_type"] in VALID_SOURCE_TYPES, (
            f"Row {i}: invalid source_type {row['source_type']!r}"
        )
        assert row["taxonomy_class"] in VALID_TAXONOMY_CLASSES, (
            f"Row {i}: invalid taxonomy_class {row['taxonomy_class']!r}"
        )
        assert row["taxonomy_confidence"] in VALID_CONFIDENCES, (
            f"Row {i}: invalid taxonomy_confidence"
        )
        assert isinstance(row["matched_rule_ids"], list), (
            f"Row {i}: matched_rule_ids must be a list"
        )
        assert isinstance(row["comment_summary"], str) and 0 < len(row["comment_summary"]) <= 200, (
            f"Row {i}: comment_summary must be 1–200 chars"
        )
        assert isinstance(row["gap_note"], str) and len(row["gap_note"]) > 0, (
            f"Row {i}: gap_note must be non-empty"
        )


def test_coverage_taxonomy_classes_valid() -> None:
    data = _load()
    rows = data["coverage"]
    for i, row in enumerate(rows):
        tc = row["taxonomy_class"]
        assert tc in VALID_TAXONOMY_CLASSES, f"Row {i}: unknown taxonomy_class {tc!r}"
        if tc in ("SEM", "PRF", "AMB"):
            assert row["matched_rule_ids"] == [], (
                f"Row {i}: {tc} rows must have empty matched_rule_ids"
            )
        if tc == "SIM":
            assert len(row["matched_rule_ids"]) >= 1, (
                f"Row {i}: SIM rows must have at least one matched_rule_id"
            )


def test_coverage_aggregate_counts_match_rows() -> None:
    data = _load()
    rows = data["coverage"]
    agg = data["aggregate"]

    assert agg["total_rows"] == len(rows), "aggregate.total_rows must equal len(coverage)"

    by_class: dict[str, int] = {}
    by_alias: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for row in rows:
        by_class[row["taxonomy_class"]] = by_class.get(row["taxonomy_class"], 0) + 1
        by_alias[row["doc_alias"]] = by_alias.get(row["doc_alias"], 0) + 1
        by_source[row["source_type"]] = by_source.get(row["source_type"], 0) + 1

    for cls, count in agg["by_taxonomy_class"].items():
        actual = by_class.get(cls, 0)
        assert actual == count, (
            f"aggregate.by_taxonomy_class[{cls!r}] mismatch: {actual} vs {count}"
        )

    for alias, count in agg["by_doc_alias"].items():
        assert by_alias.get(alias, 0) == count, f"aggregate.by_doc_alias[{alias!r}] mismatch"

    for src, count in agg["by_source_type"].items():
        assert by_source.get(src, 0) == count, f"aggregate.by_source_type[{src!r}] mismatch"

    in_scope = sum(
        by_class.get(c, 0) for c in ("SIM", "SIP", "SMI", "SBL")
    )
    out_of_scope = sum(
        by_class.get(c, 0) for c in ("SEM", "PRF", "AMB")
    )
    assert agg["in_scope_count"] == in_scope, f"in_scope_count mismatch: {in_scope}"
    assert agg["out_of_scope_count"] == out_of_scope, f"out_of_scope_count mismatch: {out_of_scope}"
