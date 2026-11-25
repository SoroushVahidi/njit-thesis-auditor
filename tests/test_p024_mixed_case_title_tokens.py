"""P024 should preserve clearly mixed-case terms while checking title case."""

from pathlib import Path

import pymupdf

from njit_auditor.audit_runner import run_pdf_audit_full


def test_p024_preserves_mixed_case_in_toc_and_list_of_tables(tmp_path: Path) -> None:
    path = tmp_path / "mixed-case-titles.pdf"
    with pymupdf.open() as doc:
        for heading, titles in (
            (
                "TABLE OF CONTENTS",
                [
                    "1.1 Results for eBrand Systems",
                    "1.2 Analysis of eModel samples",
                    "1.3 Valid Example Section",
                ],
            ),
            (
                "LIST OF TABLES",
                [
                    "Table 1.1 eBrand System Results",
                    "Table 1.2 eModel System samples",
                    "Table 1.3 Valid Example Table",
                ],
            ),
        ):
            page = doc.new_page(width=612, height=792)
            page.insert_text((220, 85), heading, fontname="Times-Bold", fontsize=14)
            for index, title in enumerate(titles):
                y = 150 + index * 27
                page.insert_text((108, y), title, fontsize=12)
                page.insert_text((494, y), f"{20 + index}", fontsize=12)
        doc.save(path)

    findings = [f for f in run_pdf_audit_full(path) if f.rule_id == "P024"]
    assert [(f.page, f.details["issue_type"]) for f in findings] == [
        (1, "toc_level_capitalization"),
        (2, "list_of_tables_title_case"),
    ]
    assert all("samples" in f.message for f in findings)
    assert all(f.details.get("bbox") for f in findings)
