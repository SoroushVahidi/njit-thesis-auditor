"""Public /rules ownership for P018 page-number issue types (2026-10-06 audit).

Authority: Ester's Q052 ("Every TOC entry must connect to a right-aligned
page number using one consistent leader style") restates the NJIT guideline's
Table of Contents bullet ("Page numbers should be right-aligned ... Use
leaders ... to connect the section title to the page number"). Its public
Table of Contents card is P075 (R075). Ester gave List of Tables and List of
Figures page-number alignment their own rows (Q069 -> P018N, Q079 -> P018Q)
but no page-number presence row, so a list-page ``missing_page_number`` is
deliberately left without a card. ``unexpected_indent_on_continuation_line``
(P015) is likewise left unmapped: neither R015 card describes it and every
Ester verdict on it so far is a false positive.
"""

from __future__ import annotations

import importlib
import io
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def _ref(wa: Any, rule_id: str, issue_type: str, **details: str) -> str:
    return str(wa._public_rule_reference_id(rule_id, issue_type=issue_type, details=details))


@pytest.mark.parametrize(
    ("issue_type", "details", "expected"),
    [
        ("misaligned_page_number_column", {"page_type": "table_of_contents"}, "P075"),
        ("missing_page_number", {"page_type": "table_of_contents"}, "P075"),
        # P018 emits ``page_type``; the list routing used to read only
        # ``section_type`` and so never fired for real P018 findings.
        ("misaligned_page_number_column", {"page_type": "list_of_tables"}, "P018N"),
        ("misaligned_page_number_column", {"page_type": "list_of_figures"}, "P018Q"),
        ("misaligned_page_number_column", {"section_type": "list_of_tables"}, "P018N"),
        ("misaligned_page_number_column", {"section_type": "list_of_figures"}, "P018Q"),
        # No Ester/NJIT presence rule for list pages: deliberately unmapped.
        ("missing_page_number", {"page_type": "list_of_tables"}, ""),
        ("missing_page_number", {"page_type": "list_of_figures"}, ""),
        # Unknown page kind: no guess.
        ("misaligned_page_number_column", {}, ""),
        ("missing_page_number", {}, ""),
    ],
)
def test_p018_page_number_findings_resolve_to_owner_card(
    client: tuple[TestClient, Any], issue_type: str, details: dict[str, str], expected: str
) -> None:
    _, wa = client
    assert _ref(wa, "P018", issue_type, **details) == expected


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "details", "expected"),
    [
        ("P018", "inconsistent_leader_dots", {"page_type": "list_of_figures"}, "P018D"),
        ("P018", "inconsistent_hierarchy_indent", {"page_type": "table_of_contents"}, "P018H"),
        (
            "P018",
            "wrapped_title_continuation_misaligned",
            {"page_type": "table_of_contents"},
            "P018R",
        ),
        ("P018", "title_to_leader_gap_too_wide", {"page_type": "table_of_contents"}, "P018S"),
        ("P048", "lot_page_number_column_misaligned", {"section_type": "list_of_tables"}, "P018N"),
        ("P048", "lof_page_number_column_misaligned", {"section_type": "list_of_figures"}, "P018Q"),
        ("P075", "toc_mixed_leader_styles", {}, "P075"),
        ("P075", "toc_missing_leader_style", {}, "P075"),
        # The page-number rule's own missing_page_number stays with R019.
        ("P019", "missing_page_number", {"page_type": "table_of_contents"}, "P019"),
        ("P032", "wrapped_entry_internal_spacing", {"page_type": "list_of_tables"}, "P018E"),
        ("P015", "unexpected_opening_indent", {}, "P015A"),
        ("P015", "missing_later_indent", {}, "P015B"),
        ("P015", "unexpected_indent_on_continuation_line", {}, ""),
    ],
)
def test_neighbouring_issue_types_keep_their_owner(
    client: tuple[TestClient, Any],
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    expected: str,
) -> None:
    _, wa = client
    assert _ref(wa, rule_id, issue_type, **details) == expected


