"""Regression tests for the P011 overflow-segment highlight rendering (task B),
the per-page composite problem view (task C), and the P011 numbered
review-note snippet list (task D). Synthetic fixtures only -- no real
dissertation content.

Every test here asserts presentation-only behavior: no detector logic,
threshold, rule ID, issue type, or finding count changes.
"""

from __future__ import annotations

import html
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_highlight import get_pdf_page_sizes
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict
from njit_auditor.rules.pdf_margins import RIGHT_MARGIN_PT, run_pdf_margin_rule

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
ALLOWED_X1 = PAGE_WIDTH - RIGHT_MARGIN_PT  # 540.0

_DESKTOP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}
_MOBILE_SAFARI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
    ),
    "Viewport-Width": "390",
}


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def app(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _text_at_x1(text: str, target_x1: float, fontsize: float = 11) -> float:
    width = fitz.get_text_length(text, fontsize=fontsize)
    return target_x1 - width


def _write_real_pdf(path: Path, *, page_count: int = 10) -> None:
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((72, 96), f"Synthetic thesis page {index + 1}.")
    doc.save(path)
    doc.close()


def _inject_job(wa: Any, findings: list[AuditFinding], *, page_count: int = 10) -> str:
    """Mirror web_app._run_audit_task's job.findings construction (see the
    identical helper in test_finding_index_page_order_consistency.py)."""
    job_id = secrets.token_urlsafe(16)
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _write_real_pdf(jdir / "upload.pdf", page_count=page_count)

    metadata = {"input_file_name": "composite-check.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        file_name="composite-check.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for finding in view.findings if finding.severity == "WARNING"),
        fail_count=sum(1 for finding in view.findings if finding.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
                "bbox": list(fv.bbox) if fv.bbox else None,
                "action_kind": fv.action_kind,
                "action_label": fv.action_label,
                "has_highlight": fv.has_highlight,
                "no_highlight_reason": fv.no_highlight_reason,
                "detailed_explanation": fv.detailed_explanation,
                "issue_type_label": fv.issue_type_label,
                "issue_type_explanation": fv.issue_type_explanation,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": row.rule_id, "count": row.count, "category": row.category}
            for row in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview=(jdir / "report.md").read_text(encoding="utf-8"),
    )
    wa._set_job(job)
    return job_id


def _make_p011(page: int, *, x0: float, count: int = 1) -> AuditFinding:
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message=f"Right margin overflow on page {page}.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "worst_overflow_pt": "6.0",
            "affected_line_count": str(count),
            "confidence": "medium",
            "bbox": f"{x0},200.0,{x0 + 50.0},230.0",
        },
    )


def _make_p013(page: int) -> AuditFinding:
    return AuditFinding(
        rule_id="P013",
        severity=Severity.WARNING,
        page=page,
        message=f"Missing page number on page {page}.",
        details={"issue_type": "missing_page_number", "confidence": "medium"},
    )


def _make_p020(page: int, *, variant: int = 0) -> AuditFinding:
    details = {
        "issue_type": "possible_title_capitalization_issue",
        "confidence": "medium",
    }
    if variant:
        # Distinguishes otherwise-identical synthetic findings so they don't
        # collapse as duplicate cards -- real occurrences differ naturally.
        details["bbox"] = f"{100 + variant},{200 + variant},{150 + variant},{220 + variant}"
    return AuditFinding(
        rule_id="P020",
        severity=Severity.WARNING,
        page=page,
        message=f"Capitalization issue on page {page}.",
        details=details,
    )


def _make_p030(page: int, *, variant: int = 0) -> AuditFinding:
    details = {"issue_type": "missing_continued_heading", "confidence": "medium"}
    if variant:
        details["bbox"] = f"{100 + variant},{300 + variant},{150 + variant},{320 + variant}"
    return AuditFinding(
        rule_id="P030",
        severity=Severity.WARNING,
        page=page,
        message=f"Missing continued heading on page {page}.",
        details=details,
    )


# ---------------------------------------------------------------------------
# Task B: overflow-segment geometry and rendering never expands beyond the
# real detection geometry, and detector output is unaffected.
# ---------------------------------------------------------------------------


