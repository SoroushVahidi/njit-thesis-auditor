#!/usr/bin/env python3
"""Privacy-safe P011 inventory for Sample A/B overnight audit.

Writes machine-readable output under /tmp only. No dissertation text committed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.p011_margin_presentation import (
    infer_margin_content_kind,
    infer_page_margin_context,
)
from njit_auditor.p011_student_preview import (
    collect_p011_margin_pages_from_serialized,
    consume_p011_finding_visibility,
    init_p011_display_state,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    LEFT_MARGIN_PT,
    OVERFLOW_TOLERANCE_PT,
    RIGHT_MARGIN_PT,
    TOP_MARGIN_PT,
    MarginSide,
    _group_confidence,
    _line_violation,
    _page_text,
)
from njit_auditor.web_samples import get_builtin_sample


def _finding_id(raw_index: int) -> str:
    return f"f{raw_index}"


OUT_DIR = Path("/tmp/njit-p011-audit-" + datetime.now(timezone.utc).strftime("%Y%m%d"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

_URL_RE = re.compile(r"https?://|www\.|\.com/|\.org/|doi\.org", re.I)
_EQUATION_RE = re.compile(r"[=+\-*/^_{}\\]|\\frac|\\sum|\\int")
_CAPTION_RE = re.compile(r"^(figure|table|fig\.|tab\.)\s*\d", re.I)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _redact_preview(text: str, max_len: int = 40) -> str:
    t = re.sub(r"\S+", "[token]", text.strip())
    return t[:max_len] if len(t) <= max_len else t[: max_len - 1] + "…"


def _classify_content(
    *,
    page_text: str,
    line_previews: list[str],
    page_context: str,
    content_kind: str,
) -> str:
    previews = " ".join(line_previews)
    if content_kind == "approval_signature":
        return "approval/signature material"
    if content_kind == "reference_entry":
        return "reference entry"
    if content_kind == "url":
        return "URL"
    if content_kind == "float_layout":
        return "table" if "table" in previews.lower() else "figure"
    if _URL_RE.search(previews):
        return "URL"
    if _EQUATION_RE.search(previews) and len(previews) < 80:
        return "equation"
    if _CAPTION_RE.search(previews):
        return "caption"
    if page_context in {"references"}:
        return "reference entry"
    if page_context == "approval_page":
        return "approval/signature material"
    if page_context == "abstract":
        return "body paragraph"
    if re.search(r"^#{0,3}\s|CHAPTER\s+\d", page_text[:500], re.I):
        return "heading"
    return "body paragraph"


def _adjudicate(
    *,
    worst_overflow: float,
    line_count: int,
    confidence: str,
    content_type: str,
) -> str:
    if confidence == "low":
        return "extraction or font-metric false positive"
    if worst_overflow < 5.0 and line_count == 1:
        return "extraction or font-metric false positive"
    if content_type == "URL" and worst_overflow < 12.0:
        return "probable true positive"
    if worst_overflow >= 12.0 or line_count >= 3:
        return "clear true positive"
    if worst_overflow >= 5.0:
        return "probable true positive"
    return "genuinely uncertain and requiring Esther's policy judgment"


@dataclass
class P011InventoryRow:
    sample: str
    raw_index: int
    finding_id: str
    visible: bool
    page: int
    side: str
    worst_overflow_pt: float
    min_overflow_pt: float
    line_count: int
    confidence: str
    page_context: str
    content_type: str
    bbox_hash: str
    highlight_bbox_count: int
    classification: str
    duplicate_group_key: str
    evidence: str = ""
    visible_problem_number: int = 0


def _raw_p011_rows(sample_id: str, pdf_path: Path) -> tuple[list[dict], list[P011InventoryRow]]:
    findings = run_pdf_audit_full(pdf_path)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    raw_list = payload.get("findings", [])
    layout = load_pdf_layout(str(pdf_path))
    page_text_by_no = {p.page_number: _page_text(p) for p in layout.pages}

    raw_rows: list[P011InventoryRow] = []
    serialized: list[dict] = []
    for idx, f in enumerate(raw_list):
        if not isinstance(f, dict) or f.get("rule_id") != "P011":
            continue
        details = f.get("details", {}) if isinstance(f.get("details"), dict) else {}
        if details.get("issue_type") != "margin_boundary_violation":
            continue
        page = int(f.get("page", 0) or 0)
        previews_raw = details.get("affected_line_texts", "")
        previews = [p.strip() for p in str(previews_raw).split("|") if p.strip()]
        page_text = page_text_by_no.get(page, "")
        page_context = infer_page_margin_context(page_text, previews)
        content_kind = infer_margin_content_kind(page_context, previews)
        content_type = _classify_content(
            page_text=page_text,
            line_previews=previews,
            page_context=page_context,
            content_kind=content_kind,
        )
        worst = float(details.get("worst_overflow_pt", "0") or 0)
        count = int(details.get("affected_line_count", "0") or 0)
        conf = str(details.get("confidence", ""))
        bbox = str(details.get("bbox", ""))
        hb = str(details.get("highlight_bboxes", ""))
        row = P011InventoryRow(
            sample=sample_id,
            raw_index=idx,
            finding_id=_finding_id(idx),
            visible=False,
            page=page,
            side=str(details.get("side", "")),
            worst_overflow_pt=worst,
            min_overflow_pt=worst,  # detector only stores worst per group
            line_count=count,
            confidence=conf,
            page_context=page_context,
            content_type=content_type,
            bbox_hash=_hash_text(bbox),
            highlight_bbox_count=len([x for x in hb.split("|") if x.strip()]),
            classification=_adjudicate(
                worst_overflow=worst,
                line_count=count,
                confidence=conf,
                content_type=content_type,
            ),
            duplicate_group_key=f"{page}|{details.get('side', '')}|{bbox[:30]}",
            evidence=(
                f"overflow={worst:.1f}pt lines={count} conf={conf} "
                f"context={page_context} kind={content_kind} "
                f"preview_hash={_hash_text('|'.join(previews))}"
            ),
        )
        raw_rows.append(row)
        serialized.append(
            {
                "raw_index": idx,
                "page": page,
                "side": details.get("side"),
                "worst_overflow_pt": worst,
                "line_count": count,
                "confidence": conf,
                "page_context": page_context,
                "content_type": content_type,
                "preview_redacted": [_redact_preview(p) for p in previews[:3]],
            }
        )

    view = build_report_view(payload)
    visible_indexes: set[int] = set()
    p011_entries = collect_p011_margin_pages_from_serialized(raw_list)
    p011_state = init_p011_display_state(p011_entries)
    for idx, f in enumerate(raw_list):
        if not isinstance(f, dict) or f.get("rule_id") != "P011":
            continue
        details = f.get("details", {}) if isinstance(f.get("details"), dict) else {}
        if details.get("issue_type") != "margin_boundary_violation":
            continue
        if consume_p011_finding_visibility(
            page=int(f.get("page", 0) or 0),
            side=str(details.get("side", "")),
            finding_index=idx,
            state=p011_state,
        ):
            visible_indexes.add(idx)

    visible_problem_by_page: dict[int, int] = {}
    for vf in view.findings:
        if vf.rule_id == "P011" and vf.page is not None:
            visible_problem_by_page[vf.page] = vf.problem_number

    for row in raw_rows:
        if row.raw_index in visible_indexes:
            row.visible = True
            row.visible_problem_number = visible_problem_by_page.get(row.page, 0)

    return serialized, raw_rows


def _boundary_near_misses(pdf_path: Path, *, flagged: set[tuple[int, str]]) -> list[dict]:
    """Find lines crossing margin not in emitted P011 (post-suppression)."""
    layout = load_pdf_layout(str(pdf_path))
    misses: list[dict] = []
    for page in layout.pages:
        allowed_x0 = LEFT_MARGIN_PT
        allowed_y0 = TOP_MARGIN_PT
        allowed_x1 = page.width - RIGHT_MARGIN_PT
        allowed_y1 = page.height - BOTTOM_MARGIN_PT
        line_index = 0
        grouped: dict[MarginSide, list] = defaultdict(list)
        for block in page.text_blocks:
            for line in block.lines:
                v = _line_violation(
                    line,
                    page.height,
                    allowed_x0,
                    allowed_y0,
                    allowed_x1,
                    allowed_y1,
                    line_index,
                )
                line_index += 1
                if v:
                    grouped[v.side].append(v)
        for side, violations in grouped.items():
            worst = max(v.overflow_pt for v in violations)
            count = len(violations)
            if worst <= OVERFLOW_TOLERANCE_PT:
                continue
            conf = _group_confidence(worst, count)
            key = (page.page_number, side.value)
            if key in flagged:
                continue
            reason = "suppressed_low_confidence" if conf == "low" else "suppressed_artifact_guard"
            if count >= 5 and worst < 8.0:
                reason = "suppressed_artifact_guard"
            misses.append(
                {
                    "page": page.page_number,
                    "side": side.value,
                    "worst_overflow_pt": round(worst, 2),
                    "line_count": count,
                    "confidence": conf,
                    "reason_not_visible": reason,
                    "preview_hash": _hash_text(violations[0].line.text.strip()[:80]),
                }
            )
    return misses


def _non_text_coverage(pdf_path: Path) -> dict[str, Any]:
    doc = fitz.open(pdf_path)
    image_rects = 0
    drawing_rects = 0
    text_only = 0
    for page in doc:
        for img in page.get_images(full=True):
            _ = img
            image_rects += 1
        for d in page.get_drawings():
            rect = d.get("rect")
            if rect:
                drawing_rects += 1
        text_only += 1
    doc.close()
    return {
        "pages": text_only,
        "image_instances": image_rects,
        "drawing_paths_with_rect": drawing_rects,
        "audited": "text lines only (pdf_margins.py)",
        "figures_checked": False,
        "raster_images_checked": False,
        "vector_drawings_checked": False,
        "table_borders_checked": False,
    }


def main() -> None:
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "samples": {},
    }
    all_rows: list[dict] = []
    for sample_id in ("ester_sample_a", "ester_sample_b"):
        sample = get_builtin_sample(sample_id)
        if not sample.abs_path.exists():
            print(f"SKIP {sample_id}: PDF missing", file=sys.stderr)
            continue
        serialized, rows = _raw_p011_rows(sample_id, sample.abs_path)
        visible = [r for r in rows if r.visible]
        flagged_keys = {(r.page, r.side) for r in rows}
        near_misses = _boundary_near_misses(sample.abs_path, flagged=flagged_keys)
        non_text = _non_text_coverage(sample.abs_path)

        by_class = defaultdict(int)
        by_conf = defaultdict(int)
        for r in visible:
            by_class[r.classification] += 1
            by_conf[r.confidence] += 1

        sample_summary = {
            "raw_p011_count": len(rows),
            "visible_p011_count": len(visible),
            "visible_pages": sorted({r.page for r in visible}),
            "by_classification": dict(by_class),
            "by_confidence": dict(by_conf),
            "boundary_near_misses": near_misses,
            "non_text_coverage": non_text,
        }
        summary["samples"][sample_id] = sample_summary
        all_rows.extend(asdict(r) for r in rows)

        (OUT_DIR / f"{sample_id}_p011_raw.json").write_text(
            json.dumps(serialized, indent=2), encoding="utf-8"
        )

    (OUT_DIR / "p011_inventory.json").write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    (OUT_DIR / "p011_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote inventory to {OUT_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
