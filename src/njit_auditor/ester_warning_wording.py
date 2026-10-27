"""Student-facing warning questions and remediations from Ester's Column C/E map."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from njit_auditor.resource_paths import resource_path

_MAP_PATH = resource_path("data", "specs", "ester_warning_wording_map.json")


@lru_cache(maxsize=1)
def _load_map() -> dict[str, Any]:
    if not _MAP_PATH.exists():
        return {"rules": {}}
    return json.loads(_MAP_PATH.read_text(encoding="utf-8"))


def _rule_entry(rule_id: str) -> dict[str, Any]:
    rules = _load_map().get("rules", {})
    entry = rules.get(rule_id, {})
    return entry if isinstance(entry, dict) else {}


def student_warning_question(rule_id: str, issue_type: str = "") -> str:
    """Return Ester's yes/no question for a rule when mapped."""
    entry = _rule_entry(rule_id)
    issue_questions = entry.get("issue_type_questions", {})
    if issue_type and isinstance(issue_questions, dict):
        override = str(issue_questions.get(issue_type, "")).strip()
        if override:
            return override
    return str(entry.get("question", "")).strip()


def student_warning_remediation(rule_id: str) -> str:
    """Return Ester's how-to-fix remediation for a rule when mapped."""
    return str(_rule_entry(rule_id).get("remediation", "")).strip()


def student_warning_applies_to_issue_type(rule_id: str, issue_type: str) -> bool:
    """True when the mapped Ester question should replace the issue-type label."""
    if not issue_type:
        return False
    entry = _rule_entry(rule_id)
    apply_to = entry.get("apply_question_to_issue_types", [])
    if not isinstance(apply_to, list):
        return False
    return issue_type in apply_to


def student_warning_label(rule_id: str, issue_type: str = "") -> str:
    """Card/drill-down title: Ester yes/no question only for mapped issue types."""
    if student_warning_applies_to_issue_type(rule_id, issue_type):
        return student_warning_question(rule_id, issue_type=issue_type)
    return ""
