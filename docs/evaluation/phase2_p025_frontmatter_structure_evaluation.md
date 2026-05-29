# P025 Front-Matter Structure Evaluation

## Rule Summary

**Rule ID:** P025  
**Description:** Heuristic checks for required structural elements in front-matter pages.  
**Severity:** WARNING  
**Categories:** `abstract_length` (missing_abstract_body), `title_page_metadata` (title page issues), `frontmatter_structure` (approval/order issues)

## Guideline Basis

| Source | Relevant Requirement |
|--------|----------------------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Front-matter required pages and content; required elements on title page |
| `Front Matter Pages Lorem Ipsum.pdf` | Visual layout of all required front-matter pages |
| `PhD Title Pages.pdf` | Department-specific title page required elements including degree, institution |

## Checks Implemented

| Check | issue_type | Trigger |
|-------|-----------|---------|
| A. Abstract body presence | `missing_abstract_body` | ABSTRACT heading found but <5 words of body text below it |
| B. Title page degree phrase | `missing_title_page_degree_phrase` | Degree phrase absent from first 4 pages when document has front-matter headings |
| C. Title page institution | `missing_title_page_institution` | "New Jersey Institute of Technology" or "NJIT" absent from first 4 pages |
| D. Approval page sparse content | `sparse_approval_page_content` | APPROVAL PAGE heading present but <3 substantial body lines below |
| E. Front-matter order | `possible_frontmatter_order_issue` | ABSTRACT heading page > TABLE OF CONTENTS page |

## Not Duplicated

| Existing Rule | Scope |
|-------------|-------|
| P014 | Named heading style (bold/centered/all-caps/near-top) |
| P021 | Abstract word count |
| P013/P019 | Page number candidate detection |

## EF PDF Evaluation

### Before text-layer guard (initial version)

| File | P025 Count | Notes |
|------|-----------|-------|
| Yin 4th review (compressed) | 0 | Degree + institution found on p3 |
| Cibaku 1st review | 2 | False positives: run-together text |
| Yin 2nd review (EF comments) | 2 | False positives: run-together text |
| Yin Haotian Second R | 2 | False positives: run-together text |

### After space-stripped fallback (refined version)

| File | P025 Count | issue_type breakdown | Notes |
|------|-----------|---------------------|-------|
| Yin 4th review (compressed) | **0** | — | Degree phrase + NJIT found on p3 via normal regex |
| Cibaku 1st review | **0** | — | "DoctorofPhilosophy" and "NewJerseyInstituteofTechnology" found via nospace fallback |
| Yin 2nd review (EF comments) | **0** | — | Same |
| Yin Haotian Second R | **0** | — | Same |

## Analysis

**Root cause of original false positives**: the 3 non-compressed PDFs use a PDF font encoding where inter-word spaces are absent from the extracted text layer. The title block is present but renders as merged tokens: "DoctorofPhilosophy" and "NewJerseyInstituteofTechnology" instead of "Doctor of Philosophy" and "New Jersey Institute of Technology". The original `\s+`-based regex could not match these.

**Fix**: the refined version also searches a space-stripped version of the combined early-page text, using simple patterns that match the merged forms ("doctorofphilosophy", "newjerseyinstituteoftechnology"). This eliminates the false positives while preserving warnings for PDFs that genuinely omit the required elements.

## Relation to Existing Rules

| Rule | Relationship |
|------|-------------|
| P014 | P025 does not re-check heading style; P025 checks content below headings |
| P021 | P021 checks word count; P025 checks whether any body text exists at all |
| P024 | P024 checks entry capitalization on TOC/LoT/LoF pages; P025 checks structural presence |

## Known Caveats and Limitations

- **Nospace fallback coverage**: the fallback patterns cover "Doctor of Philosophy", "Master of Science", "Master of Arts", "Master of Engineering", "New Jersey Institute of Technology", and "NJIT". Unusual degree names or NJIT abbreviations not matching these patterns may still be missed.
- **4-page scan window**: degree phrase and institution must appear within the first 4 pages.
- **Abstract body check**: if the abstract heading and body text are in separate text objects with block boundaries, the word count may be underestimated. Multi-page abstracts are only checked on the heading page.
- **Approval page**: very short or scanned approval pages will trigger sparse_approval_page_content regardless of actual correctness.
- All findings are heuristic warnings requiring manual review.
