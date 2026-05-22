"""Load and validate JSON rule definitions."""

from __future__ import annotations

import json
from pathlib import Path

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

        loaded.append(RuleDefinition.model_validate(rule))

    return loaded
