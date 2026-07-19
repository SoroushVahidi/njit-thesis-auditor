"""Pattern-level regression tests for njit_auditor.rule_source_scan.

Each test feeds a small, self-contained synthetic Python source snippet
(never real detector source, so these are decoupled from future rule
refactors) through `ast.parse` and the module's internal `_ModuleResolver`,
asserting the exact (rule_id, issue_type) pairs it discovers. This exercises
every code pattern the resolver's docstring claims to support, one at a
time, plus a couple of negative cases proving it does not guess when it
cannot prove a value.

Also covers the two other static ground-truth sources this module exposes:
`source_pipeline_issue_type_pairs()` (the TeX/"source" pipeline's separate
rule_id-keyed dispatch) and `full_active_issue_type_universe()` (the union,
including the one documented non-detector exception).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from njit_auditor.rule_source_scan import (
    KNOWN_NON_DETECTOR_ISSUE_TYPES,
    _ModuleResolver,
    detector_emitted_pairs_by_static_scan,
    full_active_issue_type_universe,
    source_pipeline_issue_type_pairs,
)

RULES_DIR = Path(__file__).resolve().parents[1] / "src" / "njit_auditor" / "rules"


def _pairs_for(source: str) -> set[tuple[str, str]]:
    tree = ast.parse(source)
    return _ModuleResolver(tree).emitted_pairs()


def test_audit_finding_messages_do_not_expose_source_q_rule_ids() -> None:
    """Student-facing raw detector messages should not expose internal Q IDs.

    Detectors may still keep source_q_rule_id/source_q_rule_ids in details for
    traceability and rule mapping; this only scans the message= argument passed
    to AuditFinding.
    """
    offenders: list[str] = []
    for path in sorted(RULES_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg != "message":
                    continue
                segment = ast.get_source_segment(source, keyword.value) or ""
                if re.search(r"Q0\d{2}|source_q_rule", segment):
                    offenders.append(f"{path.relative_to(RULES_DIR)}:{node.lineno}")

    assert offenders == []


def test_direct_literal_in_dict_literal() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

def check() -> list[AuditFinding]:
    return [AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": "some_literal_issue"},
    )]
"""
    assert _pairs_for(source) == {("P100", "some_literal_issue")}


def test_ternary_literal() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

def check(flag) -> list[AuditFinding]:
    issue = "issue_a" if flag else "issue_b"
    return [AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": issue},
    )]
"""
    assert _pairs_for(source) == {("P100", "issue_a"), ("P100", "issue_b")}


def test_module_dict_subscript_lookup() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

_MAP = {"a": "issue_for_a", "b": "issue_for_b"}

def check(key) -> list[AuditFinding]:
    return [AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": _MAP[key]},
    )]
"""
    assert _pairs_for(source) == {("P100", "issue_for_a"), ("P100", "issue_for_b")}


def test_module_dict_get_lookup_single_hop_tuple_unpack() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

_MAP = {"a": ("issue_for_a", "Q001"), "b": ("issue_for_b", "Q002")}

def check(key) -> list[AuditFinding]:
    issue_type, q_rule = _MAP.get(key)
    return [AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": issue_type, "source_q_rule_id": q_rule},
    )]
"""
    assert _pairs_for(source) == {("P100", "issue_for_a"), ("P100", "issue_for_b")}


def test_module_dict_lookup_through_intermediate_variable() -> None:
    """`config = _MAP.get(key); issue_type, q = config` — the two-hop case
    that motivated the fixed-point resolution in the first place (found in
    pdf_lot_lof_page_number_ordering.py / P057)."""
    source = """
from njit_auditor.models import AuditFinding, Severity

_MAP = {"a": ("issue_for_a", "Q001"), "b": ("issue_for_b", "Q002")}

def check(key) -> list[AuditFinding]:
    config = _MAP.get(key)
    issue_type, q_rule = config
    return [AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": issue_type, "source_q_rule_id": q_rule},
    )]
