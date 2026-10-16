"""Reproducible synthetic comparison: October 15 baselines and gated prototype."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

import fitz

from njit_auditor.experimental_pdf_text import UnsupportedPDF, transform_synthetic_pdf
from scripts.evaluate_pdf_editor_adaptation import (
    _anchor_comparison,
    _generate_list_of_tables_fixture,
    _strict_comparison,
)
from scripts.experimental_pdf_anonymizer import run
from scripts.experimental_pdf_engine_adapter import (
    UnsupportedEditorPDF,
    transform_with_pdf_edit_engine,
)
from scripts.generate_anonymizer_adversarial_fixtures import (
    make_adversarial_fixtures,
    make_extended_thesis,
)
from scripts.generate_synthetic_obfuscation_fixtures import generate_fixtures


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "median": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "median": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))],
        "max": ordered[-1],
    }


def _collect(path: Path) -> dict[str, Any]:
    page_boxes = []
    lines = []
    characters = []
    blocks = 0
    with fitz.open(path) as doc:
        for number, page in enumerate(doc):
            page_boxes.append(
                {
                    "mediabox": list(page.mediabox),
                    "cropbox": list(page.cropbox),
                    "rotation": page.rotation,
                }
            )
            for block in page.get_text("rawdict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                blocks += 1
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    origin = spans[0]["origin"] if spans else (0, 0)
                    lines.append(
                        {
                            "page": number,
                            "bbox": line["bbox"],
                            "origin": origin,
                            "spans": len(spans),
                            "fonts": [(s["font"], s["size"]) for s in spans],
                        }
                    )
                    for span in spans:
                        for char in span.get("chars", []):
                            characters.append({"page": number, "bbox": char["bbox"]})
    return {
        "pages": page_boxes,
        "blocks": blocks,
        "lines": lines,
        "characters": characters,
    }


def _geometry(source: Path, output: Path) -> dict[str, Any]:
    a, b = _collect(source), _collect(output)
    if len(a["lines"]) != len(b["lines"]):
        return {
            "comparable": False,
            "source_lines": len(a["lines"]),
            "output_lines": len(b["lines"]),
        }
    line_axis = defaultdict(list)
    baseline = []
    font_equal = 0
    span_equal = 0
    for first, second in zip(a["lines"], b["lines"], strict=True):
        for index, axis in enumerate(("left", "top", "right", "bottom")):
            line_axis[axis].append(abs(first["bbox"][index] - second["bbox"][index]))
        baseline.append(abs(first["origin"][1] - second["origin"][1]))
        font_equal += first["fonts"] == second["fonts"]
        span_equal += first["spans"] == second["spans"]
    source_spacing = [
        b["lines"][i]["origin"][1] - b["lines"][i - 1]["origin"][1]
        for i in range(1, len(b["lines"]))
        if b["lines"][i]["page"] == b["lines"][i - 1]["page"]
    ]
    original_spacing = [
        a["lines"][i]["origin"][1] - a["lines"][i - 1]["origin"][1]
        for i in range(1, len(a["lines"]))
        if a["lines"][i]["page"] == a["lines"][i - 1]["page"]
    ]
    char_drift = []
    if len(a["characters"]) == len(b["characters"]):
        char_drift = [
            max(abs(x - y) for x, y in zip(first["bbox"], second["bbox"], strict=True))
            for first, second in zip(a["characters"], b["characters"], strict=True)
        ]
    return {
        "comparable": True,
        "same_page_boxes": a["pages"] == b["pages"],
        "source_blocks": a["blocks"],
        "output_blocks": b["blocks"],
        "source_lines": len(a["lines"]),
        "output_lines": len(b["lines"]),
        "source_characters": len(a["characters"]),
        "output_characters": len(b["characters"]),
        "font_and_size_line_matches": font_equal,
        "span_count_matches": span_equal,
        "line_coordinate_delta_pt": {
            axis: _distribution(values) for axis, values in line_axis.items()
        },
        "baseline_y_delta_pt": _distribution(baseline),
        "adjacent_line_spacing_delta_pt": _distribution(
            [abs(x - y) for x, y in zip(original_spacing, source_spacing, strict=True)]
        ),
        "character_box_max_axis_delta_pt": _distribution(char_drift),
    }


def _render_outside_text(source: Path, output: Path) -> dict[str, int]:
    """Count changed rendered pixels outside the union of old/new text boxes."""
    changed = outside = 0
    with fitz.open(source) as original, fitz.open(output) as transformed:
        for first, second in zip(original, transformed, strict=True):
            a, b = first.get_pixmap(alpha=False), second.get_pixmap(alpha=False)
            if (a.width, a.height, a.n) != (b.width, b.height, b.n):
                raise ValueError("Render dimensions changed")
            source_pixels, output_pixels = a.samples, b.samples
            mask = bytearray(a.width * a.height)
            for page in (first, second):
                for block in page.get_text("dict").get("blocks", []):
                    for line in block.get("lines", []):
                        x0, y0, x1, y1 = line["bbox"]
                        for y in range(max(0, int(y0) - 2), min(a.height, int(y1) + 3)):
                            start = y * a.width + max(0, int(x0) - 2)
                            end = y * a.width + min(a.width, int(x1) + 3)
                            mask[start:end] = b"\1" * (end - start)
            for index in range(a.width * a.height):
                offset = index * a.n
                if source_pixels[offset : offset + a.n] != output_pixels[offset : offset + b.n]:
                    changed += 1
                    outside += not mask[index]
    return {"changed_pixels": changed, "changed_pixels_outside_text": outside}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.trials <= 20:
        parser.error("--trials must be 1..20")
    args.directory.mkdir(parents=True, exist_ok=True)
    historical = generate_fixtures(args.directory)
    supplemental = [
        _generate_list_of_tables_fixture(args.directory / "synthetic_list_of_tables.pdf"),
        make_extended_thesis(args.directory / "synthetic_extended_thesis.pdf"),
    ]
    adversarial = make_adversarial_fixtures(args.directory / "adversarial")
    supplemental.append(adversarial["multi_column"])
    rows: list[dict[str, Any]] = []
    for source in [*historical, *supplemental]:
        n = args.trials if source in historical else 1
        for seed in range(1, n + 1):
            for method in ("old_redraw", "editor_structural", "editor_balanced"):
                output = args.directory / f"{source.stem}_{method}_{seed}.pdf"
                start = time.perf_counter()
                try:
                    if method == "old_redraw":
                        # The October 15 baseline used SystemRandom. Pin its
                        # choice function in this comparison so reruns agree.
                        with patch(
                            "njit_auditor.experimental_pdf_text.secrets.choice",
                            random.Random(seed).choice,
                        ):
                            transform_synthetic_pdf(source, output)
                    elif method == "editor_structural":
                        transform_with_pdf_edit_engine(source, output, "structural", seed=seed)
                    else:
                        report = run(source, output, seed=seed)
                except (UnsupportedPDF, UnsupportedEditorPDF, ValueError, FileExistsError) as exc:
                    rows.append(
                        {
                            "fixture": source.stem,
                            "trial": seed,
                            "method": method,
                            "state": "REFUSED",
                            "reason": str(exc),
                            "seconds": time.perf_counter() - start,
                        }
                    )
                    continue
                elapsed = time.perf_counter() - start
                geometry = _geometry(source, output)
                anchors = _anchor_comparison(source, output)
                strict = _strict_comparison(source, output)
                rows.append(
                    {
                        "fixture": source.stem,
                        "trial": seed,
                        "method": method,
                        "state": "COMPLETED",
                        "seconds": elapsed,
                        "auditor": {
                            "original": strict["original"],
                            "matched": strict["matched"],
                            "lost": strict["lost"],
                            "new": strict["introduced"],
                            "per_rule": strict["per_rule"],
                            "anchor": anchors,
                            "lost_issue_locations": strict["lost_issue_locations"],
                            "introduced_issue_locations": strict["introduced_issue_locations"],
                        },
                        "geometry": geometry,
                        "render": _render_outside_text(source, output) if seed == 1 else None,
                        "privacy": report["privacy"] if method == "editor_balanced" else None,
                    }
                )
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        if row["state"] == "REFUSED":
            totals[row["method"]]["refused"] += 1
            continue
        totals[row["method"]]["completed"] += 1
        totals[row["method"]].update(
            {key: int(row["auditor"][key]) for key in ("original", "matched", "lost", "new")}
        )
    payload = {
        "scope": "synthetic_only",
        "auditor_revision": "4efd780dde53eea907a714df8bfed86e923ef86a",
        "upstream_editor_revision": "cee1d2cc042f84d0fb02c874765509c04a8624ac",
        "totals": {method: dict(counts) for method, counts in totals.items()},
        "rows": rows,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
