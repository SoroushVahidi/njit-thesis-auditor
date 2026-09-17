"""Production page-relative R036/P036 suppression and abstention policy.

This is the productionized form of the page-relative diagnostic work
(``r036_page_relative_spacing_experiment.py``). It exists because the
previous production rule -- a fixed ``1.6`` inter-entry-pitch-to-
single-line-pitch ratio -- was contradicted by 24 Ester-confirmed false
positives (12 Praneeth page-11 examples and 12 post-recovery examples from
Muyeed, Philip, and Patrick) whose normalized ratios span 1.00 through
1.56. The fixed ratio therefore cannot be a reliable production
discriminator.

Production semantics
--------------------

Every eligible inter-entry gap is classified into exactly one of three
outcomes. Only ``REPORT`` produces a student-facing finding; the other two
emit nothing:

``SUPPRESS``
    The gap matches normal local page rhythm. Confident suppression: the
    page-relative normality evidence is well supported (the page has enough
    clean, structurally comparable gaps and the candidate is not materially
    tighter than them).

``ABSTAIN``
    Context is unreliable and we refuse to decide: the page is too sparse to
    model; the candidate's entries were reconstructed ambiguously (a
    continuation line was reattached as an entry start); the candidate
    touches an unreliable wrapped/reconstructed region whose neighbor
    baseline is untrustworthy; or the comparison neighborhood is not
    trustworthy. No finding is emitted and no absolute threshold is
    fallen back on.

``REPORT``
    Reserved for exceptionally clear, multi-signal-confirmed cases. Because
    no Ester-confirmed R036 *true positive* exists in the evaluation corpus,
    this path is intentionally conservative and, in the selected production
    design (see ``PRODUCTION_REPORTING_GATE``), disabled until a real true
    positive is validated. The gate machinery is kept so that enabling
    reporting later is a one-constant change, not a redesign.

Confidence separation
---------------------

Suppression confidence, abstention confidence, and reporting confidence are
kept distinct: page-relative normality can be used *confidently* to
suppress; structural/sparse uncertainty can be used *confidently* to
abstain; positive reporting requires a *stronger* evidentiary gate than the
diagnostic neighbor floor alone. Ambiguous candidates are never forced into
``SUPPRESS`` or ``REPORT`` -- they ``ABSTAIN``.

The fixed ``1.6`` constant (``MIN_INTER_ENTRY_GAP_RATIO`` in
``pdf_toc_list_entry_spacing.py``) no longer controls production reporting.
It is retained only for backward compatibility of imports and is documented
as retired.
"""

from __future__ import annotations

import contextlib
from enum import Enum

from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import detect_toc_like_pages
from njit_auditor.rules.pdf_toc_list_entry_spacing import (
    FALLBACK_LINE_HEIGHT_PT,
    _classify_entry_level,
    _group_lines_into_entries,
    _internal_wrap_pitches_by_role,
    _is_exempt_structural_transition,
    _local_single_line_pitch_pt,
)
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import (
    _collect_entry_region_lines,
    _estimate_line_height,
    _has_intervening_page_number_line,
)
from njit_auditor.toc_list_student_preview import sanitize_toc_list_entry_preview

# Minimum number of eligible inter-entry gaps on a page before page-local
# rhythm can be modeled. Below this the page is too sparse to make a
# reliable page-relative decision, so the policy abstains.
MIN_PAGE_GAPS_FOR_PAGE_MODEL = 5
# A candidate is "materially tighter than its reliable local rhythm" only
# when its pitch is at or below this fraction of the median clean-neighbor
# pitch. This is the diagnostic neighbor floor, promoted as the
# suppression/abstention boundary.
NEIGHBOR_RELATIVE_FLOOR = 0.72
# A neighbor is a trustworthy "normal rhythm" reference only when its pitch
# is at least this fraction of the neighbor median (guards against a
# baseline built from a single tight outlier).
NORMAL_NEIGHBOR_FLOOR = 0.90
# Continuation-indent geometry: a single-line LOF/LOT entry whose first
# visual line starts at least this far (pt) right of the page's
# entry-number column is a reassembly artifact and triggers abstention.
CONTINUATION_INDENT_OFFSET_PT = 12.0
# A wrapped entry's physical lines are contiguous when their baselines stay
# within this tolerance; larger spans indicate extraction detached a line.
WRAP_Y0_TOLERANCE_PT = 2.0