"""
    assert _pairs_for(source) == {("P100", "issue_for_a"), ("P100", "issue_for_b")}


def test_for_loop_over_module_dict_items_nested_unpack() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

_SECTION_CONFIG = {
    "s1": ("issue_s1", "Q001"),
    "s2": ("issue_s2", "Q002"),
}

def check() -> list[AuditFinding]:
    findings = []
    for section, (issue_type, q_rule) in _SECTION_CONFIG.items():
        findings.append(AuditFinding(
            rule_id="P100",
            severity=Severity.WARNING,
            details={"issue_type": issue_type, "source_q_rule_id": q_rule},
        ))
    return findings
"""
    assert _pairs_for(source) == {("P100", "issue_s1"), ("P100", "issue_s2")}


def test_for_loop_over_inline_list_of_tuples() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

def check() -> list[AuditFinding]:
    findings = []
    for level, pattern in [(2, "p2"), (3, "p3")]:
        findings.append(AuditFinding(
            rule_id="P100",
            severity=Severity.WARNING,
            details={"issue_type": f"level{level}_issue"},
        ))
    return findings
"""
    assert _pairs_for(source) == {("P100", "level2_issue"), ("P100", "level3_issue")}


def test_fstring_cartesian_product_of_two_slots() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

def check() -> list[AuditFinding]:
    findings = []
    for level in (2, 3):
        for kind in ("alpha", "beta"):
            findings.append(AuditFinding(
                rule_id="P100",
                severity=Severity.WARNING,
                details={"issue_type": f"level{level}_{kind}_issue"},
            ))
    return findings
"""
    assert _pairs_for(source) == {
        ("P100", "level2_alpha_issue"),
        ("P100", "level2_beta_issue"),
        ("P100", "level3_alpha_issue"),
        ("P100", "level3_beta_issue"),
    }


def test_cross_function_call_site_literal_argument() -> None:
    """A helper function takes `issue_type` as a parameter; the literal only
    appears at its call site(s) — the dominant pattern behind most of the
    "no-details-dict-literal" gaps this module was built to close."""
    source = """
from njit_auditor.models import AuditFinding, Severity

def _make_finding(*, issue_type: str) -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": issue_type},
    )

def check_a() -> AuditFinding:
    return _make_finding(issue_type="issue_from_a")

def check_b() -> AuditFinding:
    return _make_finding(issue_type="issue_from_b")
"""
    assert _pairs_for(source) == {("P100", "issue_from_a"), ("P100", "issue_from_b")}


def test_cross_function_multihop_local_variable_passed_as_argument() -> None:
    """The caller resolves a local variable via a module-dict lookup, then
    passes THAT variable (not a literal) to the callee's parameter — requires
    the fixed point to run more than one iteration."""
    source = """
from njit_auditor.models import AuditFinding, Severity

_MAP = {"a": ("issue_for_a", "Q001"), "b": ("issue_for_b", "Q002")}

def _make_finding(*, issue_type: str) -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": issue_type},
    )

def check(key) -> AuditFinding:
    resolved_issue, q_rule = _MAP.get(key)
    return _make_finding(issue_type=resolved_issue)
"""
    assert _pairs_for(source) == {("P100", "issue_for_a"), ("P100", "issue_for_b")}


def test_dict_literal_assigned_to_local_variable() -> None:
    """`details = {...}` then `details=details` at the AuditFinding call —
    the single most common "no-details-dict-literal" shape found in the
    codebase (P011, P013, P023, P027, and many others)."""
    source = """
from njit_auditor.models import AuditFinding, Severity

def check() -> AuditFinding:
    details: dict[str, str] = {"issue_type": "built_as_local_var", "page": "1"}
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details=details,
    )
"""
    assert _pairs_for(source) == {("P100", "built_as_local_var")}


def test_wrapped_helper_call_with_dict_literal_argument() -> None:
    """`details=_helper({...}, extra_arg)` — a decorator-style helper that
    takes a dict literal and augments it (found in pdf_toc_alignment.py)."""
    source = """
from njit_auditor.models import AuditFinding, Severity

def _augment(base: dict, extra) -> dict:
    base["extra"] = extra
    return base

def check() -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details=_augment({"issue_type": "wrapped_issue"}, "x"),
    )
"""
    assert _pairs_for(source) == {("P100", "wrapped_issue")}


