"""Nonconfidential built-in example, generated locally without network access."""

import pymupdf


def sample_pdf() -> bytes:
    with pymupdf.open() as document:
        headings = [
            "SYNTHETIC THESIS", "ABSTRACT", "ACKNOWLEDGMENTS", "TABLE OF CONTENTS",
            "LIST OF TABLES", "LIST OF FIGURES", "CHAPTER 1", "REFERENCES",
        ]
        for number, heading in enumerate(headings, 1):
            page = document.new_page(width=612, height=792)
            page.insert_text((72, 72), heading, fontname="hebo", fontsize=14)
            if heading == "TABLE OF CONTENTS":
                lines = ["CHAPTER 1 INTRODUCTION ........ 1", "REFERENCES ........ 2"]
            elif heading in {"LIST OF TABLES", "LIST OF FIGURES"}:
                kind = "Table" if heading == "LIST OF TABLES" else "Figure"
                lines = [f"{kind}     Title                                  Page",
                         f"{kind} 1.1 Synthetic example ........ 1"]
            else:
                lines = ["Synthetic content for testing only. No student material is included."] * 8
            for index, line in enumerate(lines):
                page.insert_text((72, 110 + 24 * index), line, fontsize=12, fontname="tiro")
            page.insert_text((302, 755), str(number), fontsize=12)
        return document.tobytes(no_new_id=True)
