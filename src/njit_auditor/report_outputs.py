"""Structured JSON/Markdown output helpers for audit findings."""

from __future__ import annotations

import json
import re
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
P038_RULE_ID = "P038"
P044_RULE_ID = "P044"
_REPEATED_PROBLEM_CONTEXT_KEYS: tuple[str, ...] = (
    "side",
    "annotation_type",
    "position_type",
    "number_style",
    "section_type",
    "p019_triage_category",
    "source_q_rule_id",
    "source_q_rule",
    "expected_heading",
    "expected_phrase",
    "expected_value",
    "actual_value",
    "expected_label",
    "actual_label",
    "command",
    "environment",
    "issue_subtype",
    "candidate_count_on_page",
    "paragraph_index",
    "source_file",
)
_RULE_SPECIFIC_GROUPING_KEYS: dict[str, tuple[str, ...]] = {
    "P013": ("observed_summary",),
    "P026": ("observed_summary",),
}
_ROMAN_LABEL_RE = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)


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


def _compact_numeric_ranges(numbers: list[int]) -> list[str]:
    """Return sorted, deduplicated numeric values as compact en-dash ranges."""
    if not numbers:
        return []
    ordered = sorted(set(numbers))
    ranges: list[str] = []
    start = end = ordered[0]
    for number in ordered[1:]:
        if number == end + 1:
            end = number
            continue
        ranges.append(str(start) if start == end else f"{start}–{end}")
        start = end = number
    ranges.append(str(start) if start == end else f"{start}–{end}")
    return ranges


def _compact_numeric_range_text(numbers: list[int]) -> str:
    return ", ".join(_compact_numeric_ranges(numbers))


def _roman_to_int(label: str) -> int | None:
    if not label or not _ROMAN_LABEL_RE.fullmatch(label):
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for char in reversed(label.upper()):
        value = values[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total if total > 0 else None


def _int_to_roman(value: int, *, uppercase: bool = False) -> str:
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    parts: list[str] = []
    for amount, symbol in numerals:
        while remaining >= amount:
            parts.append(symbol)
            remaining -= amount
    roman = "".join(parts)
    return roman if uppercase else roman.lower()


def _compact_roman_ranges(labels: list[str]) -> list[str]:
    if not labels:
        return []
    normalized: list[tuple[int, str]] = []
    for label in labels:
        value = _roman_to_int(label)
        if value is None:
            return []
        normalized.append((value, label))
    uppercase = all(label.isupper() for _, label in normalized)
    ordered_values = sorted({value for value, _ in normalized})
    ranges: list[str] = []
    start = end = ordered_values[0]
    for value in ordered_values[1:]:
        if value == end + 1:
            end = value
            continue
        start_label = _int_to_roman(start, uppercase=uppercase)
        end_label = _int_to_roman(end, uppercase=uppercase)
        ranges.append(start_label if start == end else f"{start_label}–{end_label}")
        start = end = value
    start_label = _int_to_roman(start, uppercase=uppercase)
    end_label = _int_to_roman(end, uppercase=uppercase)
    ranges.append(start_label if start == end else f"{start_label}–{end_label}")
    return ranges


def _compact_location_ranges(
    locations: list[tuple[str, str]],
) -> tuple[list[str], str]:
    if not locations:
        return [], ""
    by_file: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"lines": []})
    standalone_files: list[str] = []
    for file_name, line in locations:
        clean_file = file_name.strip()
        clean_line = line.strip()
        if not clean_file:
            continue
        if not clean_line:
            standalone_files.append(clean_file)
            continue
        by_file[clean_file]["lines"].append(clean_line)

    tokens: list[str] = []
    for file_name in sorted(set(standalone_files)):
        tokens.append(file_name)

    for file_name in sorted(by_file):
        numeric_lines: list[int] = []
        non_numeric_lines: list[str] = []
        for line in by_file[file_name]["lines"]:
            if line.isdigit():
                numeric_lines.append(int(line))
            else:
                non_numeric_lines.append(line)
        for compact in _compact_numeric_ranges(numeric_lines):
            tokens.append(f"{file_name}:{compact}")
        for line in sorted(set(non_numeric_lines)):
            tokens.append(f"{file_name}:{line}")

    return tokens, ", ".join(tokens)


