"""Regression test for the `_classify_rule()` / `_technical_reason()` duplication.

Both functions used to independently re-derive the same student-vs-technical
classification for a rule catalog entry via two parallel if/elif chains (see
docs/RULE_ARCHITECTURE.md "Known duplication"). Nothing enforced that they could
never disagree. They now both delegate to a single helper,
`_rule_technical_classification()`; this test proves that delegation holds for
every rule in the real catalog and for a battery of synthetic edge cases,
including mixed-case field values (the one input where the two functions
previously behaved differently: `_classify_rule` compared raw `phase` while
`_technical_reason` compared a lowercased `phase`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from njit_auditor.web_app import _classify_rule, _technical_reason

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOG_PATH = _REPO_ROOT / "data/processed/rules/project_added_rules.json"


def _load_catalog() -> list[dict[str, Any]]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _assert_consistent(rule: dict[str, Any]) -> None:
    classification = _classify_rule(rule)
    reason = _technical_reason(rule)
    if classification == "technical":
        assert reason != "Technical entry", (
            f"rule classified technical but _technical_reason gave the "
            f"'no reason matched' fallback: {rule!r}"
        )
    else:
        assert reason == "Technical entry", (
            f"rule classified student but _technical_reason returned a technical "
            f"reason {reason!r}: {rule!r}"
        )


def test_classify_rule_and_technical_reason_agree_on_real_catalog() -> None:
    for rule in _load_catalog():
        _assert_consistent(rule)


def test_classify_rule_and_technical_reason_agree_on_synthetic_edge_cases() -> None:
    synthetic_rules: list[dict[str, Any]] = [
        {},
        {"phase": "pdf_layout", "rule_type": "detector"},
        {"phase": "evaluation_task"},
        {"rule_type": "evaluation_task"},
        {"rule_type": "infrastructure"},
        {"rule_type": "reporting_refinement"},
        {"rule_type": "experimental_advisory"},
        {"notes": "infrastructure-only scaffold"},
        {"notes": "reporting-only refinement"},
        {"phase": "docx_comments"},
        # Mixed-case variants — the field-casing bug class that could previously
        # make the two functions disagree (phase was lowercased in one function
        # but not the other).
        {"phase": "Evaluation_Task"},
        {"phase": "DOCX_Comments"},
        {"rule_type": "Infrastructure"},
        {"rule_type": "Reporting_Refinement"},
        {"rule_type": "EXPERIMENTAL_ADVISORY"},
        {"notes": "INFRASTRUCTURE-ONLY"},
        {"notes": "Reporting-Only"},
    ]
    for rule in synthetic_rules:
        _assert_consistent(rule)
