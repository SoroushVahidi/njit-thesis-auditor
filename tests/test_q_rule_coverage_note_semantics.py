"""Which catalog metadata may count as a P-rule implementing a Q-rule."""

from __future__ import annotations

from typing import Any

import pytest

from njit_auditor.specs.q_rule_coverage import _build_q_to_p_map, build_coverage_report


def _covered(*rules: dict[str, Any]) -> dict[str, set[str]]:
    """Return {P-rule: {Q-IDs}} for a synthetic catalog."""
    by_rule: dict[str, set[str]] = {}
    for q_id, p_rules in _build_q_to_p_map(list(rules)).items():
        for p_rule in p_rules:
            by_rule.setdefault(p_rule, set()).add(q_id)
    return by_rule


def test_structured_source_q_rule_ids_create_coverage() -> None:
    assert _covered({"id": "P900", "source_q_rule_ids": ["Q013", "Q021"]}) == {
        "P900": {"Q013", "Q021"}
    }


def test_structured_q_rule_ids_create_coverage() -> None:
    assert _covered({"id": "P900", "q_rule_ids": ["Q044"]}) == {"P900": {"Q044"}}


@pytest.mark.parametrize(
    "notes",
    [
        "Q015-Q020 remain manual-only.",
        "Q015 is not implemented.",
        "Dedication content (Q033/Q034) not checked.",
        "The LoF sentence-case check (Q074) was removed 2026-10-05.",
        "Superseded: Q074 now belongs elsewhere.",
        "Q030 is deferred.",
        "Q029 is excluded from this check.",
    ],
)
def test_negative_note_references_create_no_coverage(notes: str) -> None:
    assert _covered({"id": "P900", "notes": notes}) == {}


@pytest.mark.parametrize(
    "notes",
    [
        "Abstract pages: P044 handles Q002/Q003 via P044A/P044B.",
        "Companion to P041 (Q032).",
        "Figure single-spacing (Q076, via P032).",
    ],
)
def test_notes_crediting_another_rule_create_no_coverage(notes: str) -> None:
    assert _covered({"id": "P900", "notes": notes}) == {}


def test_positive_legacy_note_references_still_count() -> None:
    assert _covered(
        {
            "id": "P900",
            "notes": (
                "Conservative v1 PDF heuristic for Q053-Q055 and Q066. Does not verify "
                "leader dots. Public cards P900A-P900C cover Q049. Q051 remains partial."
            ),
        }
    ) == {"P900": {"Q049", "Q051", "Q053", "Q054", "Q055", "Q066"}}


def test_notes_cannot_override_structured_metadata() -> None:
    assert _covered(
        {"id": "P900", "source_q_rule_ids": ["Q013"], "notes": "Heuristic for Q021."},
        {"id": "P901", "source_q_rule_ids": [], "notes": "Heuristic for Q028/Q029."},
    ) == {"P900": {"Q013"}}


@pytest.mark.parametrize("value", ["Q052", ["Q52"], ["Q052", 7], "['Q052']"])
def test_malformed_structured_metadata_fails_clearly(value: object) -> None:
    with pytest.raises(ValueError, match=r"P900: source_q_rule_ids must be a list"):
        _build_q_to_p_map([{"id": "P900", "source_q_rule_ids": value}])


def test_real_catalog_manual_only_and_cross_references_are_not_coverage() -> None:
    rows = {row.q_id: row for row in build_coverage_report()}
    for q_id in ("Q015", "Q016", "Q017", "Q018", "Q019", "Q020"):
        assert not {"P068", "P072"} & set(rows[q_id].implementing_p_rules), q_id
    for q_id in ("Q016", "Q017", "Q018", "Q019"):
        assert rows[q_id].implementation_status == "manual_review_only"
    assert rows["Q015"].implementation_status == "unimplemented"
    assert rows["Q020"].implementation_status == "unimplemented"
    assert "P066" not in rows["Q024"].implementing_p_rules
    for q_id in ("Q002", "Q003", "Q044", "Q045"):
        assert "P015" not in rows[q_id].implementing_p_rules
    assert rows["Q002"].implementing_p_rules == ["P044"]
    assert rows["Q044"].implementing_p_rules == ["P043"]
    assert "P014" not in rows["Q001"].implementing_p_rules
    assert "P014" in rows["Q013"].implementing_p_rules


def test_real_catalog_structured_relationships_survive() -> None:
    rows = {row.q_id: row for row in build_coverage_report()}
    assert {"P018", "P075"} <= set(rows["Q052"].implementing_p_rules)
    assert {"P042", "P063"} <= set(rows["Q058"].implementing_p_rules)
    assert rows["Q028"].implementing_p_rules == ["P045"]
    assert "P024" in rows["Q074"].implementing_p_rules
    assert rows["Q025"].implementing_p_rules == ["P066"]