def _page_label_from_details(details: dict[str, str]) -> str:
    for key in ("page_label", "page_number_label"):
        value = details.get(key, "").strip()
        if value:
            return value
    return ""


def _normalize_grouping_text(
    text: str,
    *,
    audit_type: str,
    page: int | None,
    details: dict[str, str],
) -> str:
    """Normalize display text for grouping without relying on page-specific values."""
    normalized = " ".join(text.split())
    if not normalized:
        return ""

    if audit_type == "tex":
        location = format_source_location(details)
        if location and location != "source":
            normalized = normalized.replace(location, "<location>")
    elif page is not None:
        normalized = normalized.replace(f"page {page}", "page <page>")
        normalized = normalized.replace(f"p.{page}", "p.<page>")

    page_label = _page_label_from_details(details)
    if page_label:
        normalized = normalized.replace(page_label, "<page_label>")

    start = details.get("run_start_page", "").strip()
    end = details.get("run_end_page", "").strip()
    if start and end:
        range_label = start if start == end else f"{start}–{end}"
        normalized = normalized.replace(range_label, "<page_range>")

    return normalized


def _grouping_context_signature(
    rule_id: str,
    details: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    keys = set(_REPEATED_PROBLEM_CONTEXT_KEYS)
    keys.update(_RULE_SPECIFIC_GROUPING_KEYS.get(rule_id, ()))
    signature: list[tuple[str, str]] = []
    for key in sorted(keys):
        value = details.get(key, "").strip()
        if value:
            signature.append((key, value))
    return tuple(signature)


def build_grouped_findings(
    findings: list[AuditFinding],
    audit_type: str,
) -> list[dict[str, Any]]:
    """Build a deterministic grouped-problem structure for repeated findings.

    The raw ``findings`` list is preserved unchanged elsewhere. This structure is
    additive and intended for compact web/Markdown display.
    """
    from njit_auditor.polished_comments import build_polished_comment

    grouped: dict[
        tuple[Any, ...],
        dict[str, Any],
    ] = {}

    for index, finding in enumerate(findings):
        details = {str(k): str(v) for k, v in (finding.details or {}).items()}
        rule_id = finding.rule_id
        issue_type = details.get("issue_type", "")
        severity = finding.severity.value
        page = finding.page
        category = map_finding_rule_to_category(rule_id, details)
        polished_comment = build_polished_comment(
            rule_id=rule_id,
            issue_type=issue_type,
            severity=severity,
            page=page,
            details=details,
            category=category,
        )
        suggested_fix = details.get("suggested_fix", "").strip()
        confidence = details.get("confidence", "").strip()
        triage_tier = details.get("triage_tier", "").strip()
        normalized_problem = _normalize_grouping_text(
            polished_comment,
            audit_type=audit_type,
            page=page,
            details=details,
        )
        normalized_fix = _normalize_grouping_text(
            suggested_fix,
            audit_type=audit_type,
            page=page,
            details=details,
        )
        key = (
            rule_id,
            issue_type,
            severity,
            category,
            normalized_problem,
            normalized_fix,
            confidence,
            triage_tier,
            _grouping_context_signature(rule_id, details),
        )
        file_name = _source_location_basename(details)
        source_line = details.get("line", "").strip()
        page_label = _page_label_from_details(details)

        if key not in grouped:
            grouped[key] = {
                "rule_id": rule_id,
                "issue_type": issue_type,
                "severity": severity,
                "category": category,
                "problem": polished_comment,
                "suggested_fix": suggested_fix,
                "confidence": confidence,
                "triage_tier": triage_tier,
                "occurrence_count": 0,
                "pages": [],
                "page_ranges": [],
                "page_labels": [],
                "page_labels_compact": "",
                "locations": [],
                "locations_compact": "",
                "individual_indexes": [],
            }

        entry = grouped[key]
        entry["occurrence_count"] += 1
        entry["individual_indexes"].append(index)
        if page is not None:
            entry["pages"].append(int(page))
        if page_label:
            entry["page_labels"].append(page_label)
        if file_name or source_line:
            entry["locations"].append(format_source_location(details))
            entry.setdefault("_raw_locations", []).append((file_name, source_line))

    ordered_groups = sorted(
        grouped.values(),
        key=lambda entry: (entry["individual_indexes"][0], entry["rule_id"], entry["issue_type"]),
    )
    for entry in ordered_groups:
        page_values = sorted(set(int(page) for page in entry["pages"]))
        page_ranges = _compact_numeric_ranges(page_values)
        page_labels = sorted(set(str(label) for label in entry["page_labels"]))
        roman_ranges = _compact_roman_ranges(page_labels)
        raw_locations = entry.pop("_raw_locations", [])
        location_ranges, locations_compact = _compact_location_ranges(raw_locations)
        location_tokens = sorted(set(str(location) for location in entry["locations"]))

        entry["pages"] = page_values
        entry["page_ranges"] = page_ranges
        entry["pages_compact"] = ", ".join(page_ranges)
        entry["page_labels"] = page_labels
        entry["page_label_ranges"] = roman_ranges
        entry["page_labels_compact"] = (
            ", ".join(roman_ranges) if roman_ranges else ", ".join(page_labels)
        )
        entry["locations"] = location_tokens
        entry["location_ranges"] = location_ranges
        entry["locations_compact"] = locations_compact
        if entry["page_labels_compact"]:
            entry["affected_label"] = "Pages"
            entry["affected_compact"] = entry["page_labels_compact"]
        elif entry["pages_compact"]:
            entry["affected_label"] = "Pages"
            entry["affected_compact"] = entry["pages_compact"]
        elif entry["locations_compact"]:
            entry["affected_label"] = "Locations"
            entry["affected_compact"] = entry["locations_compact"]
        else:
            entry["affected_label"] = "Occurrences"
            entry["affected_compact"] = ""

    return ordered_groups


def _share_pct(count: int, total: int) -> float:
    """Return a compact percentage for report summaries."""
    if total <= 0:
        return 0.0
    return round((count / total) * 100.0, 1)


def _bucket_summary(pages: list[int]) -> dict[str, Any]:
    """Build a compact count/range summary for a page bucket."""
    deduped = sorted(set(pages))
    return {
        "count": len(deduped),
        "pages_compact": compact_page_list(deduped),
    }


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
    page_rows: list[tuple[int, int, str, str]] = []

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
        if finding.page is not None:
            page_rows.append((finding.page, candidate_count, confidence, observed))

    for finding in doc_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_DOC_ISSUE_TYPE)] += 1

    pattern_page_ranges = {
        observed: compact_page_list(sorted(set(page_list)))
        for observed, page_list in sorted(
            by_observed.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    dominant_pattern = ""
    dominant_pattern_pages: list[int] = []
    if by_observed:
        dominant_pattern, dominant_pattern_pages = max(
            (
                (observed, sorted(set(page_list)))
                for observed, page_list in by_observed.items()
            ),
            key=lambda item: (len(item[1]), item[0]),
        )

    routine_pages: list[int] = []
    other_pages: list[int] = []
    for page, candidate_count, confidence, observed in page_rows:
        if candidate_count > 1:
            continue
        if observed and observed == dominant_pattern and confidence == "medium":
            routine_pages.append(page)
        else:
            other_pages.append(page)

    affected_page_count = len(pages)
    dominant_pattern_share = _share_pct(len(dominant_pattern_pages), affected_page_count)
    routine_share = _share_pct(len(set(routine_pages)), affected_page_count)
    if routine_share >= 80.0:
        document_pattern_label = "document_wide_routine_pattern"
    elif dominant_pattern_share >= 60.0:
        document_pattern_label = "mostly_routine_pattern_with_outliers"
    else:
        document_pattern_label = "mixed_candidate_patterns"

    calibration_buckets = {
        "routine_single_candidate_dominant_pattern": _bucket_summary(routine_pages),
        "multi_candidate_pages": _bucket_summary(multi_candidate_pages),
        "other_pattern_or_low_confidence": _bucket_summary(other_pages),
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
        "document_pattern_label": document_pattern_label,
        "dominant_pattern": dominant_pattern,
        "dominant_pattern_page_count": len(dominant_pattern_pages),
        "dominant_pattern_pages_compact": compact_page_list(dominant_pattern_pages),
        "dominant_pattern_share_pct": dominant_pattern_share,
        "calibration_buckets": calibration_buckets,
        "calibration_note": (
            "Calibration buckets organize routine dominant-pattern pages separately from "
            "multi-candidate and non-dominant pages for manual triage only. Raw P013 "
            "warnings are not suppressed or re-scored."
        ),
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
    page_rows: dict[int, list[tuple[str, str, str]]] = defaultdict(list)

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
            page_rows[finding.page].append((issue_type, observed, confidence))

    family_pages = pages_by_issue.get(P026_FAMILY_ISSUE_TYPE, set())
    size_pages = pages_by_issue.get(P026_SIZE_ISSUE_TYPE, set())
    both_pages = sorted(family_pages & size_pages)

    pattern_page_ranges = {
        pattern: compact_page_list(sorted(set(page_list)))
        for pattern, page_list in sorted(
            by_pattern.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    dominant_pattern = ""
    dominant_pattern_pages: list[int] = []
    if by_pattern:
        dominant_pattern, dominant_pattern_pages = max(
            (
                (pattern, sorted(set(page_list)))
                for pattern, page_list in by_pattern.items()
            ),
            key=lambda item: (len(item[1]), item[0]),
        )

    routine_pages: list[int] = []
    size_only_pages: list[int] = []
    non_dominant_pages: list[int] = []
    for page, entries in sorted(page_rows.items()):
        issue_types = {issue_type for issue_type, _, _ in entries if issue_type}
        has_size_issue = P026_SIZE_ISSUE_TYPE in issue_types
        page_patterns = {
            _p026_pattern_key(issue_type, observed)
            for issue_type, observed, _ in entries
        }
        confidences = {confidence for _, _, confidence in entries if confidence}
        if len(issue_types) > 1:
            continue
        if has_size_issue:
            size_only_pages.append(page)
            continue
        if (
            dominant_pattern
            and page_patterns == {dominant_pattern}
            and confidences <= {"medium"}
        ):
            routine_pages.append(page)
        else:
            non_dominant_pages.append(page)

    affected_page_count = len(pages)
    dominant_pattern_share = _share_pct(len(dominant_pattern_pages), affected_page_count)
    routine_share = _share_pct(len(set(routine_pages)), affected_page_count)
    if routine_share >= 75.0 and not both_pages and not size_only_pages:
        document_pattern_label = "document_wide_single_font_pattern"
    elif dominant_pattern_share >= 50.0:
        document_pattern_label = "dominant_font_pattern_with_outliers"
    else:
        document_pattern_label = "mixed_font_patterns"

    calibration_buckets = {
        "routine_single_issue_dominant_pattern": _bucket_summary(routine_pages),
        "pages_with_both_issue_types": _bucket_summary(both_pages),
        "size_issue_only_pages": _bucket_summary(size_only_pages),
        "non_dominant_family_only_pages": _bucket_summary(non_dominant_pages),
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
        "document_pattern_label": document_pattern_label,
        "dominant_pattern": dominant_pattern,
        "dominant_pattern_page_count": len(dominant_pattern_pages),
        "dominant_pattern_pages_compact": compact_page_list(dominant_pattern_pages),
        "dominant_pattern_share_pct": dominant_pattern_share,
        "calibration_buckets": calibration_buckets,
        "calibration_note": (
            "Calibration buckets separate routine dominant-pattern pages from size-driven, "
            "mixed-issue, and non-dominant pages for manual triage only. Raw P026 warnings "
            "are not suppressed or re-scored."
        ),
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


def build_p038_frontmatter_heading_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P038-specific rollup for front-matter heading presence/phrase triage."""
    p038_findings = [f for f in findings if f.rule_id == P038_RULE_ID]
    if not p038_findings:
        return None

    pages = sorted({f.page for f in p038_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    expected_heading_counts: Counter[str] = Counter()
    missing_heading_counts: Counter[str] = Counter()
    inexact_phrase_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()

    for finding in p038_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1

        expected_heading = details.get("expected_heading", "")
        if expected_heading:
            expected_heading_counts[expected_heading] += 1
            if issue_type == "required_heading_missing":
                missing_heading_counts[expected_heading] += 1
            elif issue_type == "heading_phrase_not_exact":
                inexact_phrase_counts[expected_heading] += 1

        triage_tier = details.get("triage_tier", "").strip()
        if triage_tier:
            triage_tier_counts[triage_tier] += 1

        confidence = details.get("confidence", "").strip()
        if confidence:
            confidence_counts[confidence] += 1

    return {
        "raw_finding_count": len(p038_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "expected_heading_counts": dict(sorted(expected_heading_counts.items())),
        "missing_heading_counts": dict(sorted(missing_heading_counts.items())),
        "inexact_phrase_counts": dict(sorted(inexact_phrase_counts.items())),
        "triage_tier_counts": dict(sorted(triage_tier_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "triage_note": (
            "P038 identifies required front-matter headings that are missing or use "
            "non-exact phrases. These are advisory warnings for manual NJIT verification."
        ),
        "recommended_action": (
            "Confirm that all required front-matter headings are present and use the "
            "exact NJIT canonical phrase (APPROVAL PAGE, BIOGRAPHICAL SKETCH, "
            "ACKNOWLEDGEMENTS, TABLE OF CONTENTS)."
        ),
    }


def build_p044_abstract_indentation_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P044-specific rollup for Abstract paragraph indentation triage."""
    p044_findings = [f for f in findings if f.rule_id == P044_RULE_ID]
    if not p044_findings:
        return None

    pages = sorted({f.page for f in p044_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    source_q_rule_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    paragraph_index_counts: Counter[str] = Counter()

    for finding in p044_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1

        q_rule = (
            details.get("source_q_rule_id")
            or details.get("source_q_rule_ids")
            or "(unknown)"
        )
        source_q_rule_counts[q_rule] += 1

        triage_tier = details.get("triage_tier", "").strip()
        if triage_tier:
            triage_tier_counts[triage_tier] += 1

        para_idx_raw = details.get("paragraph_index", "")
        try:
            para_idx = str(int(para_idx_raw))
        except (ValueError, TypeError):
            para_idx = para_idx_raw or "(unknown)"
        if para_idx:
            paragraph_index_counts[para_idx] += 1

    return {
        "raw_finding_count": len(p044_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "source_q_rule_counts": dict(sorted(source_q_rule_counts.items())),
        "triage_tier_counts": dict(sorted(triage_tier_counts.items())),
        "paragraph_index_counts": dict(sorted(paragraph_index_counts.items())),
        "triage_note": (
            "P044 reports heuristic Abstract paragraph indentation warnings "
            "for manual NJIT verification."
        ),
        "recommended_action": (
            "Check whether the first Abstract paragraph is unindented and each "
            "subsequent Abstract paragraph is indented according to NJIT guidance; "
            "use raw P044 findings for per-page details."
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
    p038_triage = build_p038_frontmatter_heading_triage_summary(findings)
    if p038_triage is not None:
        result["p038_frontmatter_heading_triage"] = p038_triage
    p044_triage = build_p044_abstract_indentation_triage_summary(findings)
    if p044_triage is not None:
        result["p044_abstract_indentation_triage"] = p044_triage
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
        "grouped_findings": build_grouped_findings(prepared, audit_type),
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


def _format_grouped_findings_section(
    grouped_findings: list[dict[str, Any]],
) -> list[str]:
    """Render grouped repeated-problem display for Markdown reports."""
    repeated_groups = [
        entry
        for entry in grouped_findings
        if int(entry.get("occurrence_count", 0) or 0) > 1
    ]
    if not repeated_groups:
        return []

    lines: list[str] = []
    lines.append("## Grouped Problems")
    lines.append("")
    lines.append(
        "Repeated findings with the same rule, issue type, severity, user-facing problem, "
        "suggested fix, and meaningful triage/context metadata are grouped here for review. "
        "The raw findings remain unchanged in the per-rule findings section below."
    )
    lines.append("")

    for entry in repeated_groups:
        rule_id = str(entry.get("rule_id", ""))
        severity = str(entry.get("severity", ""))
        category = str(entry.get("category", ""))
        issue_type = str(entry.get("issue_type", ""))
        occurrence_count = int(entry.get("occurrence_count", 0) or 0)
        affected_label = str(entry.get("affected_label", "Occurrences"))
        affected_compact = str(entry.get("affected_compact", "")).strip()
        problem = str(entry.get("problem", "")).strip()
        suggested_fix = str(entry.get("suggested_fix", "")).strip()
        confidence = str(entry.get("confidence", "")).strip()
        triage_tier = str(entry.get("triage_tier", "")).strip()

        heading = f"### {rule_id} — {occurrence_count} occurrence"
        if occurrence_count != 1:
            heading += "s"
        lines.append(heading)
        lines.append("")
        lines.append(f"- Severity: `{severity}`")
        lines.append(f"- Category: `{category}`")
        if issue_type:
            lines.append(f"- Issue type: `{issue_type}`")
        if confidence:
            lines.append(f"- Confidence: `{confidence}`")
        if triage_tier:
            lines.append(f"- Triage tier: `{triage_tier}`")
        if affected_compact:
            lines.append(f"- {affected_label}: {affected_compact}")
        if problem:
            lines.append(f"- Problem: {problem}")
        if suggested_fix:
            lines.append(f"- Suggested fix: {suggested_fix}")
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

    dominant_pattern = triage.get("dominant_pattern", "")
    if dominant_pattern:
        lines.append("### Calibration summary")
        lines.append("")
        lines.append(
            f"Document pattern label: `{triage.get('document_pattern_label', '')}`"
        )
        lines.append(
            f"Dominant pattern `{dominant_pattern}` covers "
            f"{triage.get('dominant_pattern_page_count', 0)} page(s) "
            f"({triage.get('dominant_pattern_share_pct', 0.0)}%)."
        )
        lines.append("")

    calibration_buckets = triage.get("calibration_buckets", {})
    if calibration_buckets:
        lines.append("### Calibration buckets")
        lines.append("")
        lines.append(
            triage.get(
                "calibration_note",
                "Calibration buckets are triage-only summaries; raw findings remain below.",
            )
        )
        lines.append("")
        for bucket_name, bucket in calibration_buckets.items():
            lines.append(
                f"- `{bucket_name}`: {bucket.get('count', 0)} page(s)"
                + (
                    f" — pages {bucket.get('pages_compact', '')}"
                    if bucket.get("pages_compact")
                    else ""
                )
            )
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

    dominant_pattern = triage.get("dominant_pattern", "")
    if dominant_pattern:
        lines.append("### Calibration summary")
        lines.append("")
        lines.append(
            f"Document pattern label: `{triage.get('document_pattern_label', '')}`"
        )
        lines.append(
            f"Dominant pattern `{dominant_pattern}` covers "
            f"{triage.get('dominant_pattern_page_count', 0)} page(s) "
            f"({triage.get('dominant_pattern_share_pct', 0.0)}%)."
        )
        lines.append("")

    calibration_buckets = triage.get("calibration_buckets", {})
    if calibration_buckets:
        lines.append("### Calibration buckets")
        lines.append("")
        lines.append(
            triage.get(
                "calibration_note",
                "Calibration buckets are triage-only summaries; raw findings remain below.",
            )
        )
        lines.append("")
        for bucket_name, bucket in calibration_buckets.items():
            lines.append(
                f"- `{bucket_name}`: {bucket.get('count', 0)} page(s)"
                + (
                    f" — pages {bucket.get('pages_compact', '')}"
                    if bucket.get("pages_compact")
                    else ""
                )
            )
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


def _format_p038_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P038-specific triage rollup for Markdown reports."""
    triage = grouped.get("p038_frontmatter_heading_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P038 Front-Matter Heading Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P038 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    missing_counts = triage.get("missing_heading_counts", {})
    if missing_counts:
        lines.append("### Missing heading counts")
        lines.append("")
        for heading, count in sorted(missing_counts.items()):
            lines.append(f"- `{heading}`: {count}")
        lines.append("")

    inexact_counts = triage.get("inexact_phrase_counts", {})
    if inexact_counts:
        lines.append("### Non-exact phrase counts")
        lines.append("")
        for heading, count in sorted(inexact_counts.items()):
            lines.append(f"- `{heading}`: {count}")
        lines.append("")

    tier_counts = triage.get("triage_tier_counts", {})
    if tier_counts:
        lines.append("### Triage tier counts")
        lines.append("")
        for tier, count in sorted(tier_counts.items()):
            lines.append(f"- `{tier}`: {count}")
        lines.append("")

    confidence_counts = triage.get("confidence_counts", {})
    if confidence_counts:
        lines.append("### Confidence counts")
        lines.append("")
        for conf, count in sorted(confidence_counts.items()):
            lines.append(f"- `{conf}`: {count}")
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
        "Raw per-page P038 findings are listed under **Findings by Rule → P038** below."
    )
    lines.append("")
    return lines


def _format_p044_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P044-specific triage rollup for Markdown reports."""
    triage = grouped.get("p044_abstract_indentation_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P044 Abstract Indentation Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P044 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    source_q_counts = triage.get("source_q_rule_counts", {})
    if source_q_counts:
        lines.append("### Source Q-rule counts")
        lines.append("")
        for q_rule, count in sorted(source_q_counts.items()):
            lines.append(f"- `{q_rule}`: {count}")
        lines.append("")

    para_counts = triage.get("paragraph_index_counts", {})
    if para_counts:
        lines.append("### Paragraph index counts")
        lines.append("")
        for para_idx, count in sorted(para_counts.items()):
            lines.append(f"- paragraph {para_idx}: {count}")
        lines.append("")

    tier_counts = triage.get("triage_tier_counts", {})
    if tier_counts:
        lines.append("### Triage tier counts")
        lines.append("")
        for tier, count in sorted(tier_counts.items()):
            lines.append(f"- `{tier}`: {count}")
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
        "Raw per-page P044 findings are listed under **Findings by Rule → P044** below."
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

    grouped_findings_section = _format_grouped_findings_section(
        payload.get("grouped_findings", [])
    )
    lines.extend(grouped_findings_section)

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

        p038_section = _format_p038_triage_section(payload["grouped_summary"])
        lines.extend(p038_section)

        p044_section = _format_p044_triage_section(payload["grouped_summary"])
        lines.extend(p044_section)

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
