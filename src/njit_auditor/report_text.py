"""Standalone plain-text audit report: page-grouped, privacy-safe, consolidated.

Unlike the Markdown export (one "### Problem N" section per raw occurrence),
this report is organized the way a student actually reads a PDF: by page,
with repeated same-page/same-issue occurrences (e.g. two dozen Table of
Contents spacing warnings) collapsed into one record that lists every
affected location instead of repeating a near-identical paragraph.

The web text download uses the web report's visible, numbered FindingView
records through ``student_pdf_report.render_student_report_text`` so it shares
problem numbers with the combined PDF and web cards.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.issue_type_explanations import (
    has_curated_issue_type_title,
    humanize_issue_type,
    issue_type_title,
)
from njit_auditor.models import AuditFinding
from njit_auditor.p011_student_preview import (
    P011_ISSUE_TYPE,
    P011_RULE_ID,
    _join_margin_labels,
    _side_short_label,
    collect_p011_margin_pages_from_serialized,
    init_p011_display_state,
)
from njit_auditor.p012_student_preview import count_p012_annotations_by_page
from njit_auditor.p026_student_preview import (
    collect_p026_pattern_pages_from_serialized,
    init_p026_display_state,
)
from njit_auditor.report_outputs import (
    _prepare_findings_for_export,
    _problem_location_text,
    _websafe_rule_text,
    audit_findings_to_json_dict,
    category_display_label,
    individual_finding_comment_and_fix,
    public_display_rule_id,
)
from njit_auditor.resource_paths import resource_path
from njit_auditor.student_cards import (
    CONFIDENCE_NOTE,
    finding_check_lines,
    plain_student_text,
    student_card_fields,
)

PublicRuleReferenceFn = Callable[..., str]

_RULES_JSON_PATH = resource_path("data", "processed", "rules", "project_added_rules.json")

_CONFIDENCE_LABELS: dict[str, str] = {"high": "High", "medium": "Medium", "low": "Low"}

_PAGE_REFERENCE_PREFIXES: tuple[str, ...] = (
    "Page ",
    "PDF page",
    "Document page:",
    "Document-wide",
)

NOT_DETERMINED_LOCATION = "Not determined by the automated check"


def _default_public_rule_reference_id(rule_id: str, **_: Any) -> str:
    """Fallback public-rule mapping used when the caller supplies none.

    web_app.py passes its own ``_public_rule_reference_id`` (which knows
    about P018 sub-cards, hidden internal rule IDs, etc.) when generating
    live reports; this default simply echoes the P0xx rule id, which is
    already the public identifier shown on the site's Rules Reference page
    for every rule that does not need special-case splitting.
    """
    return str(rule_id).strip()


_full_remediation_cache: dict[str, str] | None = None


def _full_remediation_by_rule() -> dict[str, str]:
    """Return {rule_id: full remediation text} loaded straight from the rule JSON.

    ``polished_comments._remediation_by_rule`` caps this text at ~200 chars
    (with a trailing "...") for compact web-card display. The full-length
    downloadable report must never show a truncated "How to fix it" line, so
    this reads the same source file without that cap.
    """
    global _full_remediation_cache
    if _full_remediation_cache is not None:
        return _full_remediation_cache
    try:
        import json

        payload = json.loads(_RULES_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _full_remediation_cache = {}
        return _full_remediation_cache
    result: dict[str, str] = {}
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("id", "")).strip()
            remediation = str(item.get("remediation", "")).strip()
            if rule_id and remediation:
                result[rule_id] = remediation
    _full_remediation_cache = result
    return _full_remediation_cache


def _detruncate_fix_text(
    rule_id: str, fix_text: str, details: Mapping[str, str] | None = None
) -> str:
    """Replace a word-boundary-truncated fix ("...") with the full remediation text.

    The full text is read straight from the canonical rule JSON (see
    ``_full_remediation_by_rule``), so it must be run through the same
    ``_websafe_rule_text`` sanitization the public Rules Reference page
    applies before it reaches a student -- otherwise internal
    authoring/reviewer shorthand left in that field (e.g. a trailing
    "Ester: ..." summary note addressed to other rule authors, not
    students) would be de-truncated straight into this report verbatim.

    A truncated R011 fix on a landscape sheet is rebuilt from the finding's
    details instead: the canonical remediation states the portrait rule
    ("left margin 1.5 inches"), which misdescribes that page.
    """
    if fix_text.endswith("...") or fix_text.endswith("…"):
        if rule_id == "P011" and details and details.get("page_orientation") == "landscape":
            from njit_auditor.p011_margin_presentation import margin_primary_remediation

            return margin_primary_remediation(details)
        full = _full_remediation_by_rule().get(rule_id, "")
        if full:
            return _websafe_rule_text(rule_id, "remediation", full)
    return fix_text


def _strip_page_reference(location_text: str) -> str:
    """Drop a leading page-reference clause a location string already carries.

    Location text produced by the existing per-rule label builders is
    consistently ``"<page reference> — <precise detail>"`` (or occasionally
    just the bare page reference with no further detail). The page reference
    is redundant here because it is already shown once in the page's own
    "PDF PAGE N" heading, so only the precise detail is kept.
    """
    text = location_text.strip()
    if not text:
        return ""
    if " — " in text:
        prefix, _, rest = text.partition(" — ")
        if prefix.strip().startswith(_PAGE_REFERENCE_PREFIXES):
            return rest.strip()
        return text
    if text.startswith(_PAGE_REFERENCE_PREFIXES):
        return ""
    return text


def _confidence_label(raw: str) -> str:
    return _CONFIDENCE_LABELS.get(raw.strip().lower(), "")


_DETECTED_TEXT_LEAD_INS: tuple[str, ...] = ("Review needed: ", "Likely problem: ")


def _clean_detected_text(text: str) -> str:
    """Drop a redundant inline "Problem: " label from polished comment text.

    Several rule comment templates are written for the web card layout, where
    a bold "Problem:" label precedes the sentence. In this report the
    "What was detected:" field label already plays that role, so a leftover
    "Review needed: Problem: ..." or "Likely problem: Problem: ..." would
    read as a duplicated label (see requirement to avoid "Likely problem:
    Problem:"-style wording).
    """
    cleaned = text.strip()
    for lead_in in _DETECTED_TEXT_LEAD_INS:
        if cleaned.startswith(lead_in):
            rest = cleaned[len(lead_in) :]
            if rest.startswith("Problem: "):
                cleaned = lead_in + rest[len("Problem: ") :]
            break
    if cleaned.startswith("Problem: "):
        cleaned = cleaned[len("Problem: ") :]
    return cleaned


def _title_for(rule_id: str, issue_type: str, category: str) -> str:
    """Return a short, student-facing title for one problem record.

    Deliberately does not fall back to the long Ester-authored yes/no rule
    question (``student_facing_issue_label``'s first preference): that
    phrasing is a full sentence meant for a rule-level card, and using it
    verbatim here made many unrelated occurrences of the same rule show the
    identical long question as their title. Prefers a hand-curated short
    title, then the short humanized issue-type label -- both already
    written to be title-length and student-facing -- before falling back to
    the coarse category label.
    """
    if has_curated_issue_type_title(rule_id, issue_type):
        curated = issue_type_title(rule_id, issue_type).strip()
        if curated:
            return curated
    label = humanize_issue_type(issue_type).strip()
    if label:
        return label
    return category_display_label(category)


def _p011_margin_title(
    details: Mapping[str, str],
    page: int | None,
    p011_page_stats: dict[Any, Any] | None,
) -> str:
    """Return a side-specific title for a P011 margin-boundary problem.

    Mirrors the same page-level rollup ``individual_finding_comment_and_fix``
    and ``_problem_location_text`` use for P011, so a page with more than one
    affected side (e.g. bottom and right) names every affected side in the
    title rather than only the first underlying finding's side.
    """
    page_stats = p011_page_stats.get(page) if p011_page_stats is not None and page else None
    if page_stats is not None and getattr(page_stats, "raw_finding_count", 1) > 1:
        sides = sorted({_side_short_label(side) for side in page_stats.sides if side.strip()})
    else:
        raw_side = details.get("side", "").strip()
        sides = [_side_short_label(raw_side)] if raw_side else []
    if not sides:
        return "Margin boundary violation"
    return f"{_join_margin_labels(sides).capitalize()} boundary violation"


def _manuscript_page_labels(findings: list[AuditFinding]) -> dict[int, str]:
    """Return {pdf_page: printed/manuscript page label} from any finding's details.

    ``document_page_label`` is recorded by the page-number detectors for
    (nearly) every page while sweeping the whole document, even though most
    of those findings are informational and never surface as visible
    problems -- so this scans *all* findings, not just visible ones.
    """
    labels: dict[int, str] = {}
    for finding in findings:
        if finding.page is None:
            continue
        label = (finding.details or {}).get("document_page_label", "").strip()
        if label and finding.page not in labels:
            labels[finding.page] = label
    return labels


@dataclass(frozen=True)
class _Occurrence:
    rule_id: str
    issue_type: str
    page: int | None
    title: str
    section: str
    exact_location: str
    detected_text: str
    fix_text: str
    confidence: str
    rule_reference: str
    problem_number: int
    checks: tuple[str, ...] = ()


@dataclass
class _Record:
    page: int | None
    title: str
    section: str
    manuscript_page: str
    exact_location: str
    locations: list[str]
    detected_text: str
    fix_text: str
    confidence: str
    rule_reference: str
    occurrence_count: int
    sort_key: int
    number: int = 0
    checks: tuple[str, ...] = ()


def _build_occurrences(
    visible_findings: list[dict[str, Any]],
    *,
    audit_type: str,
    public_rule_reference_id: PublicRuleReferenceFn,
    p012_count_by_page: dict[int, int],
    p026_pattern_stats: dict[Any, Any],
    p011_page_stats: dict[Any, Any],
) -> list[_Occurrence]:
    occurrences: list[_Occurrence] = []
    for finding in visible_findings:
        details_raw = finding.get("details", {})
        details = (
            {str(k): str(v) for k, v in details_raw.items()}
            if isinstance(details_raw, Mapping)
            else {}
        )
        rule_id = str(finding.get("rule_id", ""))
        issue_type = details.get("issue_type", "")
        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        severity = str(finding.get("severity", "WARNING"))

        comment, fix = individual_finding_comment_and_fix(
            rule_id,
            issue_type,
            severity=severity,
            page=page,
            details=details,
            p012_count_by_page=p012_count_by_page,
            p026_pattern_stats=p026_pattern_stats,
            p011_page_stats=p011_page_stats,
        )
        comment = _clean_detected_text(comment)
        fix = _detruncate_fix_text(rule_id, fix, details)
        fields = student_card_fields({**finding, "polished_comment": comment,
                                      "suggested_fix": fix}, details)
        if rule_id == "P011":
            comment, fix = fields["student_summary"], fields["student_fix"]
        else:
            comment = plain_student_text(comment)
        checks = finding_check_lines(fields)
        if fields["technical_details"]:
            checks += ["Technical details:"] + [
                f"{label}: {value}" for label, value in fields["technical_details"]
            ]

        location_text = _problem_location_text(
            finding,
            audit_type=audit_type,
            p012_count_by_page=p012_count_by_page,
            p026_pattern_stats=p026_pattern_stats,
            p011_page_stats=p011_page_stats,
        )
        exact_location = _strip_page_reference(location_text) or NOT_DETERMINED_LOCATION

        category = map_finding_rule_to_category(rule_id, details)
        section = category_display_label(category)
        problem_number_raw = finding.get("problem_number")
        problem_number = (
            int(problem_number_raw) if isinstance(problem_number_raw, int) else len(occurrences)
        )

        if rule_id == P011_RULE_ID and issue_type == P011_ISSUE_TYPE:
            title = _p011_margin_title(details, page, p011_page_stats)
        else:
            title = _title_for(rule_id, issue_type, category)

        occurrences.append(
            _Occurrence(
                rule_id=rule_id,
                issue_type=issue_type,
                page=page,
                title=title,
                section=section,
                exact_location=exact_location,
                detected_text=comment,
                fix_text=fix,
                confidence=_confidence_label(details.get("confidence", "")),
                rule_reference=public_rule_reference_id(
                    rule_id,
                    issue_type=issue_type,
                    source_q_rule_id=details.get("source_q_rule_id", ""),
                    details=details,
                ),
                problem_number=problem_number,
                checks=tuple(checks),
            )
        )
    return occurrences


def _consolidate_page_occurrences(occurrences: list[_Occurrence]) -> list[_Record]:
    """Collapse same-page/same-issue/same-fix occurrences into one record each.

    Grouping key intentionally matches "same rule, issue type, suggested fix,
    and page" (the list is already scoped to one page by the caller) so a
    repeated pattern -- e.g. two dozen Table of Contents spacing warnings --
    becomes one record listing every affected location, while occurrences
    that differ in fix text (a genuinely different problem) stay separate.
    """
    order: list[tuple[str, str, str]] = []
    groups: dict[tuple[str, str, str], list[_Occurrence]] = {}
    for occ in occurrences:
        key = (occ.rule_id, occ.issue_type, occ.fix_text)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(occ)

    records: list[_Record] = []
    for key in order:
        members = groups[key]
        first = members[0]
        if len(members) == 1:
            records.append(
                _Record(
                    page=first.page,
                    title=first.title,
                    section=first.section,
                    manuscript_page="",
                    exact_location=first.exact_location,
                    locations=[],
                    detected_text=first.detected_text,
                    fix_text=first.fix_text,
                    confidence=first.confidence,
                    rule_reference=first.rule_reference,
                    checks=tuple(dict.fromkeys(line for m in members for line in m.checks)),
                    occurrence_count=1,
                    sort_key=first.problem_number,
                )
            )
            continue

        # Deliberately not reusing report_outputs._high_volume_pattern_note here: its
        # wording points readers to a "Show individual occurrences" collapsible
        # section, which is a web-page UI element that does not exist in this plain
        # text file -- every affected location is already listed directly below.
        detected_text = (
            f"{first.detected_text} This same pattern was detected {len(members)} times "
            "on this page; every affected location is listed below rather than repeating "
            "the explanation for each one."
        )
        confidences = sorted({m.confidence for m in members if m.confidence})
        records.append(
            _Record(
                page=first.page,
                title=first.title,
                section=first.section,
                manuscript_page="",
                exact_location="",
                locations=[m.exact_location for m in members],
                detected_text=detected_text,
                fix_text=first.fix_text,
                confidence="/".join(confidences),
                rule_reference=first.rule_reference,
                    checks=tuple(dict.fromkeys(line for m in members for line in m.checks)),
                occurrence_count=len(members),
                sort_key=min(m.problem_number for m in members),
            )
        )
    records.sort(key=lambda record: record.sort_key)
    return records


def _build_records(
    occurrences: list[_Occurrence], manuscript_pages: dict[int, str]
) -> tuple[list[tuple[int, str, list[_Record]]], list[_Record]]:
    """Return (page_sections, document_wide_records) with sequential numbering.

    ``page_sections`` is ``[(pdf_page, manuscript_page_label, records), ...]``
    sorted by PDF page ascending; document-wide (page-less) records are
    returned separately so the caller can render them in a final section.
    """
    by_page: dict[int | None, list[_Occurrence]] = {}
    for occ in occurrences:
        by_page.setdefault(occ.page, []).append(occ)

    page_numbers = sorted(page for page in by_page if page is not None)
    page_sections: list[tuple[int, str, list[_Record]]] = []
    next_number = 1
    for page in page_numbers:
        records = _consolidate_page_occurrences(by_page[page])
        for record in records:
            record.number = next_number
            next_number += 1
        page_sections.append((page, manuscript_pages.get(page, ""), records))

    doc_wide_records = _consolidate_page_occurrences(by_page.get(None, []))
    for record in doc_wide_records:
        record.number = next_number
        next_number += 1

    return page_sections, doc_wide_records


_SEP_HEAVY = "=" * 60
_SEP_LIGHT = "-" * 60


def _render_record(record: _Record) -> list[str]:
    lines: list[str] = []
    heading = f"Problem {record.number} — {record.title}" if record.number else record.title
    lines.append(heading)
    if record.section:
        lines.append(f"  Section: {record.section}")
    if not record.locations:
        lines.append(f"  Exact location: {record.exact_location or NOT_DETERMINED_LOCATION}")
    lines.append(f"  What was detected: {record.detected_text}")
    if record.fix_text:
        lines.append(f"  What to check: {record.fix_text}")
    if record.occurrence_count > 1:
        lines.append(f"  Affected locations: {record.occurrence_count}")
        for index, location in enumerate(record.locations, start=1):
            lines.append(f"    {index}. {location}")
    lines.extend("  " + line for line in record.checks)
    if record.confidence:
        lines.append(f"  Confidence: {record.confidence}")
    if record.rule_reference:
        lines.append(f"  Public rule reference: {public_display_rule_id(record.rule_reference)}")
    lines.append("")
    return lines


def _render_text(
    *,
    metadata: Mapping[str, str],
    page_sections: list[tuple[int, str, list[_Record]]],
    doc_wide_records: list[_Record],
) -> str:
    total_problems = sum(len(records) for _, _, records in page_sections) + len(doc_wide_records)
    total_locations = sum(
        record.occurrence_count for _, _, records in page_sections for record in records
    ) + sum(record.occurrence_count for record in doc_wide_records)

    lines: list[str] = []
    lines.append("NJIT THESIS/DISSERTATION FORMATTING AUDIT")
    lines.append("Student Report (Plain Text)")
    lines.append("")
    input_file_name = metadata.get("input_file_name", "").strip()
    if input_file_name:
        lines.append(f"Document: {input_file_name}")
    generated_at = metadata.get("generated_at", "").strip()
    if not generated_at:
        generated_at = datetime.now(timezone.utc).isoformat()
    lines.append(f"Generated: {generated_at}")
    lines.append("")

    lines.append(_SEP_LIGHT)
    problem_noun = "problem" if total_problems == 1 else "problems"
    if total_problems == 0:
        lines.append("No student-facing formatting problems were detected.")
    elif total_locations > total_problems:
        location_noun = "location" if total_locations == 1 else "locations"
        lines.append(
            f"{total_problems} {problem_noun} requiring review, representing "
            f"{total_locations} affected {location_noun}."
        )
    else:
        lines.append(f"{total_problems} {problem_noun} requiring review.")
    lines.append(_SEP_LIGHT)
    lines.append("")
    lines.append(
        "This is an automated formatting check. It does not replace a full "
        "Graduate Studies review. Verify every item below against the current "
        "NJIT Thesis/Dissertation Formatting Guidelines and your committee's "
        "requirements before you submit."
    )
    lines.append("")

    lines.extend([CONFIDENCE_NOTE, ""])

    for page, manuscript_page, records in page_sections:
        if not records:
            continue
        lines.append(_SEP_HEAVY)
        lines.append(f"PDF PAGE {page}")
        if manuscript_page:
            lines.append(f"Manuscript page: {manuscript_page}")
        lines.append(_SEP_HEAVY)
        lines.append("")
        for record in records:
            lines.extend(_render_record(record))

    if doc_wide_records:
        lines.append(_SEP_HEAVY)
        lines.append("DOCUMENT-WIDE FINDINGS")
        lines.append(_SEP_HEAVY)
        lines.append("")
        for record in doc_wide_records:
            lines.extend(_render_record(record))

    lines.append(_SEP_LIGHT)
    lines.append("End of report.")
    lines.append(_SEP_LIGHT)

    return "\n".join(lines) + "\n"


def write_text_report(
    findings: list[AuditFinding],
    metadata: dict[str, str],
    output_path: Path,
    *,
    public_rule_reference_id: PublicRuleReferenceFn | None = None,
) -> None:
    """Write the plain-text, page-grouped student audit report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reference_fn = public_rule_reference_id or _default_public_rule_reference_id

    audit_type = metadata.get("audit_type", "pdf")
    prepared = _prepare_findings_for_export(findings, audit_type)
    payload = audit_findings_to_json_dict(prepared, metadata)
    serialized_findings = payload["findings"]
    meta = payload["metadata"]

    visible_findings = [
        finding
        for finding in serialized_findings
        if isinstance(finding.get("problem_number"), int) and finding["problem_number"] > 0
    ]

    manuscript_pages = _manuscript_page_labels(prepared)

    p012_count_by_page = count_p012_annotations_by_page(serialized_findings)
    p026_pattern_stats = init_p026_display_state(
        collect_p026_pattern_pages_from_serialized(serialized_findings),
    ).pattern_stats
    p011_page_stats = init_p011_display_state(
        collect_p011_margin_pages_from_serialized(serialized_findings),
    ).page_stats

    occurrences = _build_occurrences(
        visible_findings,
        audit_type=audit_type,
        public_rule_reference_id=reference_fn,
        p012_count_by_page=p012_count_by_page,
        p026_pattern_stats=p026_pattern_stats,
        p011_page_stats=p011_page_stats,
    )
    page_sections, doc_wide_records = _build_records(occurrences, manuscript_pages)

    text = _render_text(
        metadata=meta,
        page_sections=page_sections,
        doc_wide_records=doc_wide_records,
    )
    output_path.write_text(text, encoding="utf-8")
