"""Audit runtime options for experimental and opt-in rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuditOptions:
    """Runtime flags that alter which rules run in an audit."""

    experimental_rules: frozenset[str] = field(default_factory=frozenset)

    def is_experimental_enabled(self, rule_id: str) -> bool:
        return rule_id in self.experimental_rules


DEFAULT_AUDIT_OPTIONS = AuditOptions()
