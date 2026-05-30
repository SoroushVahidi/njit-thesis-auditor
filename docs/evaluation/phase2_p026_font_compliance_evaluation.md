# P026 Body Font Compliance Evaluation

## Rule Summary

**Rule ID:** P026  
**Description:** Heuristic check for body font size (≈12pt) and font family (Times New Roman or accepted equivalent) on ordinary body-text pages.  
**Severity:** WARNING  
**Category:** `font_format`

## Guideline Basis

| Source | Relevant Requirement |
|--------|----------------------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Body text must use Times New Roman 12pt |
| `Self-Self Assessment Sheet.pdf` | Explicit checklist item: font size and family throughout body |

## Checks Implemented

| Check | issue_type | Trigger |
|-------|-----------|---------|
| A. Font size | `possible_body_font_size_issue` | >50% of body spans on page have size outside [11.0, 13.0] pt AND ≥5 such spans |
| B. Font family | `possible_body_font_family_issue` | >50% of named body spans on page are non-Times AND ≥5 such spans |

## Accepted Font Families (no warning)

| Font or Alias | Classification |
|--------------|---------------|
| Times-Roman, Times, TimesNewRoman, TimesNewRomanPSMT | `times` ✓ |
| ABCDEF+TimesNewRomanPSMT (subset prefix stripped) | `times` ✓ |
| NimbusRomNo9L | `times` ✓ |
| TeX Gyre Termes | `times` ✓ |
| Liberation Serif | `times` ✓ |
| FreeSerif, STIX, STIXGeneral | `times` ✓ |
| CMR12, CMBX12, CMTI12, CMSL12, etc. (Computer Modern) | `computer_modern` — flagged |
| Latin Modern (LMRoman, LMBX) | `computer_modern` — flagged |
| Georgia, Arial, Helvetica, Calibri, Cambria, etc. | `other` — flagged |
| CMMI, CMSY, CMEX, MSAM, MSBM, Symbol, ZapfDingbats | `math` — skipped |

## EF PDF Evaluation

| File | Body pages | P026 total | Size warnings | Family warnings | Observed fonts |
|------|:----------:|:----------:|:-------------:|:---------------:|----------------|
| `250218 Cibaku Elson First Review.pdf` (99 pages) | ~92 | **92** | 0 | 92 | CMR12, CMBX12, CMTI12, SFRM1200 |
| `260415 Yin H _2nd_review with EF Comments.pdf` | ~103 | **103** | 1 | 102 | CMR10, CMR12, CMBX10, CMBX12, CMTI12, CMTT12 |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | ~103 | **103** | 1 | 102 | (same document as 260415) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` (137 pages) | ~117 | **117** | 0 | 117 | Georgia, Georgia-Bold, Arial, ArialMT, Cambria, Verdana |

## Analysis

### Family Findings

All 4 EF PDFs use non-Times fonts throughout body text:
- **Cibaku Elson and Yin 2nd (260415/Haotian):** Computer Modern (CMR12) — the default LaTeX font. These are LaTeX-compiled dissertations. CMR12 is standard for LaTeX documents but is not Times New Roman. The NJIT guideline explicitly requires TNR; students using LaTeX without `\usepackage{mathptmx}` or similar will always trigger this finding.
- **Yin 4th (compressed):** Georgia, Arial, Cambria — likely compiled in Microsoft Word or LibreOffice with non-Times default fonts.

All P026 family findings represent real noncompliance with the Times New Roman guideline requirement. These are not false positives — they correctly identify the font discrepancy.

### Size Findings

1 size warning fires on the Yin 2nd review (both file variants). The warning corresponds to CMR10 at 10.9pt, marginally below the 11.0pt lower bound (abs(10.9 - 12.0) = 1.1 > 1.0pt tolerance). This is likely from `\small` or reduced-size text in the LaTeX source (e.g., table cells, footnote references, or caption sub-items). Review of the specific page is recommended to distinguish legitimate reduced-size content from a formatting error.

### Volume Interpretation

The high per-document counts (92–117) mean that every body page with sufficient text triggers a family warning. This is expected when the document-wide font is non-Times. Unlike P011/P013 (which fire per-candidate), P026 fires **once per page per issue type**, so 92 findings = 92 body pages. For a 100+ page dissertation using Computer Modern, this is the correct result.

### Recommendation for Auditor Users

P026 family findings for Computer Modern (CMR) are systematic warnings indicating a LaTeX font choice, not per-paragraph formatting errors. Reviewers should note:
1. If the dissertation uses LaTeX: add `\usepackage{mathptmx}` or `\usepackage{newtxtext}` to switch to Times-compatible fonts.
2. If the dissertation uses Word: change the body text font to Times New Roman 12pt throughout.

## Relation to Existing Rules

| Rule | Relationship |
|------|-------------|
| P020 | P020 uses bold metadata for heading detection; P026 uses font names for body compliance |
| P023 | P023 checks line spacing; P026 checks font properties on the same body-text lines |

## Known Caveats and Limitations

- **Font name availability:** Some PDFs flatten or subset font names, making classification harder. Subset prefixes (`ABCDEF+`) are stripped; other mangling may be missed.
- **Math fonts skipped:** CMMI, CMSY, Symbol, ZapfDingbats are excluded from family checks but may still appear in size data.
- **CMR10 at 10.9pt:** This marginally triggers the size check. The ±1pt tolerance was chosen conservatively; widening to ±1.5pt would suppress this.
- **Computer Modern is commonly acceptable:** Depending on department or advisor, CMR may be accepted in practice despite the guideline. P026 flags it to bring the issue to the reviewer's attention.
- **No body text is excerpted** in any P026 finding or this document.
