# Complete student PDF report

The completed PDF audit offers **Download Complete PDF Report**. Its first section is a full copy of the uploaded thesis, in original page order, with validated formatting highlights and small `#N` badges beside primary highlights where there is room. The second section lists every student-visible problem in physical PDF page order, then document-level findings. Each entry uses the same problem number, public rule reference, explanation, and suggested fix as the web report and web text download. Findings without reliable coordinates still appear in the report and say that an exact visual highlight is unavailable.

The report lives in the audit job's runtime directory and expires with that job. It contains the student's thesis content; handle downloaded copies securely. The uploaded PDF is never overwritten. Highlight boxes are only drawn where the existing coordinate parser and page clipping checks say they are visible. A badge may be omitted if no safe position is available; the problem remains in the appended report.

## Capability audit before this feature

1. `build_highlighted_pdf()` already copied the complete PDF and could draw boxes across multiple pages. It wrote no output when no valid box was drawn.
2. `/audits/{job_id}/pdf/highlighted` with no filters matched all raw findings and returned a complete highlighted PDF if any box was drawable; otherwise it returned the original PDF.
3. The results UI exposed per-finding highlighted pages and the original PDF, but no all-findings highlighted download.
4. No app code appended student report pages to a PDF.
5. `report_view.FindingView`, plus the web job's serialized form, is the normalized source for visible finding identity, wording, public rule references, confidence, location, and highlight eligibility.
6. Problem numbers were stable across web sorting modes but assigned in raw finding order. This feature assigns them in stable physical PDF page order. The web text download now renders from those same numbered visible findings; the standalone CLI text writer retains its existing grouped format.
7. Page-less findings, missing or invalid boxes, boxes outside the source page, and intentionally summarized findings without a reliable location are report-only. The report never invents a highlight.

## Composition and cache

`student_pdf_report.build_combined_student_pdf_report()` accepts numbered student findings and per-problem boxes selected by the existing web highlight path. It first makes a temporary annotated copy through `pdf_highlight.build_highlighted_pdf()`, generates a ReportLab report section, then inserts both into a new PyMuPDF document without rasterizing the thesis. The finished file replaces the job cache atomically. A signature over the current findings, source, and report input controls regeneration. The result records visible, highlighted, unhighlighted, and document-level finding counts, as well as boxes, pages, and badges drawn; these counts are stored in `student-report-metadata.json` inside the expiring runtime job directory. Existing highlight endpoints retain their 100-box per-page request cap; the combined report draws every validated box.

The PDF has **Thesis** and **Formatting Problems** bookmarks. For zero findings, it retains all thesis pages and appends one report page stating only that the implemented checks detected no formatting problems. The automated report does not establish full compliance with NJIT requirements.

## Comments PDF

The completed audit also offers **Download Comments PDF**. It contains student-facing comments in document order, with the same problem numbers and recommended corrections as the audit results. PDF page numbers refer to the original upload. Manuscript page labels are shown where available. Document-level problems, incomplete-check notices, and guidance for manual review are included.

The export contains selectable text, generic document metadata, and numbered report pages. It contains no manuscript pages, embedded attachments, or reviewer-only technical details. Short excerpts in student-facing comments may still identify the document. The Complete PDF, focused PDF, plain-text, Markdown, and JSON downloads remain available.

Web and desktop use the existing validated atomic PDF publication path. Desktop generation runs in the existing supervised export worker. The generated report shares the audit's normal retention and deletion lifecycle.
