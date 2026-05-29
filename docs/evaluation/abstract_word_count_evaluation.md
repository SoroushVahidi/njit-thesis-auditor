# P021 Abstract Word-Count Evaluation

- Date: 2026-05-29
- Rule: P021 — Abstract word-count validation
- Q-rule addressed: None in Q001–Q079 specifically; sourced from formatting guidelines
- Guideline source: `data/raw/guidelines/Thesis and Dissertation Formatting Guidelines (WIP).docx`

## Rule Source

Per NJIT formatting guidelines:
- PhD dissertation abstract: **maximum 350 words**
- Master's/MS abstract: **maximum 150 words**

## Implementation Scope

P021 is implemented in two modes:

### LaTeX-Source Mode (`run_latex_abstract_word_count_check`)

- Extracts abstract text from `\begin{abstract}...\end{abstract}` blocks using
  the existing `ABSTRACT_BLOCK_RE` pattern.
- Strips LaTeX commands using `strip_latex_to_text` (pylatexenc if available,
  regex fallback otherwise).
- Counts words conservatively: only tokens containing at least one letter
  (excludes bare numbers, punctuation-only tokens, and citation key fragments).
- Infers degree type from source text:
  - PhD signals: "dissertation", "doctoral", "Ph.D", "Doctor"
  - MS signals: "thesis", "master", "M.S.", "M.Eng"
  - "dissertation" takes precedence over "thesis" (NJIT PhD-specific term)
  - Unknown: warns if count > 150 (low confidence) or > 350 (high confidence)
- Integrated into `njit-audit tex` command.

### PDF Mode (`check_pdf_abstract_word_count`)

- Locates the ABSTRACT heading page using the same heading detection as P014.
- Extracts text from that page below the ABSTRACT heading line.
- Stops at the next recognized front-matter heading on the same page.
- Word count uses the same conservative tokenizer.
- Degree type inferred from early PDF pages (first 5 pages):
  - Same signals as LaTeX mode.
  - Defaults to PhD limit (350) when type is unknown.
- Only checks the first abstract page — multi-page abstracts are undercounted.
- Integrated into `njit-audit pdf` command.

## Limitations

1. **Multi-page abstracts:** The PDF mode only reads the first abstract page.
   A long abstract on two pages will be undercounted; this is conservative
   (fewer false positives) but may miss violations.

2. **Degree type inference:** The heuristic pattern matching can be confused by
   dissertation-related keywords in acknowledgements, references, or body text.
   Confidence is set to "low" when degree type cannot be determined.

3. **LaTeX stripping:** Complex LaTeX constructs (nested macros, custom commands)
   may leave residue that inflates or deflates the word count slightly.

4. **PDF word boundaries:** PyMuPDF text extraction may concatenate or split
   words at hyphenation points; the count is approximate.

5. **Unknown degree → conservative default:** When degree type cannot be
   inferred, the check uses the PhD limit (350) to avoid penalizing PhD students.
   MS students with 151–350-word abstracts in unknown-type PDFs would not be
   flagged at high confidence.

## Synthetic Test Summary

LaTeX-side tests (in `tests/test_latex_rules.py`):

| Test | Result |
|------|--------|
| PhD abstract ≤350 words | No P021 |
| PhD abstract >350 words | P021 WARNING, degree=phd, limit=350 |
| MS abstract ≤150 words | No P021 |
| MS abstract >150 words | P021 WARNING, degree=ms, limit=150 |
| LaTeX macros/citations: short abstract | No P021 (macros stripped) |
| Unknown degree, count >350 | P021 WARNING, degree=unknown, high confidence |
| Unknown degree, 151–350 words | P021 WARNING, degree=unknown, confidence=low |
| No abstract block | No P021 (empty → skip) |
| Malformed LaTeX abstract | No crash |

Unit helper tests:
- `count_abstract_words`: basic, skips pure numbers, counts mixed tokens
- `infer_degree_type`: PhD, MS, unknown

PDF-side tests (in `tests/test_pdf_rules.py`):

| Test | Result |
|------|--------|
| PDF abstract ≤350 words | No P021 |
| PDF abstract >350 words (dense lines) | P021 WARNING |
| No ABSTRACT heading present | No P021 |
| P021 finding contains expected detail fields | ✓ |
| CLI `pdf` command produces P021 output | ✓ |

## Evaluation on Available Examples

No body text is included.

| Source | Type | P021 Count | Notes |
|--------|------|:----------:|-------|
| `examples/latex/good_minimal_thesis` | LaTeX | 0 | Inferred PhD, short abstract, within limit |
| `examples/latex/njit_style_synthetic_thesis` | LaTeX | 0 | Inferred MS, short synthetic abstract, within limit |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | PDF | 0 | Abstract within PhD limit (350) |
| `250218 Cibaku Elson First Review.pdf` | PDF | 0 | Abstract within PhD limit (350) |

All evaluated files produce 0 P021 findings, which is expected — real dissertations
that have already passed at least a first review should have word-count-compliant
abstracts. P021 is most useful as a pre-submission check on draft submissions.

## Coverage Update

This rule closes the gap identified in `docs/status/rule_coverage_audit.md`
as "Abstract word-count limits: PhD ≤350, MS ≤150".

The Q-rule inventory (Q001–Q079) does not include a dedicated word-count rule;
P021 is a project-added rule that directly reflects the guideline requirements.