def test_rules_catalog_exposes_page_number_ownership(client: tuple[TestClient, Any]) -> None:
    _, wa = client
    catalog = {rule["id"]: rule for rule in wa._build_rule_catalog()["student_rules"]}

    assert "misaligned_page_number_column" in catalog["P018N"]["issue_types"]
    assert "misaligned_page_number_column" in catalog["P018Q"]["issue_types"]
    owners = {
        rule_id
        for rule_id, rule in catalog.items()
        if "misaligned_page_number_column" in (rule.get("issue_types") or ())
    }
    assert owners == {"P018N", "P018Q"}
    assert not any(
        "missing_page_number" in (rule.get("issue_types") or ()) for rule in catalog.values()
    )

    p075 = catalog["P075"]
    what = p075["what_it_checks"].lower()
    assert "right-aligned page number" in what
    assert "missing their page number" in what
    assert "right-aligned column" in what
    assert "right-align" in p075["how_to_correct"].lower()
    # Hidden parents stay hidden.
    assert "P018" not in catalog
    assert "P015" not in catalog


def test_rules_page_renders_p075_with_page_number_scope(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    body = c.get("/rules").text
    assert 'data-rule-id="P075"' in body
    assert "entries missing their page number" in body
    assert 'data-rule-id="P018"' not in body


@pytest.mark.parametrize("issue_type", ["misaligned_page_number_column", "missing_page_number"])
def test_student_wording_matches_page_number_issue(issue_type: str) -> None:
    from njit_auditor.issue_type_explanations import explain_issue_type
    from njit_auditor.polished_comments import build_polished_comment
    from njit_auditor.toc_list_student_preview import (
        p018_short_likely_problem,
        p018_short_suggested_fix,
    )

    texts = [
        p018_short_likely_problem(issue_type),
        p018_short_suggested_fix(issue_type),
        build_polished_comment(
            rule_id="P018",
            issue_type=issue_type,
            page=10,
            details={"page_type": "table_of_contents"},
        ),
        explain_issue_type("P018", issue_type, {"page_type": "table_of_contents"}),
    ]
    for text in texts:
        lower = text.lower().replace("page-number", "page number")
        assert "page number" in lower
        assert "leader" not in lower
        assert "P018" not in text and "P075" not in text


def test_job_page_links_toc_page_number_finding_to_r075(
    client: tuple[TestClient, Any],
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    def _fake_dispatch(pdf_path: Path, **kwargs: Any) -> Any:
        from njit_auditor.audit_runner import UploadedAuditResult
        from njit_auditor.upload_handling import UploadKind

        finding = AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=10,
            message="TOC/List page-number column appears misaligned across multiple entries.",
            details={
                "issue_type": "misaligned_page_number_column",
                "page_type": "table_of_contents",
                "affected_entry_count": "1",
                "worst_delta_pt": "21.2",
                "confidence": "high",
            },
        )
        return UploadedAuditResult(
            upload_kind=UploadKind.PDF, audit_type="pdf", findings=[finding]
        )

    c, wa = client
    with patch.object(wa, "run_audit_for_uploaded_file", _fake_dispatch):
        post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=True,
        )
    assert "/audits/" in str(post.url)
    html = post.content.decode()
    assert 'href="/rules#P075"' in html
    assert 'aria-label="TABLE OF CONTENTS: see rule reference">TABLE OF CONTENTS</a>' in html
    assert 'aria-label="R075: see rule reference">R075</a>' not in html
    assert ">P075<" not in html


# --- 2026-10-06 canonical P018/P075 sync -------------------------------------

_RULES_JSON = Path(__file__).resolve().parents[1] / "data/processed/rules/project_added_rules.json"


