import json
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
    assert len(project_rules) == 34
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
    assert by_id["P019"]["phase"] == "pdf_layout"
    assert by_id["P019"]["implementation_module"] == "njit_auditor.rules.pdf_page_numbers"
    assert by_id["P020"]["phase"] == "pdf_layout"
    assert (
        by_id["P020"]["implementation_module"]
        == "njit_auditor.rules.pdf_title_capitalization"
    )
    assert by_id["P021"]["phase"] == "tex_source"
    assert by_id["P021"]["implementation_module"] == "njit_auditor.rules.latex_abstract"
    assert all(item["implementation_status"] == "implemented" for item in project_rules)


def test_rule_loader_validates_all_rule_files() -> None:
    front = load_rule_file("data/processed/rules/front_matter_rules.json")
    inventory = load_rule_file("data/processed/rules/njit_rule_inventory.json")
    project_added = load_rule_file("data/processed/rules/project_added_rules.json")
    assert len(front) == 79
    assert len(inventory) == 79
    assert len(project_added) >= 1
