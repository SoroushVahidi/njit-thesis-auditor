"""Shared helpers for the all-rules Ester evaluation-package batch.

Reuses the auditor's own audit pipeline and highlight-geometry utilities so
every rule's evidence is generated the same way the live web app would
generate it -- no rule-specific visualization is hand-coded here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from njit_auditor.audit_runner import run_audit_for_uploaded_file
from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.pdf_highlight import (
    build_highlighted_single_page_pdf,
    build_single_page_pdf,
    sub_page_location_label,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict

REPO_ROOT = Path(__file__).resolve().parents[2]
# Source PDFs live in the primary "main" checkout's private (gitignored) data
# dir -- never copied into this worktree, never committed.
PRIVATE_DATA_DIR = Path("/home/soroush/njit-thesis-auditor/main/data/evaluation/private")
CACHE_DIR = REPO_ROOT / "data" / "evaluation" / "generated" / "ester_all_rules_batch_20260819"
OUTPUT_DIR = REPO_ROOT / "docs" / "evaluation" / "ester_feedback"
LOG_DIR = REPO_ROOT / "logs"

# Fixed, deterministic document order (matches the task's own numbered list).
DOCS: list[tuple[str, str]] = [
    ("Philip", "Philip_Zaleski_Thesis_Revised (1).pdf"),
    ("Muyeed", "Muyeed_Dissertation (4).pdf"),
    ("Anthony", "Anthony.Sena 3rd Review Draft.pdf"),
    ("Praneeth", "Praneeth Ivan Joel. FNU_3rd review draft.pdf"),
    ("Patrick", "Thesis Patrick Grice July 22.pdf"),
    ("Youra", "5_Youra_Shin_PhD_Dissertation_Document_3rd review.pdf"),
    ("Sebastian", "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf"),
]

CONFIDENCE_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

_MEASURE_KEY_HINTS = (
    "overflow_pt",
    "overflow",
    "gap_pt",
    "gap_ratio",
    "measured",
    "distance_pt",
    "spacing_pt",
    "amount_pt",
)

_FLOAT_RE = re.compile(r"^-?\d+(\.\d+)?$")


def doc_pdf_path(filename: str) -> Path:
    return PRIVATE_DATA_DIR / filename


def cache_path(short_name: str) -> Path:
    return CACHE_DIR / f"{short_name.lower()}.json"


def build_full_audit_json(pdf_path: Path) -> dict[str, Any]:
    """Run the current, real auditor on *pdf_path* and return its JSON report.

    This is the exact same code path the web app uses
    (``run_audit_for_uploaded_file`` -> ``audit_findings_to_json_dict``), so
    every finding here -- including which ones get a ``problem_number`` (=
    actually shown to the user) -- matches live auditor behavior.
    """
    result = run_audit_for_uploaded_file(pdf_path)
    metadata = {
        "input_file_path": str(pdf_path),
        "input_file_name": pdf_path.name,
        "audit_type": result.audit_type,
    }
    return audit_findings_to_json_dict(result.findings, metadata)


def load_or_build_doc_findings(short_name: str, filename: str, *, force: bool = False) -> dict[str, Any]:
    path = cache_path(short_name)
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))
    payload = build_full_audit_json(doc_pdf_path(filename))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)
    return payload


def visible_findings_for_rule(doc_report: dict[str, Any], rule_id: str) -> list[dict[str, Any]]:
    """Findings the *current* auditor actually surfaces to the user for one rule.

    A finding only counts when it carries a ``problem_number`` (the same
    field the live report uses to decide what to show/number for the
    student) -- this is what excludes suppressed/raw candidates.
    """
    out = []
    for f in doc_report.get("findings", []):
        if f.get("rule_id") != rule_id:
            continue
        if f.get("severity") == "PASS":
            continue
        if f.get("problem_number") is None:
            continue
        out.append(f)
    return out


def finding_confidence(finding: dict[str, Any]) -> str:
    raw = str(finding.get("details", {}).get("confidence", "")).strip().upper()
    if raw in CONFIDENCE_RANK:
        return raw
    # This rule does not report graded confidence at all -- every surviving
    # finding is equally certain, so treat as HIGH (never LOW/MEDIUM, since
    # the auditor never emits those for this rule).
    return "HIGH"


def select_weakest_finding(findings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the lowest-confidence surviving finding; deterministic tie-break.

    Selection is purely by confidence rank (LOW < MEDIUM < HIGH). Whether a
    finding has a physical page is NEVER a selection criterion -- a
    document-level finding with ``page is None`` can legitimately be the
    weakest surviving finding, and must not be discarded in favor of a
    stronger, easier-to-visualize page-anchored finding. Callers render an
    appropriate document-level evidence page when the selected finding has
    no page.
    """
    if not findings:
        return None

    def sort_key(f: dict[str, Any]) -> tuple:
        conf = finding_confidence(f)
        details = f.get("details", {})
        first_box = None
        boxes = parse_highlight_bboxes_from_details(
            details, rule_id=f.get("rule_id", ""), issue_type=details.get("issue_type", "")
        )
        if boxes:
            first_box = round(boxes[0][0], 1)
        return (
            CONFIDENCE_RANK[conf],
            f.get("page") or 0,
            first_box if first_box is not None else 0.0,
            f.get("message", ""),
        )

    return sorted(findings, key=sort_key)[0]


