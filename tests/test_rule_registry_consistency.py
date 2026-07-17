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
from njit_auditor.rule_source_scan import (
    detector_emitted_pairs_by_static_scan,
    full_active_issue_type_universe,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOG_PATH = _REPO_ROOT / "data/processed/rules/project_added_rules.json"

_REPORTING_ONLY_TYPES = frozenset(
    {"infrastructure", "infrastructure_refinement", "reporting_refinement"}
)

# Internal rule ID pattern that must never appear verbatim in student-facing text.
_RAW_ID_PATTERN = re.compile(r"\b[PQ]\d{2,3}\b")

# Default-enabled issue types with no wording coverage in polished_comments.py
# (i.e. build_polished_comment() falls to the generic fallback sentence for
# them). Empty as of the 2026-07-16 issue-type-universe audit: P082 (the only
# entry this ever held) is experimental/opt-in, and is now correctly excluded
# from `_active_default_enabled_universe()` itself (rather than included and
# then allowlisted here) — see that helper's docstring. The ratchet fails if
# this set grows without a matching template being added.
_KNOWN_WORDING_GAPS: frozenset[tuple[str, str]] = frozenset()

# Scanner false positives: rule_source_scan.py tracks *every* literal value a
# loop variable is ever bound to across a whole function, but does not narrow
# that set inside `if`/`else` branches (it is flow-insensitive by design — see
# that module's docstring on scope). In pdf_heading_levels.py's `_check_line`,
# `level` ranges over (2, 3, 4, 5), but the f-string issue types
# `f"level{level}_..."` only appear inside the `else:  # level 3, 4, 5` branch
# (never level 2), and the punctuation-check f-string is further guarded by
# `if level in (4, 5):` (never level 3). The scanner cannot see those guards,
# so it reports the full cross product, including three combinations that can
# never actually be constructed at runtime:
_SCANNER_OVER_APPROXIMATION_ARTIFACTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("P027", "level2_sentence_case_issue"),
        ("P027", "level2_sentence_case_or_punctuation_issue"),
        ("P027", "level3_sentence_case_or_punctuation_issue"),
    }
)

