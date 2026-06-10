import json
from collections import Counter
from pathlib import Path
from typing import Any

from njit_auditor.rule_loader import load_rule_file


def _load_json(path: str) -> list[dict[str, object]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_manifest() -> dict[str, Any]:
    return json.loads(
        Path("data/processed/evaluation_data_manifest.json").read_text(
            encoding="utf-8"
        )
    )


def test_inventory_and_project_rule_files_exist() -> None:
    assert Path("data/processed/rules/njit_rule_inventory.json").exists()
    assert Path("data/processed/rules/project_added_rules.json").exists()


def test_all_ester_rules_represented_in_inventory() -> None:
    inventory = _load_json("data/processed/rules/njit_rule_inventory.json")
    assert len(inventory) == 79
    ids = {str(item["id"]) for item in inventory}
    expected = {f"Q{i:03d}" for i in range(1, 80)}
    assert ids == expected


def test_njit_inventory_implementation_status_counts() -> None:
    """Guard documented Q-rule inventory counts against silent drift."""
    inventory = _load_json("data/processed/rules/njit_rule_inventory.json")
    status = Counter(str(item.get("implementation_status")) for item in inventory)
    assert status["implemented"] == 2
    assert status["partially_implemented"] == 60
    assert status["not_implemented"] == 17
    manual_only = sum(1 for item in inventory if item.get("checkability") == "manual")
    assert manual_only == 9
    assert manual_only + 8 == status["not_implemented"]


def test_q004_q005_q006_mappings() -> None:
    inventory = _load_json("data/processed/rules/njit_rule_inventory.json")
    by_id = {str(item["id"]): item for item in inventory}

    q004 = by_id["Q004"]
    assert q004["phase"] == "tex_source"
    assert q004["implementation_module"] == "njit_auditor.rules.latex_abstract"

    q005 = by_id["Q005"]
    assert q005["phase"] == "tex_source"
    assert q005["implementation_module"] == "njit_auditor.rules.latex_abstract"

    q006 = by_id["Q006"]
    assert q006["phase"] == "tex_source"
    assert q006["implementation_module"] == "njit_auditor.rules.latex_metadata"


def test_q001_q052_q007_classifications() -> None:
    inventory = _load_json("data/processed/rules/njit_rule_inventory.json")
    by_id = {str(item["id"]): item for item in inventory}
    assert by_id["Q001"]["phase"] == "pdf_layout"
    assert by_id["Q052"]["phase"] in {"pdf_layout", "mixed"}
    assert by_id["Q007"]["phase"] in {"manual_review", "mixed"}


def test_project_added_rules_implemented() -> None:
    project_rules = _load_json("data/processed/rules/project_added_rules.json")
    assert project_rules
    assert len(project_rules) == 81
    by_id = {str(item["id"]): item for item in project_rules}
    assert by_id["P028"]["phase"] == "pdf_layout"
    assert (
        by_id["P028"]["implementation_module"]
        == "njit_auditor.rules.pdf_page_numbering_regime"
    )
    assert by_id["P027"]["phase"] == "pdf_layout"
    assert (
        by_id["P027"]["implementation_module"]
        == "njit_auditor.rules.pdf_heading_levels"
    )
    assert by_id["P026"]["phase"] == "pdf_layout"
    assert (
        by_id["P026"]["implementation_module"]
        == "njit_auditor.rules.pdf_font_compliance"
    )
    assert by_id["P022"]["phase"] == "pdf_layout"
    assert (
        by_id["P022"]["implementation_module"]
        == "njit_auditor.rules.pdf_frontmatter_no_page_number"
    )
    assert by_id["P023"]["phase"] == "pdf_layout"
    assert by_id["P023"]["implementation_module"] == "njit_auditor.rules.pdf_body_spacing"
    assert by_id["P024"]["phase"] == "pdf_layout"
    assert (
        by_id["P024"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_list_formatting"
    )
    assert by_id["P025"]["phase"] == "pdf_layout"
    assert (
        by_id["P025"]["implementation_module"]
        == "njit_auditor.rules.pdf_frontmatter_structure"
    )
    assert by_id["P014"]["phase"] == "pdf_layout"
    assert by_id["P014"]["implementation_module"] == "njit_auditor.rules.pdf_headings"
    assert by_id["P015"]["phase"] == "pdf_layout"
    assert by_id["P015"]["implementation_module"] == "njit_auditor.rules.pdf_indentation"
    assert by_id["P016"]["phase"] == "pdf_layout"
    assert by_id["P016"]["implementation_module"] == "njit_auditor.rules.pdf_spacing"
    assert by_id["P017"]["phase"] == "pdf_layout"
    assert by_id["P017"]["implementation_module"] == "njit_auditor.rules.pdf_captions"
    assert by_id["P018"]["phase"] == "pdf_layout"
    assert by_id["P018"]["implementation_module"] == "njit_auditor.rules.pdf_toc_alignment"
    assert by_id["P030"]["phase"] == "pdf_layout"
    assert (
        by_id["P030"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_continued_headings"
    )
    assert by_id["P031"]["phase"] == "pdf_layout"
    assert (
        by_id["P031"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_column_headers"
    )
    assert by_id["P032"]["phase"] == "pdf_layout"
    assert (
        by_id["P032"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_list_wrapped_spacing"
    )
    assert by_id["P033"]["phase"] == "pdf_layout"
    assert (
        by_id["P033"]["implementation_module"]
        == "njit_auditor.rules.pdf_title_consistency"
    )
    assert by_id["P034"]["phase"] == "pdf_layout"
    assert (
        by_id["P034"]["implementation_module"]
        == "njit_auditor.rules.pdf_copyright_page"
    )
    assert by_id["P035"]["phase"] == "pdf_layout"
    assert (
        by_id["P035"]["implementation_module"]
        == "njit_auditor.rules.pdf_figure_table_layout"
    )
    assert by_id["P036"]["phase"] == "pdf_layout"
    assert (
        by_id["P036"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_list_entry_spacing"
    )
    assert by_id["P037"]["phase"] == "pdf_layout"
    assert (
        by_id["P037"]["implementation_module"]
        == "njit_auditor.rules.pdf_roman_section_anchors"
    )
    assert by_id["P038"]["phase"] == "pdf_layout"
    assert (
        by_id["P038"]["implementation_module"]
        == "njit_auditor.rules.pdf_frontmatter_headings"
    )
    assert by_id["P039"]["phase"] == "pdf_layout"
    assert (
        by_id["P039"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_entry_hierarchy"
    )
    assert by_id["P040"]["phase"] == "pdf_layout"
    assert (
        by_id["P040"]["implementation_module"]
        == "njit_auditor.rules.pdf_lof_terminal_punctuation"
    )
    assert by_id["P041"]["phase"] == "pdf_layout"
    assert (
        by_id["P041"]["implementation_module"]
        == "njit_auditor.rules.pdf_dedication_page"
    )
    assert by_id["P042"]["phase"] == "pdf_layout"
    assert (
        by_id["P042"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_appendix_format"
    )
    assert by_id["P043"]["phase"] == "pdf_layout"
    assert (
        by_id["P043"]["implementation_module"]
        == "njit_auditor.rules.pdf_acknowledgements_indentation"
    )
    assert by_id["P044"]["phase"] == "pdf_layout"
    assert (
        by_id["P044"]["implementation_module"]
        == "njit_auditor.rules.pdf_abstract_indentation"
    )
    assert by_id["P045"]["phase"] == "pdf_layout"
    assert (
        by_id["P045"]["implementation_module"]
        == "njit_auditor.rules.pdf_biosketch_publication_layout"
    )
    assert by_id["P046"]["phase"] == "pdf_layout"
    assert (
        by_id["P046"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_entry_number_alignment"
    )
    assert by_id["P047"]["phase"] == "pdf_layout"
    assert (
        by_id["P047"]["implementation_module"]
        == "njit_auditor.rules.pdf_biosketch_bullet_spacing"
    )
    assert by_id["P048"]["phase"] == "pdf_layout"
    assert (
        by_id["P048"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_page_number_alignment"
    )
    assert by_id["P049"]["phase"] == "pdf_layout"
    assert (
        by_id["P049"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_column_header_style_alignment"
    )
    assert by_id["P050"]["phase"] == "pdf_layout"
    assert (
        by_id["P050"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_column_header_style_alignment"
    )
    assert by_id["P051"]["phase"] == "pdf_layout"
    assert (
        by_id["P051"]["implementation_module"]
        == "njit_auditor.rules.pdf_copyright_page"
    )
    assert by_id["P052"]["phase"] == "pdf_layout"
    assert (
        by_id["P052"]["implementation_module"]
        == "njit_auditor.rules.pdf_copyright_page"
    )
    assert by_id["P053"]["phase"] == "pdf_layout"
    assert (
        by_id["P053"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_terminal_period"
    )
    assert by_id["P054"]["phase"] == "pdf_layout"
    assert by_id["P054"]["implementation_status"] == "implemented"
    assert (
        by_id["P054"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_terminal_period"
    )
    assert by_id["P055"]["phase"] == "pdf_layout"
    assert by_id["P055"]["implementation_status"] == "implemented"
    assert (
        by_id["P055"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_entry_type"
    )
    assert by_id["P056"]["phase"] == "pdf_layout"
    assert by_id["P056"]["implementation_status"] == "implemented"
    assert (
        by_id["P056"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_number_format"
    )
    assert by_id["P019"]["phase"] == "pdf_layout"
    assert by_id["P019"]["implementation_module"] == "njit_auditor.rules.pdf_page_numbers"
    assert by_id["P020"]["phase"] == "pdf_layout"
    assert (
        by_id["P020"]["implementation_module"]
        == "njit_auditor.rules.pdf_title_capitalization"
    )
    assert by_id["P021"]["phase"] == "tex_source"
    assert by_id["P021"]["implementation_module"] == "njit_auditor.rules.latex_abstract"
    assert by_id["P057"]["phase"] == "pdf_layout"
    assert by_id["P057"]["implementation_status"] == "implemented"
    assert (
        by_id["P057"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_page_number_ordering"
    )
    assert by_id["P058"]["phase"] == "pdf_layout"
    assert by_id["P058"]["implementation_status"] == "implemented"
    assert (
        by_id["P058"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_page_number_ordering"
    )
    assert by_id["P059"]["phase"] == "pdf_layout"
    assert by_id["P059"]["implementation_status"] == "implemented"
    assert (
        by_id["P059"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_entry_number_ordering"
    )
    assert by_id["P060"]["phase"] == "pdf_layout"
    assert by_id["P060"]["implementation_status"] == "implemented"
    assert (
        by_id["P060"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_entry_number_ordering"
    )
    assert by_id["P061"]["phase"] == "pdf_layout"
    assert by_id["P061"]["implementation_status"] == "implemented"
    assert (
        by_id["P061"]["implementation_module"]
        == "njit_auditor.rules.pdf_lot_lof_cross_page_entry_ordering"
    )
    assert by_id["P062"]["phase"] == "pdf_layout"
    assert by_id["P062"]["implementation_status"] == "implemented"
    assert (
        by_id["P062"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_cross_page_entry_ordering"
    )
    assert by_id["P063"]["phase"] == "pdf_layout"
    assert by_id["P063"]["implementation_status"] == "implemented"
    assert (
        by_id["P063"]["implementation_module"]
        == "njit_auditor.rules.pdf_appendix_body_headings"
    )
    assert by_id["P064"]["phase"] == "pdf_layout"
    assert by_id["P064"]["implementation_status"] == "implemented"
    assert (
        by_id["P064"]["implementation_module"]
        == "njit_auditor.rules.pdf_references_citations_structural"
    )
    assert by_id["P065"]["phase"] == "pdf_layout"
    assert by_id["P065"]["implementation_status"] == "implemented"
    assert (
        by_id["P065"]["implementation_module"]
        == "njit_auditor.rules.pdf_dedication_centering_italic"
    )
    assert by_id["P066"]["phase"] == "pdf_layout"
    assert by_id["P066"]["implementation_status"] == "implemented"
    assert (
        by_id["P066"]["implementation_module"]
        == "njit_auditor.rules.pdf_biosketch_degree_ordering"
    )
    assert by_id["P067"]["phase"] == "pdf_layout"
    assert by_id["P067"]["implementation_status"] == "implemented"
    assert (
        by_id["P067"]["implementation_module"]
        == "njit_auditor.rules.pdf_biosketch_publication_ordering"
    )
    assert by_id["P068"]["phase"] == "pdf_layout"
    assert by_id["P068"]["implementation_status"] == "implemented"
    assert (
        by_id["P068"]["implementation_module"]
        == "njit_auditor.rules.pdf_approval_page_committee_blocks"
    )
    assert by_id["P069"]["phase"] == "pdf_layout"
    assert by_id["P069"]["implementation_status"] == "implemented"
    assert (
        by_id["P069"]["implementation_module"]
        == "njit_auditor.rules.pdf_frontmatter_heading_gate"
    )
    assert by_id["P069"]["rule_type"] == "infrastructure_refinement"
    assert by_id["P069"]["issue_types"] == []
    assert by_id["P070"]["phase"] == "pdf_layout"
    assert by_id["P070"]["implementation_status"] == "implemented"
    assert (
        by_id["P070"]["implementation_module"]
        == "njit_auditor.rules.pdf_toc_alignment"
    )
    assert by_id["P070"]["rule_type"] == "infrastructure_refinement"
    assert by_id["P070"]["issue_types"] == []
    assert by_id["P071"]["phase"] == "pdf_layout"
    assert by_id["P071"]["implementation_status"] == "implemented"
    assert (
        by_id["P071"]["implementation_module"]
        == "njit_auditor.rules.pdf_references_citations_structural"
    )
    assert by_id["P071"]["rule_type"] == "infrastructure_refinement"
    assert by_id["P071"]["issue_types"] == []
    assert by_id["P072"]["phase"] == "pdf_layout"
    assert by_id["P072"]["implementation_status"] == "implemented"
    assert (
        by_id["P072"]["implementation_module"]
        == "njit_auditor.rules.pdf_approval_page_committee_blocks"
    )
    assert by_id["P072"]["rule_type"] == "infrastructure_refinement"
    assert by_id["P072"]["issue_types"] == []
    assert "P073" in by_id
    assert by_id["P073"]["implementation_status"] == "implemented"
    assert by_id["P073"]["phase"] == "pdf_layout"
    assert by_id["P073"]["rule_type"] == "infrastructure_refinement"
    assert by_id["P073"]["implementation_module"] == "njit_auditor.rules.pdf_page_numbers"
    assert by_id["P073"]["affected_rules"] == ["P019"]
    assert by_id["P073"]["issue_types"] == []
    assert "P074" in by_id
    assert by_id["P074"]["implementation_status"] == "implemented"
    assert by_id["P074"]["phase"] == "pdf_layout"
    assert (
        by_id["P074"]["implementation_module"]
        == "njit_auditor.rules.pdf_frontmatter_structure"
    )
    assert by_id["P074"]["issue_types"] == ["title_page_graduation_month_invalid"]
    assert by_id["P074"]["source_q_rule_ids"] == ["Q006"]
    assert "P076" in by_id
    assert by_id["P076"]["implementation_status"] == "implemented"
    assert by_id["P076"]["phase"] == "pdf_layout"
    assert by_id["P076"]["implementation_module"] == "njit_auditor.report_outputs"
    assert by_id["P076"]["rule_type"] == "reporting_refinement"
    assert by_id["P076"]["affected_rules"] == ["P036"]
    assert by_id["P076"]["issue_types"] == []
    assert "P077" in by_id
    assert by_id["P077"]["implementation_status"] == "implemented"
    assert by_id["P077"]["phase"] == "pdf_layout"
    assert by_id["P077"]["implementation_module"] == "njit_auditor.report_outputs"
    assert by_id["P077"]["rule_type"] == "reporting_refinement"
    assert by_id["P077"]["affected_rules"] == ["P038"]
    assert by_id["P077"]["issue_types"] == []
    assert "P078" in by_id
    assert by_id["P078"]["implementation_status"] == "implemented"
    assert by_id["P078"]["phase"] == "pdf_layout"
    assert by_id["P078"]["implementation_module"] == "njit_auditor.rules.pdf_abstract"
    assert by_id["P078"]["rule_type"] == "detection"
    assert by_id["P078"]["source_q_rule_ids"] == ["Q004", "Q005"]
    assert by_id["P078"]["issue_types"] == [
        "abstract_pdf_forbidden_term",
        "abstract_pdf_first_person_pronoun",
    ]
    assert "P079" in by_id
    assert by_id["P079"]["implementation_status"] == "implemented"
    assert by_id["P079"]["phase"] == "pdf_layout"
    assert by_id["P079"]["implementation_module"] == "njit_auditor.report_outputs"
    assert by_id["P079"]["rule_type"] == "reporting_refinement"
    assert by_id["P079"]["affected_rules"] == ["P044"]
    assert by_id["P079"]["issue_types"] == []
    assert "P080" in by_id
    assert by_id["P080"]["implementation_status"] == "implemented"
    assert by_id["P080"]["phase"] == "docx_comments"
    assert by_id["P080"]["implementation_module"] == "njit_auditor.docx_comments"
    assert by_id["P080"]["rule_type"] == "infrastructure"
    assert by_id["P080"]["issue_types"] == []
    assert "P081" in by_id
    assert by_id["P081"]["implementation_status"] == "implemented"
    assert by_id["P081"]["phase"] == "pdf_layout"
    assert by_id["P081"]["implementation_module"] == "njit_auditor.report_outputs"
    assert by_id["P081"]["rule_type"] == "reporting_refinement"
    assert by_id["P081"]["affected_rules"] == ["P013", "P026"]
    assert by_id["P081"]["issue_types"] == []
    assert "P082" in by_id
    assert by_id["P082"]["implementation_status"] == "implemented"
    assert by_id["P082"]["phase"] == "pdf_layout"
    assert (
        by_id["P082"]["implementation_module"]
        == "njit_auditor.rules.pdf_landscape_page_number_orientation"
    )
    assert by_id["P082"]["rule_type"] == "experimental_advisory"
    assert by_id["P082"]["issue_types"] == [
        "landscape_page_number_orientation_advisory",
        "landscape_page_number_position_advisory",
    ]
    assert all(
        item["implementation_status"] == "implemented"
        for item in project_rules
    )


def test_project_added_rules_sequential_no_gaps() -> None:
    """Allow only documented non-inventory P-ID gaps while rejecting drift."""
    project_rules = _load_json("data/processed/rules/project_added_rules.json")
    manifest = _load_manifest()

    inventory_ids = [str(item["id"]) for item in project_rules]
    documented_non_inventory_ids = [
        str(rule_id) for rule_id in manifest["non_inventory_project_task_ids"]
    ]

    counts = Counter(inventory_ids)
    duplicates = sorted(rid for rid, count in counts.items() if count > 1)

    inventory_numbers = [int(rule_id[1:]) for rule_id in inventory_ids]
    skipped_numbers = [int(rule_id[1:]) for rule_id in documented_non_inventory_ids]
    max_numeric_id = max(inventory_numbers + skipped_numbers)

    expected_inventory_ids = [
        f"P{i:03d}"
        for i in range(1, max_numeric_id + 1)
        if f"P{i:03d}" not in documented_non_inventory_ids
    ]

    missing = sorted(set(expected_inventory_ids) - set(inventory_ids))
    unexpected = sorted(set(inventory_ids) - set(expected_inventory_ids))
    out_of_order = inventory_ids != sorted(
        inventory_ids, key=lambda rule_id: int(rule_id[1:])
    )

    assert inventory_ids == expected_inventory_ids and not duplicates, (
        "project_added_rules.json must list all inventory P-rule IDs in order, "
        "excluding only documented non-inventory project task IDs. "
        f"missing={missing}, unexpected={unexpected}, duplicates={duplicates}, "
        f"documented_skipped_ids={documented_non_inventory_ids}, "
        f"out_of_order={out_of_order}, actual_tail={inventory_ids[-10:]}, "
        f"expected_tail={expected_inventory_ids[-10:]}"
    )


def test_rule_loader_validates_all_rule_files() -> None:
    front = load_rule_file("data/processed/rules/front_matter_rules.json")
    inventory = load_rule_file("data/processed/rules/njit_rule_inventory.json")
    project_added = load_rule_file("data/processed/rules/project_added_rules.json")
    assert len(front) == 79
    assert len(inventory) == 79
    assert len(project_added) >= 1
