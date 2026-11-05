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

## Standalone comments PDF

**Download Comments PDF** replaces the student-facing text download in the shared
website and desktop results template. `GET /audits/{job_id}/download/comments.pdf`
returns `application/pdf` with an attachment filename such as
`thesis_NJIT_Comments.pdf`. The Complete PDF Report endpoint, renderer, and cache
are unchanged. Markdown and JSON exports are unchanged. The older
`/download/text` endpoint remains available to existing clients.

`comments_pdf_report.render_comments_pdf_report()` formats the job's existing
UTF-8 `report.txt`, produced by `render_student_report_text()`. This preserves
student-visible wording, page order, problem numbers, public rule references,
explanations, corrections, confidence, coverage disclosure, incomplete-audit
notices, and findings without highlight coordinates. Only layout, a descriptive
subtitle, and numbered report footers are added. Long paragraphs and unbroken
words wrap across pages. Headings stay with the following paragraph.

The renderer accepts text only: it never opens, copies, embeds, attaches, or
rasterizes the uploaded dissertation. Report text can still quote short flagged
snippets, as before. Generation happens locally on request without persistent
PDF caching. It uses existing ReportLab and PyMuPDF dependencies, the already
bundled DejaVu font, and PyMuPDF's built-in CJK fallback. No new package, font
asset, license dependency, or network request is introduced. Supplementary-plane
Unicode mappings are corrected within the new PDF only, preserving emoji text
extraction without changing ReportLab globally or the Complete PDF Report.

Focused checks are in `tests/test_comments_pdf_report.py`, the comments route
checks in `tests/test_web_app.py`, and `tests/test_offline_desktop.py`. The synthetic
upload workflow in `tests/test_browser_audit_workflow.py` clicks the actual button,
checks the HTTP response and browser filename, extracts text with two PDF readers,
compares it with the legacy text report, rejects original-page sentinel content,
and verifies that downloading comments leaves the Complete PDF byte-identical.
