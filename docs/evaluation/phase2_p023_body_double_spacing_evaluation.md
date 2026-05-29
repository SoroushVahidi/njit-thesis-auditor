# P023 Evaluation: PDF Body Text Double-Spacing

- Date: 2026-05-29
- Rule: P023 — possible_body_text_not_double_spaced
- Branch: implement-pdf-body-double-spacing

---

## Guideline Basis

| Source | Relevant Statement |
|--------|-------------------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Body text must be double-spaced. |
| `Self-Self Assessment Sheet.pdf` | Explicit double-spacing checklist item. |

No corresponding Q-rule in the NJIT rule inventory covers this directly; P023 is a
project-added rule. It is categorized under `spacing_blank_lines`.

---

## Scope

P023 checks whether ordinary body-text lines on a page appear to be double-spaced.

**Pages checked:** All pages except those with named front-matter headings
(ABSTRACT, APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF
CONTENTS, LIST OF TABLES, LIST OF FIGURES) and REFERENCES/BIBLIOGRAPHY/WORKS
CITED pages.

**Lines considered per page:**
- Lines in the body zone (between top-15% and bottom-15% of the page)
- At least 30 characters long, alpha ratio ≥ 0.45, alpha count ≥ 15
- Not matching front-matter heading, page-number, caption (Figure/Table N), or
  bullet/list-item patterns

**Minimum evidence required before a warning is emitted:**
- At least 7 qualifying body-text lines on the page
- At least 5 measured line spacings
- At least 8 suspicious spacings (ratio < 1.55×)
- At least 60% of measured spacings are suspicious
- Median spacing ratio < 1.55×

---

## Thresholds

| Parameter | Value | Rationale |
|-----------|------:|-----------|
| `DOUBLE_SPACING_RATIO_THRESHOLD` | 1.55× | Midpoint between single (≈1.1–1.3×) and double (≈2.0–2.3×) at 12pt |
| `MIN_SUSPICIOUS_GAP_COUNT` | 8 | Requires strong evidence before flagging |
| `MIN_SUSPICIOUS_FRACTION` | 0.60 | Majority of measured spacings must be suspicious |
| `PARAGRAPH_BREAK_RATIO` | 4.0× | Gaps wider than 4× font size are skipped (paragraph breaks) |
| `MIN_BODY_LINES_FOR_CHECK` | 7 | Minimum lines to have a meaningful sample |
| Margin zone exclusion | top/bottom 15% | Excludes running headers, footnotes, page-number zones |

---

## Available-Data Evaluation (4 EF PDFs)

| File | P023 findings | Affected pages | Notes |
|------|:------------:|---------------|-------|
| Yin_H_4th_Review_with_EF_comments_compressed.pdf | **0** | — | Cleanest/most recent review; no under-spacing detected |
| 250218 Cibaku Elson First Review.pdf | 6 | 7, 92–94, 97–98 | First-review draft; ratio ≈ 1.21 on flagged pages |
| Yin_Haotian_Second_R_with_EF_Feedback.pdf | 4 | 6, 14, 82, 105 | Second-review draft; page 82 ratio ≈ 1.00 (likely table/code) |
| 260415 Yin H _2nd_review with EF Comments.pdf | 4 | 6, 14, 82, 105 | Same findings as above (same base document) |

### Observations

- The **4th (final) Yin review** has 0 findings, consistent with a clean, approved
  document. Earlier draft versions show some findings on pages with suspicious
  line-spacing ratios (1.00–1.21×, well below the 1.55× threshold).
- Flagged pages in earlier drafts (ratios 1.00–1.21×, fraction 60–82%) represent
  genuine under-spacing signal. Whether this corresponds to body text that was
  later fixed, or to table/code content accepted by the reviewer, cannot be
  determined without inspecting the source.
- **No dissertation body text is quoted in this report.**

---

## Relation to P016

| Rule | Role |
|------|------|
| P016 | Checks front-matter pages for *excessive* vertical gaps and blank lines |
| P023 | Checks body pages for *insufficient* line spacing relative to expected double-spacing |

The two rules are complementary: P016 fires on front-matter anomalies; P023 fires
on body pages that appear single- or 1.5-spaced.

---

## Limitations and False-Positive Controls

- **Table and code-block content** can produce body-text-like lines at single
  spacing. These may pass all body-text filters and cause P023 to fire on pages
  that are correctly formatted overall. The 60%-fraction threshold significantly
  reduces but does not eliminate this risk.
- **Named front-matter continuation pages** (e.g., the second page of the
  Biographical Sketch) are not identified by heading and are analyzed. Their
  content often has different spacing conventions.
- **Font size estimation** uses the median span size across body lines. Pages with
  multiple font sizes (e.g., inline footnote-size text) may produce a slightly
  inaccurate font size estimate, shifting the thresholds.
- **One finding per page**: detailed per-gap information is not emitted; only the
  median ratio, suspicious count, and estimated font size are recorded.
- **Confidence: medium** — this is a heuristic rule and results should be reviewed
  by the student before acting on them.
