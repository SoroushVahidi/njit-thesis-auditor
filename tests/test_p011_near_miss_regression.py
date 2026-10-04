"""Regression tests for intentional P011 near-miss suppression patterns."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_margins import (
    OVERFLOW_TOLERANCE_PT,
    RIGHT_MARGIN_PT,
    run_pdf_margin_rule,
)
from njit_auditor.web_samples import get_builtin_sample

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
ALLOWED_X1 = PAGE_WIDTH - RIGHT_MARGIN_PT


def test_single_line_sub_five_pt_right_overflow_suppressed(tmp_path: Path) -> None:
    """Regression: Ester Sample B pages 1/24/39 false-positive shape must not warn."""
    target_overflow = OVERFLOW_TOLERANCE_PT + 1.8
    width = fitz.get_text_length("Noise", fontsize=11)
    x0 = ALLOWED_X1 + target_overflow - width
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 200), "Noise", fontsize=11)
    pdf_path = tmp_path / "sub5_right.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]
    assert warnings == []


def test_ester_sample_b_suppressed_pages_remain_clear() -> None:
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return
    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    pages = {f.page for f in view.findings if f.rule_id == "P011"}
    assert not ({1, 24, 39} & pages)


def test_ester_sample_b_visible_p011_count_is_26() -> None:
    """26, not the prior 27: page 75's single-line, 6.5pt bottom-margin equation
    finding is now suppressed by BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT. That page
    was unreviewed ("-" in docs/status/p011_precision_false_negative_audit_20260710.md
    S3) but matches, in side/content-kind/magnitude, the bottom-margin equation
    false positive Esther confirmed for a different dissertation in the 2026-08
    R011 batch (see docs/status/p011_r011_batch_2026_08_false_positive_fix.md).
    All 20 right-margin and 6 left-margin (reference hanging-indent) findings
    are unchanged.
    """
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        return
    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p011 = [f for f in view.findings if f.rule_id == "P011"]
    assert len(p011) == 26
    assert 75 not in {f.page for f in view.findings if f.rule_id == "P011"}


def test_ester_sample_a_visible_p011_count_is_9() -> None:
    """9, not the prior 15: pages 11, 42, 66, and 71 were single-line
    bottom-margin findings at ~9.2pt (9.17pt raw), the exact recurring
    footer-zone cluster docs/status/p011_precision_false_negative_audit_20260710.md
    S7 flagged as an open policy question rather than a confirmed false
    positive. Esther has since reviewed this cluster directly (Muyeed
    physical PDF page 36, same ~9.2pt geometry) via the R011-R015 follow-up
    sheet and confirmed it is NOT a violation -- see
    docs/status/p011_r011_ester_9_2pt_boundary_resolution_20260831.md. Pages
    82 (9.8pt) and 83 (11.0pt) also have the now-recognized bounded
    final-line-box shape. All 9 reference hanging-indent left-margin cards
    remain flagged.
    """
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return
    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p011 = [f for f in view.findings if f.rule_id == "P011"]
    assert len(p011) == 9
    pages = {f.page for f in view.findings if f.rule_id == "P011"}
    assert not ({11, 26, 42, 54, 66, 71} & pages)
    assert not ({82, 83} & pages)