def test_helper_function_builds_and_returns_dict_internally() -> None:
    """`details=_helper(issue_type=issue_type)` where `_helper` builds and
    RETURNS the dict literal internally (found in
    pdf_approval_page_committee_blocks.py) — the deepest indirection level
    this resolver supports."""
    source = """
from njit_auditor.models import AuditFinding, Severity

def _base_details(*, issue_type: str) -> dict:
    return {"issue_type": issue_type, "confidence": "medium"}

def _make_finding(*, issue_type: str) -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details=_base_details(issue_type=issue_type),
    )

def check() -> AuditFinding:
    return _make_finding(issue_type="deeply_wrapped_issue")
"""
    assert _pairs_for(source) == {("P100", "deeply_wrapped_issue")}


def test_module_level_plain_string_constant() -> None:
    source = """
from njit_auditor.models import AuditFinding, Severity

_ISSUE_TYPE = "single_constant_issue"

def check() -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": _ISSUE_TYPE},
    )
"""
    assert _pairs_for(source) == {("P100", "single_constant_issue")}


def test_no_details_arg_yields_no_pairs_not_a_crash() -> None:
    """A `Severity.PASS` "clean" finding with no `details=` at all must not
    crash the scanner and must not fabricate a pair."""
    source = """
from njit_auditor.models import AuditFinding, Severity

def check() -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.PASS,
        message="No issues found.",
    )
"""
    assert _pairs_for(source) == set()


def test_unresolvable_issue_type_yields_no_pair_not_a_guess() -> None:
    """An issue_type built from something this resolver cannot prove (here,
    an arbitrary function call) must be silently omitted, never guessed at,
    and must not raise."""
    source = """
from njit_auditor.models import AuditFinding, Severity

def _dynamic_value():
    return "whatever"

def check() -> AuditFinding:
    return AuditFinding(
        rule_id="P100",
        severity=Severity.WARNING,
        details={"issue_type": _dynamic_value()},
    )
"""
    assert _pairs_for(source) == set()


def test_source_pipeline_issue_type_pairs_matches_expected_tex_dispatch() -> None:
    """Integration-style check against the real report_outputs.py: the
    TeX/source pipeline's rule_id -> issue_type dispatch is exactly P001-P010,
    one issue type each (see derive_source_issue_type)."""
    pairs = source_pipeline_issue_type_pairs()
    expected = {
        ("P001", "risky_command"),
        ("P002", "duplicate_label"),
        ("P003", "invalid_label"),
        ("P004", "dangling_reference"),
        ("P005", "missing_caption"),
        ("P006", "missing_label"),
        ("P007", "caption_punctuation"),
        ("P008", "abstract_structure"),
        ("P009", "chktex_warning"),
        ("P010", "lacheck_warning"),
    }
    assert pairs == expected


def test_full_active_issue_type_universe_includes_all_three_sources() -> None:
    universe = full_active_issue_type_universe()
    scan = detector_emitted_pairs_by_static_scan()
    tex = source_pipeline_issue_type_pairs()
    assert scan <= universe
    assert tex <= universe
    assert set(KNOWN_NON_DETECTOR_ISSUE_TYPES) <= universe
    assert universe == scan | tex | set(KNOWN_NON_DETECTOR_ISSUE_TYPES)


def test_real_scan_discovers_p014_pairs_via_cross_function_and_module_dict() -> None:
    """Integration check against the real rules/ tree: P014's two issue
    types are only discoverable via the cross-function call-site pattern
    (they're set via a helper's `issue_type` parameter one level removed
    from the literal), and were the original motivation for this module."""
    pairs = detector_emitted_pairs_by_static_scan()
    assert ("P014", "frontmatter_heading_layout_issue") in pairs
    assert ("P014", "frontmatter_heading_not_centered") in pairs


def test_real_scan_discovers_p057_pairs_via_two_hop_dict_lookup() -> None:
    """Integration check: P057's two issue types require resolving through
    an intermediate `config = _SECTION_CONFIG.get(...)` variable before the
    tuple-unpack — the two-hop pattern."""
    pairs = detector_emitted_pairs_by_static_scan()
    assert ("P057", "lot_page_numbers_not_nondecreasing") in pairs
    assert ("P057", "lof_page_numbers_not_nondecreasing") in pairs
