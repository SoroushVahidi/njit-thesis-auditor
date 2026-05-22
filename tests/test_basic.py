"""Unit tests for core helpers that do not require real PDF files."""

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.rule_loader import REQUIRED_RULE_FIELDS, load_rule_file
from njit_auditor.rules.abstract import find_first_person_pronouns, find_forbidden_abstract_words
from njit_auditor.rules.page_numbers import classify_vertical_location


def test_finding_model_defaults() -> None:
    finding = AuditFinding(rule_id="x", severity=Severity.WARNING, message="test")
    assert finding.page is None
    assert finding.details == {}


def test_finding_details_not_shared_between_instances() -> None:
    first = AuditFinding(rule_id="x1", severity=Severity.WARNING, message="test")
    second = AuditFinding(rule_id="x2", severity=Severity.WARNING, message="test")
    first.details["key"] = "value"
    assert second.details == {}


def test_forbidden_word_detection() -> None:
    text = "This paper extends prior articles while another ARTICLE is cited."
    found = find_forbidden_abstract_words(text)
    assert "paper" in found
    assert "article" in found


def test_first_person_detection() -> None:
    text = "We propose a model. Our results improve over baselines, and I discuss limits."
    found = find_first_person_pronouns(text)
    assert "we" in found
    assert "our" in found
    assert "i" in found


def test_vertical_location_classifier() -> None:
    assert classify_vertical_location(y0=0, y1=50, page_height=800) == "top"
    assert classify_vertical_location(y0=760, y1=790, page_height=800) == "bottom"
    assert classify_vertical_location(y0=300, y1=360, page_height=800) == "unknown"


def test_front_matter_rules_exist_and_load() -> None:
    rules = load_rule_file("data/processed/rules/front_matter_rules.json")
    assert rules


def test_front_matter_rule_ids_are_unique() -> None:
    rules = load_rule_file("data/processed/rules/front_matter_rules.json")
    ids = [rule.id for rule in rules]
    assert len(ids) == len(set(ids))


def test_front_matter_rules_have_required_fields() -> None:
    rule_file = "data/processed/rules/front_matter_rules.json"
    loaded = load_rule_file(rule_file)
    assert loaded
    for rule in loaded:
        rule_dict = rule.model_dump()
        assert REQUIRED_RULE_FIELDS.issubset(rule_dict.keys())
