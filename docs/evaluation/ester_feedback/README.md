# NJIT Thesis/Dissertation Auditor Evaluation-Sheet Standards

This document establishes the authoritative formatting and content standards for all auditor evaluation sheets shared with Ester Flaim (NJIT Graduate Studies). These guidelines must be strictly followed for R011, R012, R013, and all future rule review cycles.

## Core Content Principles

The primary purpose of each evaluation sheet is **human validation of the auditor**. It must allow the reviewer to locate and judge possible violations quickly and without ambiguity.

1. **Active Findings Only:** Populated spreadsheet cells must contain only actual, current auditor warning findings.
2. **Lowest Confidence Target:** For each evaluated document, select the finding with the lowest confidence among active warnings (`LOW < MEDIUM < HIGH`). If no active warning is produced, record: *"No Rxxx/Pxxx violation produced by the current auditor."*
3. **Never Use Suppressed Candidates:** Do not include raw, internal geometric candidates that were suppressed or filtered out by the auditor.
4. **Explicit Page Number Systems:** For every row, explicitly separate and record both:
   * **Physical PDF Page:** The 1-based page index in the PDF file.
   * **Printed/Document Page:** The actual page number visibly printed on the sheet (Roman numeral, Arabic numeral, or explicitly *"none visible"* / *"not reliably identifiable"*). Never assume these numbers are equal.
5. **Precise Layout Location:** Specify where on the page the content is located (e.g., *"bottom of page, final line of body text"*, *"right edge of Reference Entry [4]"*, *"middle of page, second paragraph"*).
6. **Detailed Content Identification:** Give enough surrounding text/identifying excerpt for immediate recognition.
7. **Multiple Line Isolation:** If multiple lines are implicated in a finding, identify each line separately in a numbered list. Avoid vague wording like *"together with a nearby short line."*
8. **Suspected Violation Explanation:** Describe the issue in plain English (e.g., which margin, approximate measured overflow, affected line count, and semantic roles like equations or captions).
9. **Explicit Auditor Confidence:** Always record the actual confidence classification returned by the auditor (`MEDIUM` or `HIGH` since `LOW` is suppressed). Do not manually upgrade or downgrade confidence based on personal opinion.
10. **Exclude Tie-Breaking Mechanics:** Do not burden the reviewer with internal candidate-selection or tie-breaking details (e.g., *"Tie-broken: smallest overflow..."*).
11. **Keep Reviewer Columns Blank:** Ensure columns intended for Ester's feedback (e.g., columns C, D, and E for Review, Correct? (Y/N), and Notes) remain completely empty.
12. **Privacy Protection:** Share only minimal textual excerpts required for identification; never output full paragraphs or entire documents.
13. **Exclude Elbert Word Document:** For now, exclude `Elbert` from PDF evaluations.
14. **Pre-Commit Visual Check:** Always open and visually inspect the exported Excel file to ensure text wrapping, columns widths, row heights, and top vertical alignments are clean, legible, and highly usable.
15. **Rule-by-Rule Sequentiality:** Always complete, review, and commit the current rule's sheet before moving to the next rule.

---

## Standard Structural Layout

To maximize readability, every Ester-facing cell should follow this standard structured block format:

```text
Physical PDF page: [N]
Printed/document page: [Number / Roman Numeral / none visible / not reliably identifiable]
Location: [Precise layout position on page]
Affected content:
  1. "[Line 1 text]"
  2. "[Line 2 text]"
Possible violation: [Suspected margin/formatting issue explained in plain English]
Measured amount: [Measured overflow in points, e.g. 5.6 pt]
Auditor confidence: [MEDIUM / HIGH]
```

## Maintenance of Review Artifacts
* The spreadsheet must be saved as: `Rxxx_Ester_Auditor_Feedback.xlsx` (e.g., `R011_Ester_Auditor_Feedback.xlsx`).
* It must be saved in the tracked repository directory: `docs/evaluation/ester_feedback/`.
* No student PDFs, DOCX files, raw JSON outputs, or local credentials must ever be committed to git.
