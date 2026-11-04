"""Regression tests for the P014/P018 suggested_fix raw-notation leak fix.

Root cause: the raw catalog `remediation` field for P014 and P018 is a
developer cross-reference note packed with internal `P###`/`Q###` notation
(e.g. "APPROVAL PAGE (Q013, P038)", "P018A-C (Q049-Q051)"). No per-issue-type
`_ISSUE_REMEDIATION_OVERRIDES` entry existed for six (rule_id, issue_type)
pairs, so `_resolve_remediation()` fell all the way through to that raw
catalog text and surfaced it verbatim as the student-facing `suggested_fix`.

This was tracked as a documented, staleness-tested known gap
(`_KNOWN_PRE_EXISTING_SUGGESTED_FIX_LEAKS` in test_rule_registry_consistency.py,
now removed since the allowlist is empty) discovered by the 2026-07-16
issue-type-universe audit but deliberately left unfixed at the time.

The web UI was never affected (report_view.py's `_apply_named_heading_presentation`
and toc_list_student_preview.py's `_P018_SHORT_FIX` already rewrite these
pairs' suggested_fix before display), but the markdown export path
(report_outputs.py's `_finding_markdown_line` generic branch) calls
`resolve_suggested_fix_for_display` directly and showed the raw leak.

These tests exercise the real student-facing paths end to end, not just the
`_ISSUE_REMEDIATION_OVERRIDES` dict in isolation.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import finalize_student_facing_comment_and_fix
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view

_RAW_ID_PATTERN = re.compile(r"\b[PQ]\d{2,3}\b")

_P014_PAIRS = [
    "frontmatter_heading_layout_issue",
    "frontmatter_heading_not_centered",
]
_P018_PAIRS = [
    "misaligned_page_number_column",
    "missing_page_number",
    "inconsistent_leader_dots",
    "inconsistent_hierarchy_indent",
]


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_p014_suggested_fix_has_no_raw_notation_via_base_resolver() -> None:
    for issue_type in _P014_PAIRS:
        _, fix = finalize_student_facing_comment_and_fix("P014", issue_type, "", "")
        assert fix and fix.strip()
        assert not _RAW_ID_PATTERN.findall(fix), f"{issue_type}: {fix!r}"
        assert "Q013" not in fix
        assert "P038" not in fix


def test_p018_suggested_fix_has_no_raw_notation_via_base_resolver() -> None:
    for issue_type in _P018_PAIRS:
        _, fix = finalize_student_facing_comment_and_fix("P018", issue_type, "", "")
        assert fix and fix.strip()
        assert not _RAW_ID_PATTERN.findall(fix), f"{issue_type}: {fix!r}"
        assert "atomic public cards" not in fix
        assert "P018A" not in fix


def test_p014_suggested_fix_stays_specific_and_actionable() -> None:
    """The fix must still tell the student what to do, not just be non-empty."""
    _, layout_fix = finalize_student_facing_comment_and_fix(
        "P014", "frontmatter_heading_layout_issue", "", ""
    )
    _, centered_fix = finalize_student_facing_comment_and_fix(
        "P014", "frontmatter_heading_not_centered", "", ""
    )
    assert "bold" in layout_fix.lower()
    assert "capital" in layout_fix.lower()
    assert "center" in centered_fix.lower()
    # Distinct concerns (general layout vs. specifically off-center) keep distinct wording.
    assert layout_fix != centered_fix


def test_p018_suggested_fix_stays_specific_and_distinct_per_issue_type() -> None:
    fixes = {
        issue_type: finalize_student_facing_comment_and_fix("P018", issue_type, "", "")[1]
        for issue_type in _P018_PAIRS
    }
    assert "page number" in fixes["missing_page_number"].lower()
    assert "column" in fixes["misaligned_page_number_column"].lower()
    assert "leader" in fixes["inconsistent_leader_dots"].lower()
    assert "indent" in fixes["inconsistent_hierarchy_indent"].lower()
    # Each of the four sub-cases keeps its own wording rather than collapsing
    # onto one generic sentence.
    assert len(set(fixes.values())) == len(fixes)


def test_p014_markdown_export_has_no_raw_notation(tmp_path) -> None:
    findings = [
        AuditFinding(
            rule_id="P014",
            severity=Severity.WARNING,
            page=3,
            message="Named front-matter heading may violate layout/style heuristics.",
            details={
                "heading": "DEDICATION",
                "issue_type": "frontmatter_heading_layout_issue",
                "centered": "False",
                "near_top": "True",
                "bold": "True",
                "all_caps": "True",
            },
        ),
        AuditFinding(
            rule_id="P014",
            severity=Severity.WARNING,
            page=4,
            message="Named front-matter heading may violate layout/style heuristics.",
            details={
                "heading": "APPROVAL PAGE",
                "issue_type": "frontmatter_heading_not_centered",
                "centered": "False",
                "near_top": "True",
                "bold": "True",
                "all_caps": "True",
            },
        ),
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "What to check:" in text
    for line in text.splitlines():
        if "What to check:" not in line:
            continue
        fix_part = line.split("What to check:", 1)[1]
        assert not _RAW_ID_PATTERN.findall(fix_part), line
    assert "Q013" not in text
    assert "P038" not in text


def test_p018_markdown_export_has_no_raw_notation(tmp_path) -> None:
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=6,
            message="TOC/List entry may not match NJIT formatting.",
            details={"issue_type": issue_type},
        )
        for issue_type in _P018_PAIRS
    ]
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert "What to check:" in text
    for line in text.splitlines():
        if "What to check:" not in line:
            continue
        fix_part = line.split("What to check:", 1)[1]
        assert not _RAW_ID_PATTERN.findall(fix_part), line
    assert "atomic public cards" not in text
    assert "Q049" not in text


def test_p014_web_report_view_suggested_fix_has_no_raw_notation() -> None:
    findings = [
        AuditFinding(
            rule_id="P014",
            severity=Severity.WARNING,
            page=3,
            message="Named front-matter heading may violate layout/style heuristics.",
            details={
                "heading": "DEDICATION",
                "issue_type": "frontmatter_heading_layout_issue",
                "centered": "False",
                "near_top": "True",
                "bold": "True",
                "all_caps": "True",
            },
        )
    ]
    view = build_report_view(_payload(findings))
    card = next(f for f in view.findings if f.rule_id == "P014")
    assert card.suggested_fix
    assert not _RAW_ID_PATTERN.findall(card.suggested_fix)


def test_p018_web_report_view_suggested_fix_has_no_raw_notation() -> None:
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=6,
            message="TOC entry may not match NJIT formatting.",
            details={"issue_type": issue_type},
        )
        for issue_type in _P018_PAIRS
    ]
    view = build_report_view(_payload(findings))
    for card in view.findings:
        if card.rule_id != "P018":
            continue
        assert card.suggested_fix
        assert not _RAW_ID_PATTERN.findall(card.suggested_fix)