# ---------------------------------------------------------------------------
# Reporting gate.
#
# PRODUCTION_REPORTING_GATE selects the production reporting behavior:
#   * "suppression_abstention_only"  -> Design 0: never report. The
#     REPORT outcome is unreachable; the rule emits findings only if a real
#     true positive is later validated and this is changed. This is the
#     selected production design because there is no Ester-confirmed R036
#     true positive, so positive-detection capability is unvalidated on
#     real ground truth.
#   * "strong_multi_signal"          -> Designs 1-3 comparator: report only
#     when multiple independent signals agree (extreme local deviation AND
#     page-tail confirmation AND two-sided clean neighbors AND an absolute
#     sanity floor). Kept as the future extension point; not selected.
PRODUCTION_REPORTING_GATE: str = "suppression_abstention_only"
# Parameters for the "strong_multi_signal" gate (Designs 1-3). These are NOT
# active under the selected gate; they are retained so enabling reporting
# later is a one-line change to PRODUCTION_REPORTING_GATE.
STRONG_LOCAL_ANOMALY_FLOOR = 0.65
STRONG_PAGE_TAIL_PERCENTILE = 0.05
STRONG_MIN_TWO_SIDED_NEIGHBORS = 2
STRONG_ABSOLUTE_MIN_PITCH_RATIO = 0.85


class ProductionOutcome(str, Enum):
    """The three production R036 outcomes. Only REPORT emits a finding."""

    SUPPRESS = "SUPPRESS"
    ABSTAIN = "ABSTAIN"
    REPORT = "REPORT"


class AbstainReason(str, Enum):
    SPARSE_PAGE = "sparse_page"
    RECONSTRUCTION_UNCERTAINTY = "reconstruction_uncertainty"
    UNRELIABLE_NEIGHBORHOOD = "unreliable_neighborhood"


class ReportReason(str, Enum):
    STRONG_MULTI_SIGNAL_ANOMALY = "strong_multi_signal_anomaly"


class CandidateOutcome:
    """A candidate gap's production classification.

    ``outcome`` is one of :class:`ProductionOutcome`. ``abstain_reason`` is
    set only when ``outcome`` is ``ABSTAIN``; ``report_reason`` only when
    ``outcome`` is ``REPORT``. Internal detail (scores, neighbor counts) is
    carried for diagnostics/tests but is never emitted to students.
    """

    __slots__ = (
        "outcome",
        "abstain_reason",
        "report_reason",
        "entry_pair_index",
        "pitch_pt",
        "local_single_line_pitch_pt",
        "normalized_ratio",
        "neighbor_median_pt",
        "local_ratio",
        "clean_neighbor_count",
        "page_gap_count",
    )

    def __init__(
        self,
        outcome: ProductionOutcome,
        *,
        entry_pair_index: int,
        pitch_pt: float,
        local_single_line_pitch_pt: float,
        normalized_ratio: float,
        abstain_reason: AbstainReason | None = None,
        report_reason: ReportReason | None = None,
        neighbor_median_pt: float | None = None,
        local_ratio: float | None = None,
        clean_neighbor_count: int = 0,
        page_gap_count: int = 0,
    ) -> None:
        self.outcome = outcome
        self.abstain_reason = abstain_reason
        self.report_reason = report_reason
        self.entry_pair_index = entry_pair_index
        self.pitch_pt = pitch_pt
        self.local_single_line_pitch_pt = local_single_line_pitch_pt
        self.normalized_ratio = normalized_ratio
        self.neighbor_median_pt = neighbor_median_pt
        self.local_ratio = local_ratio
        self.clean_neighbor_count = clean_neighbor_count
        self.page_gap_count = page_gap_count

    def is_finding(self) -> bool:
        return self.outcome is ProductionOutcome.REPORT


