"""Cross-source consistency checks for the rule "registry".

There is no single canonical rule-registry class in this codebase yet (see
docs/RULE_ARCHITECTURE.md for why, and for the smallest-safe-step registry
improvement this test file accompanies). Until one exists, these tests are the
guardrail that keeps `data/processed/rules/project_added_rules.json`, the
detector source, and the student-facing wording layers from silently drifting
apart the way PR #505 found and fixed for P057/P059/P062/P065/P078 (a raw
`rule_id` leaking into the generic fallback comment).

These tests only read tracked repository files — no network access, no local
generated `results/` output, so they run the same in a fresh clone and in CI.
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

import pytest

from njit_auditor.issue_type_explanations import (
    explain_issue_type,
    issue_type_title,
    student_facing_issue_label,
)
from njit_auditor.polished_comments import (
    build_polished_comment,
    finalize_student_facing_comment_and_fix,
)
from njit_auditor.rule_loader import ALLOWED_RULE_TYPES, load_rule_file
from njit_auditor.rule_source_scan import detector_emitted_pairs_by_static_scan

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOG_PATH = _REPO_ROOT / "data/processed/rules/project_added_rules.json"

_REPORTING_ONLY_TYPES = frozenset(
    {"infrastructure", "infrastructure_refinement", "reporting_refinement"}
)

# Internal rule ID pattern that must never appear verbatim in student-facing text.
_RAW_ID_PATTERN = re.compile(r"\b[PQ]\d{2,3}\b")

# Default-enabled issue types with no wording coverage in polished_comments.py
# (i.e. build_polished_comment() falls to the generic fallback sentence for
# them). P082 is experimental/opt-in — never enabled by default — so its
# fallback wording, while generic, is never seen in a default web/CLI audit;
# it is tracked here anyway so the ratchet notices if it's ever enabled by
# default without also getting real templates. The ratchet fails if this set
# grows without a matching template being added.
_KNOWN_WORDING_GAPS: frozenset[tuple[str, str]] = frozenset(
    {
        ("P082", "landscape_page_number_orientation_advisory"),
        ("P082", "landscape_page_number_position_advisory"),
    }
)


def _load_catalog() -> list[dict]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_validates_against_rule_definition_schema() -> None:
    """The full, current field set (title/rule_type/issue_types/... included) must
    round-trip through RuleDefinition without silently dropping fields — see the
    "Schema drift" note in docs/RULE_ARCHITECTURE.md for why this was previously
    silently broken."""
    rules = load_rule_file(_CATALOG_PATH)
    by_id = {r.id: r for r in rules}
    p082 = by_id["P082"]
    assert p082.rule_type == "experimental_advisory"
    assert p082.issue_types == [
        "landscape_page_number_orientation_advisory",
        "landscape_page_number_position_advisory",
    ]
    assert p082.title == "Landscape Page-Number Orientation Advisory"


def test_no_duplicate_public_rule_ids() -> None:
    catalog = _load_catalog()
    ids = [r["id"] for r in catalog]
    assert len(ids) == len(set(ids)), "duplicate rule id in project_added_rules.json"


def test_rule_type_values_are_all_recognized() -> None:
    catalog = _load_catalog()
    for rule in catalog:
        rule_type = rule.get("rule_type")
        if rule_type is not None:
            assert rule_type in ALLOWED_RULE_TYPES, (
                f"{rule['id']} has unrecognized rule_type {rule_type!r}"
            )


def test_reporting_only_rules_have_no_standalone_issue_types() -> None:
    """A reporting-only/infrastructure rule must never claim a standalone issue type
    — it should only ever appear as a triage rollup on its parent detector's
    findings, never as its own student-visible finding."""
    catalog = _load_catalog()
    for rule in catalog:
        if rule.get("rule_type") in _REPORTING_ONLY_TYPES:
            assert not rule.get("issue_types"), (
                f"{rule['id']} is rule_type={rule['rule_type']!r} but declares "
                f"standalone issue_types {rule.get('issue_types')!r}"
            )


def test_implemented_rules_have_an_implementation_module_or_are_evaluation_tasks() -> None:
    """A rule marked implemented must point at real code, unless it's an
    evaluation-task rule (produces an analysis artifact, not a detector)."""
    catalog = _load_catalog()
    for rule in catalog:
        if rule.get("implementation_status") != "implemented":
            continue
        if rule.get("rule_type") == "evaluation_task" or rule.get("phase") == "evaluation_task":
            continue
        assert rule.get("implementation_module"), (
            f"{rule['id']} is implemented but has no implementation_module"
        )


def test_implementation_modules_are_importable() -> None:
    """Catches a stale/typo'd implementation_module before it becomes a mystery
    404-style bug report — the module reference must resolve to real code."""
    catalog = _load_catalog()
    for rule in catalog:
        module_name = rule.get("implementation_module")
        if not module_name:
            continue
        importlib.import_module(module_name)  # raises ImportError if stale


def test_static_scan_finds_pairs_missing_from_catalog_issue_types() -> None:
    """Regression test for the meta-gap itself: P014's catalog entry has no
    `issue_types` populated, so the static scan is the only ground-truth
    source that sees its two emitted issue types. This proves the scanner
    would have caught the original bug (both pairs previously had zero
    wording coverage) instead of merely asserting it runs without error."""
    catalog = _load_catalog()
    p014 = next(rule for rule in catalog if rule["id"] == "P014")
    assert not p014.get("issue_types"), (
        "this test's premise (P014 has no catalog issue_types) no longer holds — "
        "update this test's docstring/rationale if that catalog entry was fixed"
    )
    scanned_pairs = detector_emitted_pairs_by_static_scan()
    assert ("P014", "frontmatter_heading_layout_issue") in scanned_pairs
    assert ("P014", "frontmatter_heading_not_centered") in scanned_pairs


_GENERIC_FALLBACK_MARKER = "This automated check found a possible"


def _has_comment_coverage(rule_id: str, issue_type: str) -> bool:
    """True unless (rule_id, issue_type) falls all the way to
    build_polished_comment()'s generic fallback sentence.

    Behavioral, not structural: a pair can be "covered" either via an
    `_ISSUE_TEMPLATES` dict entry or via a dedicated `build_polished_comment()`
    dispatch branch (e.g. P012, P014, P015, P032, P042, P045, P047 all use the
    dispatch-branch style, not the dict, and must not be flagged as gaps).
    Calling the real function is what makes this accurate for both styles at
    once instead of re-encoding which style each rule happens to use.
    """
    comment = build_polished_comment(rule_id=rule_id, issue_type=issue_type, page=1, details={})
    return _GENERIC_FALLBACK_MARKER not in comment


def test_default_enabled_wording_gaps_have_not_grown() -> None:
    """Ratchet test: fails if a *new* default-enabled (non-experimental,
    non-reporting-only) issue type has no wording coverage in
    polished_comments.py, without also updating _KNOWN_WORDING_GAPS above.

    Ground truth is the union of two sources, not just the catalog: (1) the
    catalog's `issue_types` field, and (2) a static AST scan of every
    `AuditFinding(...)` call in src/njit_auditor/rules/*.py
    (`detector_emitted_pairs_by_static_scan()`). Source (1) alone previously
    let P014 hide from this ratchet — its catalog entry has no `issue_types`
    populated, so it contributed zero pairs even though its detector emitted
    two issue types with a real wording bug. Source (2) is a conservative,
    static-only superset add: it can only surface pairs source (1) missed,
    never remove catalog-derived ground truth.
    """
    catalog = _load_catalog()
    non_reporting_rule_ids = {
        rule["id"] for rule in catalog if rule.get("rule_type") not in _REPORTING_ONLY_TYPES
    }
    excluded_rule_ids = {
        rule["id"]
        for rule in catalog
        if rule.get("rule_type") in _REPORTING_ONLY_TYPES
        or rule.get("rule_type") == "evaluation_task"
        or rule.get("phase") == "evaluation_task"
        or "experimental" in (rule.get("rule_type") or "")
    }

    current_gaps: set[tuple[str, str]] = set()
    for rule in catalog:
        if rule.get("rule_type") in _REPORTING_ONLY_TYPES:
            continue
        rule_id = rule["id"]
        for issue_type in rule.get("issue_types") or []:
            if _has_comment_coverage(rule_id, issue_type):
                continue
            current_gaps.add((rule_id, issue_type))

    for rule_id, issue_type in detector_emitted_pairs_by_static_scan():
        if rule_id in excluded_rule_ids:
            continue
        if rule_id not in non_reporting_rule_ids:
            # Rule ID not in the catalog at all — out of scope for this ratchet.
            continue
        if _has_comment_coverage(rule_id, issue_type):
            continue
        current_gaps.add((rule_id, issue_type))

    new_gaps = current_gaps - _KNOWN_WORDING_GAPS
    assert not new_gaps, (
        f"New default-enabled issue type(s) with no wording coverage: {sorted(new_gaps)}. "
        "Add a template to polished_comments._ISSUE_TEMPLATES (preferred) or a rule-level "
        "fallback, or — if this really is intentional debt — add it to _KNOWN_WORDING_GAPS "
        "in this test with a reason."
    )

    closed_gaps = _KNOWN_WORDING_GAPS - current_gaps
    if closed_gaps:
        pytest.fail(
            f"_KNOWN_WORDING_GAPS is stale — these are now covered and should be removed "
            f"from the allowlist: {sorted(closed_gaps)}"
        )


@pytest.mark.parametrize("rule_id,issue_type", sorted(_KNOWN_WORDING_GAPS))
def test_public_surfaces_never_leak_raw_rule_id(rule_id: str, issue_type: str) -> None:
    """Public student-facing surfaces must not embed raw P###/Q### tokens.

    Covers polished comments (the original leak), drilldown titles, issue-type
    labels, explanations, and suggested-fix / remediation text. Separate
    rule-reference links may still show IDs intentionally.
    """
    comment, fix = finalize_student_facing_comment_and_fix(
        rule_id, issue_type, "", ""
    )
    surfaces = {
        "comment": comment or build_polished_comment(
            rule_id=rule_id, issue_type=issue_type, page=3
        ),
        "title": issue_type_title(rule_id, issue_type),
        "label": student_facing_issue_label(rule_id, issue_type),
        "explanation": explain_issue_type(rule_id, issue_type),
        "suggested_fix": fix,
    }
    for surface, text in surfaces.items():
        assert text and str(text).strip(), (
            f"{rule_id}/{issue_type} {surface} is empty/less informative"
        )
        leaked = _RAW_ID_PATTERN.findall(str(text))
        assert not leaked, (
            f"{rule_id}/{issue_type} leaked raw id(s) {leaked} in {surface}: {text!r}"
        )


def test_generic_fallback_never_leaks_raw_rule_id_for_unknown_issue_type() -> None:
    """Same check for a made-up issue type that will never have template coverage —
    guards the fallback path itself, not just today's known gaps."""
    comment = build_polished_comment(
        rule_id="P057", issue_type="a_completely_novel_future_issue_type", page=1
    )
    leaked = _RAW_ID_PATTERN.findall(comment)
    assert not leaked, f"leaked raw id(s) {leaked} in: {comment!r}"
    title = issue_type_title("P057", "a_completely_novel_future_issue_type")
    assert not _RAW_ID_PATTERN.findall(title), f"title leaked id(s) in: {title!r}"
