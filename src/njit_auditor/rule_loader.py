"""Load and validate JSON rule definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

REQUIRED_RULE_FIELDS = {
    "id",
    "section",
    "question",
    "rule_definition",
    "remediation",
    "severity",
    "source_file",
    "implementation_status",
}
ALLOWED_PHASES = {
    "tex_source", "latex_compile", "pdf_layout", "mixed", "manual_review", "docx_comments",
    "evaluation_task",
}
ALLOWED_CHECKABILITY = {"deterministic", "heuristic", "visual", "manual"}
ALLOWED_PRIORITY = {"high", "medium", "low"}


class RuleDefinition(BaseModel):
    """Schema for one rule loaded from JSON."""

    id: str
    section: str
    question: str
    rule_definition: str
    remediation: str
    severity: str
    source_file: str
    implementation_status: str
    phase: (
        Literal[
            "tex_source", "latex_compile", "pdf_layout", "mixed", "manual_review",
            "docx_comments", "evaluation_task",
        ]
        | None
    ) = None
    checkability: Literal["deterministic", "heuristic", "visual", "manual"] | None = None
    input_required: list[str] | None = None
    implementation_module: str | None = None
    priority: Literal["high", "medium", "low"] | None = None
    notes: str | None = None


def load_rule_file(path: str | Path) -> list[RuleDefinition]:
    """Load a rule JSON file and validate fields and uniqueness."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        msg = "Rule file must contain a list of rule objects."
        raise ValueError(msg)

    seen_ids: set[str] = set()
    loaded: list[RuleDefinition] = []
    for idx, rule in enumerate(payload):
        if not isinstance(rule, dict):
            msg = f"Rule at index {idx} is not an object."
            raise ValueError(msg)

        missing = REQUIRED_RULE_FIELDS - set(rule)
        if missing:
            missing_csv = ", ".join(sorted(missing))
            msg = f"Rule at index {idx} is missing required fields: {missing_csv}"
            raise ValueError(msg)

        rule_id = str(rule["id"]).strip()
        if not rule_id:
            msg = f"Rule at index {idx} has an empty id."
            raise ValueError(msg)
        if rule_id in seen_ids:
            msg = f"Duplicate rule id found: {rule_id}"
            raise ValueError(msg)
        seen_ids.add(rule_id)

        phase = rule.get("phase")
        if phase is not None and phase not in ALLOWED_PHASES:
            msg = f"Rule id {rule_id} has invalid phase: {phase}"
            raise ValueError(msg)

        checkability = rule.get("checkability")
        if checkability is not None and checkability not in ALLOWED_CHECKABILITY:
            msg = f"Rule id {rule_id} has invalid checkability: {checkability}"
            raise ValueError(msg)

        priority = rule.get("priority")
        if priority is not None and priority not in ALLOWED_PRIORITY:
            msg = f"Rule id {rule_id} has invalid priority: {priority}"
            raise ValueError(msg)

        input_required = rule.get("input_required")
        if input_required is not None and not isinstance(input_required, list):
            msg = f"Rule id {rule_id} has non-list input_required."
            raise ValueError(msg)

        implementation_module = rule.get("implementation_module")
        if implementation_module is not None and not str(implementation_module).strip():
            msg = f"Rule id {rule_id} has empty implementation_module."
            raise ValueError(msg)

        loaded.append(RuleDefinition.model_validate(rule))

    return loaded
