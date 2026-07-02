# Current Capabilities for Graduate Studies

> **Student-facing summary.** For maintainer status (latest `main`, tests, open PRs) see
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md).

This tool is a local/offline screening assistant for thesis/dissertation PDF formatting review.
It is designed to help Graduate Studies staff quickly find likely formatting issues before detailed manual review.

## What You Can Use It For Now

- Quickly screen a submitted PDF for common formatting risks.
- Generate a clear Markdown or JSON report for office workflow and follow-up.
- Detect whether reviewer annotations/comments are still embedded.
- Create a clean PDF copy with annotations removed for re-checking.

## How to Run the PDF Audit

```bash
njit-audit pdf thesis.pdf --json-out report.json --md-out report.md
```

This prints findings to the terminal and can also save:

- `report.json` for structured processing
- `report.md` for easy reading and sharing

## Comment Extraction and Clean-Copy Workflow

Extract comment metadata:

```bash
njit-audit pdf-comments extract input.pdf --json-out comments.json --md-out comments.md
```

Create a clean copy without embedded annotations:

```bash
njit-audit pdf-comments clean input.pdf --out clean.pdf
```

## Types of Issues Currently Flagged

- Possible margin-boundary violations.
- Embedded annotations/comments.
- Page-number candidates and obvious sequence/style irregularities.
- Front-matter heading layout/style issues.
- Likely indentation and spacing inconsistencies.
- Caption/title punctuation or style anomalies.
- TOC/List of Tables/List of Figures alignment inconsistencies.

## What It Does Not Yet Do

- It does not support scanned PDFs (no OCR path yet).
- It does not do visual computer-vision layout reasoning.
- It does not replace final manual compliance judgment.
- It may miss subtle style/policy issues.

## Recommended Workflow

1. Receive student PDF.
2. Run `njit-audit pdf ... --md-out report.md`.
3. Review warnings manually.
4. If a reviewed PDF is returned with comments, run `pdf-comments extract` and optionally `pdf-comments clean`.
5. Use this tool as early screening support, not as the final decision authority.

## Important Note

All findings are heuristic signals and require human review.
