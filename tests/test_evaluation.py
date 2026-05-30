from njit_auditor.evaluation import (
    build_comment_page_category_sets,
    build_finding_page_category_sets,
    map_finding_rule_to_category,
    normalize_page_number,
    summarize_audit_findings,
    summarize_category_page_overlap,
    summarize_comment_categories,
    summarize_page_overlap,
)
from njit_auditor.models import AuditFinding, Severity


def test_rule_id_mapping() -> None:
    assert map_finding_rule_to_category("P011") == "margin_or_overflow"
    assert map_finding_rule_to_category("P012") == "annotations"
    assert map_finding_rule_to_category("P013") == "page_numbering"
    assert map_finding_rule_to_category("P019") == "page_numbering"
    assert map_finding_rule_to_category("P022") == "page_numbering"
    assert map_finding_rule_to_category("P028") == "page_numbering"
    assert map_finding_rule_to_category("P029") == "page_numbering"
    assert map_finding_rule_to_category("P026") == "font_format"
    assert map_finding_rule_to_category(
        "P027", {"issue_type": "level3_sentence_case_issue"}
    ) == "capitalization_case"
    assert map_finding_rule_to_category(
        "P027", {"issue_type": "level1_not_all_caps"}
    ) == "heading_title"
    assert map_finding_rule_to_category("P014") == "heading_title"
    assert map_finding_rule_to_category("P015") == "indentation"
    assert map_finding_rule_to_category("P016") == "spacing_blank_lines"
    assert map_finding_rule_to_category("P023") == "spacing_blank_lines"
    assert map_finding_rule_to_category("P018") == "list_of_tables_figures_toc"
    assert map_finding_rule_to_category("P020") == "capitalization_case"
    assert map_finding_rule_to_category("P021") == "abstract_length"
    assert map_finding_rule_to_category("P017", {"caption_type": "table"}) == "table_format"
    assert map_finding_rule_to_category("P017", {"caption_type": "figure"}) == "figure_format"
    assert (
        map_finding_rule_to_category("P017", {"issue_type": "missing_terminal_punctuation"})
        == "punctuation"
    )
    assert map_finding_rule_to_category("Q004") == "abstract_language"
    assert map_finding_rule_to_category("Q006") == "title_page_metadata"
    assert map_finding_rule_to_category("UNKNOWN") == "other"


def test_summarize_comment_categories_counts() -> None:
    annotations = [
        {"content": "nothing can be in the margins"},
        {"content": "delete indent"},
        {"content": "delete indent and add period"},
        {"content": ""},
    ]
    summary = summarize_comment_categories(annotations)
    assert summary["margin_or_overflow"] == 1
    assert summary["indentation"] == 2
    assert summary["punctuation"] == 1
    assert summary["unclear_or_other"] == 1


def test_summarize_audit_findings_counts() -> None:
    findings = [
        AuditFinding(rule_id="P011", severity=Severity.WARNING, message="m1"),
        AuditFinding(rule_id="P011", severity=Severity.WARNING, message="m2"),
        AuditFinding(rule_id="P013", severity=Severity.WARNING, message="p"),
        AuditFinding(rule_id="P019", severity=Severity.WARNING, message="pn"),
        AuditFinding(rule_id="P014", severity=Severity.WARNING, message="h"),
        AuditFinding(rule_id="P015", severity=Severity.WARNING, message="i"),
        AuditFinding(rule_id="P016", severity=Severity.WARNING, message="s"),
        AuditFinding(
            rule_id="P017",
            severity=Severity.WARNING,
            message="t",
            details={"caption_type": "table", "issue_type": "possible_title_case_issue"},
        ),
        AuditFinding(
            rule_id="P017",
            severity=Severity.WARNING,
            message="f",
            details={"caption_type": "figure", "issue_type": "possible_sentence_case_issue"},
        ),
        AuditFinding(
            rule_id="P017",
            severity=Severity.WARNING,
            message="p",
            details={"caption_type": "figure", "issue_type": "missing_terminal_punctuation"},
        ),
        AuditFinding(rule_id="P018", severity=Severity.WARNING, message="toc"),
        AuditFinding(rule_id="UNKNOWN", severity=Severity.WARNING, message="x"),
    ]
    summary = summarize_audit_findings(findings)
    assert summary["margin_or_overflow"] == 2
    assert summary["page_numbering"] == 2
    assert summary["heading_title"] == 1
    assert summary["indentation"] == 1
    assert summary["spacing_blank_lines"] == 1
    assert summary["list_of_tables_figures_toc"] == 1
    assert summary["table_format"] == 1
    assert summary["figure_format"] == 1
    assert summary["punctuation"] == 1
    assert summary["other"] == 1


def test_normalize_page_number() -> None:
    assert normalize_page_number(3) == 3
    assert normalize_page_number(3.0) == 3
    assert normalize_page_number(" 7 ") == 7
    assert normalize_page_number(0) is None
    assert normalize_page_number(-2) is None
    assert normalize_page_number("abc") is None
    assert normalize_page_number(None) is None


def test_page_overlap_helpers() -> None:
    annotations = [
        {"page_number": 2, "content": "delete indent"},
        {"page_number": "3", "content": "table title format"},
        {"page_number": "bad", "content": "ignored"},
    ]
    findings = [
        AuditFinding(rule_id="P015", severity=Severity.WARNING, message="indent", page=2),
        AuditFinding(rule_id="P017", severity=Severity.WARNING, message="table", page=5),
        AuditFinding(
            rule_id="P017",
            severity=Severity.WARNING,
            message="punct",
            page=3,
            details={"issue_type": "missing_terminal_punctuation"},
        ),
    ]

    comment_pages = set(build_comment_page_category_sets(annotations).keys())
    finding_pages = set(build_finding_page_category_sets(findings).keys())
    overlap = summarize_page_overlap(comment_pages, finding_pages)
    assert overlap["pages_with_ef_comments"] == 2
    assert overlap["pages_with_tool_findings"] == 3
    assert overlap["pages_with_both"] == 2
    assert overlap["tool_only_pages"] == [5]

    category_overlap = summarize_category_page_overlap(
        build_comment_page_category_sets(annotations),
        build_finding_page_category_sets(findings),
        categories=["indentation", "table_format", "punctuation"],
    )
    assert category_overlap["indentation"]["both_pages"] == [2]
    assert category_overlap["table_format"]["ef_only_pages"] == [3]
    assert category_overlap["table_format"]["tool_only_pages"] == [5]
    assert category_overlap["punctuation"]["tool_pages"] == [3]
