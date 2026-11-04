"""Evidence boundaries and presentation-only changes, using synthetic findings."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import build_audit_report, write_markdown_report
from njit_auditor.report_text import write_text_report
from njit_auditor.student_cards import margin_presentation, student_card_fields


@pytest.mark.parametrize('value', ['', 'nan', 'inf', '-inf', '0', '-1', None, 'unknown'])
def test_unmeasured_crossing_has_no_automatic_answer(value):
    fields = student_card_fields(
        {'rule_id': 'P011'}, {'side': 'bottom_margin', 'worst_overflow_pt': value}
    )
    assert fields['margin_questions'] == []
    assert len(fields['check_yourself']) == 3
    assert fields['technical_details'] == []
    assert 'Yes' not in str(fields['check_yourself'])
    assert 'No' not in str(fields['check_yourself'])
    assert 'Needs review' not in str(fields)


@pytest.mark.parametrize('side', ['left', 'right', 'top', 'bottom'])
def test_answer_describes_detection_not_document_settings(side):
    details = {'side': f'{side}_margin', 'worst_overflow_pt': '22.012345', 'confidence': 'low'}
    before = deepcopy(details)
    fields = student_card_fields({'rule_id': 'P011'}, details)
    assert fields['margin_questions'] == [
        (f'Did the check detect text crossing the {side} margin?', 'Yes')
    ]
    assert 'about 0.31 inch' in fields['student_summary']
    assert fields['technical_details'] == [(f'Detected {side} overflow', '22.012345 pt')]
    assert 'If it crosses' in fields['student_fix']
    assert 'Set left margin' not in fields['student_fix']
    assert f'{side} margin boundary' in fields['student_fix']
    assert 'do not establish' in fields['student_note']
    assert details == before


@pytest.mark.parametrize('edge', ['top', 'bottom', 'undetermined', ''])
def test_landscape_setting_is_a_manual_check_even_with_detected_text(edge):
    fields = margin_presentation({'page_orientation': 'landscape', 'binding_edge': edge,
                                  'side': 'right_margin', 'worst_overflow_pt': '8'})
    assert fields['margin_questions'] == [
        ('Did the check detect text crossing the right margin?', 'Yes')
    ]
    question, instruction = fields['check_yourself'][0]
    assert 'set correctly' in question
    assert '1.5-inch' in instruction
    assert 'Confirm which edge is bound' in instruction
    assert 'Yes' not in question + instruction and 'No' not in question + instruction


def test_multiple_edges_retain_each_measurement_and_unknowns():
    fields = margin_presentation({}, [
        {'side': 'left_margin', 'worst_overflow_pt': '12'},
        {'side': 'bottom_margin', 'worst_overflow_pt': '24'},
        {'side': 'unknown', 'worst_overflow_pt': '7'},
    ])
    assert len(fields['margin_questions']) == 2
    assert len(fields['technical_details']) == 2
    assert len(fields['check_yourself']) == 3
    assert 'left and bottom margin boundaries' in fields['student_fix']
    assert '0.17 inch' in fields['student_summary'] and '0.33 inch' in fields['student_summary']


def test_human_exports_do_not_mutate_raw_findings_or_machine_report(tmp_path: Path):
    finding = AuditFinding(rule_id='P011', severity=Severity.WARNING, page=2,
                           message='Synthetic raw margin result', details={
                               'side': 'bottom_margin', 'worst_overflow_pt': '22',
                               'issue_type': 'margin_boundary_violation', 'confidence': 'medium',
                           })
    findings = [finding]
    original = deepcopy(finding.model_dump())
    before = build_audit_report(findings, {'audit_type': 'pdf'})
    md = tmp_path / 'report.md'
    txt = tmp_path / 'report.txt'
    write_markdown_report(findings, {'audit_type': 'pdf'}, md)
    write_text_report(findings, {'audit_type': 'pdf'}, txt)
    for text in [md.read_text(), txt.read_text()]:
        assert 'Check yourself' in text
        assert 'Text appears to extend about 0.31 inch past the bottom margin boundary' in text
        assert 'Technical details:' in text and '22 pt' in text
        assert 'Needs review' not in text
        assert 'Set left margin' not in text
    assert finding.model_dump() == original
    after = build_audit_report(findings, {'audit_type': 'pdf'})
    assert before['findings'] == after['findings']
    assert before['grouped_summary'] == after['grouped_summary']
    assert before['grouped_findings'] == after['grouped_findings']


def test_uncertain_finding_has_conditional_suggestion():
    finding = {'rule_id': 'P025', 'issue_type_label': 'Degree phrase missing',
               'confidence_level': 'medium', 'suggested_fix': 'Add the degree phrase.'}
    original = deepcopy(finding)
    fields = student_card_fields(finding)
    assert fields['student_summary'] == 'Possible issue: Degree phrase missing'
    assert fields['student_fix'] == 'If confirmed, add the degree phrase.'
    assert finding == original
