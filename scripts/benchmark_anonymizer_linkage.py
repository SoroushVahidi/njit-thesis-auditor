"""Synthetic-only candidate-original linkage benchmark for the local PDF experiment.

The benchmark generates all PDFs locally. The output JSON contains aggregate
statistics and SHA256 hashes, never document text. Run it in an ignored private
directory; it is not a confidential-document evaluation or privacy guarantee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz

from scripts.experimental_pdf_anonymizer import run
from scripts.experimental_pdf_engine_adapter import UnsupportedEditorPDF

_WORDS = (
    "amber",
    "blue",
    "cobalt",
    "delta",
    "ember",
    "fern",
    "granite",
    "harbor",
    "island",
    "juniper",
    "kinetic",
    "linen",
    "marble",
    "novel",
    "opal",
    "paper",
    "quartz",
    "ribbon",
    "silver",
    "timber",
    "umbra",
    "velvet",
    "willow",
    "yellow",
    "zenith",
    "atlas",
    "cinder",
    "distant",
    "echo",
    "fabric",
    "garden",
    "hollow",
)
_TEMPLATES = (
    ("helv", 12, 612, 792, 1, 108),
    ("tiro", 11, 612, 792, 2, 112),
    ("cour", 10, 595, 842, 1, 104),
    ("hebo", 11, 595, 842, 2, 110),
)


def _generate(path: Path, template: int, seed: int, distribution: int) -> str:
    """Use controlled local generation; the editable PDF title proves nothing."""
    rng = random.Random(seed)
    font, size, width, height, pages, x = _TEMPLATES[template]
    vocabulary = (_WORDS[:16], _WORDS[16:], _WORDS)[distribution]
    with fitz.open() as doc:
        for page_number in range(pages):
            page = doc.new_page(width=width, height=height)
            page.insert_text((x, 105), "METHODS", fontname=font, fontsize=size + 2)
            for line_number in range(5):
                # Constant layout and small shared vocabulary avoid ID text or
                # an artificially unique placement per generated document.
                words = [rng.choice(vocabulary) for _ in range(rng.randint(5, 8))]
                page.insert_text(
                    (x + (28 if line_number == 0 else 0), 165 + line_number * 23),
                    " ".join(words) + ".",
                    fontname=font,
                    fontsize=size,
                )
            page.insert_text((width / 2 - 3, height - 55), str(page_number + 1), fontname=font)
        doc.set_metadata({"title": "SYNTHETIC linkage population"})
        doc.save(path, garbage=4, deflate=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _features(path: Path, *, include_text: bool = True) -> dict[str, Any]:
    import re

    dimensions: list[tuple[float, float]] = []
    layout: list[tuple[int, float, float, float, str]] = []
    right: list[float] = []
    word_lengths: list[tuple[int, ...]] = []
    heading: list[tuple[int, float, float]] = []
    with fitz.open(path) as doc:
        for page_number, page in enumerate(doc):
            dimensions.append((round(page.rect.width, 2), round(page.rect.height, 2)))
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    span = line["spans"][0]
                    x0, _, x1, _ = line["bbox"]
                    origin = span["origin"]
                    layout.append(
                        (
                            page_number,
                            round(x0, 2),
                            round(origin[1], 2),
                            round(span["size"], 2),
                            str(span["font"]),
                        )
                    )
                    right.append(round(x1 - x0, 3))
                    if include_text:
                        word_lengths.append(
                            tuple(len(w) for w in re.findall(r"[A-Za-z0-9]+", span["text"]))
                        )
                    if span["size"] > _TEMPLATES[0][1]:
                        heading.append((page_number, round(x0, 2), round(origin[1], 2)))
    return {
        "dimensions": dimensions,
        "layout": layout,
        "right": right,
        "word_lengths": word_lengths,
        "heading": heading,
    }


def _distance(query: dict[str, Any], candidate: dict[str, Any], attack: str) -> float:
    if query["dimensions"] != candidate["dimensions"]:
        return 1e6
    layout = query["layout"] != candidate["layout"]
    heading = query["heading"] != candidate["heading"]
    right = sum(abs(a - b) for a, b in zip(query["right"], candidate["right"], strict=True))
    if attack == "page":
        return 0
    if attack == "layout_font_heading":
        return float(layout) + float(heading)
    if attack == "line_geometry":
        return right
    words = sum(
        abs(len(a) - len(b)) + sum(x != y for x, y in zip(a, b))
        for a, b in zip(query["word_lengths"], candidate["word_lengths"], strict=True)
    )
    if attack == "word_lengths":
        return float(words)
    if attack == "combined":
        return right + 0.1 * words + 1000 * float(layout or heading)
    raise ValueError(attack)


def _topk_expected(distances: list[tuple[int, float]], truth: int, k: int) -> float:
    """Credit ties fractionally, so candidate order and filenames cannot win."""
    ordered = sorted(score for _, score in distances)
    true_score = next(score for index, score in distances if index == truth)
    before = sum(score < true_score - 1e-9 for score in ordered)
    tied = sum(abs(score - true_score) <= 1e-9 for score in ordered)
    return min(1.0, max(0.0, (k - before) / tied))


def _word_pattern_metrics(source: dict[str, Any], output: dict[str, Any]) -> tuple[float, float]:
    left = [length for line in source["word_lengths"] for length in line]
    right = [length for line in output["word_lengths"] for length in line]
    count = max(len(left), len(right), 1)
    positional_match = sum(a == b for a, b in zip(left, right)) / count
    paired = list(zip(left, right))
    if len(paired) < 2 or len({a for a, _ in paired}) < 2 or len({b for _, b in paired}) < 2:
        correlation = 0.0
    else:
        correlation = statistics.correlation([a for a, _ in paired], [b for _, b in paired])
    return positional_match, correlation


def _score(
    indices: list[int],
    candidate_indices: list[int],
    originals: dict[int, dict[str, Any]],
    outputs: dict[int, tuple[dict[str, Any], dict[str, Any]]],
    templates: dict[int, int],
    seed: int,
) -> dict[str, Any]:
    if not indices:
        return {}
    rng = random.Random(seed)
    attacks = ("page", "layout_font_heading", "line_geometry", "word_lengths", "combined")
    by_template: dict[int, list[int]] = defaultdict(list)
    for index in candidate_indices:
        by_template[templates[index]].append(index)
    result: dict[str, Any] = {}
    for k in (2, 5, 10, 20):
        if any(len(group) < k for group in by_template.values()):
            continue
        totals: dict[str, dict[str, float]] = {
            attack: {"top1": 0.0, "top3": 0.0} for attack in attacks
        }
        for truth in indices:
            distractors = rng.sample(
                [i for i in by_template[templates[truth]] if i != truth], k - 1
            )
            candidates = [truth, *distractors]
            for attack in attacks:
                # The first extraction never accesses span text. Use it for
                # every geometry-only attack, including the combined geometry
                # components when no lexical feature is requested.
                query = outputs[truth][1 if attack in {"word_lengths", "combined"} else 0]
                distances = [
                    (index, _distance(query, originals[index], attack)) for index in candidates
                ]
                totals[attack]["top1"] += _topk_expected(distances, truth, 1)
                totals[attack]["top3"] += _topk_expected(distances, truth, min(3, k))
        result[str(k)] = {
            attack: {
                "top1": round(counts["top1"] / len(indices), 4),
                "top3": round(counts["top3"] / len(indices), 4),
            }
            for attack, counts in totals.items()
        }
        result[str(k)]["chance"] = {"top1": round(1 / k, 4), "top3": round(min(3, k) / k, 4)}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--per-template", type=int, default=30)
    args = parser.parse_args()
    if args.per_template < 10:
        parser.error("Use at least ten documents per template")
    directory = args.directory
    directory.mkdir(parents=True, exist_ok=True)
    originals: dict[int, dict[str, Any]] = {}
    templates: dict[int, int] = {}
    manifest: list[dict[str, Any]] = []
    for template in range(len(_TEMPLATES)):
        for ordinal in range(args.per_template):
            index = template * args.per_template + ordinal
            document_seed = args.seed + template * 100000 + ordinal
            path = directory / f"source-{index:03d}.pdf"
            distribution = ordinal % 3
            digest = _generate(path, template, document_seed, distribution)
            originals[index] = _features(path)
            templates[index] = template
            manifest.append(
                {
                    "index": index,
                    "template": template,
                    "distribution": distribution,
                    "seed": document_seed,
                    "sha256": digest,
                }
            )
    # Split is fixed before any policy results are inspected. Every template
    # contributes one third to the held-out population.
    heldout = [i for i in originals if i % args.per_template >= args.per_template * 2 // 3]
    development = [i for i in originals if i not in heldout]
    strategies: dict[str, Any] = {}
    for strategy in ("balanced", "boundary", "segmented"):
        outputs: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
        refusals: list[int] = []
        refusal_reasons: Counter[str] = Counter()
        reports: list[dict[str, Any]] = []
        for index in originals:
            source = directory / f"source-{index:03d}.pdf"
            output = directory / f"{strategy}-{index:03d}.pdf"
            try:
                report = run(source, output, seed=args.seed + index + 17, strategy=strategy)
            except UnsupportedEditorPDF as exc:
                refusals.append(index)
                refusal_reasons[str(exc)] += 1
                continue
            reports.append(report)
            outputs[index] = (_features(output, include_text=False), _features(output))
        accepted_development = [i for i in development if i in outputs]
        accepted_heldout = [i for i in heldout if i in outputs]
        signatures = [tuple(outputs[i][0]["right"]) for i in accepted_heldout]
        counts = Counter(signatures)
        word_metrics = [_word_pattern_metrics(originals[i], outputs[i][1]) for i in outputs]
        strategies[strategy] = {
            "accepted": len(outputs),
            "refused": len(refusals),
            "refused_indices": refusals,
            "refusal_reasons": dict(refusal_reasons),
            "development_queries": len(accepted_development),
            "heldout_queries": len(accepted_heldout),
            "development": _score(
                accepted_development, development, originals, outputs, templates, args.seed + 1
            ),
            "heldout": _score(
                accepted_heldout, heldout, originals, outputs, templates, args.seed + 2
            ),
            "heldout_unique_line_geometry_fraction": round(
                sum(counts[signature] == 1 for signature in signatures) / len(signatures), 4
            )
            if signatures
            else None,
            "word_length_pattern_equal_fraction": round(
                sum(report["privacy"]["word_length_pattern_equal"] for report in reports)
                / len(reports),
                4,
            )
            if reports
            else None,
            "mean_word_length_positional_match": round(
                statistics.mean(pair[0] for pair in word_metrics), 4
            )
            if word_metrics
            else None,
            "mean_aligned_word_length_correlation": round(
                statistics.mean(pair[1] for pair in word_metrics), 4
            )
            if word_metrics
            else None,
            "max_line_right_drift_pt": max(
                (report["geometry"]["max_line_end_x_delta_pt"] for report in reports), default=None
            ),
            "max_character_box_drift_pt": max(
                (report["max_character_bbox_delta_pt"] for report in reports), default=None
            ),
            "auditor_lost": sum(report["auditor"]["lost"] for report in reports),
            "auditor_new": sum(report["auditor"]["introduced"] for report in reports),
            "auditor_source": sum(report["auditor"]["original"] for report in reports),
            "auditor_matched": sum(report["auditor"]["full_box_matched"] for report in reports),
            "recovered_source_words": sum(
                report["privacy"]["recovered_nonstructural_source_words"] for report in reports
            ),
            "residual_structure_failures": sum(
                bool(any(report["privacy"]["residual_structures"].values()))
                or bool(report["privacy"]["unindexed_or_duplicate_object_definitions"])
                or report["privacy"]["eof_markers"] != 1
                for report in reports
            ),
        }
    payload = {
        "scope": "synthetic_only",
        "source": "controlled local PyMuPDF Base14 ASCII generation",
        "provenance_limit": "Editable PDF metadata is not an origin proof",
        "seed": args.seed,
        "per_template": args.per_template,
        "template_count": len(_TEMPLATES),
        "population": len(originals),
        "development": len(development),
        "heldout": len(heldout),
        "manifest": manifest,
        "strategies": strategies,
    }
    (directory / "results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"population": len(originals), "strategies": strategies}, sort_keys=True))


if __name__ == "__main__":
    main()
