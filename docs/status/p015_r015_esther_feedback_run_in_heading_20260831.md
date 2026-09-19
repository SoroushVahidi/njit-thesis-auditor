# R015/P015 Ester Paragraph-Boundary Follow-Up

**Updated:** 2026-09-18
**Branch:** `fix/r015-ester-paragraph-indentation-followup-20260918`
**Scope:** R015/P015 paragraph indentation only. The separate unnumbered-bold
heading/style issue Ester noted is recorded below but not implemented here.

R015 is the reviewer-facing rule identifier. P015 is the internal detector in
`src/njit_auditor/rules/pdf_indentation.py`.

## Reviewer Ground Truth

Ester's latest R015 feedback established four cases:

| Case | Judgment | Required R015 behavior |
|---|---|---|
| Youra physical page 101 | The previous report was on the wrong line, but the underlying missing-indent violation is real | Do not report the continuation line; report the actual paragraph-start line immediately above |
| Youra physical page 86 | False positive | Do not report; the line is mid-sentence continuation text |
| Muyeed physical page 144 | False positive | Do not report; math/special-character extraction made continuation text look like a new paragraph |
| Philip physical page 17 | False positive | Do not report; Greek/math extraction made continuation text look like a new paragraph |

No private dissertation text is included here.

## Root Cause

The prior R015 run-in handling correctly reassembled a bold run-in phrase and
its same-row regular body text into one paragraph, preventing the following
line from being treated as a standalone paragraph start. However, the same
change also exempted any paragraph starting with a bold run-in phrase from the
missing-later-indent check. Ester's later decision clarified that this is not
an R015 exemption: the bold run-in phrase can be the real paragraph start, and
if that paragraph is missing the expected first-line indent, R015 should report
that start line.

The older false positives on Youra page 86, Muyeed page 144, and Philip page
17 are already handled by the existing paragraph reassembly and continuation
logic:

- same-baseline/same-style fragment merging for ordinary extraction splits;
- row-remnant x0 recovery for equation, subscript, superscript, and symbol
  fragments;
- continuation-like paragraph suppression for lower-case equation continuations;
- guards for section-number-only fragments and bracketed markers.

## Implemented Policy

The fix separates two concerns that were previously coupled:

1. **Paragraph grouping:** bold run-in phrase plus same-row regular continuation
   still form one paragraph, with the bold phrase as the paragraph's true first
   line.
2. **R015 reporting:** that run-in paragraph is no longer heading-exempt for
   `missing_later_indent`; if it is a later body paragraph on a page with a
   confident indented-paragraph style, it may be reported.
3. **Page-style baseline estimation:** run-in paragraphs are still excluded from
   page-style baseline counts so they do not distort the confidence gate for
   unrelated paragraphs.

No student names, page numbers, private text strings, or dissertation-specific
exceptions are used by the detector.

## Seven-Document Corpus Result

The seven private evaluation dissertations were rerun for R015. Elbert remains
excluded.

| Document | Before | After | Delta |
|---|---:|---:|---:|
| Youra | 0 | 1 | +1 |
| Anthony | 0 | 0 | 0 |
| Muyeed | 1 | 1 | 0 |
| Philip | 6 | 6 | 0 |
| Praneeth | 0 | 0 | 0 |
| Sebastian | 0 | 0 | 0 |
| Patrick | 0 | 0 | 0 |
| **Total** | **7** | **8** | **+1** |

The only material corpus change is the intended Youra page-101 correct-line
recovery: the previously wrong continuation-line report remains absent, and the
actual paragraph-start line is reported as `missing_later_indent`.

## Separate Bold-Heading Observation

Ester also observed that the same bold phrase lacks a section number and that
bold should be reserved for numbered titles/headings. That is a separate
formatting issue, not R015 paragraph indentation.

Rule-ownership audit:

- P020 checks capitalization/style of recognized title-like headings but does
  not currently report unnumbered bold run-in phrases.
- P027 checks numbered heading level/style consistency and therefore cannot own
  an unnumbered phrase.
- P026 checks font family/size compliance, not whether bold is reserved for
  headings.

No existing rule currently covers this exact issue. It is recorded as a future
rule gap and was not added to R015.

## Validation

Synthetic/privacy-safe tests cover:

- continuation lines that should not be reported;
- genuine unindented later paragraph starts;
- wrong-second-line prevention for run-in paragraph starts;
- displayed-equation continuation behavior;
- Greek/special-character fragmentation;
- subscript/superscript fragmentation;
- numbered heading plus run-in body boundary cases.

Targeted P015/indent regression run:

- `python -m pytest tests/test_p015_r015_ester_run_in_heading_20260831.py tests -k "p015 or P015 or r015 or R015 or indent" -q`
- Result: 169 passed, 3375 deselected.

Full validation is recorded in the PR report for this branch.