def _wraps(entry: list) -> bool:
    if len(entry) < 2:
        return False
    y0s = [line.bbox.y0 for line in entry]
    return max(y0s) - min(y0s) > WRAP_Y0_TOLERANCE_PT


def _entry_text(entry: list) -> str:
    return sanitize_toc_list_entry_preview(" ".join(line.text for line in entry), max_len=220)


def _is_reconstructed_single_line_entry(
    candidate: dict, page_number_column: float | None
) -> bool:
    """A single-line LOF/LOT entry whose first visual line starts at the
    caption-continuation indent (right of the page's entry-number column) is
    a reassembly artifact: its true first line was detached by extraction and
    a continuation line was reattached as the entry start. Such entries make
    the measured gap a reconstruction artifact, so the policy abstains."""
    if candidate["section_type"] not in {"list_of_figures", "list_of_tables"}:
        return False
    if page_number_column is None:
        return False
    return candidate["previous_first_x0"] >= page_number_column + CONTINUATION_INDENT_OFFSET_PT


def _clean_neighbor_pitches(
    page_candidates: list[dict], index: int
) -> list[float]:
    """Nearest clean, non-lower-tail neighbor pitches on each side.

    A neighbor is clean when it does not touch a wrapped entry (LOF/LOT) and
    is not itself a lower-tail point that would drag the baseline down. TOC
    pages use the original fixed window (offsets -2..2 excluding the
    candidate) because their wrapped headings are common and legitimate and
    the fixed window was already validated against the reviewed TOC false
    positives."""
    section_type = page_candidates[index]["section_type"]
    if section_type == "table_of_contents":
        return [
            page_candidates[i]["pitch_pt"]
            for i in (index - 2, index - 1, index + 1, index + 2)
            if 0 <= i < len(page_candidates)
        ]

    other_clean = [
        c["pitch_pt"]
        for i, c in enumerate(page_candidates)
        if i != index and not (c["previous_wraps"] or c["next_wraps"])
    ]
    reference = _median(other_clean) if other_clean else None

    def _is_lower_tail(j: int) -> bool:
        if reference is None or reference <= 0:
            return False
        return page_candidates[j]["pitch_pt"] <= NEIGHBOR_RELATIVE_FLOOR * reference

    neighbors: list[float] = []
    for direction in (-1, 1):
        found = False
        for offset in range(1, len(page_candidates)):
            j = index + direction * offset
            if not 0 <= j < len(page_candidates):
                break
            neighbor = page_candidates[j]
            if neighbor["previous_wraps"] or neighbor["next_wraps"]:
                continue
            if _is_lower_tail(j):
                continue
            neighbors.append(neighbor["pitch_pt"])
            found = True
            break
        if not found:
            for offset in range(1, len(page_candidates)):
                j = index + direction * offset
                if 0 <= j < len(page_candidates):
                    neighbors.append(page_candidates[j]["pitch_pt"])
                    break
    return neighbors


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _rank_percentile(values: list[float], value: float) -> float:
    if len(values) <= 1:
        return 1.0
    below = sum(1 for item in values if item < value)
    equal = sum(1 for item in values if item == value)
    midpoint_rank = below + ((equal + 1) / 2)
    return (midpoint_rank - 1) / (len(values) - 1)