def _canonical(rule_id: str) -> dict[str, Any]:
    import json

    rules = json.loads(_RULES_JSON.read_text(encoding="utf-8"))
    return next(rule for rule in rules if isinstance(rule, dict) and rule.get("id") == rule_id)


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "source_q", "details", "expected"),
    [
        # A rule with its own public card keeps it even when it cites a Q row
        # shared with a P018 card.
        ("P075", "toc_mixed_leader_styles", "Q052", {}, "P075"),
        ("P075", "toc_missing_leader_style", "Q052", {}, "P075"),
        ("P054", "toc_entry_has_terminal_period", "Q050", {}, "P054"),
        ("P063", "body_appendix_heading_label", "Q058", {}, "P063"),
        ("P063", "body_appendix_heading_label", "Q059", {}, "P063"),
        # Context-specific page-number routing outranks a Q hint.
        ("P018", "missing_page_number", "Q052", {"page_type": "table_of_contents"}, "P075"),
        (
            "P018",
            "misaligned_page_number_column",
            "Q052",
            {"page_type": "table_of_contents"},
            "P075",
        ),
        ("P018", "missing_page_number", "Q052", {"page_type": "list_of_figures"}, ""),
        # The P018 family keeps its Q routing.
        ("P018", "inconsistent_leader_dots", "Q052", {"page_type": "list_of_tables"}, "P018D"),
        ("P024", "toc_level_capitalization", "Q049", {"entry_level": "1"}, "P018A"),
        ("P039", "toc_l2_not_indented_relative_to_l1", "Q056", {}, "P018H"),
        ("P042", "single_appendix_missing_title", "Q058", {}, "P018J"),
        ("P042", "multiple_appendix_missing_letter", "Q059", {}, "P018K"),
        ("P046", "lot_entry_number_column_misaligned", "Q068", {}, "P018M"),
        ("P048", "lot_page_number_column_misaligned", "Q069", {}, "P018N"),
        ("P048", "lof_page_number_column_misaligned", "Q079", {}, "P018Q"),
        ("P036", "toc_inter_entry_spacing_too_tight", "Q057", {}, "P018I"),
    ],
)
def test_source_q_hint_never_overrides_specific_owner(
    client: tuple[TestClient, Any],
    rule_id: str,
    issue_type: str,
    source_q: str,
    details: dict[str, str],
    expected: str,
) -> None:
    _, wa = client
    assert (
        wa._public_rule_reference_id(
            rule_id, issue_type=issue_type, source_q_rule_id=source_q, details=details
        )
        == expected
    )


def test_p075_canonical_text_matches_q052_toc_scope() -> None:
    p075 = _canonical("P075")
    definition = p075["rule_definition"].lower()
    assert "every toc entry must connect to a right-aligned page number" in definition
    assert "one consistent leader style" in definition
    assert "missing their page number" in definition
    assert "right-aligned column" in definition
    # Remediation stays Ester's Q052 wording ("1d" in her P018 feedback).
    remediation = p075["remediation"].lower()
    assert remediation.startswith(
        "right-align page numbers and use one consistent leader style (dots or hyphens)"
    )
    assert "leader style" in remediation
    assert "table of contents" in remediation
    for text in (definition, remediation):
        assert "list of tables" not in text and "list of figures" not in text
    # issue_types lists only the issue types P075's own detector emits.
    assert p075["issue_types"] == ["toc_mixed_leader_styles", "toc_missing_leader_style"]
    assert p075["source_q_rule_ids"] == ["Q052"]


def test_p018_canonical_metadata_documents_page_number_ownership() -> None:
    p018 = _canonical("P018")
    remediation = p018["remediation"]
    assert (
        "Table of Contents leader style, page-number column and missing page numbers: "
        "P075 (Q052)" in remediation
    )
    assert "List of Tables/List of Figures leaders: P018D (Q052)" in remediation
    assert "maps to P018N/P018Q" in remediation
    assert "missing_page_number has no public card" in remediation
    assert "no NJIT or Ester rule covers page-number presence on list pages" in remediation
    notes = p018["notes"]
    assert "intentionally unmapped pending authority" in notes
    assert "link to P075" in notes


def test_p075_public_card_comes_from_canonical_json_without_override(
    client: tuple[TestClient, Any],
) -> None:
    from njit_auditor.report_outputs import _RULE_TEXT_OVERRIDES

    _, wa = client
    assert "P075" not in _RULE_TEXT_OVERRIDES
    card = {rule["id"]: rule for rule in wa._build_rule_catalog()["student_rules"]}["P075"]
    p075 = _canonical("P075")
    assert card["what_it_checks"] == p075["rule_definition"]
    assert card["how_to_correct"] == p075["remediation"]
    assert card["title"] == p075["question"]
