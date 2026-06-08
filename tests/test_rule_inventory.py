import json
from collections import Counter
from pathlib import Path

from njit_auditor.rule_loader import load_rule_file


def _load_json(path: str) -> list[dict[str, object]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
    assert status["partially_implemented"] == 55
    assert status["not_implemented"] == 22
    manual_only = sum(1 for item in inventory if item.get("checkability") == "manual")
    assert manual_only == 9
    assert manual_only + 13 == status["not_implemented"]


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
    assert len(project_rules) == 66
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
    assert all(
        item["implementation_status"] == "implemented"
        for item in project_rules
    )


def test_rule_loader_validates_all_rule_files() -> None:
    front = load_rule_file("data/processed/rules/front_matter_rules.json")
    inventory = load_rule_file("data/processed/rules/njit_rule_inventory.json")
    project_added = load_rule_file("data/processed/rules/project_added_rules.json")
    assert len(front) == 79
    assert len(inventory) == 79
    assert len(project_added) >= 1
