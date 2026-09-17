"""Diagnostic-only page-relative spacing experiment for R036/P036.

This module intentionally does not participate in production auditing.
It reuses the current R036 entry reconstruction and structural exemptions,
then evaluates page-relative spacing models over the surviving inter-entry
gaps without changing :func:`check_pdf_toc_list_entry_spacing`.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
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

MIN_PAGE_GAPS_FOR_PAGE_MODEL = 5
MAD_SCALE = 1.4826
MEDIAN_RELATIVE_FLOOR = 0.72
ROBUST_Z_FLOOR = -2.5
LOWER_TAIL_PERCENTILE = 0.10
NEIGHBOR_RELATIVE_FLOOR = 0.72
NORMAL_NEIGHBOR_FLOOR = 0.90
CLUSTER_SEPARATION_RATIO = 0.80
WRAP_Y0_TOLERANCE_PT = 2.0


class DiagnosticOutcome(str, Enum):
    ANOMALY = "POTENTIAL_PAGE_RELATIVE_ANOMALY"
    SUPPRESSED = "SUPPRESSED_AS_NORMAL_PAGE_RHYTHM"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class DiagnosticModel(str, Enum):
    MEDIAN_RELATIVE = "Model A - Median-relative ratio"
    ROBUST_Z = "Model B - Robust z-score"
    LOWER_TAIL = "Model C - Lower-tail percentile"
    TWO_MODE = "Model D - Two-mode clustering"
    NEIGHBOR_RELATIVE = "Model E - Neighbor-relative anomaly"


@dataclass(frozen=True)
class PageSpacingStats:
    document: str
    page_number: int
    section_type: str
    count: int
    median_pitch: float | None
    median_normalized_ratio: float | None
    q1_pitch: float | None
    q3_pitch: float | None
    mad_pitch: float | None
    p10_pitch: float | None
    p25_pitch: float | None
    p75_pitch: float | None
    pitch_values: tuple[float, ...]
    normalized_ratio_values: tuple[float, ...]


@dataclass(frozen=True)
class SpacingCandidate:
    document: str
    page_number: int
    section_type: str
    entry_pair_index: int
    previous_entry: str
    next_entry: str
    previous_level: str
    next_level: str
    previous_wraps: bool
    next_wraps: bool
    previous_x0: float
    next_x0: float
    pitch_pt: float
    local_single_line_pitch_pt: float
    normalized_ratio: float
    page_stats: PageSpacingStats | None = None

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.document, self.page_number, self.entry_pair_index)


@dataclass(frozen=True)
class ModelDecision:
    model: DiagnosticModel
    outcome: DiagnosticOutcome
    score: float | None
    reason: str


@dataclass(frozen=True)
class EvaluatedCandidate:
    candidate: SpacingCandidate
    decisions: dict[DiagnosticModel, ModelDecision] = field(default_factory=dict)


def _wraps(entry: list) -> bool:
    if len(entry) < 2:
        return False
    y0s = [line.bbox.y0 for line in entry]
    return max(y0s) - min(y0s) > WRAP_Y0_TOLERANCE_PT


def _entry_text(entry: list) -> str:
    return sanitize_toc_list_entry_preview(" ".join(line.text for line in entry), max_len=220)


def _percentile(sorted_values: list[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = fraction * (len(sorted_values) - 1)
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return sorted_values[lower]
    weight = pos - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _rank_percentile(values: tuple[float, ...], value: float) -> float:
    if len(values) <= 1:
        return 1.0
    below = sum(1 for item in values if item < value)
    equal = sum(1 for item in values if item == value)
    midpoint_rank = below + ((equal + 1) / 2)
    return (midpoint_rank - 1) / (len(values) - 1)


def _mad(values: list[float], median: float) -> float:
    deviations = [abs(value - median) for value in values]
    return statistics.median(deviations) if deviations else 0.0


def _page_stats(
    document: str, page_number: int, section_type: str, candidates: list[SpacingCandidate]
) -> PageSpacingStats:
    pitches = sorted(candidate.pitch_pt for candidate in candidates)
    ratios = sorted(candidate.normalized_ratio for candidate in candidates)
    if not pitches:
        return PageSpacingStats(
            document=document,
            page_number=page_number,
            section_type=section_type,
            count=0,
            median_pitch=None,
            median_normalized_ratio=None,
            q1_pitch=None,
            q3_pitch=None,
            mad_pitch=None,
            p10_pitch=None,
            p25_pitch=None,
            p75_pitch=None,
            pitch_values=(),
            normalized_ratio_values=(),
        )
    median_pitch = statistics.median(pitches)
    return PageSpacingStats(
        document=document,
        page_number=page_number,
        section_type=section_type,
        count=len(pitches),
        median_pitch=median_pitch,
        median_normalized_ratio=statistics.median(ratios),
        q1_pitch=_percentile(pitches, 0.25),
        q3_pitch=_percentile(pitches, 0.75),
        mad_pitch=_mad(pitches, median_pitch),
        p10_pitch=_percentile(pitches, 0.10),
        p25_pitch=_percentile(pitches, 0.25),
        p75_pitch=_percentile(pitches, 0.75),
        pitch_values=tuple(pitches),
        normalized_ratio_values=tuple(ratios),
    )


def collect_r036_spacing_candidates(
    pdf_document: PdfDocument, *, document_name: str = ""
) -> list[SpacingCandidate]:
    """Collect every eligible R036 inter-entry gap after current exemptions.

    This mirrors production reconstruction through the structural-exemption
    step, but deliberately does not apply ``MIN_INTER_ENTRY_GAP_RATIO``.
    """
    collected: list[SpacingCandidate] = []
    for context in detect_toc_like_pages(pdf_document):
        lines = _collect_entry_region_lines(context)
        entries = _group_lines_into_entries(lines, context.page_type)
        if len(entries) < 2:
            continue

        page_fallback_height = _estimate_line_height(lines[0], lines[0]) or FALLBACK_LINE_HEIGHT_PT
        heading_pitches, entry_pitches = _internal_wrap_pitches_by_role(entries, context.page_type)
        page_candidates: list[SpacingCandidate] = []

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
                SpacingCandidate(
                    document=document_name,
                    page_number=context.page.page_number,
                    section_type=context.page_type,
                    entry_pair_index=pair_index,
                    previous_entry=_entry_text(previous_entry),
                    next_entry=_entry_text(next_entry),
                    previous_level=prev_level,
                    next_level=next_level,
                    previous_wraps=_wraps(previous_entry),
                    next_wraps=_wraps(next_entry),
                    previous_x0=last_line.bbox.x0,
                    next_x0=first_line.bbox.x0,
                    pitch_pt=pitch_pt,
                    local_single_line_pitch_pt=local_single_line_pitch,
                    normalized_ratio=pitch_pt / local_single_line_pitch,
                )
            )

        stats = _page_stats(
            document_name, context.page.page_number, context.page_type, page_candidates
        )
        collected.extend(
            SpacingCandidate(
                document=candidate.document,
                page_number=candidate.page_number,
                section_type=candidate.section_type,
                entry_pair_index=candidate.entry_pair_index,
                previous_entry=candidate.previous_entry,
                next_entry=candidate.next_entry,
                previous_level=candidate.previous_level,
                next_level=candidate.next_level,
                previous_wraps=candidate.previous_wraps,
                next_wraps=candidate.next_wraps,
                previous_x0=candidate.previous_x0,
                next_x0=candidate.next_x0,
                pitch_pt=candidate.pitch_pt,
                local_single_line_pitch_pt=candidate.local_single_line_pitch_pt,
                normalized_ratio=candidate.normalized_ratio,
                page_stats=stats,
            )
            for candidate in page_candidates
        )
    return collected


def _insufficient(candidate: SpacingCandidate, model: DiagnosticModel) -> ModelDecision | None:
    stats = candidate.page_stats
    if stats is None or stats.count < MIN_PAGE_GAPS_FOR_PAGE_MODEL:
        count = 0 if stats is None else stats.count
        return ModelDecision(
            model=model,
            outcome=DiagnosticOutcome.INSUFFICIENT_CONTEXT,
            score=None,
            reason=(
                f"page has {count} eligible gap(s); need at least "
                f"{MIN_PAGE_GAPS_FOR_PAGE_MODEL}"
            ),
        )
    return None


def _evaluate_median_relative(candidate: SpacingCandidate) -> ModelDecision:
    model = DiagnosticModel.MEDIAN_RELATIVE
    if (decision := _insufficient(candidate, model)) is not None:
        return decision
    assert candidate.page_stats is not None
    median = candidate.page_stats.median_pitch or 0.0
    if median <= 0:
        return ModelDecision(
            model, DiagnosticOutcome.INSUFFICIENT_CONTEXT, None, "page median pitch unavailable"
        )
    ratio = candidate.pitch_pt / median
    if ratio <= MEDIAN_RELATIVE_FLOOR:
        return ModelDecision(
            model,
            DiagnosticOutcome.ANOMALY,
            ratio,
            f"gap/page median ratio {ratio:.2f} <= {MEDIAN_RELATIVE_FLOOR:.2f}",
        )
    return ModelDecision(
        model,
        DiagnosticOutcome.SUPPRESSED,
        ratio,
        f"gap/page median ratio {ratio:.2f} is within page rhythm",
    )


def _evaluate_robust_z(candidate: SpacingCandidate) -> ModelDecision:
    model = DiagnosticModel.ROBUST_Z
    if (decision := _insufficient(candidate, model)) is not None:
        return decision
    assert candidate.page_stats is not None
    median = candidate.page_stats.median_pitch or 0.0
    mad = candidate.page_stats.mad_pitch or 0.0
    if median <= 0 or mad <= 0:
        return ModelDecision(
            model,
            DiagnosticOutcome.SUPPRESSED,
            None,
            "page spread is zero; no lower-tail outlier exists",
        )
    robust_z = (candidate.pitch_pt - median) / (mad * MAD_SCALE)
    if robust_z <= ROBUST_Z_FLOOR:
        return ModelDecision(
            model,
            DiagnosticOutcome.ANOMALY,
            robust_z,
            f"robust z-score {robust_z:.2f} <= {ROBUST_Z_FLOOR:.2f}",
        )
    return ModelDecision(
        model,
        DiagnosticOutcome.SUPPRESSED,
        robust_z,
        f"robust z-score {robust_z:.2f} is not extreme",
    )


def _evaluate_lower_tail(candidate: SpacingCandidate) -> ModelDecision:
    model = DiagnosticModel.LOWER_TAIL
    if (decision := _insufficient(candidate, model)) is not None:
        return decision
    assert candidate.page_stats is not None
    percentile = _rank_percentile(candidate.page_stats.pitch_values, candidate.pitch_pt)
    if percentile <= LOWER_TAIL_PERCENTILE and len(set(candidate.page_stats.pitch_values)) > 1:
        return ModelDecision(
            model,
            DiagnosticOutcome.ANOMALY,
            percentile,
            f"gap rank percentile {percentile:.2f} <= {LOWER_TAIL_PERCENTILE:.2f}",
        )
    return ModelDecision(
        model,
        DiagnosticOutcome.SUPPRESSED,
        percentile,
        f"gap rank percentile {percentile:.2f} is not an extreme lower-tail point",
    )


def _best_two_cluster_split(values: tuple[float, ...]) -> tuple[float, float, float] | None:
    unique = sorted(set(values))
    if len(unique) < 2:
        return None
    best: tuple[float, float, float] | None = None
    for split_index in range(1, len(unique)):
        low = [value for value in values if value <= unique[split_index - 1]]
        high = [value for value in values if value >= unique[split_index]]
        if not low or not high:
            continue
        low_median = statistics.median(low)
        high_median = statistics.median(high)
        if high_median <= 0:
            continue
        within = sum((value - low_median) ** 2 for value in low) + sum(
            (value - high_median) ** 2 for value in high
        )
        if best is None or within < best[2]:
            best = (low_median, high_median, within)
    return best


def _evaluate_two_mode(candidate: SpacingCandidate) -> ModelDecision:
    model = DiagnosticModel.TWO_MODE
    if (decision := _insufficient(candidate, model)) is not None:
        return decision
    assert candidate.page_stats is not None
    split = _best_two_cluster_split(candidate.page_stats.pitch_values)
    if split is None:
        return ModelDecision(model, DiagnosticOutcome.SUPPRESSED, None, "no distinct modes")
    low_median, high_median, _within = split
    separation = low_median / high_median if high_median > 0 else 1.0
    in_low_mode = candidate.pitch_pt <= low_median
    low_count = sum(1 for value in candidate.page_stats.pitch_values if value <= low_median)
    high_count = candidate.page_stats.count - low_count
    if (
        in_low_mode
        and low_count < high_count
        and separation <= CLUSTER_SEPARATION_RATIO
    ):
        return ModelDecision(
            model,
            DiagnosticOutcome.ANOMALY,
            separation,
            f"lower spacing mode is separated from dominant mode ({separation:.2f})",
        )
    return ModelDecision(
        model,
        DiagnosticOutcome.SUPPRESSED,
        separation,
        "candidate is not in a smaller, clearly separated tight mode",
    )


def _neighbor_pitches(candidates: list[SpacingCandidate], index: int) -> list[float]:
    out: list[float] = []
    for offset in (-2, -1, 1, 2):
        neighbor_index = index + offset
        if 0 <= neighbor_index < len(candidates):
            out.append(candidates[neighbor_index].pitch_pt)
    return out


def _evaluate_neighbor_relative(
    candidate: SpacingCandidate, page_candidates: list[SpacingCandidate], index: int
) -> ModelDecision:
    model = DiagnosticModel.NEIGHBOR_RELATIVE
    if (decision := _insufficient(candidate, model)) is not None:
        return decision
    neighbors = _neighbor_pitches(page_candidates, index)
    if len(neighbors) < 2:
        return ModelDecision(
            model,
            DiagnosticOutcome.INSUFFICIENT_CONTEXT,
            None,
            "fewer than two nearby gaps available",
        )
    neighbor_median = statistics.median(neighbors)
    if neighbor_median <= 0:
        return ModelDecision(
            model, DiagnosticOutcome.INSUFFICIENT_CONTEXT, None, "bad neighbor median"
        )
    ratio = candidate.pitch_pt / neighbor_median
    has_normal_neighbor = max(neighbors) / neighbor_median >= NORMAL_NEIGHBOR_FLOOR
    if ratio <= NEIGHBOR_RELATIVE_FLOOR and has_normal_neighbor:
        return ModelDecision(
            model,
            DiagnosticOutcome.ANOMALY,
            ratio,
            f"gap/nearby median ratio {ratio:.2f} <= {NEIGHBOR_RELATIVE_FLOOR:.2f}",
        )
    return ModelDecision(
        model,
        DiagnosticOutcome.SUPPRESSED,
        ratio,
        f"gap/nearby median ratio {ratio:.2f} is consistent with local rhythm",
    )


def evaluate_page_relative_models(
    candidates: list[SpacingCandidate],
) -> list[EvaluatedCandidate]:
    by_page: dict[tuple[str, int, str], list[SpacingCandidate]] = {}
    for candidate in candidates:
        by_page.setdefault(
            (candidate.document, candidate.page_number, candidate.section_type), []
        ).append(candidate)

    evaluated: list[EvaluatedCandidate] = []
    for page_candidates in by_page.values():
        ordered = sorted(page_candidates, key=lambda candidate: candidate.entry_pair_index)
        for index, candidate in enumerate(ordered):
            decisions = {
                DiagnosticModel.MEDIAN_RELATIVE: _evaluate_median_relative(candidate),
                DiagnosticModel.ROBUST_Z: _evaluate_robust_z(candidate),
                DiagnosticModel.LOWER_TAIL: _evaluate_lower_tail(candidate),
                DiagnosticModel.TWO_MODE: _evaluate_two_mode(candidate),
                DiagnosticModel.NEIGHBOR_RELATIVE: _evaluate_neighbor_relative(
                    candidate, ordered, index
                ),
            }
            evaluated.append(EvaluatedCandidate(candidate=candidate, decisions=decisions))
    return sorted(
        evaluated,
        key=lambda item: (
            item.candidate.document,
            item.candidate.page_number,
            item.candidate.entry_pair_index,
        ),
    )


def selected_candidate_decision(evaluated: EvaluatedCandidate) -> ModelDecision:
    """Return the currently preferred diagnostic decision.

    Model E is selected because it asks whether a gap is tight relative to
    nearby page rhythm, while still abstaining on pages without enough
    comparable gaps.
    """
    return evaluated.decisions[DiagnosticModel.NEIGHBOR_RELATIVE]
