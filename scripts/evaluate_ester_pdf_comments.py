"""Local utility to compare Ester annotation categories vs PDF audit findings."""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.evaluation import summarize_audit_findings, summarize_comment_categories
from njit_auditor.pdf_comments import (
    extract_pdf_annotations,
    remove_pdf_annotations,
    write_annotations_json,
    write_annotations_markdown,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbers import run_pdf_page_number_candidates_rule


def main() -> None:
    source_pdf = Path("data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf")
    out_dir = Path("data/evaluation/generated/ester_yin_second_review")
    out_dir.mkdir(parents=True, exist_ok=True)

    annotations = extract_pdf_annotations(source_pdf)
    write_annotations_json(annotations, out_dir / "annotations.json")
    write_annotations_markdown(annotations, out_dir / "annotations.md")

    clean_pdf = out_dir / "clean_without_annotations.pdf"
    remove_pdf_annotations(source_pdf, clean_pdf)

    pdf_doc = load_pdf_layout(str(clean_pdf))
    findings = []
    findings.extend(run_pdf_page_number_candidates_rule(pdf_doc))
    findings.extend(run_pdf_margin_rule(pdf_doc))
    findings.extend(run_pdf_annotation_rule(str(clean_pdf)))

    comment_summary = summarize_comment_categories(annotations)
    finding_summary = summarize_audit_findings(findings)

    summary = {
        "source_pdf": source_pdf.name,
        "annotation_count": len(annotations),
        "comment_categories": comment_summary,
        "automatic_finding_categories": finding_summary,
    }
    (out_dir / "comparison_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
