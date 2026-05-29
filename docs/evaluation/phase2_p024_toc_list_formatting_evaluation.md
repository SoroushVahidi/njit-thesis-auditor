# P024 TOC/List Entry Formatting Evaluation

## Rule Summary

**Rule ID:** P024  
**Description:** Heuristic checks for capitalization and punctuation in TABLE OF CONTENTS, LIST OF TABLES, and LIST OF FIGURES entry lines.  
**Severity:** WARNING  
**Category:** `list_of_tables_figures_toc` (or `punctuation` for `unexpected_terminal_punctuation`)

## Guideline Basis

| Source | Relevant Requirement |
|--------|----------------------|
| `Titles Examples Level 1 to 5.docx` | L1=ALL CAPS bold centered; L2=Title Case bold centered |
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | TOC entries follow chapter/section capitalization conventions |
| `Self-Self Assessment Sheet.pdf` | Checklist items reference proper TOC/LoT/LoF formatting |

## Q-Rule Mapping

| Q-Rule | Description | P024 Coverage |
|--------|-------------|---------------|
| Q049 | TOC level-1 chapter titles in ALL CAPS | `toc_level_capitalization` (entry_level=1) |
| Q050 | TOC level-2 titles in title case | `toc_level_capitalization` (entry_level=2) |
| Q065 area | Table titles do not end with a period | `unexpected_terminal_punctuation` on LoT pages |

## Behavior Summary

- **Pages checked:** Only pages detected as TABLE OF CONTENTS, LIST OF TABLES, or LIST OF FIGURES by heading text.
- **TOC:** Classifies entry level from numbering patterns (`1.1`, `1.1.1`, `CHAPTER/APPENDIX`) and indentation clusters. Level 1 warns if clearly not ALL CAPS (≥2 lowercase major words). Level 2 warns if `check_apa_title_case_phrase` finds a clear violation. Level 3+ is skipped.
- **LoT:** Strips table number prefix and leader dots. Warns on title-case violations and terminal periods.
- **LoF:** Strips figure number prefix and leader dots. Warns conservatively if >60% of later content words are capitalized (sentence-case expected).
- **Skipped:** Body pages, references pages, entries too short (<10 chars, <3 words), ambiguous-level TOC entries.

## EF PDF Evaluation

| File | P024 Count | TOC pages detected | Notes |
|------|-----------|-------------------|-------|
| Yin 4th review (compressed) | 12 | ✓ (pp. 12, 14, 17) | 8 LoT title-case, 2 terminal punct, 1 TOC L2, 1 LoF |
| Cibaku 1st review | 0 | ✗ (text layer not extractable) | TOC pages not detected |
| Yin 2nd review (EF comments) | 0 | ✗ | TOC pages not detected |
| Yin Haotian Second R (EF feedback) | 0 | ✗ | TOC pages not detected |

### Yin 4th Review Issue Breakdown

| issue_type | count | page |
|-----------|-------|------|
| list_of_tables_title_case | 8 | 14 |
| unexpected_terminal_punctuation | 2 | 14 |
| toc_level_capitalization (L2) | 1 | 12 |
| list_of_figures_sentence_case | 1 | 17 |

The 8 LoT title-case warnings suggest the table titles in this document use sentence case or mixed case rather than strict Title Case, which NJIT guidelines require. All findings require manual review.

## Relation to Existing Rules

| Rule | Overlap |
|------|---------|
| P018 | Uses same page detection (`detect_toc_like_pages`) and entry extraction; P018 checks alignment, P024 checks capitalization |
| P020 | P020 skips TOC pages entirely; P024 fills that gap. P020 may catch LoT entries via caption detection on LoT pages (partial overlap). |
| P017 | P017 checks `Table N. body` caption lines for terminal punctuation. P024 checks plain LoT entry lines. |

## Known Caveats and Limitations

- **Three EF files have no detectable TOC/List pages** — text extraction appears to not expose heading text in those compressed/rendered PDFs. P024 produces 0 findings for those files not because they are correct, but because the page-type detection fails.
- **LoT title-case false positives possible** — if an author legitimately uses sentence case for table titles (not NJIT standard), P024 will flag those entries.
- **CHAPTER entries with ≤4 words are filtered** by the upstream `_likely_entry_line` heuristic from P018 and do not reach P024's level check. Use ≥5-word chapter names to avoid this limitation.
- **Level 1 ALL CAPS check is conservative** — Title Case Level 1 entries (e.g., "Chapter 1 Introduction") are not flagged, only clearly all-lowercase entries.
- All findings are medium-confidence heuristic warnings requiring manual review.
