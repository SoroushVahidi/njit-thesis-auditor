"""Tests for the Ester YES/NO audit logic matrix spec fixture (Q001-Q079).

Validates:
1. Fixture parses correctly and contains all 79 Q-rules
2. Every Q-rule has non-empty question/definition/remediation
3. Manual-review rules are explicitly marked
4. Coverage audit: 0 unimplemented automatable Q-rules
5. Coverage summary totals are consistent
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from njit_auditor.specs.q_rule_coverage import (
    QRuleCoverage,
    build_coverage_report,
    coverage_summary,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_Q_MATRIX_PATH = _REPO_ROOT / "data" / "specs" / "ester_q_matrix.json"
_P_FEEDBACK_PATH = _REPO_ROOT / "data" / "specs" / "ester_p_rule_feedback.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def q_matrix() -> dict:
    return json.loads(_Q_MATRIX_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def p_feedback() -> dict:
    return json.loads(_P_FEEDBACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def coverage_report() -> list[QRuleCoverage]:
    return build_coverage_report()


# ---------------------------------------------------------------------------
# Group 1: Q-matrix fixture integrity
# ---------------------------------------------------------------------------


class TestQMatrixFixture:
    def test_fixture_exists(self):
        assert _Q_MATRIX_PATH.exists(), "data/specs/ester_q_matrix.json not found"

    def test_fixture_has_79_rules(self, q_matrix):
        assert len(q_matrix["rules"]) == 79

    def test_all_q001_to_q079_present(self, q_matrix):
        ids = {r["id"] for r in q_matrix["rules"]}
        for n in range(1, 80):
            expected = f"Q{n:03d}"
            assert expected in ids, f"{expected} missing from Q-matrix fixture"

    def test_no_duplicate_ids(self, q_matrix):
        ids = [r["id"] for r in q_matrix["rules"]]
        assert len(ids) == len(set(ids)), "Duplicate Q-rule IDs in fixture"

    def test_every_rule_has_question(self, q_matrix):
        for r in q_matrix["rules"]:
            assert r.get("question"), f"{r['id']} has empty question"

    def test_every_rule_has_rule_definition(self, q_matrix):
        for r in q_matrix["rules"]:
            assert r.get("rule_definition"), f"{r['id']} has empty rule_definition"

    def test_every_rule_has_remediation(self, q_matrix):
        for r in q_matrix["rules"]:
            assert r.get("remediation"), f"{r['id']} has empty remediation"

    def test_every_rule_has_section(self, q_matrix):
        for r in q_matrix["rules"]:
            assert r.get("section"), f"{r['id']} has empty section"

    def test_metadata_present(self, q_matrix):
        meta = q_matrix.get("metadata", {})
        assert meta.get("source_file"), "metadata.source_file missing"
        assert meta.get("author") == "Ester Flaim"
        assert meta.get("total_rules") == 79

    def test_manual_review_rules_marked(self, q_matrix):
        manual = {r["id"] for r in q_matrix["rules"] if not r.get("automatable", True)}
        # These are the known non-automatable Q-rules
        expected_manual = {"Q007", "Q016", "Q017", "Q018", "Q019",
                           "Q037", "Q038", "Q039", "Q040", "Q041", "Q042", "Q043"}
        assert expected_manual == manual, (
            f"Manual-review set mismatch.\n"
            f"  Expected: {sorted(expected_manual)}\n"
            f"  Got: {sorted(manual)}"
        )

    def test_manual_review_rules_have_reason(self, q_matrix):
        for r in q_matrix["rules"]:
            if not r.get("automatable", True):
                assert r.get("manual_review_reason"), (
                    f"{r['id']} is marked manual_review but has no reason"
                )


# ---------------------------------------------------------------------------
# Group 2: P-rule feedback fixture integrity
# ---------------------------------------------------------------------------


class TestPRuleFeedbackFixture:
    def test_fixture_exists(self):
        assert _P_FEEDBACK_PATH.exists(), "data/specs/ester_p_rule_feedback.json not found"

    def test_has_p_rules_for_p011_to_p018(self, p_feedback):
        ids = {e["id"] for e in p_feedback["feedback"]}
        for pid in ("P011", "P013", "P014", "P015", "P016", "P017", "P018"):
            assert pid in ids, f"{pid} missing from P-rule feedback fixture"

    def test_no_empty_id(self, p_feedback):
        for e in p_feedback["feedback"]:
            assert e.get("id"), "Empty ID in P-rule feedback"

    def test_p011_proposed_question(self, p_feedback):
        p011 = next(e for e in p_feedback["feedback"] if e["id"] == "P011")
        q = p011["proposed_question_edit"].lower()
        assert "contained entirely within" in q

    def test_p013_proposed_question(self, p_feedback):
        p013 = next(e for e in p_feedback["feedback"] if e["id"] == "P013")
        q = p013["proposed_question_edit"].lower()
        assert "bottom-center" in q or "designated bottom" in q

    def test_p016_proposed_question(self, p_feedback):
        p016 = next(e for e in p_feedback["feedback"] if e["id"] == "P016")
        q = p016["proposed_question_edit"].lower()
        assert "page breaks" in q


# ---------------------------------------------------------------------------
# Group 3: Coverage audit
# ---------------------------------------------------------------------------


class TestQRuleCoverage:
    def test_coverage_report_has_79_entries(self, coverage_report):
        assert len(coverage_report) == 79

    def test_zero_unimplemented_automatable_q_rules(self, coverage_report):
        unimplemented = [
            r for r in coverage_report if r.implementation_status == "unimplemented"
        ]
        assert unimplemented == [], (
            "Unimplemented automatable Q-rules: "
            + ", ".join(r.q_id for r in unimplemented)
        )

    def test_implemented_count_at_least_60(self, coverage_report):
        implemented = sum(1 for r in coverage_report if r.implementation_status == "implemented")
        assert implemented >= 60, f"Only {implemented} Q-rules implemented (expected ≥60)"

    def test_manual_review_count_is_12(self, coverage_report):
        manual = sum(1 for r in coverage_report if r.implementation_status == "manual_review_only")
        assert manual == 12

    def test_coverage_summary_totals_consistent(self, coverage_report):
        summary = coverage_summary(coverage_report)
        assert summary["total"] == 79
        total = summary["implemented"] + summary["manual_review_only"] + summary["unimplemented"]
        assert total == 79

    def test_q001_covered_by_p_rule(self, coverage_report):
        q001 = next(r for r in coverage_report if r.q_id == "Q001")
        assert q001.implementation_status == "implemented"
        assert q001.implementing_p_rules  # has at least one P-rule

    def test_q075_covered_by_p_rule(self, coverage_report):
        q075 = next(r for r in coverage_report if r.q_id == "Q075")
        assert q075.implementation_status == "implemented"

    def test_manual_review_q007(self, coverage_report):
        q007 = next(r for r in coverage_report if r.q_id == "Q007")
        assert q007.implementation_status == "manual_review_only"
        assert not q007.automatable

    def test_manual_review_q016_to_q019(self, coverage_report):
        for qid in ("Q016", "Q017", "Q018", "Q019"):
            r = next(x for x in coverage_report if x.q_id == qid)
            assert r.implementation_status == "manual_review_only", (
                f"{qid} should be manual_review_only, got {r.implementation_status}"
            )

    def test_manual_review_q037_to_q043(self, coverage_report):
        for qid in ("Q037", "Q038", "Q039", "Q040", "Q041", "Q042", "Q043"):
            r = next(x for x in coverage_report if x.q_id == qid)
            assert r.implementation_status == "manual_review_only", (
                f"{qid} should be manual_review_only, got {r.implementation_status}"
            )


# ---------------------------------------------------------------------------
# Group 4: Catalog wording alignment with Ester's P-rule feedback
# ---------------------------------------------------------------------------


class TestCatalogWording:
    @pytest.fixture(scope="class")
    def catalog(self) -> dict:
        import json
        catalog_path = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"
        rules = json.loads(catalog_path.read_text(encoding="utf-8"))
        return {r["id"]: r for r in rules}

    def test_p013_question_mentions_bottom_center(self, catalog):
        q = catalog["P013"]["question"].lower()
        assert "bottom" in q and "center" in q

    def test_p013_question_mentions_0_5_inches(self, catalog):
        q = catalog["P013"].get("question", "") + catalog["P013"].get("remediation", "")
        assert "0.5" in q

    def test_p016_question_mentions_page_breaks(self, catalog):
        q = catalog["P016"]["question"].lower()
        assert "page breaks" in q

    def test_p016_question_mentions_figures_tables(self, catalog):
        q = catalog["P016"]["question"].lower()
        assert "figures" in q or "tables" in q

    def test_p011_question_mentions_contained_within(self, catalog):
        q = catalog["P011"]["question"].lower()
        assert "contained" in q

    def test_p017_question_mentions_sentence_case(self, catalog):
        q = catalog["P017"]["question"].lower()
        assert "sentence case" in q

    def test_p017_question_mentions_title_case(self, catalog):
        q = catalog["P017"]["question"].lower()
        assert "title case" in q

    def test_p018_question_mentions_toc_lot_lof(self, catalog):
        q = catalog["P018"]["question"].lower()
        assert "contents" in q and "tables" in q and "figures" in q
