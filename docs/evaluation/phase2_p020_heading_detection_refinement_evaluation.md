# P020 Heading Detection Refinement Evaluation

## Context

The P001–P028 evaluation (`current_auditor_after_p028_evaluation.md`) showed P020 firing
**0 findings** on 3 of 4 EF PDFs (Cibaku Elson, both Yin H 2nd review files) despite EF
comment evidence of real heading/capitalization issues on those PDFs (9 `capitalization_case`
comments on Cibaku Elson alone). The cause was that all three PDFs are LaTeX-compiled and use
Computer Modern fonts — specifically CMBX12 for bold headings — which were not recognized as
bold by the P020 detection logic.

## Root Cause

`pdf_layout.py::_style_flags_from_font_name` only checked for `"bold"` as a substring
of the font name. Computer Modern Bold Extended fonts are named `CMBX12`, `CMBX10`, etc.
— none contain the word "bold". Consequently:

- `span.bold = False` for all CMBX spans
- `_all_spans_bold()` returned False for CMBX heading lines
- Those headings were never presented to the title-case checker
- P020 = 0 on all CMR-based PDFs

## Changes Made

### 1. `src/njit_auditor/pdf_layout.py` — `_style_flags_from_font_name`

Updated to recognize Computer Modern Bold Extended fonts:

```python
# Before:
return ("bold" in lowered), ("italic" in lowered or "oblique" in lowered)

# After:
base = lowered.split("+")[-1]   # strip embedded subset prefix
bold = "bold" in lowered or "black" in lowered or "heavy" in lowered or base.startswith("cmbx")
italic = "italic" in lowered or "oblique" in lowered or base.startswith("cmti") or base.startswith("cmsl")
return bold, italic
```

This change benefits all rules that use `span.bold`, including P014, P020, and P027.

### 2. `src/njit_auditor/rules/pdf_title_capitalization.py` — Multiple updates

- **`_BOLD_FONT_HINT_RE`**: Added `cmbx` to the inline regex pattern as a secondary check.
- **`_is_math_font()`**: New helper to exclude CMMI/CMSY/CMEX math fonts from bold detection.
- **`_spans_bold_reason()`**: Replaced `_all_spans_bold()` with a function that also returns
  the detection reason: `"bold_heading"`, `"cmbx_bold_heading"`, or `None`.
- **Font-size fallback**: New `_is_font_size_heading()` and `_estimate_document_body_size()`
  add a conservative second path: lines where ≥70% of spans are ≥ body_size + 2pt are
  treated as heading-like even without bold metadata.
- **`detection_reason` in findings**: All P020 findings now include `detection_reason` in
  their `details` dict (`bold_heading`, `cmbx_bold_heading`, `font_size_heading_fallback`).

## Before/After P020 Counts

| File | Before | After | Δ | detection_reasons |
|------|:------:|:-----:|:--:|-------------------|
| Cibaku Elson (1st) | 0 | **2** | +2 | cmbx_bold_heading×2 |
| Yin H 2nd (260415) | 0 | **1** | +1 | cmbx_bold_heading×1 |
| Yin Haotian 2nd | 0 | **1** | +1 | cmbx_bold_heading×1 |
| Yin H 4th (compressed) | 30 | **30** | 0 | bold_heading×30 |
| Sebastian Fine (baseline) | 3 | **3** | 0 | bold_heading×3 |

**Key result:** CMBX detection adds 2–4 new P020 findings across the CMR-based PDFs.
Yin H 4th and Sebastian Fine are unchanged (they already used fonts with explicit bold
metadata). The clean baseline shows no unexpected inflation.

## Quality Assessment

- **New findings are real:** Each new P020 finding on Cibaku and Yin 2nd corresponds to a
  section heading in CMBX12 (bold) font that has a title-case violation. These are genuine
  formatting issues consistent with EF reviewer comments.
- **No false-positive increase on baseline:** Sebastian Fine stays at 3 findings.
- **Conservative:** Only 2–4 new findings per EF document — P020 remains a focused, low-volume rule.

## Font-Size Fallback

The font-size fallback (`font_size_heading_fallback`) is designed for document types
where headings are rendered at a visibly larger font size than body text (e.g., 14pt
headings in a Word document with 12pt body). In the current EF test set, all CMR-based
PDFs use CMBX12 at 12pt (same size as body text), so the fallback does not trigger for
those files. The fallback triggers correctly in synthetic test PDFs with 14pt headings
and 12pt body. It does not trigger for body paragraphs.

## Caveats

- CMBX recognition now sets `span.bold = True` globally at the layout extraction layer.
  This may affect other rules using `span.bold` (P014, P027). P014 already had its own
  CMBX-aware `BOLD_FONT_HINT_RE`; P027 uses section-number pattern detection, not bold.
- Math fonts (CMMI, CMSY, CMEX) are explicitly excluded from the bold-heading detection.
- The font-size fallback uses a 2.0pt threshold above the estimated body font size. This
  is conservative; adjust `_FONT_SIZE_HEADING_MARGIN_PT` if too many or too few
  large-text lines are captured.
- All P020 findings remain heuristic warnings requiring manual review.
