# P027 Heading-Level Style Evaluation

## Rule Summary

**Rule ID:** P027  
**Description:** Conservative heading-level style check using numbered-section patterns to infer level and expected capitalization/punctuation style.  
**Severity:** WARNING  
**Categories:** `capitalization_case` (case violations), `heading_title` (structural violations)

## Guideline Basis

| Source | Relevant Requirement |
|--------|----------------------|
| `Titles Examples Level 1 to 5.docx` | L1=ALL CAPS bold centered; L2=Title Case bold; L3=Sentence case bold; L4/L5=Sentence case ending with period |
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Heading hierarchy must follow NJIT style at each level |

## Q-Rule Basis

| Q-Rule | Requirement | P027 Coverage |
|--------|-------------|:-------------:|
| Q051 | Level 3 headings in sentence case | 🟡 partial — flags `level3_sentence_case_issue` when ≥2 non-first major words capitalized |

## Checks Implemented

| Check | issue_type | Trigger |
|-------|-----------|---------|
| L1 not all-caps | `level1_not_all_caps` | CHAPTER/APPENDIX heading where title part is not ≥80% uppercase |
| L2 title-case | `level2_title_case_issue` | Pattern `1.1 Heading` with first-word lowercase or word-after-separator lowercase (high confidence only) |
| L3 sentence-case | `level3_sentence_case_issue` | Pattern `1.1.1 Heading` with ≥2 non-first capitalized major words |
| L4 sentence-case | `level4_sentence_case_issue` | Pattern `1.1.1.1 Heading` with ≥2 non-first capitalized major words |
| L4 period | `level4_sentence_case_or_punctuation_issue` | Pattern `1.1.1.1 Heading` not ending with period |
| L5 sentence-case | `level5_sentence_case_issue` | Pattern `1.1.1.1.1 Heading` with ≥2 non-first capitalized major words |
| L5 period | `level5_sentence_case_or_punctuation_issue` | Pattern `1.1.1.1.1 Heading` not ending with period |

## Relation to Existing Rules

| Rule | Relationship |
|------|-------------|
| P014 | P014 checks named front-matter heading style; P027 checks body numbered headings |
| P020 | P020 uses bold metadata on any bold line; P027 uses numbered-section patterns — provides coverage when bold metadata is absent |
| P024 | P024 checks TOC/List entry capitalization; P027 checks body heading text directly |

## EF PDF Evaluation

| File | P027 count | issue_type breakdown | Notes |
|------|:----------:|---------------------|-------|
| `250218 Cibaku Elson First Review.pdf` | **1** | `level1_not_all_caps`: 1 | One chapter/appendix heading with mixed-case title part |
| `260415 Yin H _2nd_review with EF Comments.pdf` | **0** | — | No detectable numbered-heading style violations |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | **0** | — | (Same document as 260415) |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | **2** | `level1_not_all_caps`: 2 | Two chapter headings with mixed-case title parts |

## Analysis

**Low finding counts are expected.** P027 is conservative by design:
- L2-L5 numbered sections are only flagged when the text clearly meets a high threshold (≥2 non-first capitalized major words for sentence-case violations; only high-confidence issues for L2 title-case).
- The EF PDFs in late review stages likely have corrected most heading capitalization issues.

**L1 findings (3 total):** CHAPTER or APPENDIX headings with mixed-case titles. These are clear NJIT guideline violations (L1 must be ALL CAPS) and are correctly detected. Require manual verification.

**No L2-L5 findings:** The EF PDFs appear to have numbered sections in roughly correct capitalization styles, or the PDF text layer does not expose enough numbered headings to trigger the checks.

**Noise assessment:** 3 total findings across 4 PDFs is very low volume. P027 is not a high-volume rule by design.

## Known Caveats and Limitations

- **Level inference is pattern-based:** Only lines beginning with `N.N`, `N.N.N`, etc. patterns are classified. Headings without numbered prefixes are not checked (except `CHAPTER N` pattern for L1).
- **Bold/italic style not enforced:** L3 should be bold; L5 should be italic per guidelines. Bold/italic are not enforced because metadata is unreliable.
- **L2 overlap with P020:** For bold PDFs, L2 issues may already be flagged by P020. P027 provides supplementary coverage for non-bold PDFs.
- **L4/L5 period check (low confidence):** Period requirement is flagged at `"confidence": "low"` — these may fire on transitional headings or headings without periods by author choice.
- **No body text is excerpted** in any P027 finding or this document.