# Pre-existing bug, discovered by this pass's broadened leak-check coverage,
# deliberately NOT fixed here (out of scope: this task is architectural
# ground-truth-discovery work, not a wording fix pass — see the task
# instructions' "isolate and document separately" guidance). Root cause: the
# raw catalog `remediation` field for P014 and P018 embeds internal
# cross-reference notation (e.g. "APPROVAL PAGE (Q013, P038)", "P018A-C
# (Q049-Q051)") intended as a developer note about which Q/P rules cover
# which sub-cases. No per-issue-type remediation override exists for these
# six pairs, so `_resolve_remediation()`'s catalog-level fallback surfaces
# that raw internal text to students verbatim. Recommended fix (not applied
# here): add `_ISSUE_REMEDIATION_OVERRIDES` entries in polished_comments.py
# for these six pairs with clean, student-facing remediation text — a
# presentation-only change, no raw-JSON edit needed.
_KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS: frozenset[tuple[str, str]] = frozenset(
    {
        ("P014", "frontmatter_heading_layout_issue"),
        ("P014", "frontmatter_heading_not_centered"),
        ("P018", "inconsistent_hierarchy_indent"),
        ("P018", "inconsistent_leader_dots"),
        ("P018", "misaligned_page_number_column"),
        ("P018", "missing_page_number"),
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


def _active_default_enabled_universe() -> set[tuple[str, str]]:
    """The complete active, default-enabled (rule_id, issue_type) universe:
    the union of every ground-truth source this repo knows about
    (`rule_source_scan.full_active_issue_type_universe()` — the catalog's own
    `issue_types` field is intentionally NOT unioned in separately here,
    since every pair it has ever contained is already a subset of the
    static-scan sources; see test_catalog_issue_types_are_a_subset_of_the_
    static_universe below), filtered down to rule_ids that are (a) present
    in the catalog and (b) not reporting-only/experimental/evaluation-task.
    """
    catalog = _load_catalog()
    known_rule_ids = {rule["id"] for rule in catalog}
    excluded_rule_ids = {
        rule["id"]
        for rule in catalog
        if rule.get("rule_type") in _REPORTING_ONLY_TYPES
        or rule.get("rule_type") == "evaluation_task"
        or rule.get("phase") == "evaluation_task"
        or "experimental" in (rule.get("rule_type") or "")
    }
    return {
        (rule_id, issue_type)
        for rule_id, issue_type in full_active_issue_type_universe()
        if rule_id in known_rule_ids and rule_id not in excluded_rule_ids
    }


def test_catalog_issue_types_are_a_subset_of_the_static_universe() -> None:
    """Sanity check on the ground-truth hierarchy itself: every pair the
    catalog's `issue_types` field has ever declared must also be discoverable
    by the static scan (or one of its documented exceptions/sources). If this
    ever fails, either a catalog entry drifted from the real detector, or the
    scanner has a real blind spot that needs a new pattern, not a silent gap."""
    catalog = _load_catalog()
    catalog_pairs = {
        (rule["id"], issue_type)
        for rule in catalog
        for issue_type in (rule.get("issue_types") or [])
    }
    static_universe = full_active_issue_type_universe()
    missing = catalog_pairs - static_universe
    assert not missing, (
        f"Catalog issue_types not found by any static source: {sorted(missing)}. "
        "Either the catalog is stale, or rule_source_scan.py needs a new pattern."
    )


def test_default_enabled_wording_gaps_have_not_grown() -> None:
    """Ratchet test: fails if a *new* default-enabled (non-experimental,
    non-reporting-only) issue type has no wording coverage in
    polished_comments.py, without also updating _KNOWN_WORDING_GAPS above.

    Ground truth is `rule_source_scan.full_active_issue_type_universe()` — a
    comprehensive static scan of every `AuditFinding(...)` call site in
    src/njit_auditor/rules/*.py (handling module-level config-dict lookups,
    same-module cross-function argument tracing, and f-string templates over
    finite domains — see that module's docstring), plus the TeX/source
    pipeline's separate rule_id-keyed dispatch and one documented
    non-detector exception (P021). This replaced sourcing ground truth from
    only the catalog's `issue_types` field, which is populated for a
    minority of rows and is exactly how P014 hid from this ratchet before
    the 2026-07-16 audit that added rule_source_scan.py.
    """
    current_gaps: set[tuple[str, str]] = {
        (rule_id, issue_type)
        for rule_id, issue_type in _active_default_enabled_universe()
        if not _has_comment_coverage(rule_id, issue_type)
    }

    # _SCANNER_OVER_APPROXIMATION_ARTIFACTS are unreachable-in-practice pairs
    # the scanner's flow-insensitivity over-generates (see its docstring) —
    # they are not real wording debt, so they never even reach the
    # _KNOWN_WORDING_GAPS staleness check below.
    current_gaps -= _SCANNER_OVER_APPROXIMATION_ARTIFACTS

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


@pytest.mark.parametrize("rule_id,issue_type", sorted(_active_default_enabled_universe()))
def test_public_surfaces_never_leak_raw_rule_id(rule_id: str, issue_type: str) -> None:
    """Public student-facing surfaces must not embed raw P###/Q### tokens.

    Covers polished comments (the original leak), drilldown titles, issue-type
    labels, explanations, and suggested-fix / remediation text. Separate
    rule-reference links may still show IDs intentionally.

    Parametrized over the *complete* active default-enabled issue-type
    universe (rule_source_scan.full_active_issue_type_universe(), filtered to
    non-reporting/non-experimental rule_ids) — not just the small known-gaps
    allowlist — so this test verifies title/comment/explanation/remediation
    coverage and non-leakage for every pair the project can currently prove
    exists, not only the ones someone remembered to list by hand.
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
        pair = (rule_id, issue_type)
        if surface == "suggested_fix" and pair in _KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS:
            # Pre-existing bug, discovered by this test, deliberately not fixed
            # here — see _KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS' docstring.
            continue
        leaked = _RAW_ID_PATTERN.findall(str(text))
        assert not leaked, (
            f"{rule_id}/{issue_type} leaked raw id(s) {leaked} in {surface}: {text!r}"
        )


def test_known_pre_existing_suggested_fix_leaks_are_not_stale() -> None:
    """Staleness guard for _KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS: if a pair
    listed there no longer actually leaks (e.g. someone added a remediation
    override), it should be removed from the allowlist so the main leak test
    goes back to checking `suggested_fix` for that pair too."""
    for rule_id, issue_type in sorted(_KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS):
        _, fix = finalize_student_facing_comment_and_fix(rule_id, issue_type, "", "")
        leaked = _RAW_ID_PATTERN.findall(fix)
        assert leaked, (
            f"{rule_id}/{issue_type} no longer leaks in suggested_fix ({fix!r}) — "
            "remove it from _KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS."
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
