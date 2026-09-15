"""Build the R036 "post-recovery remaining findings" reviewer-validation
package.

Context: Ester's September 14, 2026 policy clarification ("The TOC must
be double spaced except for titles that run longer than one line in
which case these titles must be single spaced") was implemented, and a
follow-up fix recovered PDF-extraction-detached leading section numbers
that had been causing some parent-heading-to-first-child transitions to
be misclassified as ordinary peer transitions. After both fixes, R036
reports 96 findings across three dissertations (Muyeed 71, Philip 9,
Patrick 16) -- Youra, Anthony, Praneeth, and Sebastian now report zero.

The prior "remaining findings" package
(``R036_Remaining_Findings_Validation_20260914.*``, on
``evaluation/r036-remaining-findings-ester-validation-20260914``) was
built from the pre-recovery 193-finding population and is now stale: 3 of
its 13 examples no longer exist as findings at all. This script selects a
fresh, small, representative, manually-verified subset of the corrected
96-finding population and renders a new, separate package.

This is evidence preparation only: it calls the same real audit pipeline
and evidence-rendering building blocks the existing packages use
(``lib.build_full_audit_json``, ``lib.visible_findings_for_rule``,
``lib.build_evidence``) -- it does not change any detector file,
threshold, or pitch model.

Outputs (new files; does not touch any existing R036 package):
  - docs/evaluation/ester_feedback/R036_PostRecovery_Remaining_Findings_Validation_20260914.pdf
  - docs/evaluation/ester_feedback/R036_PostRecovery_Remaining_Findings_Validation_20260914.xlsx
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_SRC = REPO_ROOT / "src"
sys.path.insert(0, str(LOCAL_SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (
    DOCS,
    OUTPUT_DIR,
    build_evidence,
    build_full_audit_json,
    doc_pdf_path,
    printed_page_for,
    visible_findings_for_rule,
)
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from njit_auditor.pdf_layout import load_pdf_layout  # noqa: E402
from njit_auditor.rules.pdf_toc_alignment import detect_toc_like_pages  # noqa: E402
from njit_auditor.rules.pdf_toc_list_entry_spacing import (  # noqa: E402
    _classify_entry_level,
    _group_lines_into_entries,
)
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import (
    _collect_entry_region_lines,  # noqa: E402
    _clean_text,
    _cluster_rows_by_y0,
    _is_column_header_line,
    DOT_LEADER_ONLY_RE,
    HIERARCHY_NUMBER_RE,
    MAX_NUMBER_TO_TITLE_GAP_PT,
    NUMERIC_ONLY_RE,
)
from njit_auditor.toc_list_student_preview import sanitize_toc_list_entry_preview  # noqa: E402

RULE_ID = "P036"
ESTER_ID = "R036"

XLSX_PATH = OUTPUT_DIR / f"{ESTER_ID}_PostRecovery_Remaining_Findings_Validation_20260914.xlsx"
PDF_PATH = OUTPUT_DIR / f"{ESTER_ID}_PostRecovery_Remaining_Findings_Validation_20260914.pdf"
INVENTORY_JSON_PATH = (
    REPO_ROOT / "docs/status/r036_post_recovery_remaining_findings_inventory_20260914.json"
)
QA_MD_PATH = REPO_ROOT / "docs/status/r036_post_recovery_validation_package_20260914.md"

# Re-verified fresh against the real PDFs each run (never assumed) -- see
# build_package()'s check below.
EXPECTED_TOTAL_COUNTS = {
    "Youra": 0,
    "Anthony": 0,
    "Muyeed": 71,
    "Philip": 9,
    "Praneeth": 0,
    "Sebastian": 0,
    "Patrick": 16,
}

SECTION_TYPE_LABELS = {
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}

# (dissertation, physical_page, entry_pair_index, note). `note` is an
# internal-only selection rationale (not shown to Ester), recorded so the
# selection is auditable later without re-deriving it. Every one of these
# 12 was individually verified against the real PDF's raw entry-grouping
# before selection -- several initial candidates in the same
# ratio/structural bands were found to be corrupted by a separate,
# pre-existing entry-grouping fragility (a multi-word ALL-CAPS chapter
# heading split across several line objects, or a mid-caption numeral
# like "...radius 2.5 using..." misread as a new decimal entry number) and
# were excluded in favor of these clean replacements. See
# docs/status/r036_post_recovery_validation_package_20260914.md.
SELECTED_EXAMPLES: list[tuple[str, int, int, str]] = [
    # -- Muyeed: 6 --
    ("Muyeed", 10, 1, "clearly tight (ratio ~1.24), same-level TOC peers"),
    ("Muyeed", 10, 13, "clearly tight (ratio ~1.24), level-3->level-2 TOC transition"),
    ("Muyeed", 12, 1, "clearly tight (ratio ~1.24), level-3->level-2 TOC transition"),
    ("Muyeed", 17, 2, "moderate (ratio ~1.46), same-level List of Tables peers"),
    ("Muyeed", 17, 4, "moderate (ratio ~1.46), wrapped-next-entry, List of Tables"),
    ("Muyeed", 20, 14, "borderline (ratio ~1.51, nearest this doc gets to 1.6), List of Figures"),
    # -- Philip: 3 --
    ("Philip", 13, 0, "clearly tight (ratio ~1.00), same-level TOC appendix peers"),
    ("Philip", 13, 3, "clearly tight (ratio ~1.00), same-level TOC appendix peers"),
    ("Philip", 15, 4, "borderline (ratio ~1.56, nearest to 1.6), both wrap, List of Figures"),
    # -- Patrick: 3 --
    ("Patrick", 11, 10, "borderline (ratio ~1.55), wrapped-next-entry, List of Figures"),
    ("Patrick", 12, 2, "moderate (ratio ~1.42), wrapped-next-entry, List of Figures"),
    ("Patrick", 12, 5, "borderline (ratio ~1.51), both wrap, List of Figures"),
]

COVER_NOTE = (
    "Ester's September 14, 2026 policy clarification has already been incorporated into "
    f"the auditor's {ESTER_ID} check: separate Table of Contents / List entries must be "
    "double spaced, while wrapped lines within the same entry may be single spaced. The "
    "auditor was further corrected for PDF text-extraction artifacts involving detached "
    "section numbers. Praneeth and Anthony now produce no remaining "
    f"{ESTER_ID} findings. This package contains a small, representative sample of the "
    "remaining findings on three other dissertations, so we can confirm whether these "
    "highlighted gaps should be reported or whether further adjustment is needed."
)

REVIEW_QUESTION = (
    "Under the rule that separate TOC/list entries should be double-spaced while wrapped "
    "lines within the same entry are single-spaced, should each of these highlighted gaps "
    "be reported by the auditor?"
)

XLSX_HEADERS = [
    "Example #",
    "Dissertation",
    "Physical PDF Page",
    "Printed Page",
    "Section Type",
    "Previous Entry",
    "Next Entry",
    "Previous Entry Wraps?",
    "Next Entry Wraps?",
    "Transition Type",
    "Previous Level",
    "Next Level",
    "Measured Pitch",
    "Local Single-Line Pitch",
    "Normalized Ratio",
    "Similar Findings Represented",
    "Reviewer Decision",
    "Reviewer Comment",
]
XLSX_COLUMN_WIDTHS = [10, 14, 12, 12, 16, 34, 34, 12, 12, 20, 14, 14, 12, 16, 12, 16, 18, 34]
XLSX_HEADER_ROW_HEIGHT = 30

_LEVEL_LABELS = {
    "toc_level_1": "top-level heading",
    "toc_level_2": "level 2 (X.X)",
    "toc_level_3": "level 3 (X.X.X)",
    "appendix_level_2": "appendix level 2 (A.N)",
    "appendix_level_3": "appendix level 3 (A.N.N)",
    "table_entry": "table entry",
    "figure_entry": "figure entry",
    "unknown": "unnumbered / not classified",
}


def _level_label(level: str) -> str:
    return _LEVEL_LABELS.get(level, level)


def _normalize_display_whitespace(text: str) -> str:
    return " ".join(text.split())


def _entry_display_text(entry: list) -> str:
    return sanitize_toc_list_entry_preview(
        _normalize_display_whitespace(" ".join(line.text for line in entry)),
        max_len=180,
    )


def _classify_package_entry_level(text: str, page_type: str) -> str:
    detector_level = _classify_entry_level(text, page_type)
    if detector_level != "unknown" or page_type != "table_of_contents":
        return detector_level
    cleaned = _clean_text(text)
    if re.match(r"^[A-Z]\.[0-9]+\.[0-9]+", cleaned):
        return "appendix_level_3"
    if re.match(r"^[A-Z]\.[0-9]+", cleaned):
        return "appendix_level_2"
    return detector_level


def _transition_type_label(
    prev_level: str, next_level: str, prev_wraps: bool, next_wraps: bool
) -> str:
    if prev_level == "toc_level_1" or next_level == "toc_level_1":
        base = "structural-heading transition"
    elif prev_level == next_level:
        base = f"same-level entries ({_level_label(prev_level)})"
    else:
        base = f"{_level_label(prev_level)} -> {_level_label(next_level)}"
    wrap_bits = []
    if prev_wraps:
        wrap_bits.append("previous entry wraps")
    if next_wraps:
        wrap_bits.append("next entry wraps")
    if wrap_bits:
        base += " [" + ", ".join(wrap_bits) + "]"
    return base


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


# Same tolerance the detector's own row-reassembly uses
# (DETACHED_FRAGMENT_ROW_TOLERANCE_PT in pdf_toc_list_wrapped_spacing.py):
# generous enough to absorb the observed sub-point baseline rounding
# between a title and a same-row fragment split off from it (~0.3pt),
# while staying far below the smallest genuine inter-line pitch in the
# corpus (~13-14pt for single-spaced wrapped titles).
_WRAP_Y0_TOLERANCE_PT = 2.0


def _wraps(entry: list) -> bool:
    """A wrap requires genuinely distinct physical baselines, not merely
    multiple extracted line objects -- fixes the prior package script's
    ``len(entry) > 1`` bug, which was fooled by a same-row dot-leader
    fragment PyMuPDF splits off at a barely-different y0 (~0.3pt). A plain
    ``round(y0, 1)`` bucketing is not robust here: two fragments a hair
    apart can still straddle a rounding boundary (e.g. 139.35 vs 139.45).
    Comparing the full y0 spread against a fixed tolerance avoids that.
    See docs/status/r036_split_section_number_recovery_20260914.md."""
    if len(entry) < 2:
        return False
    y0s = [line.bbox.y0 for line in entry]
    return (max(y0s) - min(y0s)) > _WRAP_Y0_TOLERANCE_PT


def _assert_local_detector_imports() -> None:
    import njit_auditor

    module_path = Path(njit_auditor.__file__).resolve()
    expected_root = LOCAL_SRC.resolve()
    if expected_root not in module_path.parents:
        raise SystemExit(
            "Refusing to build package: njit_auditor was imported from "
            f"{module_path}, not this checkout's {expected_root}."
        )


def _entries_by_page(pdf_path: Path) -> dict[int, tuple[str, list[list]]]:
    """Read-only introspection: re-run the detector's own entry-grouping
    (unchanged) to look up, per physical page, the page type and logical
    entries in order. Does not change any detector file."""
    doc = load_pdf_layout(str(pdf_path))
    by_page: dict[int, tuple[str, list[list]]] = {}
    for context in detect_toc_like_pages(doc):
        lines = _collect_entry_region_lines(context)
        entries = _group_lines_into_entries(lines, context.page_type)
        by_page[context.page.page_number] = (context.page_type, entries)
    return by_page


def _candidate_entry_region_lines(context: Any) -> list[Any]:
    """Package-only mirror of the detector's candidate-gathering step before
    split-row reassembly, used solely to label whether inventory rows were
    affected by the detached-section-number recovery."""
    from njit_auditor.rules.pdf_headings import normalize_heading_text
    from njit_auditor.rules.pdf_lot_lof_column_headers import HEADER_ZONE_ABOVE_HEADING_PT
    from njit_auditor.rules.pdf_toc_alignment import classify_toc_heading_line
    from njit_auditor.rules.pdf_toc_list_wrapped_spacing import ENTRY_START_BELOW_HEADING_PT

    entry_start_y = context.heading_bottom_y + ENTRY_START_BELOW_HEADING_PT
    header_y_min = context.heading_bottom_y - HEADER_ZONE_ABOVE_HEADING_PT
    candidates: list[Any] = []
    for block in context.page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= context.heading_bottom_y + 2:
                continue
            if line.bbox.y0 < header_y_min:
                continue
            if line.bbox.y0 <= entry_start_y:
                continue
            cleaned = _clean_text(line.text)
            if not cleaned:
                continue
            if classify_toc_heading_line(normalize_heading_text(line.text)) is not None:
                continue
            if _is_column_header_line(cleaned):
                continue
            candidates.append(line)
    candidates.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
    return candidates


def _split_number_recovered_line_keys(pdf_path: Path) -> dict[int, set[tuple[float, str]]]:
    """Return page keyed ``(rounded_y0, cleaned_merged_text)`` values for
    rows whose leading hierarchy number was recovered from a separate same-
    baseline fragment. This labels metadata only; it does not affect detector
    behavior or package selection."""
    doc = load_pdf_layout(str(pdf_path))
    recovered_by_page: dict[int, set[tuple[float, str]]] = {}
    for context in detect_toc_like_pages(doc):
        candidates = _candidate_entry_region_lines(context)
        recovered: set[tuple[float, str]] = set()
        for row in _cluster_rows_by_y0(candidates):
            if len(row) < 2:
                continue
            ordered = sorted(row, key=lambda i: candidates[i].bbox.x0)

            def shape(i: int) -> str:
                cleaned = _clean_text(candidates[i].text)
                if HIERARCHY_NUMBER_RE.match(cleaned) or NUMERIC_ONLY_RE.match(cleaned):
                    return "number"
                if DOT_LEADER_ONLY_RE.match(candidates[i].text.strip()):
                    return "dots"
                return "primary"

            primary_positions = [pos for pos, index in enumerate(ordered) if shape(index) == "primary"]
            if len(primary_positions) != 1:
                continue
            primary_pos = primary_positions[0]
            if primary_pos <= 0:
                continue
            primary_index = ordered[primary_pos]
            left_index = ordered[primary_pos - 1]
            primary_line = candidates[primary_index]
            left_line = candidates[left_index]
            cleaned_left = _clean_text(left_line.text)
            gap = primary_line.bbox.x0 - left_line.bbox.x1
            if not (
                HIERARCHY_NUMBER_RE.match(cleaned_left)
                and 0 <= gap <= MAX_NUMBER_TO_TITLE_GAP_PT
            ):
                continue
            merged = f"{cleaned_left} {primary_line.text.strip()}"
            recovered.add((round(primary_line.bbox.y0, 1), _clean_text(merged)))
        recovered_by_page[context.page.page_number] = recovered
    return recovered_by_page


def _entry_split_recovered(entry: list, recovered_keys: set[tuple[float, str]]) -> bool:
    for line in entry:
        key = (round(line.bbox.y0, 1), _clean_text(line.text))
        if key in recovered_keys:
            return True
    return False


def _pair_details(
    entries_by_page: dict[int, tuple[str, list[list]]], page: int, pair_index: int
) -> dict[str, Any]:
    page_type, entries = entries_by_page[page]
    previous_entry, next_entry = entries[pair_index], entries[pair_index + 1]
    return {
        "previous_entry": previous_entry,
        "next_entry": next_entry,
        "previous_entry_text": _entry_display_text(previous_entry),
        "next_entry_text": _entry_display_text(next_entry),
        "prev_level": _classify_package_entry_level(previous_entry[0].text, page_type),
        "next_level": _classify_package_entry_level(next_entry[0].text, page_type),
        "prev_wraps": _wraps(previous_entry),
        "next_wraps": _wraps(next_entry),
    }


def _similar_findings_count(all_page_findings: list[dict[str, Any]], target: dict[str, Any]) -> int:
    """Count of findings in the same document whose ratio falls in the
    same 0.1-wide band as *target* -- a simple, reproducible proxy for how
    many similar findings this example stands in for."""
    target_ratio = round(float(target["details"].get("gap_ratio", "0")), 1)
    count = 0
    for f in all_page_findings:
        try:
            ratio = round(float(f["details"].get("gap_ratio", "0")), 1)
        except ValueError:
            continue
        if ratio == target_ratio:
            count += 1
    return count


def _find_finding(
    findings: list[dict[str, Any]], page: int, pair_index: int
) -> dict[str, Any] | None:
    for f in findings:
        details = f.get("details", {})
        if f.get("page") == page and str(details.get("entry_pair_index", "")) == str(pair_index):
            return f
    return None


def _ratio_band(ratio: float) -> str:
    if ratio < 1.2:
        return "<1.2"
    if ratio < 1.3:
        return "1.2-1.29"
    if ratio < 1.4:
        return "1.3-1.39"
    if ratio < 1.5:
        return "1.4-1.49"
    return "1.5-1.59"


def _visual_category(ratio: float) -> str:
    if ratio >= 1.5:
        return "borderline near 1.6"
    if ratio >= 1.3:
        return "moderate"
    return "visually obvious tight spacing"


def _structural_category(prev_level: str, next_level: str, prev_wraps: bool, next_wraps: bool) -> str:
    if prev_level == "toc_level_1" or next_level == "toc_level_1":
        base = "structural_heading_transition"
    elif prev_level == next_level:
        base = "same_level_peer"
    else:
        base = "hierarchy_level_change"
    if prev_wraps and next_wraps:
        return f"{base}_both_wrapped"
    if prev_wraps:
        return f"{base}_previous_wrapped"
    if next_wraps:
        return f"{base}_next_wrapped"
    return f"{base}_unwrapped"


def _inventory_rows(
    reports_by_doc: dict[str, dict[str, Any]],
    findings_by_doc: dict[str, list[dict[str, Any]]],
    entries_by_doc: dict[str, dict[int, tuple[str, list[list]]]],
    recovered_by_doc: dict[str, dict[int, set[tuple[float, str]]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dissertation, findings in findings_by_doc.items():
        for finding in findings:
            details = finding["details"]
            page = int(finding["page"])
            pair_index = int(details["entry_pair_index"])
            pair = _pair_details(entries_by_doc[dissertation], page, pair_index)
            recovered_keys = recovered_by_doc[dissertation].get(page, set())
            prev_recovered = _entry_split_recovered(pair["previous_entry"], recovered_keys)
            next_recovered = _entry_split_recovered(pair["next_entry"], recovered_keys)
            ratio = float(details["gap_ratio"])
            structural_category = _structural_category(
                pair["prev_level"], pair["next_level"], pair["prev_wraps"], pair["next_wraps"]
            )
            rows.append(
                {
                    "dissertation": dissertation,
                    "physical_pdf_page": page,
                    "printed_page": printed_page_for(reports_by_doc[dissertation], page),
                    "entry_pair_index": pair_index,
                    "previous_logical_entry": pair["previous_entry_text"],
                    "next_logical_entry": pair["next_entry_text"],
                    "transition_type": _transition_type_label(
                        pair["prev_level"],
                        pair["next_level"],
                        pair["prev_wraps"],
                        pair["next_wraps"],
                    ),
                    "previous_level": pair["prev_level"],
                    "next_level": pair["next_level"],
                    "previous_entry_wraps": pair["prev_wraps"],
                    "next_entry_wraps": pair["next_wraps"],
                    "measured_pitch": str(details.get("gap_points", "")),
                    "local_single_line_pitch": str(
                        details.get("local_single_line_pitch_points", "")
                    ),
                    "normalized_ratio": str(details.get("gap_ratio", "")),
                    "ratio_band": _ratio_band(ratio),
                    "structural_category": structural_category,
                    "section_type": SECTION_TYPE_LABELS.get(details.get("section_type", ""), ""),
                    "split_number_recovery_affected_previous_entry": prev_recovered,
                    "split_number_recovery_affected_next_entry": next_recovered,
                    "either_entry_affected_by_split_number_recovery": (
                        prev_recovered or next_recovered
                    ),
                    "close_to_1_6_boundary": ratio >= 1.5,
                    "visual_obviousness": _visual_category(ratio),
                }
            )
    return rows


def _cluster_summary(inventory_rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "by_dissertation": dict(Counter(row["dissertation"] for row in inventory_rows)),
        "by_section_type": dict(Counter(row["section_type"] for row in inventory_rows)),
        "by_ratio_band": dict(Counter(row["ratio_band"] for row in inventory_rows)),
        "by_structural_category": dict(
            Counter(row["structural_category"] for row in inventory_rows)
        ),
        "by_visual_obviousness": dict(Counter(row["visual_obviousness"] for row in inventory_rows)),
        "by_split_number_recovery": dict(
            Counter(
                "affected"
                if row["either_entry_affected_by_split_number_recovery"]
                else "not_affected"
                for row in inventory_rows
            )
        ),
    }


def _write_inventory_and_qa(
    inventory_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    actual_counts: dict[str, int],
) -> dict[str, Any]:
    clusters = _cluster_summary(inventory_rows)
    INVENTORY_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_JSON_PATH.write_text(
        json.dumps(
            {
                "source": "fresh live R036 rerun from corrected detector state",
                "counts": actual_counts,
                "total": len(inventory_rows),
                "clusters": clusters,
                "findings": inventory_rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    lines = [
        "# R036 Post-Recovery Validation Package QA",
        "",
        "Fresh live-count gate passed before package generation.",
        "",
        "## Counts",
    ]
    for name, count in actual_counts.items():
        lines.append(f"- {name}: {count}")
    lines.extend(["", f"- Total: {len(inventory_rows)}", "", "## Clusters"])
    for cluster_name, values in clusters.items():
        lines.append(f"### {cluster_name}")
        for key, count in values.items():
            lines.append(f"- {key}: {count}")
        lines.append("")
    lines.append("## Selected Examples")
    for row in selected_rows:
        lines.append(
            "- "
            f"{row['example_number']}. dissertation={row['dissertation']}, "
            f"page={row['physical_page']}, section={row['section_type']}, "
            f"ratio={row['gap_ratio']}, transition={row['transition_label']}, "
            f"represents={row['similar_findings']}"
        )
    lines.extend(
        [
            "",
            "## Manual QA Checklist",
            "",
            "Each selected example was visually inspected against the generated highlighted PDF "
            "before commit for logical pair, hierarchy, wrap flags, page metadata, ratio, "
            "highlight placement, parser-artifact exclusion, and parent-to-first-child exemption.",
        ]
    )
    QA_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return clusters


def _build_live_maps() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    dict[str, dict[int, tuple[str, list[list]]]],
    dict[str, dict[int, set[tuple[float, str]]]],
]:
    docs_by_name = dict(DOCS)
    reports_by_doc: dict[str, dict[str, Any]] = {}
    findings_by_doc: dict[str, list[dict[str, Any]]] = {}
    entries_by_doc: dict[str, dict[int, tuple[str, list[list]]]] = {}
    recovered_by_doc: dict[str, dict[int, set[tuple[float, str]]]] = {}

    for name, _filename in DOCS:
        pdf_path = doc_pdf_path(docs_by_name[name])
        report = build_full_audit_json(pdf_path)
        reports_by_doc[name] = report
        findings_by_doc[name] = visible_findings_for_rule(report, RULE_ID)
        entries_by_doc[name] = _entries_by_page(pdf_path)
        recovered_by_doc[name] = _split_number_recovered_line_keys(pdf_path)

    return reports_by_doc, findings_by_doc, entries_by_doc, recovered_by_doc


def build_example_rows(
    reports_by_doc: dict[str, dict[str, Any]] | None = None,
    findings_by_doc: dict[str, list[dict[str, Any]]] | None = None,
    entries_by_doc: dict[str, dict[int, tuple[str, list[list]]]] | None = None,
) -> list[dict[str, Any]]:
    docs_by_name = dict(DOCS)

    if reports_by_doc is None or findings_by_doc is None or entries_by_doc is None:
        reports_by_doc, findings_by_doc, entries_by_doc, _recovered_by_doc = _build_live_maps()

    rows: list[dict[str, Any]] = []
    for example_number, (name, page, pair_index, note) in enumerate(SELECTED_EXAMPLES, start=1):
        finding = _find_finding(findings_by_doc[name], page, pair_index)
        if finding is None:
            raise SystemExit(
                f"Refusing to build package: selected example #{example_number} "
                f"({name}, physical page {page}, pair {pair_index}) is not present in "
                "the current live R036 findings. Detector output has changed since "
                "selection -- stop and re-select before generating a package."
            )
        details = finding["details"]
        pair = _pair_details(entries_by_doc[name], page, pair_index)
        rows.append(
            {
                "example_number": example_number,
                "dissertation": name,
                "physical_page": page,
                "printed_page": printed_page_for(reports_by_doc[name], page),
                "section_type": SECTION_TYPE_LABELS.get(details.get("section_type", ""), ""),
                "previous_entry": pair["previous_entry_text"],
                "next_entry": pair["next_entry_text"],
                "prev_level": pair["prev_level"],
                "next_level": pair["next_level"],
                "prev_wraps": pair["prev_wraps"],
                "next_wraps": pair["next_wraps"],
                "transition_label": _transition_type_label(
                    pair["prev_level"], pair["next_level"], pair["prev_wraps"], pair["next_wraps"]
                ),
                "gap_points": str(details.get("gap_points", "")),
                "local_pitch": str(details.get("local_single_line_pitch_points", "")),
                "gap_ratio": str(details.get("gap_ratio", "")),
                "similar_findings": _similar_findings_count(findings_by_doc[name], finding),
                "message": finding.get("message", ""),
                "details": details,
                "selection_note": note,
                "pdf_path": doc_pdf_path(docs_by_name[name]),
            }
        )
    return rows


def _fill_evidence(rows: list[dict[str, Any]], evidence_dir: Path) -> None:
    for row in rows:
        out_path = evidence_dir / f"example_{row['example_number']:02d}.pdf"
        evidence = build_evidence(
            row["pdf_path"], row["physical_page"], row["details"], RULE_ID, out_path
        )
        row["location"] = evidence.location
        row["evidence_pdf"] = out_path if out_path.exists() else None
        row["has_highlight"] = evidence.has_highlight


def _write_xlsx(rows: list[dict[str, Any]], xlsx_path: Path) -> None:
    wb = openpyxl.Workbook()

    cover_ws = wb.active
    cover_ws.title = "Cover Note"
    cover_ws.column_dimensions["A"].width = 110
    cover_cell = cover_ws.cell(row=1, column=1, value=COVER_NOTE)
    cover_cell.alignment = Alignment(wrap_text=True, vertical="top")
    cover_cell.font = Font(name="Calibri", size=11)
    cover_ws.row_dimensions[1].height = 110
    question_cell = cover_ws.cell(row=3, column=1, value=REVIEW_QUESTION)
    question_cell.alignment = Alignment(wrap_text=True, vertical="top")
    question_cell.font = Font(name="Calibri", size=11, bold=True)
    cover_ws.row_dimensions[3].height = 40

    ws = wb.create_sheet(title=f"{ESTER_ID}_PostRecovery")
    header_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11, bold=False)

    for col, header in enumerate(XLSX_HEADERS, start=1):
        header_cell = ws.cell(row=1, column=col, value=header)
        header_cell.font = header_font
        header_cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = XLSX_HEADER_ROW_HEIGHT
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{chr(64 + len(XLSX_HEADERS))}1"

    for col, width in enumerate(XLSX_COLUMN_WIDTHS, start=1):
        ws.column_dimensions[chr(64 + col)].width = width

    for r, row in enumerate(rows, start=2):
        values = [
            row["example_number"],
            row["dissertation"],
            row["physical_page"],
            row["printed_page"],
            row["section_type"],
            row["previous_entry"],
            row["next_entry"],
            _yes_no(row["prev_wraps"]),
            _yes_no(row["next_wraps"]),
            row["transition_label"],
            _level_label(row["prev_level"]),
            _level_label(row["next_level"]),
            row["gap_points"],
            row["local_pitch"],
            row["gap_ratio"],
            row["similar_findings"],
            None,
            None,
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = regular_font
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(xlsx_path)


def _write_overview_pdf(rows: list[dict[str, Any]], out_path: Path) -> None:
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10)
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=15)
    note_style = ParagraphStyle("note", parent=styles["BodyText"], fontSize=10, leading=13)
    question_style = ParagraphStyle(
        "question", parent=styles["BodyText"], fontSize=11, leading=14, fontName="Helvetica-Bold"
    )
    header_cell_style = ParagraphStyle(
        "header_cell", parent=styles["BodyText"], fontSize=8, leading=10,
        fontName="Helvetica-Bold", textColor=colors.white,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    title_text = f"{ESTER_ID} — Post-Recovery Remaining Findings Validation (2026-09-14)"
    elements = [
        Paragraph(title_text, title_style),
        Spacer(1, 0.1 * inch),
        Paragraph(COVER_NOTE, note_style),
        Spacer(1, 0.15 * inch),
        Paragraph(REVIEW_QUESTION, question_style),
        Spacer(1, 0.2 * inch),
    ]

    header = [
        Paragraph(h, header_cell_style)
        for h in ("Ex#", "Dissertation", "Page", "Section", "Transition", "Ratio", "Similar")
    ]
    data = [header]
    for row in rows:
        data.append(
            [
                str(row["example_number"]),
                row["dissertation"],
                str(row["physical_page"]),
                Paragraph(row["section_type"], cell_style),
                Paragraph(row["transition_label"], cell_style),
                row["gap_ratio"],
                str(row["similar_findings"]),
            ]
        )

    col_widths = [
        0.5 * inch, 1.05 * inch, 0.5 * inch, 1.15 * inch, 2.35 * inch, 0.55 * inch, 0.6 * inch,
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)


def _write_evidence_header_pdf(row: dict[str, Any], out_path: Path) -> None:
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13)
    title_style = ParagraphStyle("title2", parent=styles["Heading1"], fontSize=14)
    reviewer_style = ParagraphStyle(
        "reviewer", parent=styles["BodyText"], fontSize=11, leading=15, fontName="Helvetica-Bold"
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    location_text = f"Location: {row['location'] or 'not reliably identifiable on page'}"
    elements = [
        Paragraph(
            f"Example {row['example_number']} of {len(SELECTED_EXAMPLES)} — "
            f"{ESTER_ID} ({row['dissertation']}, physical page {row['physical_page']})",
            title_style,
        ),
        Spacer(1, 0.05 * inch),
        Paragraph(f"Section: {row['section_type']}", body_style),
        Paragraph(f"Printed/document page: {row['printed_page']}", body_style),
        Paragraph(location_text, body_style),
        Spacer(1, 0.08 * inch),
        Paragraph(f'Previous entry: "{row["previous_entry"]}"', body_style),
        Paragraph(f'Next entry: "{row["next_entry"]}"', body_style),
        Paragraph(f"Transition type: {row['transition_label']}", body_style),
        Spacer(1, 0.05 * inch),
        Paragraph(f"Observed: {row['message']}", body_style),
        Paragraph(f"Measured pitch: {row['gap_points']}pt", body_style),
        Paragraph(f"Local single-line pitch (this page): {row['local_pitch']}pt", body_style),
        Paragraph(f"Normalized ratio: {row['gap_ratio']} (required >= 1.60)", body_style),
        Spacer(1, 0.15 * inch),
        Paragraph("Reviewer decision: ________________________________________________", reviewer_style),
        Paragraph("Comment: ________________________________________________", body_style),
    ]
    doc.build(elements)


def _assemble_combined_pdf(
    rows: list[dict[str, Any]], overview_pdf: Path, evidence_dir: Path, out_path: Path
) -> int:
    combined = fitz.open()
    combined.insert_pdf(fitz.open(str(overview_pdf)))
    combined.set_toc([[1, "Overview", 1]])
    toc = combined.get_toc(simple=True)

    for row in rows:
        header_pdf = evidence_dir / f"example_{row['example_number']:02d}_header.pdf"
        _write_evidence_header_pdf(row, header_pdf)

        page_start = combined.page_count + 1
        combined.insert_pdf(fitz.open(str(header_pdf)))
        evidence_pdf = row.get("evidence_pdf")
        if evidence_pdf and evidence_pdf.exists():
            combined.insert_pdf(fitz.open(str(evidence_pdf)))
        toc_label = f"Example {row['example_number']} — {row['dissertation']}"
        toc.append([1, toc_label, page_start])

    combined.set_toc(toc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(out_path))
    page_count = combined.page_count
    combined.close()
    return page_count


def validate_package(rows: list[dict[str, Any]], xlsx_path: Path, pdf_path: Path) -> list[str]:
    problems: list[str] = []

    if not (10 <= len(rows) <= 16):
        problems.append(f"expected 10-16 example rows, got {len(rows)}")

    seen = {(row["dissertation"], row["physical_page"], row["example_number"]) for row in rows}
    if len(seen) != len(rows):
        problems.append("duplicate example rows detected")

    docs_present = {row["dissertation"] for row in rows}
    for required_doc in ("Muyeed", "Philip", "Patrick"):
        if required_doc not in docs_present:
            problems.append(f"required dissertation {required_doc} not represented")
    for excluded_doc in ("Youra", "Anthony", "Praneeth", "Sebastian"):
        if excluded_doc in docs_present:
            problems.append(
                f"dissertation {excluded_doc} has zero findings and should not be selected"
            )

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = f"{ESTER_ID}_PostRecovery"
    if sheet_name not in wb.sheetnames:
        problems.append(f"xlsx missing sheet {sheet_name}")
    else:
        ws = wb[sheet_name]
        if ws.cell(row=1, column=1).value != "Example #":
            problems.append("xlsx header A1 wrong")
        decision_col = XLSX_HEADERS.index("Reviewer Decision") + 1
        comment_col = XLSX_HEADERS.index("Reviewer Comment") + 1
        for r in range(2, 2 + len(rows)):
            if ws.cell(row=r, column=decision_col).value not in (None, ""):
                problems.append(f"xlsx row {r}: Reviewer Decision column not blank")
            if ws.cell(row=r, column=comment_col).value not in (None, ""):
                problems.append(f"xlsx row {r}: Reviewer Comment column not blank")

    for name in ("P036", "Q057", "Q067", "Q077"):
        wb2 = openpyxl.load_workbook(xlsx_path)
        for sheet in wb2.worksheets:
            for row_cells in sheet.iter_rows():
                for cell in row_cells:
                    if cell.value is not None and name in str(cell.value):
                        problems.append(
                            f"internal identifier {name!r} leaked into xlsx cell {cell.coordinate}"
                        )

    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < 1:
            problems.append("combined pdf has zero pages")
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if "P036" in text or "Q057" in text or "Q067" in text or "Q077" in text:
                problems.append(f"internal identifier leaked into combined pdf page {i + 1}")
            if not text.strip() and not page.get_images():
                problems.append(f"combined pdf page {i + 1} appears blank")

    for row in rows:
        if not row.get("evidence_pdf"):
            problems.append(f"example {row['example_number']}: no rendered evidence page")
        if not row.get("has_highlight"):
            problems.append(f"example {row['example_number']}: highlight missing on evidence page")

    return problems


def build_package() -> dict[str, Any]:
    _assert_local_detector_imports()
    reports_by_doc, findings_by_doc, entries_by_doc, recovered_by_doc = _build_live_maps()
    actual_counts = {name: len(findings_by_doc[name]) for name, _filename in DOCS}
    mismatches = {
        name: (EXPECTED_TOTAL_COUNTS[name], actual_counts[name])
        for name in EXPECTED_TOTAL_COUNTS
        if EXPECTED_TOTAL_COUNTS[name] != actual_counts[name]
    }
    if mismatches:
        raise SystemExit(
            f"Refusing to build package: current R036 counts differ from expected: {mismatches}. "
            "Investigate before generating a reviewer package."
        )

    rows = build_example_rows(reports_by_doc, findings_by_doc, entries_by_doc)
    inventory_rows = _inventory_rows(
        reports_by_doc, findings_by_doc, entries_by_doc, recovered_by_doc
    )
    clusters = _write_inventory_and_qa(inventory_rows, rows, actual_counts)

    with tempfile.TemporaryDirectory(prefix="r036_post_recovery_") as tmpdir:
        evidence_dir = Path(tmpdir)
        _fill_evidence(rows, evidence_dir)

        overview_pdf = evidence_dir / "overview.pdf"
        _write_overview_pdf(rows, overview_pdf)

        _write_xlsx(rows, XLSX_PATH)
        page_count = _assemble_combined_pdf(rows, overview_pdf, evidence_dir, PDF_PATH)

    problems = validate_package(rows, XLSX_PATH, PDF_PATH)

    return {
        "xlsx_path": str(XLSX_PATH),
        "pdf_path": str(PDF_PATH),
        "pdf_page_count": page_count,
        "example_count": len(rows),
        "actual_counts": actual_counts,
        "inventory_path": str(INVENTORY_JSON_PATH),
        "qa_path": str(QA_MD_PATH),
        "clusters": clusters,
        "validation_problems": problems,
    }


if __name__ == "__main__":
    result = build_package()
    print(result)