def _evaluate_candidate(
    candidate: dict,
    page_candidates: list[dict],
    index: int,
) -> CandidateOutcome:
    """Classify one candidate gap under the production policy."""
    page_gap_count = len(page_candidates)

    # Gate 1: structural reliability. A reconstructed entry (continuation
    # line reattached as an entry start) makes the gap a reconstruction
    # artifact -> abstain.
    if candidate["previous_entry_is_reconstructed"]:
        return CandidateOutcome(
            ProductionOutcome.ABSTAIN,
            entry_pair_index=candidate["entry_pair_index"],
            pitch_pt=candidate["pitch_pt"],
            local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
            normalized_ratio=candidate["normalized_ratio"],
            abstain_reason=AbstainReason.RECONSTRUCTION_UNCERTAINTY,
            page_gap_count=page_gap_count,
        )

    # Gate 2: page-context sufficiency. Too few eligible gaps -> abstain
    # (never fall back to an absolute threshold).
    if page_gap_count < MIN_PAGE_GAPS_FOR_PAGE_MODEL:
        return CandidateOutcome(
            ProductionOutcome.ABSTAIN,
            entry_pair_index=candidate["entry_pair_index"],
            pitch_pt=candidate["pitch_pt"],
            local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
            normalized_ratio=candidate["normalized_ratio"],
            abstain_reason=AbstainReason.SPARSE_PAGE,
            page_gap_count=page_gap_count,
        )

    neighbors = _clean_neighbor_pitches(page_candidates, index)
    neighbor_median = _median(neighbors)
    if neighbor_median is None or neighbor_median <= 0 or len(neighbors) < 2:
        return CandidateOutcome(
            ProductionOutcome.ABSTAIN,
            entry_pair_index=candidate["entry_pair_index"],
            pitch_pt=candidate["pitch_pt"],
            local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
            normalized_ratio=candidate["normalized_ratio"],
            abstain_reason=AbstainReason.UNRELIABLE_NEIGHBORHOOD,
            page_gap_count=page_gap_count,
            clean_neighbor_count=len(neighbors),
        )

    local_ratio = candidate["pitch_pt"] / neighbor_median
    has_normal_neighbor = max(neighbors) / neighbor_median >= NORMAL_NEIGHBOR_FLOOR

    # Gate 3: normal-rhythm suppression. Not materially tighter than the
    # reliable local rhythm (and a normal neighbor exists) -> suppress.
    if local_ratio > NEIGHBOR_RELATIVE_FLOOR or not has_normal_neighbor:
        return CandidateOutcome(
            ProductionOutcome.SUPPRESS,
            entry_pair_index=candidate["entry_pair_index"],
            pitch_pt=candidate["pitch_pt"],
            local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
            normalized_ratio=candidate["normalized_ratio"],
            neighbor_median_pt=neighbor_median,
            local_ratio=local_ratio,
            clean_neighbor_count=len(neighbors),
            page_gap_count=page_gap_count,
        )

    # The candidate is materially tighter than its reliable local rhythm.
    # Under the selected gate (Design 0) this still abstains: positive
    # detection is unvalidated on real ground truth, so we do not report.
    if PRODUCTION_REPORTING_GATE == "suppression_abstention_only":
        return CandidateOutcome(
            ProductionOutcome.ABSTAIN,
            entry_pair_index=candidate["entry_pair_index"],
            pitch_pt=candidate["pitch_pt"],
            local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
            normalized_ratio=candidate["normalized_ratio"],
            abstain_reason=AbstainReason.UNRELIABLE_NEIGHBORHOOD,
            neighbor_median_pt=neighbor_median,
            local_ratio=local_ratio,
            clean_neighbor_count=len(neighbors),
            page_gap_count=page_gap_count,
        )

    # Strong multi-signal gate (Designs 1-3 comparator; not selected).
    page_pitches = [c["pitch_pt"] for c in page_candidates]
    page_tail = _rank_percentile(page_pitches, candidate["pitch_pt"])
    two_sided = (
        len([n for n in neighbors if n >= candidate["pitch_pt"]])
        >= STRONG_MIN_TWO_SIDED_NEIGHBORS
    )
    absolute_ok = (
        candidate["pitch_pt"]
        >= STRONG_ABSOLUTE_MIN_PITCH_RATIO * candidate["local_single_line_pitch_pt"]
    )
    if (
        local_ratio <= STRONG_LOCAL_ANOMALY_FLOOR
        and page_tail <= STRONG_PAGE_TAIL_PERCENTILE
        and two_sided
        and absolute_ok
    ):
        return CandidateOutcome(
            ProductionOutcome.REPORT,
            entry_pair_index=candidate["entry_pair_index"],
            pitch_pt=candidate["pitch_pt"],
            local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
            normalized_ratio=candidate["normalized_ratio"],
            report_reason=ReportReason.STRONG_MULTI_SIGNAL_ANOMALY,
            neighbor_median_pt=neighbor_median,
            local_ratio=local_ratio,
            clean_neighbor_count=len(neighbors),
            page_gap_count=page_gap_count,
        )
    return CandidateOutcome(
        ProductionOutcome.ABSTAIN,
        entry_pair_index=candidate["entry_pair_index"],
        pitch_pt=candidate["pitch_pt"],
        local_single_line_pitch_pt=candidate["local_single_line_pitch_pt"],
        normalized_ratio=candidate["normalized_ratio"],
        abstain_reason=AbstainReason.UNRELIABLE_NEIGHBORHOOD,
        neighbor_median_pt=neighbor_median,
        local_ratio=local_ratio,
        clean_neighbor_count=len(neighbors),
        page_gap_count=page_gap_count,
    )


