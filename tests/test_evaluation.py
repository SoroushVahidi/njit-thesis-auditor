from njit_auditor.evaluation import (
    map_finding_rule_to_category,
    summarize_audit_findings,
    summarize_comment_categories,
)
from njit_auditor.models import AuditFinding, Severity


def test_rule_id_mapping() -> None:
    assert map_finding_rule_to_category("P011") == "margin_or_overflow"
    assert map_finding_rule_to_category("P012") == "annotations"
    assert map_finding_rule_to_category("P013") == "page_numbering"
    assert map_finding_rule_to_category("P014") == "heading_title"
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
        AuditFinding(rule_id="P014", severity=Severity.WARNING, message="h"),
        AuditFinding(rule_id="UNKNOWN", severity=Severity.WARNING, message="x"),
    ]
    summary = summarize_audit_findings(findings)
    assert summary["margin_or_overflow"] == 2
    assert summary["page_numbering"] == 1
    assert summary["heading_title"] == 1
    assert summary["other"] == 1