def test_overflow_segment_never_extends_beyond_the_source_line_box(tmp_path: Path) -> None:
    """The overflow-only segment must always be a sub-rectangle of the full
    affected-line box -- never wider, never past the line's own edges."""
    text = "This line runs well past the required right margin boundary xxxxxx"
    x0 = _text_at_x1(text, ALLOWED_X1 + 15, 11)
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 120), text, fontsize=11)
    pdf_path = tmp_path / "overflow_subset.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]
    assert len(warnings) == 1
    details = warnings[0].details

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    line_box = next(b for b in boxes if b.kind == "line")
    overflow_box = next(b for b in boxes if b.kind == "overflow")

    assert overflow_box[0] >= line_box[0], "overflow x0 must not start before the line's own x0"
    assert overflow_box[2] <= line_box[2], "overflow x1 must not extend past the line's own x1"
    assert overflow_box[1] == line_box[1]
    assert overflow_box[3] == line_box[3]
    assert overflow_box[0] >= ALLOWED_X1 - 0.01, "overflow segment must start at/after the margin"


def test_overflow_segment_geometry_addition_does_not_change_detector_output(
    tmp_path: Path,
) -> None:
    """Adding overflow_segment_bboxes/guide geometry to details must not change
    what counts as a P011 violation, its severity, side, or confidence."""
    text = "This line runs well past the required right margin boundary xxxxxx"
    x0 = _text_at_x1(text, ALLOWED_X1 + 15, 11)
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 120), text, fontsize=11)
    page.insert_text((150, 300), "A normal clean line well inside the margins.", fontsize=11)
    pdf_path = tmp_path / "no_detector_change.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.severity.value == "WARNING"]
    assert len(warnings) == 1
    assert warnings[0].rule_id == "P011"
    assert warnings[0].details["side"] == "right_margin"
    assert warnings[0].details["confidence"] == "high"
    assert warnings[0].details["affected_line_count"] == "1"


def test_overflow_and_line_boxes_are_visually_distinct_styles(tmp_path: Path) -> None:
    """Design 1 (light line highlight + strong overflow fill + thin guide)
    must actually render three distinguishable annotation styles, not one
    uniform box repeated -- otherwise the "clearer visual distinction for the
    overflow segment" requirement isn't met."""
    text = "This line runs well past the required right margin boundary xxxxxx"
    x0 = _text_at_x1(text, ALLOWED_X1 + 15, 11)
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 120), text, fontsize=11)
    pdf_path = tmp_path / "styled.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]
    details = warnings[0].details

    from njit_auditor.pdf_highlight import build_highlighted_single_page_pdf

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    out_path = tmp_path / "highlighted.pdf"
    result = build_highlighted_single_page_pdf(
        pdf_path, out_path, source_page_number=1, boxes=boxes
    )
    assert result.has_highlight

    out_doc = fitz.open(out_path)
    annots = list(out_doc[0].annots() or [])
    fills = {tuple(round(c, 2) for c in a.colors.get("fill") or ()) for a in annots}
    strokes = {tuple(round(c, 2) for c in a.colors.get("stroke") or ()) for a in annots}
    opacities = {round(a.opacity, 2) for a in annots}
    # Three distinct kinds drawn -> at least 2 distinct fills (line has a fill,
    # guide has none) and at least 2 distinct opacities (line vs overflow).
    assert len(fills) >= 2, f"expected line/overflow/guide fills to differ, got {fills}"
    assert len(opacities) >= 2, f"expected line/overflow opacity to differ, got {opacities}"
    assert len(strokes) >= 2
    out_doc.close()


def test_pdf_content_type_and_validity_preserved_for_overflow_rendering(
    app: tuple[TestClient, Any],
) -> None:
    """The highlighted-page response must stay a valid single-page PDF with
    Content-Type application/pdf -- the new box kinds must never corrupt the
    output or change the response contract."""
    c, wa = app
    job_id = _inject_job(wa, [_make_p011(3, x0=520.0, count=1)])
    url = (
        f"/audits/{job_id}/highlighted-page.pdf"
        "?page=3&rule_id=P011&issue_type=margin_boundary_violation"
    )
    resp = c.get(url)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert doc.is_pdf
        assert doc.page_count == 1


# ---------------------------------------------------------------------------
# Task C: composite per-page problem view.
# ---------------------------------------------------------------------------


def test_composite_page_view_lists_every_finding_with_a_legend(
    app: tuple[TestClient, Any],
) -> None:
    """A page with three distinct rule/issue-type findings must show all
    three together with a numbered legend -- the composite view's core job."""
    c, wa = app
    findings = [_make_p013(7), _make_p020(7), _make_p030(7)]
    job_id = _inject_job(wa, findings)

    resp = c.get(f"/audits/{job_id}/problems/page/7")
    assert resp.status_code == 200
    text = html.unescape(resp.text)

    assert "Page 7" in text
    assert "P013" in text
    assert "P020" in text
    assert "P030" in text
    # Numbered legend markers 1, 2, 3 present.
    for n in ("1", "2", "3"):
        assert re.search(rf'page-legend__marker"[^>]*>{n}<', text), f"missing legend marker {n}"
    # Each example card carries a matching numbered marker (not color alone).
    marker_count = len(re.findall(r'example-card__marker"[^>]*>\d+<', text))
    assert marker_count == 3


