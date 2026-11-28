"""Compare synthetic source and rebuilt PDFs by geometry, audit findings and text leakage."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.experimental_pdf_text import transform_synthetic_pdf
from njit_auditor.models import AuditFinding
from scripts.generate_synthetic_obfuscation_fixtures import generate_fixtures


def _layout(
    pdf: Path,
) -> tuple[list[tuple[float, float]], list[tuple[Any, ...]], list[tuple[float, ...]], int]:
    sizes: list[tuple[float, float]] = []
    chars: list[tuple[Any, ...]] = []
    line_boxes: list[tuple[float, ...]] = []
    block_count = 0
    with fitz.open(pdf) as doc:
        for page_number, page in enumerate(doc, 1):
            sizes.append((round(page.rect.width, 3), round(page.rect.height, 3)))
            for block in page.get_text("rawdict").get("blocks", []):
                if block.get("type") == 0:
                    block_count += 1
                for line in block.get("lines", []):
                    line_boxes.append(tuple(float(v) for v in line["bbox"]))
                    for span in line.get("spans", []):
                        for char in span.get("chars", []):
                            chars.append(
                                (
                                    page_number,
                                    tuple(float(v) for v in char["bbox"]),
                                    str(span["font"]),
                                    float(span["size"]),
                                )
                            )
    return sizes, chars, line_boxes, block_count


def _finding_key(finding: AuditFinding) -> tuple[str, int | None, str, str, str]:
    details = finding.details
    raw_bbox = str(details.get("bbox", ""))
    try:
        bbox = ",".join(str(round(float(v))) for v in raw_bbox.split(",")) if raw_bbox else ""
    except ValueError:
        bbox = raw_bbox
    return (
        finding.rule_id,
        finding.page,
        str(details.get("issue_type", "")),
        bbox,
        finding.severity.value,
    )


def evaluate_pair(original: Path, transformed: Path) -> dict[str, Any]:
    orig_sizes, orig_chars, orig_line_boxes, orig_blocks = _layout(original)
    new_sizes, new_chars, new_line_boxes, new_blocks = _layout(transformed)
    if len(orig_chars) == len(new_chars):
        bbox_deltas = [
            abs(a - b)
            for (_, first, _, _), (_, second, _, _) in zip(orig_chars, new_chars, strict=True)
            for a, b in zip(first, second, strict=True)
        ]
        font_match = sum(a[2] == b[2] for a, b in zip(orig_chars, new_chars, strict=True))
        size_deltas = [abs(a[3] - b[3]) for a, b in zip(orig_chars, new_chars, strict=True)]
    else:
        bbox_deltas = []
        font_match = 0
        size_deltas = []
    line_deltas = (
        [
            abs(a - b)
            for first, second in zip(orig_line_boxes, new_line_boxes, strict=True)
            for a, b in zip(first, second, strict=True)
        ]
        if len(orig_line_boxes) == len(new_line_boxes)
        else []
    )

    original_audit = run_pdf_audit_full(original)
    transformed_audit = run_pdf_audit_full(transformed)
    original_findings = Counter(
        _finding_key(f) for f in original_audit if f.severity.value != "PASS"
    )
    transformed_findings = Counter(
        _finding_key(f) for f in transformed_audit if f.severity.value != "PASS"
    )
    original_passes = Counter(_finding_key(f) for f in original_audit if f.severity.value == "PASS")
    transformed_passes = Counter(
        _finding_key(f) for f in transformed_audit if f.severity.value == "PASS"
    )
    matched = original_findings & transformed_findings
    lost = original_findings - transformed_findings
    introduced = transformed_findings - original_findings
    rules = sorted({key[0] for key in original_findings | transformed_findings})
    per_rule = {
        rule: {
            "original": sum(n for key, n in original_findings.items() if key[0] == rule),
            "transformed": sum(n for key, n in transformed_findings.items() if key[0] == rule),
            "matched": sum(n for key, n in matched.items() if key[0] == rule),
            "lost": sum(n for key, n in lost.items() if key[0] == rule),
            "introduced": sum(n for key, n in introduced.items() if key[0] == rule),
        }
        for rule in rules
    }

    with fitz.open(original) as source_doc, fitz.open(transformed) as output_doc:
        source_text = "\n".join(page.get_text() for page in source_doc)
        output_text = "\n".join(page.get_text() for page in output_doc)
        source_title = str(source_doc.metadata.get("title", ""))
        output_title = str(output_doc.metadata.get("title", ""))
        output_attachments = output_doc.embfile_count()
        output_images = sum(len(page.get_images(full=True)) for page in output_doc)
        output_annotations = sum(page.first_annot is not None for page in output_doc)
        output_links = sum(len(page.get_links()) for page in output_doc)
        object_data = "\n".join(
            output_doc.xref_object(xref)
            + "\n"
            + (output_doc.xref_stream(xref) or b"").decode("latin-1", errors="ignore")
            for xref in range(1, output_doc.xref_length())
        ).lower()
    original_words = {word.lower() for word in re.findall(r"[A-Za-z]{5,}", source_text)}
    output_words = {word.lower() for word in re.findall(r"[A-Za-z]{5,}", output_text)}
    remaining_words = sorted(original_words & output_words)
    source_lines = [
        line.strip().lower() for line in source_text.splitlines() if len(line.strip()) >= 8
    ]
    raw_bytes = transformed.read_bytes()
    reader = PdfReader(transformed)
    pypdf_text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()
    return {
        "original": original.name,
        "transformed": transformed.name,
        "pages": len(orig_sizes),
        "page_sizes_identical": orig_sizes == new_sizes,
        "original_blocks": orig_blocks,
        "transformed_blocks": new_blocks,
        "original_lines": len(orig_line_boxes),
        "transformed_lines": len(new_line_boxes),
        "original_characters": len(orig_chars),
        "transformed_characters": len(new_chars),
        "font_name_matches": font_match,
        "max_font_size_delta_pt": max(size_deltas, default=None),
        "max_character_bbox_delta_pt": max(bbox_deltas, default=None),
        "max_line_bbox_delta_pt": max(line_deltas, default=None),
        "original_findings": sum(original_findings.values()),
        "transformed_findings": sum(transformed_findings.values()),
        "matched_findings": sum(matched.values()),
        "lost_findings": sum(lost.values()),
        "introduced_findings": sum(introduced.values()),
        "per_rule": per_rule,
        "pass_results": {
            "original": sum(original_passes.values()),
            "transformed": sum(transformed_passes.values()),
            "matched": sum((original_passes & transformed_passes).values()),
        },
        "content_checks": {
            "original_words_5plus_in_extracted_output": remaining_words,
            "original_words_5plus_in_pypdf_output": sorted(
                word for word in original_words if word in pypdf_text
            ),
            "original_lines_in_pdf_objects": sorted(
                line for line in source_lines if line in object_data
            ),
            "source_title_in_output_metadata": source_title in output_title,
            "source_title_in_output_bytes": source_title.encode() in raw_bytes,
            "output_attachments": output_attachments,
            "pypdf_attachments": len(reader.attachments),
            "output_images": output_images,
            "output_annotations": output_annotations,
            "output_links": output_links,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Scratch directory for synthetic PDFs")
    parser.add_argument("--output", type=Path, help="Write machine-readable JSON here")
    parser.add_argument("--trials", type=int, default=1, help="Independent substitutions per PDF")
    args = parser.parse_args()
    if not 1 <= args.trials <= 20:
        parser.error("--trials must be between 1 and 20")
    reports = []
    for original in generate_fixtures(args.directory):
        for trial in range(1, args.trials + 1):
            transformed = original.with_name(original.stem + f"_obfuscated_t{trial}.pdf")
            summary = transform_synthetic_pdf(original, transformed)
            report = evaluate_pair(original, transformed)
            report["trial"] = trial
            report["transformation"] = summary.__dict__
            reports.append(report)
    payload = json.dumps(reports, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(args.output)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
