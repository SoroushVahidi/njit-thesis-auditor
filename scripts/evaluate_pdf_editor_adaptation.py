"""Compare synthetic PDF editor strategies with the previous reconstruction baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.experimental_pdf_text import transform_synthetic_pdf
from njit_auditor.models import AuditFinding
from scripts.evaluate_synthetic_obfuscation import evaluate_pair
from scripts.experimental_anonpdf_adapter import transform_with_anonpdf
from scripts.experimental_pdf_engine_adapter import _planned_lines, transform_with_pdf_edit_engine
from scripts.generate_synthetic_obfuscation_fixtures import generate_fixtures


def _anchor_key(finding: AuditFinding) -> tuple[Any, ...]:
    """Match the same issue at the same line origin, allowing width drift."""
    raw = str(finding.details.get("bbox") or "")
    if raw:
        try:
            x0, y0, _x1, y1 = (float(part) for part in raw.split(","))
            location: tuple[int, int, int] | str = (round(x0), round(y0), round(y1))
        except ValueError:
            location = raw
    else:
        location = ""
    return (
        finding.rule_id,
        finding.page,
        str(finding.details.get("issue_type", "")),
        finding.severity.value,
        location,
        finding.message if not raw else "",
    )


def _strict_key(finding: AuditFinding) -> tuple[Any, ...]:
    """Match issue, page, severity and rounded full box with multiplicity.

    A digest distinguishes unboxed messages without storing their text in a
    report. This remains a fixture comparison, not adjudicated reviewer truth.
    """
    raw = str(finding.details.get("bbox") or "")
    if raw:
        try:
            location: tuple[int, ...] | str = tuple(round(float(part)) for part in raw.split(","))
        except ValueError:
            location = raw
        message_digest = ""
    else:
        location = ""
        message_digest = hashlib.sha256(finding.message.encode()).hexdigest()[:16]
    return (
        finding.rule_id,
        finding.page,
        str(finding.details.get("issue_type", "")),
        finding.severity.value,
        location,
        message_digest,
    )


def _strict_comparison(original: Path, transformed: Path) -> dict[str, Any]:
    source = Counter(
        _strict_key(f) for f in run_pdf_audit_full(original) if f.severity.value != "PASS"
    )
    output = Counter(
        _strict_key(f) for f in run_pdf_audit_full(transformed) if f.severity.value != "PASS"
    )
    matched, lost, introduced = source & output, source - output, output - source
    rules = sorted({key[0] for key in source | output})
    return {
        "original": sum(source.values()),
        "matched": sum(matched.values()),
        "lost": sum(lost.values()),
        "introduced": sum(introduced.values()),
        "per_rule": {
            rule: {
                name: sum(value for key, value in counts.items() if key[0] == rule)
                for name, counts in (
                    ("original", source),
                    ("matched", matched),
                    ("lost", lost),
                    ("introduced", introduced),
                )
            }
            for rule in rules
        },
        "lost_issue_locations": [
            {
                "rule": key[0],
                "page": key[1],
                "issue_type": key[2],
                "severity": key[3],
                "rounded_bbox": key[4],
                "count": count,
            }
            for key, count in sorted(lost.items(), key=lambda item: str(item[0]))
        ],
        "introduced_issue_locations": [
            {
                "rule": key[0],
                "page": key[1],
                "issue_type": key[2],
                "severity": key[3],
                "rounded_bbox": key[4],
                "count": count,
            }
            for key, count in sorted(introduced.items(), key=lambda item: str(item[0]))
        ],
    }


def _anchor_comparison(original: Path, transformed: Path) -> dict[str, Any]:
    first = Counter(
        _anchor_key(f) for f in run_pdf_audit_full(original) if f.severity.value != "PASS"
    )
    second = Counter(
        _anchor_key(f) for f in run_pdf_audit_full(transformed) if f.severity.value != "PASS"
    )
    matched = first & second
    lost = first - second
    introduced = second - first
    rules = sorted({key[0] for key in first | second})
    return {
        "original": sum(first.values()),
        "matched": sum(matched.values()),
        "lost": sum(lost.values()),
        "introduced": sum(introduced.values()),
        "per_rule": {
            rule: {
                name: sum(value for key, value in counts.items() if key[0] == rule)
                for name, counts in (
                    ("original", first),
                    ("matched", matched),
                    ("lost", lost),
                    ("introduced", introduced),
                )
            }
            for rule in rules
        },
    }


def _geometry_detail(original: Path, transformed: Path) -> dict[str, Any]:
    def collect(path: Path) -> tuple[list[tuple[float, ...]], int, list[float]]:
        boxes: list[tuple[float, ...]] = []
        spans = 0
        leftmost: list[float] = []
        with fitz.open(path) as doc:
            for page in doc:
                page_left: list[float] = []
                for block in page.get_text("dict").get("blocks", []):
                    for line in block.get("lines", []):
                        boxes.append(tuple(float(v) for v in line["bbox"]))
                        spans += len(line.get("spans", []))
                        page_left.append(float(line["bbox"][0]))
                leftmost.append(min(page_left, default=page.rect.width))
        return boxes, spans, leftmost

    original_boxes, original_spans, original_leftmost = collect(original)
    transformed_boxes, transformed_spans, transformed_leftmost = collect(transformed)
    if len(original_boxes) != len(transformed_boxes):
        raise ValueError("Line counts changed; position comparison is unavailable")
    return {
        "original_spans": original_spans,
        "transformed_spans": transformed_spans,
        "max_line_start_x_delta_pt": max(
            (abs(a[0] - b[0]) for a, b in zip(original_boxes, transformed_boxes, strict=True)),
            default=0.0,
        ),
        "max_line_start_y_delta_pt": max(
            (abs(a[1] - b[1]) for a, b in zip(original_boxes, transformed_boxes, strict=True)),
            default=0.0,
        ),
        "max_line_end_x_delta_pt": max(
            (abs(a[2] - b[2]) for a, b in zip(original_boxes, transformed_boxes, strict=True)),
            default=0.0,
        ),
        "leftmost_text_x_original": original_leftmost,
        "leftmost_text_x_transformed": transformed_leftmost,
    }


def _generate_list_of_tables_fixture(path: Path) -> Path:
    """Add List of Tables coverage without changing the historical 190 denominator."""
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((196, 100), "LIST OF TABLES", fontname="tibo", fontsize=14)
        page.insert_text(
            (108, 160), "Table 1.1 Synthetic values ........ 2", fontname="tiro", fontsize=12
        )
        page.insert_text(
            (108, 184), "Table 1.2 Fabricated matrix ......... 3", fontname="tiro", fontsize=12
        )
        page.insert_text((300, 736), "v", fontname="tiro", fontsize=12)
        page = doc.new_page(width=612, height=792)
        page.insert_text((108, 100), "CHAPTER 1", fontname="tibo", fontsize=14)
        page.insert_text((108, 130), "RESULTS", fontname="tibo", fontsize=14)
        page.insert_text((108, 180), "Invented table data has no research meaning.", fontsize=12)
        page.insert_text((108, 210), "Table 1.1: Synthetic values.", fontname="tiit", fontsize=11)
        page.insert_text((300, 736), "1", fontname="tiro", fontsize=12)
        doc.set_metadata({"title": "SYNTHETIC List of Tables layout"})
        doc.save(path, garbage=4, deflate=True)
    return path


def _reconstruct_structural(source: Path, destination: Path) -> None:
    """Control: same marker-preserving text, but the prior per-glyph redraw method."""
    edits = _planned_lines(source, "structural")
    output = fitz.open()
    edit_index = 0
    with fitz.open(source) as doc:
        for original in doc:
            page = output.new_page(width=original.rect.width, height=original.rect.height)
            for block in original.get_text("rawdict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        chars = span.get("chars", [])
                        replacement = edits[edit_index].replacement
                        edit_index += 1
                        if len(chars) != len(replacement):
                            raise ValueError("Reconstruction control character count changed")
                        for char, substitute in zip(chars, replacement, strict=True):
                            if substitute.isspace():
                                continue
                            page.insert_text(
                                fitz.Point(char["origin"]),
                                substitute,
                                fontname={
                                    "Helvetica": "helv",
                                    "Helvetica-Bold": "hebo",
                                    "Times-Roman": "tiro",
                                    "Times-Bold": "tibo",
                                    "Times-Italic": "tiit",
                                    "Courier": "cour",
                                    "Courier-Bold": "cobo",
                                }[span["font"]],
                                fontsize=span["size"],
                            )
    if edit_index != len(edits):
        raise ValueError("Reconstruction control line count changed")
    output.set_metadata({"title": "SYNTHETIC structural reconstruction control"})
    with tempfile.NamedTemporaryFile(
        prefix="structural-control-", suffix=".pdf", dir=destination.parent, delete=False
    ) as temp:
        temporary = Path(temp.name)
    try:
        output.save(temporary, garbage=4, deflate=True)
        os.link(temporary, destination)
    finally:
        output.close()
        temporary.unlink(missing_ok=True)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    per_rule: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        totals.update(
            {
                name: int(row[name])
                for name in (
                    "original_findings",
                    "matched_findings",
                    "lost_findings",
                    "introduced_findings",
                )
            }
        )
        for rule, counts in row["per_rule"].items():
            per_rule[rule].update(counts)
    return {
        "pairs": len(rows),
        "totals": dict(totals),
        "per_rule": {rule: dict(counts) for rule, counts in sorted(per_rule.items())},
        "max_character_bbox_delta_pt": max(row["max_character_bbox_delta_pt"] for row in rows),
        "max_line_bbox_delta_pt": max(row["max_line_bbox_delta_pt"] for row in rows),
        "all_page_sizes_identical": all(row["page_sizes_identical"] for row in rows),
        "all_line_counts_identical": all(
            row["original_lines"] == row["transformed_lines"] for row in rows
        ),
        "all_block_counts_identical": all(
            row["original_blocks"] == row["transformed_blocks"] for row in rows
        ),
        "all_character_counts_identical": all(
            row["original_characters"] == row["transformed_characters"] for row in rows
        ),
        "all_font_names_identical": all(
            row["font_name_matches"] == row["original_characters"] for row in rows
        ),
        "max_font_size_delta_pt": max(row["max_font_size_delta_pt"] for row in rows),
        "max_line_start_x_delta_pt": max(
            row["geometry_detail"]["max_line_start_x_delta_pt"] for row in rows
        ),
        "max_line_start_y_delta_pt": max(
            row["geometry_detail"]["max_line_start_y_delta_pt"] for row in rows
        ),
        "max_line_end_x_delta_pt": max(
            row["geometry_detail"]["max_line_end_x_delta_pt"] for row in rows
        ),
        "all_span_counts_identical": all(
            row["geometry_detail"]["original_spans"] == row["geometry_detail"]["transformed_spans"]
            for row in rows
        ),
        "anchor_totals": {
            name: sum(row["anchor_comparison"][name] for row in rows)
            for name in ("original", "matched", "lost", "introduced")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--anonpdf-script", type=Path)
    args = parser.parse_args()
    if not 1 <= args.trials <= 20:
        parser.error("--trials must be 1–20")
    rows: dict[str, list[dict[str, Any]]] = {
        strategy: []
        for strategy in (
            "reconstruction",
            "reconstruction_structural",
            "random",
            "width",
            "structural",
        )
    }
    if args.anonpdf_script:
        rows["anonpdf_fixed"] = []

    def transform(source: Path, strategy: str, trial: int) -> dict[str, Any]:
        destination = source.with_name(f"{source.stem}_{strategy}_{trial}.pdf")
        if strategy == "reconstruction":
            transform_synthetic_pdf(source, destination)
        elif strategy == "reconstruction_structural":
            _reconstruct_structural(source, destination)
        elif strategy == "anonpdf_fixed":
            transform_with_anonpdf(source, destination, args.anonpdf_script)
        else:
            transform_with_pdf_edit_engine(source, destination, strategy)
        report = evaluate_pair(source, destination)
        report["geometry_detail"] = _geometry_detail(source, destination)
        report["anchor_comparison"] = _anchor_comparison(source, destination)
        report["trial"] = trial
        return report

    for source in generate_fixtures(args.directory):
        for trial in range(1, args.trials + 1):
            for strategy in rows:
                rows[strategy].append(transform(source, strategy, trial))
    supplemental_source = _generate_list_of_tables_fixture(
        args.directory / "synthetic_list_of_tables.pdf"
    )
    supplemental = {strategy: transform(supplemental_source, strategy, 1) for strategy in rows}
    payload = {
        "auditor_revision": "991e45bb06b8d8168a9da63f4274f3876ac21075",
        "upstream_pdf_edit_engine_commit": "cee1d2cc042f84d0fb02c874765509c04a8624ac",
        "summary": {strategy: _aggregate(group) for strategy, group in rows.items()},
        "supplemental_list_of_tables": supplemental,
        "pairs": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