def test_composite_page_view_omits_redundant_per_card_page_badge(
    app: tuple[TestClient, Any],
) -> None:
    """The page number is already the page this whole view is for; repeating
    'Page 7' on every card duplicates it needlessly (task D/C constraint)."""
    c, wa = app
    job_id = _inject_job(wa, [_make_p013(7), _make_p020(7)])
    resp = c.get(f"/audits/{job_id}/problems/page/7")
    text = html.unescape(resp.text)
    # Exactly one "Page 7" info badge (the hero's) -- not one per card, which
    # would repeat the page the whole view is already scoped to.
    assert text.count('badge-info">Page 7<') == 1


def test_composite_page_view_404_for_page_with_no_findings(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_make_p013(2)])
    resp = c.get(f"/audits/{job_id}/problems/page/99")
    assert resp.status_code == 404


def test_composite_page_view_reachable_from_main_results_page(
    app: tuple[TestClient, Any],
) -> None:
    """The per-page view must actually be linked from the main findings list,
    not just reachable by guessing the URL."""
    c, wa = app
    job_id = _inject_job(wa, [_make_p013(7), _make_p020(7)])
    resp = c.get(f"/audits/{job_id}", headers=_DESKTOP_HEADERS)
    text = html.unescape(resp.text)
    assert f"/audits/{job_id}/problems/page/7" in text


def test_composite_page_legend_does_not_rely_on_color_alone(
    app: tuple[TestClient, Any],
) -> None:
    """Each legend entry and card marker must carry a text number, not just a
    CSS color class -- accessibility requirement from task C."""
    c, wa = app
    job_id = _inject_job(wa, [_make_p013(7), _make_p020(7)])
    resp = c.get(f"/audits/{job_id}/problems/page/7")
    text = html.unescape(resp.text)
    # Legend markers must contain visible digit text, not an empty colored dot.
    for marker in re.findall(r'page-legend__marker"[^>]*>([^<]*)<', text):
        assert marker.strip().isdigit()
    for marker in re.findall(r'example-card__marker"[^>]*>([^<]*)<', text):
        assert marker.strip().isdigit()


# ---------------------------------------------------------------------------
# Task D: numbered review-note snippet list + matching PDF markers.
# ---------------------------------------------------------------------------


def _p011_view_finding(*, page: int, affected_line_texts: str, affected_line_count: str) -> Any:
    """Build a FindingView for a P011 finding through the real production
    pipeline (audit_findings_to_json_dict -> build_report_view), so this
    exercises the actual presentation override
    (report_view._apply_margin_presentation -> _margin_comment_and_fix ->
    _margin_affected_lines_clause), not a bypassed/lower-level call."""
    finding = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message="Right margin overflow.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "worst_overflow_pt": "3.0",
            "affected_line_count": affected_line_count,
            "affected_line_texts": affected_line_texts,
            "confidence": "medium",
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload, pdf_page_sizes=[(PAGE_WIDTH, PAGE_HEIGHT)])
    return view.findings[0]


def test_review_note_lists_affected_snippets_as_a_numbered_list() -> None:
    fv = _p011_view_finding(
        page=5,
        affected_line_count="3",
        affected_line_texts="first affected line | second affected line | third affected line",
    )
    comment = fv.polished_comment
    assert '1. "first affected line"' in comment
    assert '2. "second affected line"' in comment
    assert '3. "third affected line"' in comment
    # The page number must appear exactly once in the note (no duplication
    # across the observed clause and the snippet list).
    assert comment.count("page 5") == 1


def test_single_affected_line_stays_unnumbered() -> None:
    """Numbering a single item adds nothing -- only 2+ snippets get numbers."""
    fv = _p011_view_finding(
        page=4, affected_line_count="1", affected_line_texts="only affected line"
    )
    comment = fv.polished_comment
    assert 'Affected text: "only affected line"' in comment
    assert "1. " not in comment