def classify_r036_spacing_candidates(
    pdf_document: PdfDocument, *, document_name: str = ""
) -> list[dict]:
    """Run the production page-relative R036 policy over every eligible gap.

    Returns one record per candidate gap with its :class:`CandidateOutcome`
    plus the geometry needed to build a finding (if REPORT). This is the
    decision core; :func:`run_r036_production` wraps it into findings.
    """
    records: list[dict] = []
    for context in detect_toc_like_pages(pdf_document):
        lines = _collect_entry_region_lines(context)
        entries = _group_lines_into_entries(lines, context.page_type)
        if len(entries) < 2:
            continue

        page_fallback_height = _estimate_line_height(lines[0], lines[0]) or FALLBACK_LINE_HEIGHT_PT
        heading_pitches, entry_pitches = _internal_wrap_pitches_by_role(entries, context.page_type)
        page_candidates: list[dict] = []

        for pair_index, (previous_entry, next_entry) in enumerate(zip(entries, entries[1:])):
            last_line = previous_entry[-1]
            first_line = next_entry[0]
            if _has_intervening_page_number_line(context, last_line, first_line):
                continue

            prev_level = _classify_entry_level(previous_entry[0].text, context.page_type)
            next_level = _classify_entry_level(next_entry[0].text, context.page_type)
            if _is_exempt_structural_transition(prev_level, next_level):
                continue

            pitch_pt = first_line.bbox.y0 - last_line.bbox.y0
            if pitch_pt <= 0:
                continue

            local_single_line_pitch = _local_single_line_pitch_pt(
                prev_level, heading_pitches, entry_pitches, page_fallback_height
            )
            if local_single_line_pitch <= 0:
                continue

            page_candidates.append(
                {
                    "entry_pair_index": pair_index,
                    "previous_entry": _entry_text(previous_entry),
                    "next_entry": _entry_text(next_entry),
                    "previous_level": prev_level,
                    "next_level": next_level,
                    "previous_wraps": _wraps(previous_entry),
                    "next_wraps": _wraps(next_entry),
                    "previous_first_x0": previous_entry[0].bbox.x0,
                    "previous_entry_line_count": len(previous_entry),
                    "last_line": last_line,
                    "first_line": first_line,
                    "pitch_pt": pitch_pt,
                    "local_single_line_pitch_pt": local_single_line_pitch,
                    "normalized_ratio": pitch_pt / local_single_line_pitch,
                    "section_type": context.page_type,
                    "page_number": context.page.page_number,
                }
            )

        if not page_candidates:
            continue

        page_number_column = min(
            c["previous_first_x0"] for c in page_candidates
        )
        for candidate in page_candidates:
            candidate["previous_entry_is_reconstructed"] = (
                candidate["previous_entry_line_count"] == 1
                and _is_reconstructed_single_line_entry(
                    candidate, page_number_column
                )
            )

        for index, candidate in enumerate(page_candidates):
            outcome = _evaluate_candidate(candidate, page_candidates, index)
            records.append({**candidate, "outcome": outcome})
    return records


