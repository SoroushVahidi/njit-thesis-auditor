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

| File | P025 Count | issue_type breakdown | Notes |
|------|-----------|---------------------|-------|
| Yin 4th review (compressed) | **0** | — | Degree phrase + NJIT found on p3 (within scan window) |
| Cibaku 1st review | **2** | missing_title_page_degree_phrase, missing_title_page_institution | Title page text layer not extractable (likely image-based); false positives |
| Yin 2nd review (EF comments) | **2** | missing_title_page_degree_phrase, missing_title_page_institution | Same limitation |
| Yin Haotian Second R (EF feedback) | **2** | missing_title_page_degree_phrase, missing_title_page_institution | Same limitation |

## Analysis

- **Yin 4th review** correctly produces 0 P025 findings: the PDF has a rich text layer where the degree and institution appear on page 3.
- **3 remaining files** all produce the same 2 title-page findings. Investigation shows that `NJIT` and the degree phrase are absent from the first 4 extractable pages in those files — the title pages are either image-rendered or use font encodings that suppress text extraction.
- The 2 title-page findings for those 3 files are likely **false positives caused by limited text extraction**, not genuine formatting errors.
- No `missing_abstract_body`, `sparse_approval_page_content`, or `possible_frontmatter_order_issue` findings on any file, suggesting those checks produce no false positives on this dataset.

## Relation to Existing Rules

| Rule | Relationship |
|------|-------------|
| P014 | P025 does not re-check heading style; P025 checks content below headings |
| P021 | P021 checks word count; P025 checks whether any body text exists at all |
| P024 | P024 checks entry capitalization on TOC/LoT/LoF pages; P025 checks structural presence |

## Known Caveats and Limitations

- **Title page checks are unreliable when the title page is image-based** — text extraction yields no title page text, producing false positives for missing degree/institution.
- **4-page scan window**: degree phrase and institution must appear within the first 4 pages. For documents with non-standard front-matter ordering (e.g., copyright page before abstract), the window may need extending.
- **Abstract body check**: if the abstract heading and body text are rendered as separate text objects across block boundaries, the check may undercount body words. Multi-page abstracts are only checked on the heading page.
- **Approval page**: a very short approval page (e.g., for a scanned or minimal PDF) will always trigger sparse_approval_page_content regardless of actual content correctness.
- All findings are heuristic warnings requiring manual review.