def test_multi_item_detail_survives_export_truncation() -> None:
    """A regression guard for the real bug found while implementing this: the
    generic 120-char MAX_DETAIL_TEXT_LEN export cap was silently cutting
    affected_line_texts off mid-item, dropping items 3+ from the numbered
    list even though the detector itself produced all of them. The per-key
    override must let at least 4 60-char preview items survive export."""
    from njit_auditor.report_outputs import audit_findings_to_json_dict

    long_previews = " | ".join(
        f"preview snippet number {i} padded out to sixty chars xx" for i in range(1, 5)
    )
    finding = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=5,
        message="Right margin overflow.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "affected_line_count": "4",
            "affected_line_texts": long_previews,
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    exported = payload["findings"][0]["details"]["affected_line_texts"]
    assert exported.count(" | ") == 3, f"expected all 4 items to survive export, got: {exported!r}"


def test_multi_item_detail_truncation_never_cuts_mid_item() -> None:
    """If a details dict is somehow constructed with more/longer items than
    the detector itself would ever produce (e.g. a future change to the
    per-item cap, or a hand-built AuditFinding), the export truncation must
    drop whole trailing items rather than emit a half-cut fragment that would
    render as if it were a complete snippet in the numbered list."""
    from njit_auditor.report_outputs import audit_findings_to_json_dict

    # Deliberately exceeds both the item-count and total-length limits.
    oversized_items = [f"item number {i} " + ("x" * 80) for i in range(1, 10)]
    oversized_value = " | ".join(oversized_items)
    finding = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=5,
        message="Right margin overflow.",
        details={
            "issue_type": "margin_boundary_violation",
            "affected_line_texts": oversized_value,
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    exported = payload["findings"][0]["details"]["affected_line_texts"]

    kept_items = exported.split(" | ") if exported else []
    # Every surviving item must be one of the original whole items verbatim
    # -- never a prefix/suffix fragment of one.
    for item in kept_items:
        assert item in oversized_items, f"found a non-whole-item fragment: {item!r}"
    # Bounded: neither the item count nor the total size can grow unbounded.
    assert len(kept_items) <= 6
    assert len(exported) <= 340


def test_multi_item_detail_item_count_capped_even_when_short() -> None:
    """Many short items must still be capped by item count, not just length --
    the total-length bound alone wouldn't stop unbounded item counts if every
    item were tiny."""
    from njit_auditor.report_outputs import audit_findings_to_json_dict

    many_short_items = [f"i{i}" for i in range(1, 21)]  # 20 tiny items
    finding = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=5,
        message="Right margin overflow.",
        details={
            "issue_type": "margin_boundary_violation",
            "affected_line_texts": " | ".join(many_short_items),
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    exported = payload["findings"][0]["details"]["affected_line_texts"]
    assert exported.split(" | ") == many_short_items[:6]


def test_matching_numbered_markers_drawn_beside_overflow_boxes(tmp_path: Path) -> None:
    """When a finding has 2+ *separated* affected lines (non-adjacent groups),
    each overflow-segment box gets a small numbered text label matching the
    review note's numbered list. Lines must be non-adjacent (a clean line
    between them) so they form two separate groups/boxes -- two immediately
    adjacent lines merge into a single box (see
    test_adjacent_right_margin_lines_merge_without_extra_content in
    test_p011_margin_visual_polish.py), which needs no marker."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    over_text = "This line runs well past the required right margin boundary xxxxxx"
    x0 = _text_at_x1(over_text, ALLOWED_X1 + 15, 11)
    page.insert_text((x0, 100.0), over_text, fontsize=11)
    page.insert_text((150, 120.0), "A normal clean line well inside the margins.", fontsize=11)
    page.insert_text((x0, 300.0), over_text, fontsize=11)
    pdf_path = tmp_path / "two_line_marker.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]
    assert len(warnings) == 1
    details = warnings[0].details
    assert details["affected_line_count"] == "2"

    from njit_auditor.pdf_highlight import build_highlighted_single_page_pdf

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    out_path = tmp_path / "marked.pdf"
    build_highlighted_single_page_pdf(pdf_path, out_path, source_page_number=1, boxes=boxes)

    out_doc = fitz.open(out_path)
    words = out_doc[0].get_text("words")
    markers = sorted(w[4] for w in words if w[4] in ("1", "2") and w[0] > ALLOWED_X1)
    assert markers == ["1", "2"], f"expected numbered markers 1 and 2, found: {markers}"
    out_doc.close()


def test_single_overflow_box_gets_no_marker(tmp_path: Path) -> None:
    """A single-line finding needs no marker -- nothing to disambiguate."""
    text = "This line runs well past the required right margin boundary xxxxxx"
    x0 = _text_at_x1(text, ALLOWED_X1 + 15, 11)
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 120), text, fontsize=11)
    pdf_path = tmp_path / "single_marker.pdf"
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]
    details = warnings[0].details

    from njit_auditor.pdf_highlight import build_highlighted_single_page_pdf

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    out_path = tmp_path / "marked_single.pdf"
    build_highlighted_single_page_pdf(pdf_path, out_path, source_page_number=1, boxes=boxes)

    out_doc = fitz.open(out_path)
    words = out_doc[0].get_text("words")
    markers = [w[4] for w in words if w[4] == "1" and w[0] > ALLOWED_X1]
    assert markers == []
    out_doc.close()


# ---------------------------------------------------------------------------
# Mobile parity (task E, unit-level: server response shape is identical
# regardless of client User-Agent/viewport -- the server never branches on
# device type for correctness-relevant output).
# ---------------------------------------------------------------------------


def test_highlighted_page_response_identical_for_desktop_and_mobile_ua(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_make_p011(4, x0=520.0, count=1)])
    url = (
        f"/audits/{job_id}/highlighted-page.pdf"
        "?page=4&rule_id=P011&issue_type=margin_boundary_violation"
    )
    desktop_resp = c.get(url, headers=_DESKTOP_HEADERS)
    mobile_resp = c.get(url, headers=_MOBILE_SAFARI_HEADERS)
    assert desktop_resp.status_code == mobile_resp.status_code == 200
    assert desktop_resp.headers["content-type"] == "application/pdf"
    assert mobile_resp.headers["content-type"] == "application/pdf"
    assert desktop_resp.content == mobile_resp.content


def test_composite_page_view_renders_for_mobile_safari_without_error(
    app: tuple[TestClient, Any],
) -> None:
    c, wa = app
    job_id = _inject_job(wa, [_make_p013(7), _make_p020(7), _make_p030(7)])
    resp = c.get(f"/audits/{job_id}/problems/page/7", headers=_MOBILE_SAFARI_HEADERS)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    # No stray JSON/error body -- a real rendered page.
    assert "<html" in resp.text.lower()


# ---------------------------------------------------------------------------
# Real-browser checks (task E/5): long labels must wrap, not overflow, and a
# page with many findings (11+, matching real-world List of Figures/Tables
# pages) must stay usable at a narrow mobile width. Mirrors the exact
# Playwright pattern in test_ui_help_mobile_overflow.py.
# ---------------------------------------------------------------------------

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright


@pytest.fixture()
def app_url(tmp_path: Path):
    import threading
    import time

    import uvicorn

    _, wa = _make_app(tmp_path)
    config = uvicorn.Config(wa.app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started
    host, port = server.servers[0].sockets[0].getsockname()[:2]
    yield f"http://{host}:{port}", wa
    server.should_exit = True
    thread.join(timeout=5)


def _no_horizontal_overflow(page: Any) -> bool:
    return page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          return doc.scrollWidth <= doc.clientWidth + 1
            && body.scrollWidth <= body.clientWidth + 1;
        }"""
    )


def test_composite_page_view_no_overflow_with_long_labels_and_many_findings(
    app_url: tuple[str, Any],
) -> None:
    """An artificially long issue-type label plus 11 findings on one page
    (matching the real-world List of Figures/Tables scale this feature was
    built to handle) must not force horizontal scrolling at 390px."""
    base_url, wa = app_url
    long_label_finding = AuditFinding(
        rule_id="P020",
        severity=Severity.WARNING,
        page=9,
        message="Capitalization issue.",
        details={
            "issue_type": "possible_title_capitalization_issue",
            "confidence": "medium",
        },
    )
    # P013 is deliberately excluded here: its page_number_candidate findings
    # are informational and filtered from the visible/counted list by
    # report_view's own triage -- not something this feature changes, so
    # this stress test uses only rule/issue-type combos that stay visible.
    # P020 findings without a distinguishing flagged word are intentionally
    # collapsed to one representative card by report_view's own display-dedup
    # (pre-existing behavior, unrelated to this feature) -- P030 with varied
    # bboxes stays distinct, so it's used here to reach a genuine 11 cards.
    findings = [long_label_finding] + [_make_p030(9, variant=i) for i in range(1, 11)]
    job_id = _inject_job(wa, findings)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(f"{base_url}/audits/{job_id}/problems/page/9", wait_until="networkidle")
        overflow_ok = _no_horizontal_overflow(page)
        marker_count = page.locator(".example-card__marker").count()
        browser.close()

    assert overflow_ok is True
    assert marker_count == 11