def run_r036_production(
    pdf_document: PdfDocument,
    *,
    reporting_gate: str | None = None,
) -> tuple[list, list[dict]]:
    """Produce production R036 findings under the page-relative policy.

    Returns ``(findings, records)`` where ``records`` is the full
    per-candidate classification (for tests/diagnostics) and ``findings``
    contains one ``AuditFinding`` per ``REPORT`` outcome. Under the selected
    ``suppression_abstention_only`` gate, ``findings`` is empty.

    ``reporting_gate`` optionally overrides the module-level gate for a
    single call (used by the design-comparison evaluation); it is restored
    afterward.
    """
    gate = reporting_gate if reporting_gate is not None else PRODUCTION_REPORTING_GATE
    with _gate_override(gate):
        records = classify_r036_spacing_candidates(pdf_document)

    findings = [
        _build_finding(record)
        for record in records
        if record["outcome"].outcome is ProductionOutcome.REPORT
    ]
    return findings, records


@contextlib.contextmanager
def _gate_override(gate: str):
    """Temporarily set ``PRODUCTION_REPORTING_GATE`` for the duration of the
    block, restoring the previous value on exit. Module-global mutation is
    confined to this helper so the decision core stays pure."""
    import njit_auditor.rules.r036_production_page_relative_spacing as self_module

    previous = self_module.PRODUCTION_REPORTING_GATE
    self_module.PRODUCTION_REPORTING_GATE = gate
    try:
        yield
    finally:
        self_module.PRODUCTION_REPORTING_GATE = previous


def _build_finding(record: dict):
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.pdf_models import format_bbox_detail
    from njit_auditor.rules.pdf_toc_list_entry_spacing import (
        ISSUE_TYPE_BY_SECTION,
        SOURCE_Q_RULE_IDS_BY_SECTION,
    )
    from njit_auditor.toc_list_student_preview import gap_bbox_between_boxes

    section_type = record["section_type"]
    issue_type = ISSUE_TYPE_BY_SECTION[section_type]
    last_line = record["last_line"]
    first_line = record["first_line"]
    previous_preview = sanitize_toc_list_entry_preview(last_line.text)
    next_preview = sanitize_toc_list_entry_preview(first_line.text)
    gap_bbox = gap_bbox_between_boxes(last_line.bbox, first_line.bbox)
    local_single_line_pitch = record["local_single_line_pitch_pt"]
    details: dict[str, str] = {
        "page_number": str(record["page_number"]),
        "section_type": section_type,
        "issue_type": issue_type,
        "entry_pair_index": str(record["entry_pair_index"]),
        "gap_points": f"{record['pitch_pt']:.1f}",
        "required_gap_points": f"{local_single_line_pitch * 2.0:.1f}",
        "local_single_line_pitch_points": f"{local_single_line_pitch:.1f}",
        "gap_ratio": f"{record['normalized_ratio']:.2f}",
        "triage_tier": "high",
        "source_q_rule_ids": SOURCE_Q_RULE_IDS_BY_SECTION[section_type],
    }
    if previous_preview:
        details["previous_entry_preview"] = previous_preview
    if next_preview:
        details["next_entry_preview"] = next_preview
    if gap_bbox is not None:
        details["bbox"] = format_bbox_detail(gap_bbox)
    return AuditFinding(
        rule_id="P036",
        severity=Severity.WARNING,
        page=record["page_number"],
        message=(
            "Consecutive TOC/List entries appear to have insufficient "
            "inter-entry vertical spacing."
        ),
        details=details,
    )
