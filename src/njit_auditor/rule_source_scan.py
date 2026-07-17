"""Static (no-import, no-execution) ground-truth extraction for detector rules.

Scans `src/njit_auditor/rules/*.py` source text with `ast` to recover which
`(rule_id, issue_type)` pairs a detector actually constructs via
`AuditFinding(...)`, without importing or running any detector.

Why this exists: `data/processed/rules/project_added_rules.json`'s
`issue_types` field is the usual ground truth for "what does this rule emit",
but it is only populated for a minority of catalog rows (see
docs/RULE_ARCHITECTURE.md). A rule whose catalog entry has no `issue_types`
was previously invisible to the wording-coverage ratchet in
`tests/test_rule_registry_consistency.py` — which is exactly how P014 shipped
a real wording bug ("...issue issue...") undetected. This scanner is a
conservative, static-only *superset* addition: it can only surface pairs the
catalog missed, never remove catalog-derived ground truth, and it is not a
full data-flow analysis (dict-lookup-based issue types, e.g. built from a
per-section mapping rather than a simple local-variable assignment, are not
resolved and are simply absent from its output — exactly as invisible as
they were before this module existed).

Used by:
- tests/test_rule_registry_consistency.py (the wording-coverage ratchet)
- scripts/atomic_presentation_inventory.py (the diagnostic inventory report)
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = _REPO_ROOT / "src/njit_auditor/rules"


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_name_string_values(func_node: ast.AST) -> dict[str, set[str]]:
    """Every string literal ever assigned to each local name within *func_node*.

    Handles the common `issue_type = "..."` pattern, including conditional
    reassignment (like P014's `check_named_frontmatter_headings`, which sets
    `issue_type` to one literal and may reassign it to another before the
    finding is built) by collecting the full set of literal values ever bound
    to a name in that function, rather than only the last one.
    """
    values: dict[str, set[str]] = {}
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign):
            literal = _string_literal(node.value)
            if literal is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values.setdefault(target.id, set()).add(literal)
    return values


def detector_emitted_pairs_by_static_scan() -> set[tuple[str, str]]:
    """Statically extract (rule_id, issue_type) pairs from `AuditFinding(...)`
    call sites in src/njit_auditor/rules/*.py.
    """
    pairs: set[tuple[str, str]] = set()
    for path in sorted(RULES_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            local_values = _collect_name_string_values(func)
            for call in ast.walk(func):
                if not isinstance(call, ast.Call):
                    continue
                if not (isinstance(call.func, ast.Name) and call.func.id == "AuditFinding"):
                    continue
                rule_ids: set[str] = set()
                details_dict: ast.Dict | None = None
                for kw in call.keywords:
                    if kw.arg == "rule_id":
                        literal = _string_literal(kw.value)
                        if literal is not None:
                            rule_ids.add(literal)
                        elif isinstance(kw.value, ast.Name):
                            rule_ids |= local_values.get(kw.value.id, set())
                    if kw.arg == "details" and isinstance(kw.value, ast.Dict):
                        details_dict = kw.value
                if not rule_ids or details_dict is None:
                    continue
                issue_values: set[str] = set()
                for key_node, value_node in zip(details_dict.keys, details_dict.values):
                    if not (isinstance(key_node, ast.Constant) and key_node.value == "issue_type"):
                        continue
                    literal = _string_literal(value_node)
                    if literal is not None:
                        issue_values.add(literal)
                    elif isinstance(value_node, ast.Name):
                        issue_values |= local_values.get(value_node.id, set())
                for rule_id in rule_ids:
                    for issue_type in issue_values:
                        pairs.add((rule_id, issue_type))
    return pairs
