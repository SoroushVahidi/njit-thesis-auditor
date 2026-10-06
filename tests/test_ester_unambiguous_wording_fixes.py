"""Regression tests for unambiguous Ester-source wording alignment fixes."""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.finding_explanations import _RULE_FALLBACKS

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOG_PATH = _REPO_ROOT / "data/processed/rules/project_added_rules.json"


def _rule(rule_id: str) -> dict[str, str]:
    rules = {item["id"]: item for item in json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))}
    return rules[rule_id]


def test_p037_catalog_describes_continuation_after_bio() -> None:
    rule = _rule("P037")
    blob = " ".join(
        rule.get(key, "") for key in ("question", "rule_definition", "remediation")
    ).lower()
    assert "biographical sketch" in blob and "iv" in blob
    assert "preceding" in blob and "continuation pages" in blob
    assert "fixed njit template slots" not in blob
    assert "dedication (v" not in blob
    assert "acknowledgements vi" not in blob


def test_p019_catalog_avoids_internal_candidate_wording() -> None:
    rule = _rule("P019")
    question = rule["question"].lower()
    assert "candidate" not in question
    assert "obvious" not in question
    assert "visible page numbers" in question


def test_p019_rule_fallback_uses_ester_section_language() -> None:
    text = _RULE_FALLBACKS["P019"].lower()
    assert "candidate" not in text
    assert "roman numerals" in text
    assert "arabic numerals" in text


def test_catalog_p037_question_matches_dynamic_lot_wording() -> None:
    rule = _rule("P037")
    assert "continue the lowercase roman numeral sequence" in rule["question"].lower()
