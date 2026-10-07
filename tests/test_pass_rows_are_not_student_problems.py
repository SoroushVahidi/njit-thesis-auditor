"""A PASS row (a check that ran clean) is never a numbered student problem.

R011 emits one document-level PASS row when a PDF has no margin violations;
before this guard it became "Problem #N — R011 — Formatting problem" telling
the student their text was outside the margins.
"""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.student_pdf_report import render_student_report_text

R011_PASS = AuditFinding(
    rule_id="P011",
    severity=Severity.PASS,
    message="No obvious margin-boundary text violations detected.",
)
WARNING = AuditFinding(
    rule_id="P020",
    severity=Severity.WARNING,
    page=3,
    message="Heading may not use title case.",
    details={"issue_type": "possible_title_capitalization_issue"},
)


def test_clean_r011_pass_row_is_not_numbered_or_shown() -> None:
    payload = audit_findings_to_json_dict([R011_PASS], {"audit_type": "pdf"})
    assert [f.get("problem_number") for f in payload["findings"]] == [None]
    view = build_report_view(payload)
    assert view.findings == []
    assert view.counts_by_severity["PASS"] == 0


def test_pass_row_does_not_shift_real_problem_numbers() -> None:
    payload = audit_findings_to_json_dict([R011_PASS, WARNING], {"audit_type": "pdf"})
    numbers = {f["rule_id"]: f.get("problem_number") for f in payload["findings"]}
    assert numbers == {"P011": None, "P020": 1}
    view = build_report_view(payload)
    assert [(f.rule_id, f.problem_number) for f in view.findings] == [("P020", 1)]


def test_student_text_report_has_no_r011_problem_for_a_clean_document() -> None:
    view = build_report_view(audit_findings_to_json_dict([R011_PASS], {"audit_type": "pdf"}))
    findings = [
        {
            "rule_id": f.rule_id,
            "page": f.page,
            "problem_number": f.problem_number,
            "polished_comment": f.polished_comment,
        }
        for f in view.findings
    ]
    text = render_student_report_text(findings, file_name="clean.pdf")
    assert "R011" not in text
    assert "No formatting problems were detected" in text
