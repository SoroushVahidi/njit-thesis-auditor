"""Offline duplicate-*candidate* cluster analysis for visible findings.

Computes CANDIDATE clusters of visible findings that *might* represent the
same underlying student-facing defect, using only general structural
features (same page, bbox overlap, shared normalized issue-type label).

This module is diagnostic only:
  - it never mutates, suppresses, or reorders findings;
  - it never touches report generation (report_view.py / web_app.py never
    import from here);
  - it does no network calls, embeddings, or ML -- only geometry and exact
    string/label comparisons on data the report already computed;
  - it reads no dissertation body text -- only rule_id, issue_type, page,
    and bbox coordinates, none of which is private content.

Every result is a *candidate*, never a confirmed duplicate: whether two
rule_ids genuinely describe the same root cause (and therefore whether they
should ever be merged or suppressed) is a product/policy decision, not
something bbox geometry or label equality alone can decide. Callers must
treat every ``DuplicateCandidate`` as requiring human review.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

# Two findings on the same page whose bboxes overlap at least this much are
# geometric duplicate candidates worth surfacing for review.
DEFAULT_IOU_THRESHOLD = 0.3


def bbox_iou(
    a: tuple[float, float, float, float] | None,
    b: tuple[float, float, float, float] | None,
) -> float:
    """Intersection-over-union of two (x0, y0, x1, y1) boxes; 0.0 if either is missing/disjoint."""
    if not a or not b:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _stable_finding_id(index: int, fv: dict[str, Any]) -> str:
    """Prefer the report's own stable per-finding identifier over raw list
    position. ``problem_anchor``/``problem_number`` are the same identifiers
    already used for URL anchors and cross-view linking elsewhere in the
    report (see report_view.py) -- reusing them here means a human reviewing
    candidates can find "problem-12" in the actual report, unlike a bare
    list index, which is meaningless outside a single run and must never be
    used to reconstruct or link to a finding (see prior highlight-URL bug:
    list position is not a stable identifier).
    """
    anchor = str(fv.get("problem_anchor") or "").strip()
    if anchor:
        return anchor
    number = fv.get("problem_number")
    if number:
        return f"problem-{number}"
    return f"index-{index}"


@dataclass(frozen=True)
class DuplicateCandidate:
    """One CANDIDATE pair of findings that may describe the same defect.

    Not a confirmed duplicate. ``reasons`` states explicitly, in
    machine-readable form, why the pair was flagged, so a human reviewer
    (or a future automated policy layer) never has to re-derive the
    evidence from scratch.
    """

    page: int
    finding_id_a: str
    finding_id_b: str
    rule_id_a: str
    issue_type_a: str
    rule_id_b: str
    issue_type_b: str
    bbox_iou: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DuplicateClusterReport:
    candidates: tuple[DuplicateCandidate, ...] = field(default_factory=tuple)

    def by_rule_pair(self) -> dict[tuple[str, str], list[DuplicateCandidate]]:
        grouped: dict[tuple[str, str], list[DuplicateCandidate]] = {}
        for c in self.candidates:
            key_a = f"{c.rule_id_a}:{c.issue_type_a}"
            key_b = f"{c.rule_id_b}:{c.issue_type_b}"
            first, second = sorted([key_a, key_b])
            grouped.setdefault((first, second), []).append(c)
        return grouped


def find_geometric_duplicate_candidates(
    findings: Sequence[dict[str, Any]],
    *,
    iou_threshold: float = DEFAULT_IOU_THRESHOLD,
) -> DuplicateClusterReport:
    """Find same-page, bbox-overlapping CANDIDATE pairs across *different*
    (rule_id, issue_type) combinations.

    Same-rule/issue_type pairs are excluded here -- that is exact/near-exact
    duplication, already handled by each rule's own presentation-layer
    dedup key, not a cross-rule semantic-duplicate candidate. Two findings
    on the same object with different rule_ids are common and often
    *legitimately distinct* (e.g. one flags casing, the other flags
    punctuation, on the same list entry) -- bbox overlap alone never
    upgrades a pair past "candidate."

    ``findings`` are visible-finding dicts (post-suppression) with at
    least: rule_id, issue_type, page, bbox (4-tuple or None), and
    optionally problem_anchor/problem_number for stable identification.
    """
    by_page: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, fv in enumerate(findings):
        page = fv.get("page")
        bbox = fv.get("bbox")
        if page is None or not bbox:
            continue
        by_page.setdefault(int(page), []).append((index, fv))

    candidates: list[DuplicateCandidate] = []
    for page, items in by_page.items():
        for i in range(len(items)):
            idx_a, fv_a = items[i]
            for j in range(i + 1, len(items)):
                idx_b, fv_b = items[j]
                key_a = (fv_a.get("rule_id", ""), fv_a.get("issue_type", ""))
                key_b = (fv_b.get("rule_id", ""), fv_b.get("issue_type", ""))
                if key_a == key_b:
                    continue
                iou = bbox_iou(tuple(fv_a["bbox"]), tuple(fv_b["bbox"]))
                if iou < iou_threshold:
                    continue
                reasons = ["same_page", f"bbox_overlap:{iou:.2f}"]
                if fv_a.get("issue_type_label") == fv_b.get("issue_type_label"):
                    reasons.append("same_issue_type_label")
                candidates.append(
                    DuplicateCandidate(
                        page=page,
                        finding_id_a=_stable_finding_id(idx_a, fv_a),
                        finding_id_b=_stable_finding_id(idx_b, fv_b),
                        rule_id_a=str(key_a[0]),
                        issue_type_a=str(key_a[1]),
                        rule_id_b=str(key_b[0]),
                        issue_type_b=str(key_b[1]),
                        bbox_iou=iou,
                        reasons=tuple(reasons),
                    )
                )
    return DuplicateClusterReport(candidates=tuple(candidates))


def find_same_page_normalized_wording_candidates(
    findings: Sequence[dict[str, Any]],
) -> DuplicateClusterReport:
    """Find same-page CANDIDATE pairs across *different* rule_ids that share
    the identical student-facing ``issue_type`` label (post rule_id ->
    student issue-type normalization, e.g. P019 and P028 both surfacing
    "wrong_page_numbering_style"). This catches wording-level duplication
    that bbox overlap alone would miss when one of the two findings has no
    bbox at all (a common case for document-scope findings).
    """
    by_page: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, fv in enumerate(findings):
        page = fv.get("page")
        if page is None:
            continue
        by_page.setdefault(int(page), []).append((index, fv))

    candidates: list[DuplicateCandidate] = []
    for page, items in by_page.items():
        for i in range(len(items)):
            idx_a, fv_a = items[i]
            for j in range(i + 1, len(items)):
                idx_b, fv_b = items[j]
                rule_a, issue_a = fv_a.get("rule_id", ""), fv_a.get("issue_type", "")
                rule_b, issue_b = fv_b.get("rule_id", ""), fv_b.get("issue_type", "")
                if rule_a == rule_b:
                    continue
                if not issue_a or issue_a != issue_b:
                    continue
                bbox_a = fv_a.get("bbox")
                bbox_b = fv_b.get("bbox")
                iou = bbox_iou(
                    tuple(bbox_a) if bbox_a else None,
                    tuple(bbox_b) if bbox_b else None,
                )
                reasons = ["same_page", "same_normalized_issue_type"]
                if iou > 0:
                    reasons.append(f"bbox_overlap:{iou:.2f}")
                candidates.append(
                    DuplicateCandidate(
                        page=page,
                        finding_id_a=_stable_finding_id(idx_a, fv_a),
                        finding_id_b=_stable_finding_id(idx_b, fv_b),
                        rule_id_a=str(rule_a),
                        issue_type_a=str(issue_a),
                        rule_id_b=str(rule_b),
                        issue_type_b=str(issue_b),
                        bbox_iou=iou,
                        reasons=tuple(reasons),
                    )
                )
    return DuplicateClusterReport(candidates=tuple(candidates))