def printed_page_for(doc_report: dict[str, Any], physical_page: int | None) -> str:
    """Best-effort printed/document page label for *physical_page*.

    Looks across *all* findings for the document (any rule) for a
    page-numbering finding that already carries a detected printed-page
    label for this physical page. Never guesses.
    """
    if physical_page is None:
        return "not reliably identifiable"
    for f in doc_report.get("findings", []):
        if f.get("page") != physical_page:
            continue
        label = str(f.get("details", {}).get("document_page_label", "")).strip()
        if label:
            return label
    return "not reliably identifiable"


def measured_amount(details: dict[str, Any]) -> str:
    for key, value in details.items():
        lower_key = key.lower()
        if not any(hint in lower_key for hint in _MEASURE_KEY_HINTS):
            continue
        text = str(value).strip()
        if _FLOAT_RE.match(text):
            label = key.replace("_", " ")
            return f"{text} ({label})"
    return "Not applicable for this rule"


@dataclass
class EvidenceResult:
    boxes: list[tuple[float, float, float, float]]
    location: str
    affected_lines: list[str]
    page_size: tuple[float, float] | None
    has_highlight: bool


def build_evidence(
    pdf_path: Path,
    physical_page: int | None,
    details: dict[str, Any],
    rule_id: str,
    out_pdf_path: Path,
) -> EvidenceResult:
    """Render a one-page evidence PDF for *physical_page*, highlighting the
    finding's own geometry when available, and extract minimal excerpt text
    strictly from the highlighted region(s)."""
    issue_type = str(details.get("issue_type", ""))
    boxes = parse_highlight_bboxes_from_details(details, rule_id=rule_id, issue_type=issue_type)

    if physical_page is None or physical_page < 1:
        return EvidenceResult([], "", [], None, False)

    with fitz.open(pdf_path) as doc:
        if physical_page > doc.page_count:
            return EvidenceResult([], "", [], None, False)
        page = doc[physical_page - 1]
        page_size = (page.rect.width, page.rect.height)
        location = sub_page_location_label(boxes[0] if boxes else None, page_size)

        affected_lines: list[str] = []
        for box in boxes[:4]:
            clip = fitz.Rect(*box)
            text = page.get_text("text", clip=clip).strip()
            text = " ".join(text.split())
            if len(text) > 160:
                text = text[:157] + "..."
            if text:
                affected_lines.append(text)

    if boxes:
        result = build_highlighted_single_page_pdf(
            pdf_path, out_pdf_path, source_page_number=physical_page, boxes=boxes
        )
        has_highlight = result.has_highlight
        if not has_highlight:
            build_single_page_pdf(pdf_path, out_pdf_path, source_page_number=physical_page)
    else:
        build_single_page_pdf(pdf_path, out_pdf_path, source_page_number=physical_page)
        has_highlight = False

    return EvidenceResult(boxes, location, affected_lines, page_size, has_highlight)
