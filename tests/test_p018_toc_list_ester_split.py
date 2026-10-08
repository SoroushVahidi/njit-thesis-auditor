"""Ester-aligned P018 TOC/LoT/LoF atomic public rule-reference split."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[1]

_P018_PUBLIC_CARDS = tuple(f"P018{letter}" for letter in "ABCDEFGHIJKLMNOPQRS")

_P018_SUPERSEDED_CARDS = (
    "P024A",
    "P024B",
    "P024C",
    "P032A",
    "P036A",
    "P036B",
    "P036C",
    "P042A",
    "P042B",
    "P046A",
    "P046B",
    "P048A",
    "P048B",
)

_P018_ESTER_QUESTIONS: dict[str, str] = {
    "P018A": (
        "In the Table of Contents, are all level-1 chapter titles displayed in all caps?"
    ),
    "P018B": (
        "In the Table of Contents, are all level-2 section titles displayed in title case?"
    ),
    "P018C": (
        "In the Table of Contents, are all level-3 section titles displayed in "
        "sentence case?"
    ),
    "P018D": (
        "Is each List of Tables and List of Figures entry connected to its page "
        "number by a consistent leader style?"
    ),
    "P018E": (
        "Is every wrapped level-1 Table of Contents entry single-spaced internally?"
    ),
    "P018F": (
        "Is every wrapped level-2 Table of Contents entry single-spaced internally?"
    ),
    "P018G": (
        "Is every wrapped level-3 Table of Contents entry single-spaced internally?"
    ),
    "P018H": (
        "Are level-2 and level-3 Table of Contents entries indented to show hierarchy?"
    ),
    "P018I": (
        "Is there visible double spacing between consecutive Table of Contents "
        "section-title entries?"
    ),
    "P018J": (
        "If only one appendix is listed in the Table of Contents, does it begin with "
        "'APPENDIX' followed by its title?"
    ),
    "P018K": (
        "If multiple appendices are listed in the Table of Contents, are they "
        "identified by letters?"
    ),
    "P018L": (
        "Is there visible double spacing between consecutive List of Tables entries?"
    ),
    "P018M": (
        "Are all table numbers in the List of Tables aligned vertically in one left "
        "column?"
    ),
    "P018N": (
        "Are all List of Tables page numbers aligned vertically in one right column?"
    ),
    "P018O": (
        "Is there visible double spacing between consecutive List of Figures entries?"
    ),
    "P018P": (
        "Are all figure numbers in the List of Figures aligned vertically in one left "
        "column?"
    ),
    "P018Q": (
        "Are all List of Figures page numbers aligned vertically in one right column?"
    ),
    "P018R": (
        "When a Table of Contents title runs for more than one line, does the "
        "second line align with the text of the first line, not the number?"
    ),
    "P018S": (
        "In the Table of Contents, List of Tables, and List of Figures, do leader "
        "dots begin right after the title (after its final line), with at most "
        "one space?"
    ),
}


def _make_app(tmp_path: Path) -> tuple[TestClient, object]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, object]:
    return _make_app(tmp_path)


def test_broad_p018_is_not_public(client: tuple[TestClient, object]) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    visible_ids = {rule["id"] for rule in catalog["student_rules"]}
    assert "P018" not in visible_ids
    assert "P039" not in visible_ids


def test_disabled_inter_entry_spacing_cards_disclose_manual_review(
    client: tuple[TestClient, object],
) -> None:
    web_client, wa = client
    catalog = {
        rule["id"]: rule for rule in wa._build_rule_catalog()["student_rules"]
    }
    manual_ids = {
        rule_id
        for rule_id, rule in catalog.items()
        if rule.get("manual_review_only")
    }
    assert manual_ids == {"P018I", "P018L", "P018O"}
    body = web_client.get("/rules").text
    for rule_id in manual_ids:
        assert f'id="{rule_id}"' in body
    assert body.count("Manual review — no automated finding") == 3


def test_p018_atomic_cards_are_public(client: tuple[TestClient, object]) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    visible_ids = {rule["id"] for rule in catalog["student_rules"]}
    assert set(_P018_PUBLIC_CARDS) <= visible_ids


def test_superseded_delegated_cards_are_hidden(client: tuple[TestClient, object]) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    visible_ids = {rule["id"] for rule in catalog["student_rules"]}
    assert not set(_P018_SUPERSEDED_CARDS) & visible_ids
    assert {"P024D", "P024E", "P032B", "P032C"} <= visible_ids


@pytest.mark.parametrize("card_id,question", list(_P018_ESTER_QUESTIONS.items()))
def test_p018_split_card_question_matches_ester(
    client: tuple[TestClient, object],
    card_id: str,
    question: str,
) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    by_id = {rule["id"]: rule for rule in catalog["student_rules"]}
    assert by_id[card_id]["title"] == question


def test_p018_split_cards_have_single_remediation(
    client: tuple[TestClient, object],
) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    by_id = {rule["id"]: rule for rule in catalog["student_rules"]}
    for card_id in _P018_PUBLIC_CARDS:
        fix = by_id[card_id]["how_to_correct"]
        assert fix.strip()
        lower = fix.lower()
        assert "table of contents, list of tables, and list of figures" not in lower
        assert "likely alignment inconsistencies" not in lower


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "details", "source_q", "expected"),
    [
        ("P024", "toc_level_capitalization", {"entry_level": "1"}, "Q049", "P018A"),
        ("P024", "toc_level_capitalization", {"entry_level": "2"}, "Q050", "P018B"),
        ("P024", "toc_level_capitalization", {"entry_level": "3"}, "Q051", "P018C"),
        ("P018", "inconsistent_leader_dots", {}, "Q052", "P018D"),
        ("P032", "wrapped_entry_internal_spacing", {"entry_kind": "toc_level_1"}, "", "P018E"),
        ("P032", "wrapped_entry_internal_spacing", {"entry_kind": "toc_level_2"}, "", "P018F"),
        ("P032", "wrapped_entry_internal_spacing", {"entry_kind": "toc_level_3"}, "", "P018G"),
        ("P039", "toc_l2_not_indented_relative_to_l1", {}, "Q056", "P018H"),
        ("P036", "toc_inter_entry_spacing_too_tight", {}, "Q057", "P018I"),
        ("P042", "single_appendix_missing_title", {}, "Q058", "P018J"),
        ("P042", "multiple_appendix_missing_letter", {}, "Q059", "P018K"),
        ("P036", "lot_inter_entry_spacing_too_tight", {}, "Q067", "P018L"),
        ("P046", "lot_entry_number_column_misaligned", {}, "Q068", "P018M"),
        ("P048", "lot_page_number_column_misaligned", {}, "Q069", "P018N"),
        ("P036", "lof_inter_entry_spacing_too_tight", {}, "Q077", "P018O"),
        ("P046", "lof_entry_number_column_misaligned", {}, "Q078", "P018P"),
        ("P048", "lof_page_number_column_misaligned", {}, "Q079", "P018Q"),
        ("P018", "wrapped_title_continuation_misaligned", {}, "", "P018R"),
        ("P018", "title_to_leader_gap_too_wide", {"page_type": "list_of_figures"}, "", "P018S"),
        ("P018", "leader_dots_before_final_title_line", {}, "", "P018S"),
    ],
)
def test_backend_findings_map_to_p018_split_cards(
    client: tuple[TestClient, object],
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    source_q: str,
    expected: str,
) -> None:
    _, wa = client
    assert (
        wa._public_rule_reference_id(
            rule_id,
            issue_type=issue_type,
            source_q_rule_id=source_q,
            details=details,
        )
        == expected
    )


def test_p018d_leader_mapping_does_not_use_capitalization_card(
    client: tuple[TestClient, object],
) -> None:
    _, wa = client
    assert (
        wa._public_rule_reference_id(
            "P018",
            issue_type="inconsistent_leader_dots",
            source_q_rule_id="Q052",
        )
        == "P018D"
    )
    assert (
        wa._public_rule_reference_id(
            "P024",
            issue_type="toc_level_capitalization",
            details={"entry_level": "1"},
        )
        != "P018D"
    )


def test_p018_leader_warning_is_atomic() -> None:
    from njit_auditor.toc_list_student_preview import (
        p018_short_likely_problem,
        p018_short_suggested_fix,
    )

    comment = p018_short_likely_problem("inconsistent_leader_dots").lower()
    fix = p018_short_suggested_fix("inconsistent_leader_dots").lower()
    assert "capital" not in comment
    assert "capital" not in fix
    assert "leader" in comment or "leader-dot" in comment


def test_p018h_hierarchy_warning_does_not_mention_leaders() -> None:
    from njit_auditor.toc_list_student_preview import p018_short_likely_problem

    comment = p018_short_likely_problem("inconsistent_hierarchy_indent").lower()
    assert "leader" not in comment
    assert "indent" in comment


def test_p018i_spacing_warning_does_not_mention_capitalization() -> None:
    from njit_auditor.polished_comments import build_polished_comment

    comment = build_polished_comment(
        rule_id="P036",
        issue_type="toc_inter_entry_spacing_too_tight",
        page=12,
        details={"section_type": "table_of_contents", "entry_pair_index": "2"},
    ).lower()
    assert "capital" not in comment
    assert "title case" not in comment


def test_lot_alignment_warning_does_not_mention_lof() -> None:
    from njit_auditor.report_view import FindingView, _apply_lot_lof_alignment_presentation

    finding = FindingView(
        rule_id="P046",
        category="list_of_tables_figures_toc",
        page=8,
        severity="WARNING",
        issue_type="lot_entry_number_column_misaligned",
        polished_comment="placeholder",
        suggested_fix="placeholder",
    )
    updated, keep = _apply_lot_lof_alignment_presentation(
        finding,
        {"section_type": "list_of_tables", "affected_entry_count": "4"},
    )
    assert keep
    combined = (updated.polished_comment + " " + updated.suggested_fix).lower()
    assert "list of figures" not in combined
    assert "figure number" not in combined


def test_rules_page_renders_p018_split_cards_not_broad_p018(
    client: tuple[TestClient, object],
) -> None:
    c, _ = client
    body = c.get("/rules").text
    assert 'data-rule-id="P018A"' in body
    assert 'data-rule-id="P018Q"' in body
    assert 'data-rule-id="P018"' not in body
    assert "likely alignment inconsistencies" not in body.lower()


_ESTER_20260923_ISSUE_TYPES = (
    ("wrapped_title_continuation_misaligned", "P018R"),
    ("title_to_leader_gap_too_wide", "P018S"),
    ("leader_dots_before_final_title_line", "P018S"),
)


@pytest.mark.parametrize(("issue_type", "card_id"), _ESTER_20260923_ISSUE_TYPES)
def test_ester_20260923_findings_link_to_public_cards_without_internal_ids(
    client: tuple[TestClient, object], issue_type: str, card_id: str
) -> None:
    import re

    from njit_auditor.polished_comments import build_polished_comment
    from njit_auditor.toc_list_student_preview import (
        p018_short_likely_problem,
        p018_short_suggested_fix,
    )

    c, wa = client
    assert wa._public_rule_reference_id("P018", issue_type=issue_type) == card_id
    assert wa.public_display_rule_id(card_id) == "R" + card_id[1:]
    catalog = {rule["id"]: rule for rule in wa._build_rule_catalog()["student_rules"]}
    card = catalog[card_id]
    texts = [
        card["title"],
        card["how_to_correct"],
        build_polished_comment(rule_id="P018", issue_type=issue_type, page=9, details={}),
        p018_short_likely_problem(issue_type),
        p018_short_suggested_fix(issue_type),
    ]
    for text in texts:
        assert text.strip()
        assert not re.search(r"\b[PQ]\d{3}", text), text
        assert "This automated check found a possible" not in text
    assert f'data-rule-id="{card_id}"' in c.get("/rules").text


def test_catalog_p018_card_range_matches_implemented_cards(
    client: tuple[TestClient, object],
) -> None:
    """The P018 catalog entry names its public card range; keep it in sync with
    the implemented specs so the range cannot silently drift again."""
    import json
    import re

    _, wa = client
    card_ids = [spec["id"] for spec in wa._P018_PUBLIC_CARD_SPECS]
    assert card_ids == list(_P018_PUBLIC_CARDS)
    last = card_ids[-1]
    catalog = json.loads(
        (_REPO_ROOT / "data/processed/rules/project_added_rules.json").read_text(
            encoding="utf-8"
        )
    )
    rules = catalog if isinstance(catalog, list) else catalog["rules"]
    p018 = next(rule for rule in rules if rule["id"] == "P018")
    for field in ("rule_definition", "remediation", "notes"):
        ranges = re.findall(r"P018A[–-]P018([A-Z])", p018[field])
        assert ranges, field
        assert all(f"P018{letter}" == last for letter in ranges), (field, ranges)
    rule_ids = sorted(rule["id"] for rule in rules if re.fullmatch(r"P\d{3}", rule["id"]))
    assert rule_ids[-1] == "P086"
