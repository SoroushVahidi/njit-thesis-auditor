"""P071/Q030 and P024/Q074 structured Q metadata (2026-10-06 reconciliation)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from njit_auditor.specs.q_rule_coverage import build_coverage_report

_RULES = Path(__file__).resolve().parents[1] / "data/processed/rules/project_added_rules.json"


def _rule(rule_id: str) -> dict[str, Any]:
    rules = json.loads(_RULES.read_text(encoding="utf-8"))
    return next(r for r in rules if isinstance(r, dict) and r.get("id") == rule_id)


def _rows() -> dict[str, Any]:
    return {row.q_id: row for row in build_coverage_report()}


def test_p071_does_not_claim_manual_only_q030() -> None:
    p071 = _rule("P071")
    assert "Q030" not in p071["source_q_rule_ids"]
    # Structured metadata and notes now agree.
    assert "Q030 remains manual-only" in p071["notes"]
    assert p071["issue_types"] == []


def test_q030_has_no_implementing_rule() -> None:
    q030 = _rows()["Q030"]
    assert q030.implementing_p_rules == []
    assert q030.implementation_status == "unimplemented"


def test_p024_declares_the_q_rows_its_detector_emits() -> None:
    import inspect

    from njit_auditor.rules import pdf_toc_list_formatting

    declared = _rule("P024")["source_q_rule_ids"]
    assert declared == ["Q049", "Q050", "Q065", "Q074"]
    source = inspect.getsource(pdf_toc_list_formatting)
    for q_id in declared:
        assert f'"{q_id}"' in source, q_id


def test_q074_is_implemented_by_p024_list_of_figures_title_case() -> None:
    q074 = _rows()["Q074"]
    assert "P024" in q074.implementing_p_rules
    # P017's superseded List of Figures sentence-case relationship stays gone.
    assert "P017" not in q074.implementing_p_rules
    assert q074.implementation_status == "implemented"


def test_r024d_and_r024e_stay_distinct_and_q_backed() -> None:
    import njit_auditor.web_app as wa

    specs = {spec["id"]: spec for spec in wa._P024_REMAINING_PUBLIC_CARD_SPECS}
    assert specs["P024D"]["source_q_rule_ids"] == ("Q065",)
    assert specs["P024D"]["issue_types"] == ("list_of_tables_title_case",)
    assert specs["P024E"]["source_q_rule_ids"] == ("Q074",)
    assert specs["P024E"]["issue_types"] == ("list_of_figures_title_case",)
    assert "title case" in specs["P024E"]["title"].lower()
    assert (
        wa._public_rule_reference_id(
            "P024", issue_type="list_of_figures_title_case", source_q_rule_id="Q074"
        )
        == "P024E"
    )
    assert wa._public_rule_reference_id("P024", issue_type="list_of_tables_title_case") == "P024D"
