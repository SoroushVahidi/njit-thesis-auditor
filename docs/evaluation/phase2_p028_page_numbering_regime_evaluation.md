# P028 Page-Numbering Regime Evaluation

## Rule Summary

**Rule ID:** P028  
**Description:** Conservative check that front-matter pages use lowercase Roman numerals and body pages use Arabic numerals.  
**Severity:** WARNING  
**Category:** `page_numbering`

## Guideline Basis

| Source | Relevant Requirement |
|--------|----------------------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Front matter uses lowercase Roman numerals; body uses Arabic numerals |
| `Front Matter Pages Lorem Ipsum.pdf` | Visual confirmation of Roman numeral regime in front matter |
| `Self-Self Assessment Sheet.pdf` | Page-numbering checklist item |

## Q-Rule Basis

| Q-Rule | Requirement | P028 Coverage |
|--------|-------------|:-------------:|
| Q022 | Bio-sketch page correct Roman numeral | 🟡 partial — checks Roman style on detected front-matter pages |
| Q031 | Dedication page correct lowercase Roman | 🟡 partial — checks Roman style on front-matter pages |
| Q035 | Acknowledgements page correct Roman numeral | 🟡 partial — same |
| Q046 | TOC continues Roman numeral sequence | 🟡 partial — checks Roman style; not sequence |
| Q060 | List of Tables continues Roman numeral sequence | 🟡 partial — checks Roman style; not sequence |

## Checks Implemented

| Check | issue_type | Trigger |
|-------|-----------|---------|
| Arabic on front-matter | `arabic_number_on_frontmatter_page` | Front-matter page with Arabic candidate |
| Uppercase Roman on front-matter | `uppercase_roman_on_frontmatter_page` | Front-matter page with roman_upper candidate |
| Roman on body | `roman_number_on_body_page` | Body page with roman (upper or lower) candidate |

## Region Detection

- **Front-matter:** pages before the first detected CHAPTER/APPENDIX heading
- **Body:** pages at and after the first detected CHAPTER/APPENDIX heading
- **Ambiguous:** pages where neither front-matter nor body can be determined → skipped
- **No-number pages excluded from P028:** pages with ABSTRACT or APPROVAL PAGE headings (P022 handles those)

## Relation to Existing Rules

| Rule | Relationship |
|------|-------------|
| P013 | P013 detects candidates globally; P028 classifies them by expected regime |
| P019 | P019 checks sequence/style consistency; P028 checks regime correctness |
| P022 | P022 checks no-number pages (ABSTRACT, APPROVAL, title); P028 skips those |

## EF PDF Evaluation

| File | P028 count | issue_type breakdown | Notes |
|------|:----------:|---------------------|-------|
| `250218 Cibaku Elson First Review.pdf` | **8** | `arabic_number_on_frontmatter_page`: 8 | 8 front-matter pages with Arabic numbering instead of Roman |
| `260415 Yin H _2nd_review with EF Comments.pdf` | **0** | — | No detectable regime violations |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | **0** | — | Same document as 260415 |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | **8** | `arabic_number_on_frontmatter_page`: 4, `roman_number_on_body_page`: 4 | Mixed regime: some front-matter pages use Arabic, some body pages use Roman |

## Analysis

**Cibaku Elson (8 findings — all Arabic on front-matter):** This dissertation's front-matter pages appear to use Arabic numerals (1, 2, 3...) where lowercase Roman (i, ii, iii...) is required. These are real NJIT formatting violations — using Arabic throughout without switching from Roman to Arabic at the body chapter.

**Yin H 2nd (0 findings):** No regime violations detected. The PDF likely uses lowercase Roman in the front matter and Arabic in the body, or page-number detection did not yield enough candidates to classify.

**Yin H 4th compressed (8 findings — mixed):** 4 front-matter Arabic findings suggest some front-matter pages use Arabic numbers. 4 body Roman findings suggest some body pages still show Roman numerals. This is consistent with a dissertation where the Roman-to-Arabic transition is not cleanly handled — a common formatting issue that EF would flag.

**Noise assessment:** 8 findings per file, all on distinct (page, issue_type) pairs. No per-rule volume concern. Findings are plausible and targeted.

## Known Caveats and Limitations

- **Body detection is CHAPTER-pattern-based:** If no "CHAPTER N" heading is detected in the body (e.g., a dissertation structured differently), body_start remains None and only named front-matter pages are classified.
- **Page 1 not excluded from P028 by default:** If page 1 (title page) happens to have a page-number candidate, P028 may flag it as `arabic_number_on_frontmatter_page`. P022 would also flag it. This is acceptable — both are relevant warnings with different explanations.
- **Sequence not validated:** P028 only checks style (Arabic vs. Roman), not whether the sequence is correct (i, ii, iii order). P019 partially covers sequence.
- **Uppercase Roman detection:** If a document uses "IV" instead of "iv", P028 flags it as `uppercase_roman_on_frontmatter_page`. This is correct per NJIT guidelines (must be lowercase).
- All findings are heuristic warnings requiring manual review.
