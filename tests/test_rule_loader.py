from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

from njit_auditor.rule_loader import (
    ALLOWED_CHECKABILITY,
    ALLOWED_PHASES,
    ALLOWED_PRIORITY,
    RuleCheckability,
    RuleDefinition,
    RulePhase,
    RulePriority,
)


def _minimal_rule() -> dict[str, object]:
    return {
        "id": "P999",
        "section": "Synthetic",
        "question": "Synthetic question?",
        "rule_definition": "Synthetic definition.",
        "remediation": "Synthetic remediation.",
        "severity": "warning",
        "source_file": "project_added",
        "implementation_status": "implemented",
    }


def test_allowed_sets_are_derived_from_literal_definitions() -> None:
    assert ALLOWED_PHASES == frozenset(get_args(RulePhase))
    assert ALLOWED_CHECKABILITY == frozenset(get_args(RuleCheckability))
    assert ALLOWED_PRIORITY == frozenset(get_args(RulePriority))


@pytest.mark.parametrize("phase", sorted(ALLOWED_PHASES))
def test_rule_definition_accepts_all_allowed_phases(phase: str) -> None:
    payload = _minimal_rule()
    payload["phase"] = phase
    assert RuleDefinition.model_validate(payload).phase == phase


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase", "bad_phase"),
        ("checkability", "bad_checkability"),
        ("priority", "bad_priority"),
    ],
)
def test_rule_definition_rejects_invalid_literal_values(field: str, value: str) -> None:
    payload = _minimal_rule()
    payload[field] = value
    with pytest.raises(ValidationError):
        RuleDefinition.model_validate(payload)
