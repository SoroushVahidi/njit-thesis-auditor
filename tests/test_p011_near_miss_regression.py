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


def test_ester_sample_a_visible_p011_count_is_15() -> None:
    """15, not the prior 17: pages 26 (6.0pt) and 54 (5.7pt) were single-line
    bottom-margin "probable TP" guesses in
    docs/status/p011_precision_false_negative_audit_20260710.md S7 (never
    confirmed by Esther) and are now suppressed by
    BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT -- consistent with Esther's newly
    confirmed 5.6pt bottom-margin false positive in the 2026-08 R011 batch. The
    remaining bottom-margin cluster (pages 11, 42, 66, 71, 82, 83 at 9.2-11.0pt)
    and all 9 reference hanging-indent left-margin cards are unchanged.
    """
    sample = get_builtin_sample("ester_sample_a")
    if not sample.abs_path.exists():
        return
    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p011 = [f for f in view.findings if f.rule_id == "P011"]
    assert len(p011) == 15
    pages = {f.page for f in view.findings if f.rule_id == "P011"}
    assert not ({26, 54} & pages)
