# Graduate Studies PDF Audit Demo Workflow

## Purpose

This workflow provides a local, privacy-preserving early-screening process for thesis/dissertation PDF formatting.
It helps Graduate Studies quickly identify likely formatting issues before final manual review.

## Basic PDF audit command

Run the PDF audit and generate both office-friendly and machine-readable reports:

```bash
njit-audit pdf student_thesis.pdf --md-out thesis_audit_report.md --json-out thesis_audit_report.json
```

## Comment extraction workflow

When a reviewed PDF includes annotation comments, extract and separate them from layout checks:

```bash
njit-audit pdf-comments extract reviewed_thesis.pdf --json-out comments.json --md-out comments.md
njit-audit pdf-comments clean reviewed_thesis.pdf --out clean_without_comments.pdf
njit-audit pdf clean_without_comments.pdf --md-out clean_pdf_audit.md --json-out clean_pdf_audit.json
```

## What the report currently flags

The current PDF checks (P011-P019) provide conservative warnings for:

- possible margin problems
- reviewer annotations/comments
- page-number candidates
- front-matter heading issues
- indentation warnings
- spacing/blank-line warnings
- caption/title formatting warnings
- TOC/List alignment warnings
- page-number sequence/style warnings

## How to interpret findings

- Findings are warnings, not final decisions.
- High-confidence warnings should be manually checked on the referenced pages.
- Missing warnings do not prove full compliance.
- The tool is an assistant and does not replace Graduate Studies review.

## Recommended office workflow

1. Receive student PDF.
2. Run the PDF audit with Markdown and JSON outputs.
3. Review the Markdown report and focus on pages with warnings.
4. Manually confirm each relevant warning in the PDF.
5. Send the student a concise feedback summary (or attach the report if appropriate).
6. Keep the JSON report for internal tracking when useful.

## Privacy

- Processing runs locally.
- No thesis PDF upload is required for these commands.
- Generated reports should be stored securely.
- Do not commit real student reports to GitHub.

## Limitations

- Digital PDFs only.
- No OCR/scanned-PDF support yet.
- No computer-vision layout analysis.
- Rules are heuristic.
- Manual review is still required.
