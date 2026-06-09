"""Structured JSON/Markdown output helpers for audit findings."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.models import AuditFinding, Severity

MAX_DETAIL_TEXT_LEN = 120
# Rules with this many or more findings appear in high_volume_rules summary.
HIGH_VOLUME_THRESHOLD = 5
# Maximum page-range segments shown in compact page lists before truncation.
_MAX_COMPACT_RANGES = 8
P013_RULE_ID = "P013"
P013_PAGE_ISSUE_TYPE = "page_number_candidate"
P013_DOC_ISSUE_TYPE = "p013_document_overview"
P026_RULE_ID = "P026"
P026_FAMILY_ISSUE_TYPE = "possible_body_font_family_issue"
P026_SIZE_ISSUE_TYPE = "possible_body_font_size_issue"
P011_RULE_ID = "P011"
P011_ISSUE_TYPE = "margin_boundary_violation"
P012_RULE_ID = "P012"
P012_ISSUE_TYPE = "pdf_annotation_detected"
P019_RULE_ID = "P019"
P036_RULE_ID = "P036"


def _truncate(value: str, max_len: int = MAX_DETAIL_TEXT_LEN) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 3]}..."


def _sanitize_details(details: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in details.items():
        sanitized[key] = _truncate(str(value))
    return sanitized


def _severity_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = Counter(finding.severity.value for finding in findings)
    return {
        Severity.PASS.value: counts.get(Severity.PASS.value, 0),
        Severity.WARNING.value: counts.get(Severity.WARNING.value, 0),
        Severity.FAIL.value: counts.get(Severity.FAIL.value, 0),
    }


def _rule_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = Counter(finding.rule_id for finding in findings)
    return dict(sorted(counts.items()))


def _category_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for finding in findings:
        counts[map_finding_rule_to_category(finding.rule_id, finding.details)] += 1
    return dict(sorted(counts.items()))


def derive_source_issue_type(rule_id: str, details: dict[str, str] | None = None) -> str:
    """Map a source/TeX finding to a stable issue_type for export and comments."""
    safe = details or {}
    explicit = safe.get("issue_type", "").strip()
    if explicit:
        return explicit
    if rule_id == "P001":
        return "risky_command"
    if rule_id == "P002":
        return "duplicate_label"
    if rule_id == "P003":
        return "invalid_label"
    if rule_id == "P004":
        return "dangling_reference"
    if rule_id == "P005":
        return "missing_caption"
    if rule_id == "P006":
        return "missing_label"
    if rule_id == "P007":
        return "caption_punctuation"
    if rule_id == "P008":
        return "abstract_structure"
    if rule_id == "P009":
        return "chktex_warning"
    if rule_id == "P010":
        return "lacheck_warning"
    return "source_check"


def _source_location_basename(details: dict[str, str]) -> str:
    file_path = details.get("file", "").strip()
    if not file_path:
        return ""
    return Path(file_path).name


def _prepare_findings_for_export(
    findings: list[AuditFinding], audit_type: str
) -> list[AuditFinding]:
    """Return findings with export-friendly details (issue_type for source audits)."""
    if audit_type != "tex":
        return findings
    prepared: list[AuditFinding] = []
    for finding in findings:
        details = dict(finding.details)
        if not details.get("issue_type"):
            details["issue_type"] = derive_source_issue_type(finding.rule_id, details)
        prepared.append(
            AuditFinding(
                rule_id=finding.rule_id,
                severity=finding.severity,
                message=finding.message,
                page=finding.page,
                details=details,
            )
        )
    return prepared


def build_source_report(
    findings: list[AuditFinding],
    *,
    input_file_path: str,
    input_file_name: str,
    input_kind: str = "tex",
    main_tex_path: str = "",
    loaded_tex_file_count: int | None = None,
    job_id: str = "",
) -> dict[str, Any]:
    """Build a JSON-compatible source-audit report for TeX/ZIP uploads."""
    metadata: dict[str, str] = {
        "input_file_path": input_file_path,
        "input_file_name": input_file_name,
        "audit_type": "tex",
        "input_kind": input_kind,
        "main_tex_path": main_tex_path,
        "loaded_tex_file_count": (
            str(loaded_tex_file_count) if loaded_tex_file_count is not None else ""
        ),
        "job_id": job_id,
    }
    return audit_findings_to_json_dict(findings, metadata)


def build_audit_report(
    findings: list[AuditFinding],
    metadata: dict[str, str],
) -> dict[str, Any]:
    """Build a JSON-compatible report for PDF or source audits."""
    audit_type = metadata.get("audit_type", "pdf")
    prepared = _prepare_findings_for_export(findings, audit_type)
    return audit_findings_to_json_dict(prepared, metadata)


def compact_page_list(pages: list[int], max_ranges: int = _MAX_COMPACT_RANGES) -> str:
    """Convert a list of page numbers to a compact range string.

    Examples:
        [1, 2, 3, 5, 7, 8] → "1-3, 5, 7-8"
        Long lists truncated: "1-3, 5, 7-8, ... (42 pages)"
    """
    if not pages:
        return ""
    sorted_pages = sorted(set(pages))
    ranges: list[tuple[int, int]] = []
    start = end = sorted_pages[0]
    for page in sorted_pages[1:]:
        if page == end + 1:
            end = page
        else:
            ranges.append((start, end))
            start = end = page
    ranges.append((start, end))

    parts: list[str] = []
    for s, e in ranges[:max_ranges]:
        parts.append(str(s) if s == e else f"{s}-{e}")

    result = ", ".join(parts)
    if len(ranges) > max_ranges:
        result += f", ... ({len(sorted_pages)} pages total)"
    return result


def build_p013_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P013-specific rollup for high-volume page-number candidate triage.

    Raw findings are not modified. This summary separates document overview from
    per-page candidate warnings and adds position/style pattern page ranges.
    """
    p013_findings = [f for f in findings if f.rule_id == P013_RULE_ID]
    if not p013_findings:
        return None

    page_findings = [f for f in p013_findings if f.page is not None]
    doc_findings = [f for f in p013_findings if f.page is None]

    pages = sorted({f.page for f in page_findings if f.page is not None})
    position_type_counts: Counter[str] = Counter()
    number_style_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    issue_type_counts: Counter[str] = Counter()
    multi_candidate_pages: list[int] = []
    by_observed: dict[str, list[int]] = defaultdict(list)

    for finding in page_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_PAGE_ISSUE_TYPE)] += 1
        position_type = details.get("position_type", "")
        if position_type:
            position_type_counts[position_type] += 1
        number_style = details.get("number_style", "")
        if number_style:
            number_style_counts[number_style] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        try:
            candidate_count = int(details.get("candidate_count_on_page", "1"))
        except ValueError:
            candidate_count = 1
        if candidate_count > 1 and finding.page is not None:
            multi_candidate_pages.append(finding.page)
        observed = details.get("observed_summary", "")
        if observed and finding.page is not None:
            by_observed[observed].append(finding.page)

    for finding in doc_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_DOC_ISSUE_TYPE)] += 1

    pattern_page_ranges = {
        observed: compact_page_list(sorted(set(page_list)))
        for observed, page_list in sorted(
            by_observed.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    return {
        "raw_finding_count": len(p013_findings),
        "page_level_finding_count": len(page_findings),
        "document_overview_finding_count": len(doc_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "position_type_counts": dict(sorted(position_type_counts.items())),
        "number_style_counts": dict(sorted(number_style_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "pages_with_multiple_candidates": len(multi_candidate_pages),
        "multiple_candidate_pages_compact": compact_page_list(multi_candidate_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "triage_tier": "informational",
        "triage_note": (
            "P013 reports heuristic page-number candidates for manual NJIT verification. "
            "Page-level warnings are triage signals, not confirmed formatting defects."
        ),
    }


def _p026_pattern_key(issue_type: str, observed_summary: str) -> str:
    """Build a privacy-safe grouping key for P026 pattern page ranges."""
    observed = observed_summary.strip() or "(unspecified)"
    if len(observed) > 60:
        observed = f"{observed[:57]}..."
    return f"{issue_type}/{observed}"


def build_p026_font_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P026-specific rollup for high-volume body-font compliance triage.

    Raw findings are not modified. Groups consecutive pages by issue type and
    observed font label/size summary for compact pattern page ranges.
    """
    p026_findings = [f for f in findings if f.rule_id == P026_RULE_ID]
    if not p026_findings:
        return None

    pages = sorted({f.page for f in p026_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    font_label_counts: Counter[str] = Counter()
    size_label_counts: Counter[str] = Counter()
    by_pattern: dict[str, list[int]] = defaultdict(list)
    pages_by_issue: dict[str, set[int]] = defaultdict(set)

    for finding in p026_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        issue_type_counts[issue_type] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        observed = details.get("observed_summary", "").strip()
        if issue_type == P026_FAMILY_ISSUE_TYPE and observed:
            font_label_counts[observed] += 1
        elif issue_type == P026_SIZE_ISSUE_TYPE and observed:
            size_label_counts[observed] += 1
        if finding.page is not None:
            pages_by_issue[issue_type].add(finding.page)
            pattern_key = _p026_pattern_key(issue_type, observed)
            by_pattern[pattern_key].append(finding.page)

    family_pages = pages_by_issue.get(P026_FAMILY_ISSUE_TYPE, set())
    size_pages = pages_by_issue.get(P026_SIZE_ISSUE_TYPE, set())
    both_pages = sorted(family_pages & size_pages)

    pattern_page_ranges = {
        pattern: compact_page_list(sorted(set(page_list)))
        for pattern, page_list in sorted(
            by_pattern.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    return {
        "raw_finding_count": len(p026_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "font_label_counts": dict(
            font_label_counts.most_common(8),
        ),
        "size_observed_label_counts": dict(
            size_label_counts.most_common(8),
        ),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "pages_with_both_issue_types": len(both_pages),
        "both_issue_types_pages_compact": compact_page_list(both_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "triage_tier": "informational",
        "triage_note": (
            "P026 reports heuristic body-font size/family compliance warnings for manual "
            "NJIT verification. Page-level warnings are triage signals, not confirmed "
            "formatting defects."
        ),
    }


def _parse_overflow_pt(details: dict[str, str]) -> float | None:
    raw = details.get("worst_overflow_pt", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def build_p012_annotation_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P012-specific rollup for embedded PDF annotation/comment triage.

    Raw findings are not modified. Summaries use annotation types and page numbers
    only — never annotation text content.
    """
    p012_findings = [f for f in findings if f.rule_id == P012_RULE_ID]
    if not p012_findings:
        return None

    pages = sorted({f.page for f in p012_findings if f.page is not None})
    annotation_type_counts: Counter[str] = Counter()
    annotations_by_page: Counter[int] = Counter()
    by_type_pages: dict[str, list[int]] = defaultdict(list)

    for finding in p012_findings:
        details = finding.details or {}
        annotation_type = details.get("annotation_type", "") or "(unknown)"
        annotation_type_counts[annotation_type] += 1
        if finding.page is not None:
            annotations_by_page[finding.page] += 1
            by_type_pages[annotation_type].append(finding.page)

    multi_annotation_pages = sorted(
        page for page, count in annotations_by_page.items() if count > 1
    )
    type_page_ranges = {
        annotation_type: compact_page_list(sorted(set(page_list)))
        for annotation_type, page_list in sorted(
            by_type_pages.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    dominant_type = ""
    if annotation_type_counts:
        dominant_type = annotation_type_counts.most_common(1)[0][0]

    return {
        "raw_finding_count": len(p012_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "annotation_type_counts": dict(sorted(annotation_type_counts.items())),
        "annotations_per_page_max": (
            max(annotations_by_page.values()) if annotations_by_page else 0
        ),
        "pages_with_multiple_annotations": len(multi_annotation_pages),
        "multiple_annotations_pages_compact": compact_page_list(
            multi_annotation_pages
        ),
        "type_page_ranges": type_page_ranges,
        "dominant_annotation_type": dominant_type,
        "triage_tier": "informational",
        "triage_note": (
            "P012 reports embedded PDF annotations and reviewer comments for manual "
            "cleanup before final submission. This is an informational triage category; "
            "resolve or remove comments rather than treating each warning as a "
            "formatting defect."
        ),
        "recommended_action": (
            "Review affected pages, resolve feedback, and remove or flatten annotations "
            "before submitting the final PDF."
        ),
    }


def build_p011_margin_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P011-specific rollup for margin/overflow triage.

    Raw findings are not modified. Groups pages by margin side for compact ranges
    and summarizes overflow distance by side.
    """
    p011_findings = [
        f
        for f in findings
        if f.rule_id == P011_RULE_ID and f.severity == Severity.WARNING
    ]
    if not p011_findings:
        return None

    pages = sorted({f.page for f in p011_findings if f.page is not None})
    side_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    by_side: dict[str, list[int]] = defaultdict(list)
    overflow_by_side: dict[str, list[float]] = defaultdict(list)
    pages_by_side: dict[str, set[int]] = defaultdict(set)
    total_affected_lines = 0

    for finding in p011_findings:
        details = finding.details or {}
        side = details.get("side", "") or "(unspecified)"
        side_counts[side] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        try:
            total_affected_lines += int(details.get("affected_line_count", "0"))
        except ValueError:
            pass
        overflow = _parse_overflow_pt(details)
        if overflow is not None:
            overflow_by_side[side].append(overflow)
        if finding.page is not None:
            by_side[side].append(finding.page)
            pages_by_side[side].add(finding.page)

    page_side_count: Counter[int] = Counter()
    for page in pages:
        page_side_count[page] = sum(1 for s in pages_by_side.values() if page in s)
    multi_side_pages = sorted(page for page, n in page_side_count.items() if n > 1)

    pattern_page_ranges = {
        side: compact_page_list(sorted(set(page_list)))
        for side, page_list in sorted(
            by_side.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    max_overflow_by_side = {
        side: round(max(values), 1)
        for side, values in sorted(overflow_by_side.items())
        if values
    }
    median_overflow_by_side = {
        side: round(statistics.median(values), 1)
        for side, values in sorted(overflow_by_side.items())
        if values
    }

    dominant_side = side_counts.most_common(1)[0][0] if side_counts else ""

    return {
        "raw_finding_count": len(p011_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "side_counts": dict(sorted(side_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "total_affected_line_count": total_affected_lines,
        "max_overflow_by_side_pt": max_overflow_by_side,
        "median_overflow_by_side_pt": median_overflow_by_side,
        "pages_with_multiple_sides": len(multi_side_pages),
        "multiple_sides_pages_compact": compact_page_list(multi_side_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "dominant_margin_side": dominant_side,
        "triage_tier": "informational",
        "triage_note": (
            "P011 reports heuristic margin-boundary crossings for manual NJIT verification. "
            "Page-level warnings are triage signals, not confirmed layout defects. "
            "Many small same-side overflows on compressed PDFs may reflect coordinate shifts "
            "rather than true margin violations."
        ),
    }


def build_p019_page_numbering_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P019-specific rollup for page-numbering sequence/style triage.

    Raw findings are not modified. Groups by issue_type, triage_tier, and
    p019_triage_category. Never includes candidate text or page content.
    """
    p019_findings = [f for f in findings if f.rule_id == P019_RULE_ID]
    if not p019_findings:
        return None

    issue_type_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    affected_pages: list[int] = []

    for finding in p019_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1
        tier = details.get("triage_tier", "")
        if tier:
            triage_tier_counts[tier] += 1
        category = details.get("p019_triage_category", "")
        if category:
            category_counts[category] += 1
        if finding.page is not None:
            affected_pages.append(finding.page)

    return {
        "total_findings": len(p019_findings),
        "by_issue_type": dict(sorted(issue_type_counts.items())),
        "by_triage_tier": dict(sorted(triage_tier_counts.items())),
        "by_category": dict(sorted(category_counts.items())),
        "high_priority_count": triage_tier_counts.get("high", 0),
        "medium_priority_count": triage_tier_counts.get("medium", 0),
        "low_priority_count": triage_tier_counts.get("low", 0),
        "affected_pages_compact": compact_page_list(sorted(set(affected_pages))),
        "review_guidance": (
            "High-priority: review first — especially sequence gaps and missing page numbers. "
            "Medium-priority: manual review; may include boundary or multiple-candidate cases. "
            "Low-priority: likely artifact-heavy; spot check only."
        ),
    }


def _normalize_p036_section_type(details: dict[str, str]) -> str:
    section_type = details.get("section_type", "").strip()
    if section_type:
        return section_type

    issue_type = details.get("issue_type", "").strip().lower()
    if issue_type.startswith("toc_"):
        return "toc"
    if issue_type.startswith("lot_"):
        return "lot"
    if issue_type.startswith("lof_"):
        return "lof"
    return "unknown"


def _parse_p036_gap_ratio(details: dict[str, str]) -> float | None:
    raw = details.get("gap_ratio", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _bucket_p036_gap_ratio(gap_ratio: float) -> str:
    if gap_ratio < 0.25:
        return "very_tight"
    if gap_ratio < 0.50:
        return "tight"
    if gap_ratio < 0.75:
        return "moderately_tight"
    if gap_ratio < 1.0:
        return "slightly_tight"
    return "unexpected_non_tight"


def build_p036_toc_list_spacing_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P036-specific rollup for TOC/LoT/LoF inter-entry spacing triage."""
    p036_findings = [f for f in findings if f.rule_id == P036_RULE_ID]
    if not p036_findings:
        return None

    pages = sorted({f.page for f in p036_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    section_type_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    spacing_gap_bucket_counts: Counter[str] = Counter()
    section_pages: dict[str, list[int]] = defaultdict(list)
    gap_ratios: list[float] = []

    for finding in p036_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1

        section_type = _normalize_p036_section_type(details)
        section_type_counts[section_type] += 1
        if finding.page is not None:
            section_pages[section_type].append(finding.page)

        triage_tier = details.get("triage_tier", "").strip()
        if triage_tier:
            triage_tier_counts[triage_tier] += 1

        gap_ratio = _parse_p036_gap_ratio(details)
        if gap_ratio is not None:
            gap_ratios.append(gap_ratio)
            spacing_gap_bucket_counts[_bucket_p036_gap_ratio(gap_ratio)] += 1

    section_page_ranges = {
        section_type: compact_page_list(sorted(set(page_list)))
        for section_type, page_list in sorted(section_pages.items())
    }

    return {
        "raw_finding_count": len(p036_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "section_type_counts": dict(sorted(section_type_counts.items())),
        "section_page_ranges": section_page_ranges,
        "triage_tier_counts": dict(sorted(triage_tier_counts.items())),
        "spacing_gap_bucket_counts": dict(sorted(spacing_gap_bucket_counts.items())),
        "min_gap_ratio": min(gap_ratios) if gap_ratios else None,
        "max_gap_ratio": max(gap_ratios) if gap_ratios else None,
        "triage_note": (
            "P036 reports heuristic TOC/LoT/LoF inter-entry spacing warnings for "
            "manual NJIT verification."
        ),
        "recommended_action": (
            "Review affected TOC/List pages first; repeated same-section findings may "
            "indicate a systematic list-spacing issue; spot-check compressed PDFs for "
            "coordinate artifacts."
        ),
    }


def build_grouped_summary(findings: list[AuditFinding]) -> dict[str, Any]:
    """Build a grouped summary structure for triage use in JSON/Markdown reports.

    Returns a dict with two keys:
    - ``high_volume_rules``: list of rule summaries for rules with ≥5 findings.
    - ``by_rule_issue_type``: nested breakdown by rule_id → issue_type.

    Raw findings are not modified. This summary is additive.
    """
    # Group findings by rule_id → issue_type.
    by_rule_issue: dict[str, dict[str, list[AuditFinding]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for finding in findings:
        issue_type = (finding.details or {}).get("issue_type", "")
        by_rule_issue[finding.rule_id][issue_type].append(finding)

    # Build by_rule_issue_type (full cross-tabulation).
    by_rule_issue_type: dict[str, dict[str, dict[str, Any]]] = {}
    for rule_id in sorted(by_rule_issue):
        by_rule_issue_type[rule_id] = {}
        for issue_type, rule_findings in sorted(by_rule_issue[rule_id].items()):
            pages = sorted({f.page for f in rule_findings if f.page is not None})
            obs_counts: Counter[str] = Counter()
            conf_counts: Counter[str] = Counter()
            for f in rule_findings:
                obs = (f.details or {}).get("observed_summary", "")
                if obs:
                    obs_counts[obs] += 1
                conf = (f.details or {}).get("confidence", "")
                if conf:
                    conf_counts[conf] += 1
            entry: dict[str, Any] = {
                "count": len(rule_findings),
                "affected_page_count": len(pages),
                "affected_pages_compact": compact_page_list(pages),
            }
            if obs_counts:
                entry["observed_summary_sample"] = ", ".join(
                    v for v, _ in obs_counts.most_common(3)
                )
            if conf_counts:
                entry["confidence_counts"] = dict(conf_counts)
            by_rule_issue_type[rule_id][issue_type] = entry

    # Build high_volume_rules list (rules with ≥ HIGH_VOLUME_THRESHOLD findings).
    high_volume: list[dict[str, Any]] = []
    for rule_id in sorted(by_rule_issue):
        all_rule_findings = [
            f for issue_fs in by_rule_issue[rule_id].values() for f in issue_fs
        ]
        total = len(all_rule_findings)
        if total < HIGH_VOLUME_THRESHOLD:
            continue
        category = map_finding_rule_to_category(rule_id)
        issue_type_counts = {
            it: len(fs) for it, fs in sorted(by_rule_issue[rule_id].items())
        }
        pages = sorted({f.page for f in all_rule_findings if f.page is not None})
        obs_counts = Counter(
            (f.details or {}).get("observed_summary", "")
            for f in all_rule_findings
            if (f.details or {}).get("observed_summary")
        )
        entry = {
            "rule_id": rule_id,
            "count": total,
            "category": category,
            "issue_type_counts": issue_type_counts,
            "affected_page_count": len(pages),
            "affected_pages_compact": compact_page_list(pages),
        }
        if obs_counts:
            entry["observed_summary_sample"] = ", ".join(
                v for v, _ in obs_counts.most_common(3)
            )
        high_volume.append(entry)

    result: dict[str, Any] = {
        "high_volume_rules": high_volume,
        "by_rule_issue_type": by_rule_issue_type,
    }
    p013_triage = build_p013_triage_summary(findings)
    if p013_triage is not None:
        result["p013_triage"] = p013_triage
    p026_triage = build_p026_font_triage_summary(findings)
    if p026_triage is not None:
        result["p026_font_triage"] = p026_triage
    p011_triage = build_p011_margin_triage_summary(findings)
    if p011_triage is not None:
        result["p011_margin_triage"] = p011_triage
    p012_triage = build_p012_annotation_triage_summary(findings)
    if p012_triage is not None:
        result["p012_annotation_triage"] = p012_triage
    p019_triage = build_p019_page_numbering_triage_summary(findings)
    if p019_triage is not None:
        result["p019_page_numbering_triage"] = p019_triage
    p036_triage = build_p036_toc_list_spacing_triage_summary(findings)
    if p036_triage is not None:
        result["p036_toc_list_spacing_triage"] = p036_triage
    return result


def audit_findings_to_json_dict(
    findings: list[AuditFinding], metadata: dict[str, str]
) -> dict[str, Any]:
    """Convert findings + metadata into a structured serializable payload."""
    audit_type = metadata.get("audit_type", "pdf")
    prepared = _prepare_findings_for_export(findings, audit_type)

    serialized_findings: list[dict[str, Any]] = []
    for finding in prepared:
        details = _sanitize_details(finding.details)
        entry: dict[str, Any] = {
            "rule_id": finding.rule_id,
            "severity": finding.severity.value,
            "message": finding.message,
            "page": finding.page,
            "details": details,
        }
        if audit_type == "tex":
            entry["source_file"] = _source_location_basename(details)
            entry["source_line"] = details.get("line", "")
        serialized_findings.append(entry)

    meta_block: dict[str, Any] = {
        **metadata,
        "total_findings": len(prepared),
        "counts_by_severity": _severity_counts(prepared),
        "counts_by_rule_id": _rule_counts(prepared),
        "counts_by_category": _category_counts(prepared),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Findings are heuristic signals and require human review.",
    }
    if audit_type == "tex":
        locations = {
            (details.get("file", ""), details.get("line", ""))
            for details in (f.details for f in prepared)
            if details.get("file") or details.get("line")
        }
        meta_block["source_location_count"] = len(locations)

    return {
        "metadata": meta_block,
        "grouped_summary": build_grouped_summary(prepared),
        "findings": serialized_findings,
    }


# Detail keys that may contain private source content (label names, ref keys,
# body text, author/title info).  These are removed from web-exported JSON
# findings for source (TeX) audits.  Numeric/structural keys are preserved.
_UNSAFE_SOURCE_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "label",
        "ref",
        "caption",
        "caption_text",
        "title",
        "title_text",
        "author",
        "author_name",
        "body",
        "text",
        "line_text",
        "body_text",
        "extracted_text",
        "entry_text",
        "heading_text",
        "observed_summary",
        "annotation_text",
        "comment_text",
    }
)

# Source rule IDs whose message fields may embed private label/ref/caption names.
_SOURCE_RULE_IDS_FOR_SANITIZE: frozenset[str] = frozenset(
    {"P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"}
)


def _privacy_safe_source_message(rule_id: str, issue_type: str, details: dict[str, str]) -> str:
    """Return a generic privacy-safe message for a source-audit finding.

    This replaces the raw ``message`` field (which may contain label/ref/caption
    names) with a short structural description suitable for web export.
    """
    location = format_source_location(details)
    rule_label = f"{rule_id} ({issue_type})" if issue_type else rule_id
    return f"{rule_label} issue detected at {location}. See polished comment for details."


def sanitize_report_for_web_export(report: dict[str, Any]) -> dict[str, Any]:
    """Return a privacy-reduced copy of an audit report for web JSON/Markdown export.

    Applied only to source (TeX) audits.  PDF audit reports are returned unchanged.

    Sanitization rules:
    - ``findings[].message`` for source rules (P001–P010) is replaced with a
      generic structural message that does not embed label names, ref keys,
      caption text, or other private content.
    - Unsafe detail keys (``label``, ``ref``, ``caption``, ``title``, ``author``,
      ``body``, ``text``, and related source-snippet keys) are removed from each
      finding's ``details`` dict.
    - Safe structural keys (``file``, ``line``, ``issue_type``, ``command``,
      ``confidence``, ``triage_tier``, ``suggested_fix``, numeric counts, etc.)
      are preserved.
    - Finding counts, rule IDs, severity, category, ``source_file``, and
      ``source_line`` are never altered.
    - PDF report structure (``grouped_summary``, ``metadata``) is not modified.
    """
    import copy

    audit_type = str(report.get("metadata", {}).get("audit_type", "pdf"))
    if audit_type != "tex":
        return report

    result = copy.deepcopy(report)
    sanitized_findings: list[dict[str, Any]] = []
    for finding in result.get("findings", []):
        rule_id = str(finding.get("rule_id", ""))
        details_raw = finding.get("details", {})
        if isinstance(details_raw, dict):
            # Remove unsafe keys; keep safe structural / numeric keys.
            clean_details = {
                k: v
                for k, v in details_raw.items()
                if k not in _UNSAFE_SOURCE_DETAIL_KEYS
            }
        else:
            clean_details = {}
        finding["details"] = clean_details

        # Replace raw message for source rules to avoid leaking label/ref names.
        if rule_id in _SOURCE_RULE_IDS_FOR_SANITIZE:
            issue_type = str(clean_details.get("issue_type", ""))
            finding["message"] = _privacy_safe_source_message(
                rule_id, issue_type, {str(k): str(v) for k, v in clean_details.items()}
            )
        sanitized_findings.append(finding)
    result["findings"] = sanitized_findings
    return result


def write_json_report(
    findings: list[AuditFinding], metadata: dict[str, str], output_path: Path
) -> None:
    """Write structured JSON report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = audit_findings_to_json_dict(findings, metadata)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _format_summary_table(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    sev = meta["counts_by_severity"]
    lines = [
        "| Metric | Value |",
        "|---|---:|",
        f"| Total findings | {meta['total_findings']} |",
        f"| PASS | {sev.get('PASS', 0)} |",
        f"| WARNING | {sev.get('WARNING', 0)} |",
        f"| FAIL | {sev.get('FAIL', 0)} |",
    ]
    return "\n".join(lines)


def _format_grouped_summary_section(grouped: dict[str, Any]) -> list[str]:
    """Render the grouped summary as Markdown lines."""
    high_volume = grouped.get("high_volume_rules", [])
    if not high_volume:
        return []

    lines: list[str] = []
    lines.append("## Repeated Findings Summary")
    lines.append("")
    lines.append(
        f"Rules with {HIGH_VOLUME_THRESHOLD}+ findings grouped for triage. "
        "Raw findings are listed below. All findings are heuristic warnings "
        "requiring manual review."
    )
    lines.append("")
    lines.append("| Rule | Count | Category | Pages | Top Issue Types |")
    lines.append("|------|------:|---------|------:|-----------------|")
    for entry in high_volume:
        rule_id = entry["rule_id"]
        count = entry["count"]
        category = entry["category"]
        page_count = entry["affected_page_count"]
        page_str = f"{page_count}" if page_count else "—"
        issue_parts = [
            f"{it}×{n}" for it, n in sorted(entry["issue_type_counts"].items()) if it
        ]
        if not issue_parts:
            issue_parts = [f"{n} findings" for n in entry["issue_type_counts"].values()]
        issue_str = "; ".join(issue_parts[:2])
        obs = entry.get("observed_summary_sample", "")
        if obs:
            issue_str += f" ({obs[:40]})" if len(obs) > 40 else f" ({obs})"
        lines.append(f"| `{rule_id}` | {count} | {category} | {page_str} | {issue_str} |")
    lines.append("")
    return lines


def _format_p013_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P013-specific triage rollup for Markdown reports."""
    triage = grouped.get("p013_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P013 Page-Number Candidate Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P013 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Page-level warnings | {triage['page_level_finding_count']} |")
    lines.append(f"| Document overview | {triage['document_overview_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Pages with multiple candidates | {triage['pages_with_multiple_candidates']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            label = issue_type or "(unspecified)"
            lines.append(f"- `{label}`: {count}")
        lines.append("")

    position_counts = triage.get("position_type_counts", {})
    style_counts = triage.get("number_style_counts", {})
    if position_counts or style_counts:
        lines.append("### Position and style distribution (page-level)")
        lines.append("")
        for position, count in sorted(position_counts.items()):
            lines.append(f"- position `{position}`: {count}")
        for style, count in sorted(style_counts.items()):
            lines.append(f"- style `{style}`: {count}")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        lines.append("### Position/style pattern page ranges")
        lines.append("")
        for observed, page_range in pattern_ranges.items():
            lines.append(f"- `{observed}`: pages {page_range}")
        lines.append("")

    multi_compact = triage.get("multiple_candidate_pages_compact", "")
    if multi_compact:
        lines.append(f"Pages with multiple candidates: {multi_compact}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P013 findings are listed under **Findings by Rule → P013** below."
    )
    lines.append("")
    return lines


def _format_p026_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P026-specific triage rollup for Markdown reports."""
    triage = grouped.get("p026_font_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P026 Body Font Compliance Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P026 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    both_count = triage.get("pages_with_both_issue_types", 0)
    if both_count:
        lines.append(f"| Pages with family and size issues | {both_count} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            label = issue_type or "(unspecified)"
            lines.append(f"- `{label}`: {count}")
        lines.append("")

    font_labels = triage.get("font_label_counts", {})
    if font_labels:
        lines.append("### Dominant non-compliant font labels (family issues)")
        lines.append("")
        for label, count in font_labels.items():
            lines.append(f"- `{label}`: {count} page(s)")
        lines.append("")

    size_labels = triage.get("size_observed_label_counts", {})
    if size_labels:
        lines.append("### Observed size labels (size issues)")
        lines.append("")
        for label, count in size_labels.items():
            lines.append(f"- `{label}`: {count} page(s)")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        lines.append("### Issue/font pattern page ranges")
        lines.append("")
        for pattern, page_range in pattern_ranges.items():
            lines.append(f"- `{pattern}`: pages {page_range}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P026 findings are listed under **Findings by Rule → P026** below."
    )
    lines.append("")
    return lines


def _format_p012_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P012-specific triage rollup for Markdown reports."""
    triage = grouped.get("p012_annotation_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P012 Annotation/Comment Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P012 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    max_per_page = triage.get("annotations_per_page_max", 0)
    if max_per_page:
        lines.append(f"| Max annotations on one page | {max_per_page} |")
    multi_count = triage.get("pages_with_multiple_annotations", 0)
    if multi_count:
        lines.append(f"| Pages with multiple annotations | {multi_count} |")
    dominant = triage.get("dominant_annotation_type", "")
    if dominant:
        lines.append(f"| Dominant annotation type | `{dominant}` |")
    lines.append("")

    type_counts = triage.get("annotation_type_counts", {})
    if type_counts:
        lines.append("### Annotation type counts")
        lines.append("")
        for annotation_type, count in sorted(type_counts.items()):
            lines.append(f"- `{annotation_type}`: {count}")
        lines.append("")

    type_ranges = triage.get("type_page_ranges", {})
    if type_ranges:
        lines.append("### Annotation type page ranges")
        lines.append("")
        for annotation_type, page_range in type_ranges.items():
            lines.append(f"- `{annotation_type}`: pages {page_range}")
        lines.append("")

    multi_compact = triage.get("multiple_annotations_pages_compact", "")
    if multi_compact:
        lines.append(f"Pages with multiple annotations: {multi_compact}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    recommended = triage.get("recommended_action", "")
    if recommended:
        lines.append(f"**Recommended action:** {recommended}")
        lines.append("")

    lines.append(
        "Raw per-annotation P012 findings are listed under **Findings by Rule → P012** "
        "below. Annotation text is not repeated in this triage section."
    )
    lines.append("")
    return lines


def _format_p011_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P011-specific triage rollup for Markdown reports."""
    triage = grouped.get("p011_margin_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P011 Margin/Overflow Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P011 warnings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Total affected lines (sum) | {triage.get('total_affected_line_count', 0)} |")
    multi = triage.get("pages_with_multiple_sides", 0)
    if multi:
        lines.append(f"| Pages with multiple margin sides | {multi} |")
    dominant = triage.get("dominant_margin_side", "")
    if dominant:
        lines.append(f"| Dominant margin side | `{dominant}` |")
    lines.append("")

    side_counts = triage.get("side_counts", {})
    if side_counts:
        lines.append("### Margin side counts")
        lines.append("")
        for side, count in sorted(side_counts.items()):
            lines.append(f"- `{side}`: {count}")
        lines.append("")

    confidence_counts = triage.get("confidence_counts", {})
    if confidence_counts:
        lines.append("### Confidence distribution")
        lines.append("")
        for level, count in sorted(confidence_counts.items()):
            lines.append(f"- `{level}`: {count}")
        lines.append("")

    max_overflow = triage.get("max_overflow_by_side_pt", {})
    median_overflow = triage.get("median_overflow_by_side_pt", {})
    if max_overflow or median_overflow:
        lines.append("### Overflow distance by side (pt)")
        lines.append("")
        for side in sorted(set(max_overflow) | set(median_overflow)):
            max_pt = max_overflow.get(side)
            med_pt = median_overflow.get(side)
            parts = []
            if max_pt is not None:
                parts.append(f"max {max_pt}")
            if med_pt is not None:
                parts.append(f"median {med_pt}")
            lines.append(f"- `{side}`: {', '.join(parts)}")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        lines.append("### Margin-side page ranges")
        lines.append("")
        for side, page_range in pattern_ranges.items():
            lines.append(f"- `{side}`: pages {page_range}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P011 findings are listed under **Findings by Rule → P011** below."
    )
    lines.append("")
    return lines


def _format_p019_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P019-specific triage rollup for Markdown reports."""
    triage = grouped.get("p019_page_numbering_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P019 Page-Numbering Triage Summary")
    lines.append("")
    lines.append(
        "P019 reports heuristic page-numbering sequence and style issues for manual NJIT "
        "verification. Raw findings are preserved; this section summarizes by triage priority."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total P019 findings | {triage['total_findings']} |")
    lines.append(f"| High-priority | {triage['high_priority_count']} |")
    lines.append(f"| Medium-priority | {triage['medium_priority_count']} |")
    lines.append(f"| Low-priority | {triage['low_priority_count']} |")
    lines.append("")

    issue_counts = triage.get("by_issue_type", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    tier_counts = triage.get("by_triage_tier", {})
    if tier_counts:
        lines.append("### Triage tier counts")
        lines.append("")
        for tier, count in sorted(tier_counts.items()):
            lines.append(f"- `{tier}`: {count}")
        lines.append("")

    guidance = triage.get("review_guidance", "")
    if guidance:
        lines.append("### Reviewer guidance")
        lines.append("")
        for part in guidance.split(". "):
            part = part.strip()
            if part:
                lines.append(f"- {part}.")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"Affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P019 findings are listed under **Findings by Rule → P019** below."
    )
    lines.append("")
    return lines


def _format_p036_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P036-specific triage rollup for Markdown reports."""
    triage = grouped.get("p036_toc_list_spacing_triage")
    if not triage:
        return []

    def _fmt_ratio(value: Any) -> str:
        if isinstance(value, (int, float)):
            return f"{float(value):.2f}"
        return "—"

    lines: list[str] = []
    lines.append("## P036 TOC/List Spacing Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P036 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Min gap ratio | {_fmt_ratio(triage.get('min_gap_ratio'))} |")
    lines.append(f"| Max gap ratio | {_fmt_ratio(triage.get('max_gap_ratio'))} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    section_counts = triage.get("section_type_counts", {})
    if section_counts:
        lines.append("### Section type counts")
        lines.append("")
        for section_type, count in sorted(section_counts.items()):
            lines.append(f"- `{section_type}`: {count}")
        lines.append("")

    tier_counts = triage.get("triage_tier_counts", {})
    if tier_counts:
        lines.append("### Triage tier counts")
        lines.append("")
        for tier, count in sorted(tier_counts.items()):
            lines.append(f"- `{tier}`: {count}")
        lines.append("")

    bucket_counts = triage.get("spacing_gap_bucket_counts", {})
    if bucket_counts:
        lines.append("### Spacing gap bucket counts")
        lines.append("")
        for bucket, count in sorted(bucket_counts.items()):
            lines.append(f"- `{bucket}`: {count}")
        lines.append("")

    page_ranges = triage.get("section_page_ranges", {})
    if page_ranges:
        lines.append("### Section page ranges")
        lines.append("")
        for section_type, page_range in sorted(page_ranges.items()):
            lines.append(f"- `{section_type}`: pages {page_range}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    recommended_action = triage.get("recommended_action", "")
    if recommended_action:
        lines.append(f"**Recommended action:** {recommended_action}")
        lines.append("")

    lines.append(
        "Raw per-page P036 findings are listed under **Findings by Rule → P036** below."
    )
    lines.append("")
    return lines


def _group_findings_by_rule(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        grouped[str(finding["rule_id"])].append(finding)
    return dict(sorted(grouped.items()))


def format_source_location(details: dict[str, str]) -> str:
    """Return a privacy-safe file:line label for source findings."""
    file_name = _source_location_basename(details)
    line = details.get("line", "").strip()
    if file_name and line:
        return f"{file_name}:{line}"
    if file_name:
        return file_name
    return "source"


def _safe_source_location(details: dict[str, str]) -> str:
    return format_source_location(details)


def _finding_markdown_line(finding: dict[str, Any], *, audit_type: str = "pdf") -> str:
    from njit_auditor.polished_comments import build_polished_comment

    details = finding.get("details", {})
    if not isinstance(details, dict):
        details = {}
    safe_details = {str(k): str(v) for k, v in details.items()}
    issue_type = safe_details.get("issue_type", "")
    page_raw = finding.get("page")
    page = int(page_raw) if page_raw is not None else None

    if audit_type == "tex":
        loc_text = _safe_source_location(safe_details)
    else:
        loc_text = f"p.{page}" if page is not None else "p.-"

    polished = build_polished_comment(
        rule_id=str(finding.get("rule_id", "")),
        issue_type=issue_type,
        severity=str(finding.get("severity", "WARNING")),
        page=page,
        details=safe_details,
    )
    line = f"- **{loc_text}** [{finding['severity']}] {polished}"
    suggested_fix = safe_details.get("suggested_fix")
    if suggested_fix:
        line += f" | Suggested fix: {suggested_fix}"
    return line


def write_markdown_report(
    findings: list[AuditFinding], metadata: dict[str, str], output_path: Path
) -> None:
    """Write student/office-friendly markdown audit report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_type = metadata.get("audit_type", "pdf")
    prepared = _prepare_findings_for_export(findings, audit_type)
    payload = audit_findings_to_json_dict(prepared, metadata)
    meta = payload["metadata"]
    serialized_findings = payload["findings"]
    grouped_by_rule = _group_findings_by_rule(serialized_findings)

    lines: list[str] = []
    title = (
        "# NJIT Source Audit Report"
        if audit_type == "tex"
        else "# NJIT PDF Audit Report"
    )
    lines.append(title)
    lines.append("")
    lines.append(f"- Input file: `{meta.get('input_file_name', '-')}`")
    lines.append(f"- Input path: `{meta.get('input_file_path', '-')}`")
    lines.append(f"- Audit type: `{meta.get('audit_type', 'pdf')}`")
    if audit_type == "tex":
        lines.append(f"- Input kind: `{meta.get('input_kind', 'tex')}`")
        if meta.get("main_tex_path"):
            lines.append(f"- Main TeX file: `{meta.get('main_tex_path', '-')}`")
        if meta.get("loaded_tex_file_count"):
            lines.append(f"- Loaded TeX files: `{meta.get('loaded_tex_file_count', '-')}`")
    lines.append(f"- Generated at: `{meta.get('generated_at', '-')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(_format_summary_table(payload))
    lines.append("")
    lines.append("### Counts by Rule")
    lines.append("")
    for rule_id, count in meta["counts_by_rule_id"].items():
        lines.append(f"- `{rule_id}`: {count}")
    lines.append("")
    lines.append("### Counts by Category")
    lines.append("")
    for category, count in meta["counts_by_category"].items():
        lines.append(f"- `{category}`: {count}")

    # Grouped summary and PDF-only triage sections.
    lines.append("")
    grouped_section = _format_grouped_summary_section(payload["grouped_summary"])
    lines.extend(grouped_section)

    if audit_type != "tex":
        p011_section = _format_p011_triage_section(payload["grouped_summary"])
        lines.extend(p011_section)

        p012_section = _format_p012_triage_section(payload["grouped_summary"])
        lines.extend(p012_section)

        p013_section = _format_p013_triage_section(payload["grouped_summary"])
        lines.extend(p013_section)

        p019_section = _format_p019_triage_section(payload["grouped_summary"])
        lines.extend(p019_section)

        p026_section = _format_p026_triage_section(payload["grouped_summary"])
        lines.extend(p026_section)

        p036_section = _format_p036_triage_section(payload["grouped_summary"])
        lines.extend(p036_section)

    lines.append("## Findings by Rule")
    lines.append("")
    for rule_id, rule_findings in grouped_by_rule.items():
        lines.append(f"### {rule_id}")
        lines.append("")
        if audit_type == "tex":
            sort_key = lambda item: (  # noqa: E731
                item.get("source_file", ""),
                int(item.get("source_line") or 0),
                item.get("rule_id", ""),
            )
        else:
            sort_key = lambda item: (  # noqa: E731
                item["page"] is None,
                item["page"] or 0,
                item["message"],
            )
        sorted_findings = sorted(rule_findings, key=sort_key)
        for finding in sorted_findings:
            lines.append(_finding_markdown_line(finding, audit_type=audit_type))
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Privacy: report output avoids dissertation body text and source line quotes.")
    lines.append("- Limitation: findings are heuristic and require human review.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
