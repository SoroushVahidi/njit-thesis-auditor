# Rule Coverage Audit Against Guideline Sources

- Date: 2026-05-29
- Auditor version: P001–P025 implemented (P022 added; Q004–Q005 implemented)
- Main branch: f30417e (P025); P022 on implement-p022-frontmatter-no-page-number branch

## Purpose

Determine which NJIT thesis/dissertation formatting rules are implemented,
partially implemented, or not yet implemented, mapped against:
- `data/processed/rules/njit_rule_inventory.json` (Q001–Q079)
- `data/processed/rules/project_added_rules.json` (P001–P020)
- `data/raw/guidelines/Thesis and Dissertation Formatting Guidelines (WIP).docx`
- `data/raw/guidelines/Titles Examples Level 1 to 5.docx`
- `data/raw/guidelines/Self-Self Assessment Sheet.pdf`
- `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf`
- `data/raw/guidelines/PhD Title Pages.pdf`
- `data/raw/guidelines/Dissertation Review Process.pdf`

---

## 1. Q-Rule Inventory Coverage (Q001–Q079)

Status key:
- **✅ implemented** — rule fires from source or PDF input
- **🟡 partial** — a related P-rule partially addresses it
- **❌ not implemented** — not automated at all
- **👤 manual-only** — requires human judgment; automation not practical

### Abstract (Q001–Q005)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q001 | Abstract page free of visible page number | 🟡 partial | P022 detects page-number candidates on ABSTRACT heading page; P013/P019 global detection | P022 targets named page; still heuristic |
| Q002 | First body paragraph flush-left (no indent) | 🟡 partial | P015 detects opening indent on abstract page | P015 covers abstract page first-paragraph case |
| Q003 | Subsequent paragraphs indented | 🟡 partial | P015 detects missing later indent | P015 is conservative; may miss subtle cases |
| Q004 | Abstract avoids "paper"/"article" language | ✅ implemented | `latex_abstract.py` (tex source) | TeX source only; not checked in PDF text layer |
| Q005 | Abstract free of first-person pronouns | ✅ implemented | `latex_abstract.py` (tex source) | TeX source only; not checked in PDF text layer |

### Title Page (Q006–Q008)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q006 | Graduation month is Aug/Dec/May | 🟡 partial | `latex_metadata.py` + `title_page.py` (PDF) | Detects month text; heuristic/partial |
| Q007 | Institutional identity block matches department template | 👤 manual-only | Not automated | Requires per-department template comparison |
| Q008 | Title page free of visible page number | 🟡 partial | P022 checks page 1 when doc has named front-matter headings; years suppressed | Title-page detection is heuristic (page 1 assumption) |

### Copyright Page (Q009–Q012)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q009 | Copyright page free of header text | ❌ not implemented | — | Requires named page identification |
| Q010 | Copyright year matches title page year | ❌ not implemented | — | Requires multi-field cross-check |
| Q011 | Copyright author name matches title page | ❌ not implemented | — | Requires cross-page text extraction and comparison |
| Q012 | Copyright page free of visible page number | 🟡 partial | P022 checks if copyright signal found in early pages; conservative | Copyright detection requires text-layer copyright signal |

### Approval Page (Q013–Q020)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q013 | "APPROVAL PAGE" heading present, all caps, bold, centered | 🟡 partial | P014 checks heading style; P025 checks content below heading | P025 warns if approval page body is sparse |
| Q014 | Approval page free of visible page number | 🟡 partial | P022 detects candidates on APPROVAL PAGE heading page | Heading must be detected by P014 logic |
| Q015 | Every committee entry preceded by honorific (Dr./Mr./Ms.) | 👤 manual-only | — | Requires NLP name/title parsing |
| Q016 | Dissertation Advisor listed first | 👤 manual-only | — | Requires semantic role understanding |
| Q017 | Committee members listed in descending rank order | 👤 manual-only | — | Requires rank NLP |
| Q018 | Same-rank members listed alphabetically by surname | 👤 manual-only | — | Requires name + rank parsing |
| Q019 | External members listed after NJIT members | 👤 manual-only | — | Requires affiliation parsing |
| Q020 | External entries include institution/company/city/state | 👤 manual-only | — | Requires structured field detection |

### Biographical Sketch (Q021–Q030)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q021 | "BIOGRAPHICAL SKETCH" heading present, correct format | 🟡 partial | P014 checks named front-matter heading | P014 covers style; not content presence |
| Q022 | First bio-sketch page has correct Roman numeral | 🟡 partial | P013/P019 detect page-number candidates | Exact Roman numeral not validated |
| Q023 | No place/date of birth in bio text | ❌ not implemented | — | Heuristic NLP possible but fragile |
| Q024 | No work experience in bio | ❌ not implemented | — | Requires semantic parsing |
| Q025 | Degrees listed most-recent to oldest | ❌ not implemented | — | Requires date/degree ordering logic |
| Q026 | Education bullet items single-spaced within | ❌ not implemented | — | Requires intra-paragraph spacing geometry |
| Q027 | Publications ordered most-recent to oldest | ❌ not implemented | — | Requires year extraction and ordering |
| Q028 | Pub/Pres entries single-spaced, blank line between | ❌ not implemented | — | Spacing geometry |
| Q029 | Pub/Pres entries use hanging indent | ❌ not implemented | — | Indentation geometry (different from P015) |
| Q030 | Pub/Pres entries follow one consistent citation style | ❌ not implemented | — | Style analysis; manual |

### Dedication Page (Q031–Q034)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q031 | Dedication has next sequential lowercase Roman numeral | ❌ not implemented | — | Requires page-number cross-section tracking |
| Q032 | No header text in top margin | 🟡 partial | P011 margin detection may catch extreme cases | P011 is not header-specific |
| Q033 | Dedication text block visually centered | ❌ not implemented | — | Requires geometric centering analysis |
| Q034 | Dedication text italicized (if Latin alphabet) | ❌ not implemented | — | Requires italic style detection per block |

### Acknowledgements (Q035–Q045)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q035 | Acknowledgements page has correct Roman numeral | 🟡 partial | P013/P019 candidate detection | Exact value not confirmed |
| Q036 | "ACKNOWLEDGEMENTS" heading present, correct format | 🟡 partial | P014 checks heading style | P014 covers ACKNOWLEDGEMENTS heading |
| Q037 | First paragraph thanks advisor | 👤 manual-only | — | Semantic intent detection |
| Q038 | Second paragraph thanks committee | 👤 manual-only | — | Semantic intent detection |
| Q039 | Third paragraph mentions technical + financial support | 👤 manual-only | — | Semantic intent detection |
| Q040 | Grant support includes full agency name + grant number | 👤 manual-only | — | Regex plausible but fragile |
| Q041 | Fifth paragraph thanks peers/colleagues | 👤 manual-only | — | Semantic intent detection |
| Q042 | Sixth paragraph (if present) thanks family | 👤 manual-only | — | Semantic intent detection |
| Q043 | Full first + last names for all individuals mentioned | ❌ not implemented | — | NLP named-entity recognition |
| Q044 | First acknowledgements paragraph flush-left | 🟡 partial | P015 may detect opening-paragraph indent | P015 is conservative for front-matter pages |
| Q045 | Subsequent paragraphs indented | 🟡 partial | P015 detects missing later indent | Same coverage as Q003 |

### Table of Contents (Q046–Q059)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q046 | TOC continues Roman numeral sequence | 🟡 partial | P013/P019 detect page-number candidates | Exact sequence on TOC pages not confirmed |
| Q047 | First TOC page heading correct ("TABLE OF CONTENTS") | 🟡 partial | P014 checks heading style | P014 confirms bold/all-caps/centered |
| Q048 | Subsequent TOC pages show "(Continued)" heading | ❌ not implemented | — | Multi-page TOC not yet handled |
| Q049 | TOC level-1 chapter titles in ALL CAPS | 🟡 partial | P024 checks Level 1 entries for obvious non-ALL-CAPS | Conservative: only flags entries with ≥2 lowercase major words |
| Q050 | TOC level-2 titles in title case | 🟡 partial | P024 uses check_apa_title_case_phrase on Level 2 entries | Requires numbered-level pattern (1.x) or indentation classification |
| Q051 | TOC level-3 titles in sentence case | ❌ not implemented | — | P024 skips Level 3+ entries |
| Q052 | Leader dots/hyphens connect entry to page number | 🟡 partial | P018 detects inconsistent leader usage | P018 flags absent/inconsistent leaders |
| Q053 | Wrapped level-1 entries single-spaced | ❌ not implemented | — | Intra-entry spacing geometry |
| Q054 | Wrapped level-2 entries single-spaced | ❌ not implemented | — | Same |
| Q055 | Wrapped level-3 entries single-spaced | ❌ not implemented | — | Same |
| Q056 | Level-2/3 entries indented to show hierarchy | 🟡 partial | P018 detects obvious hierarchy indent outliers | Conservative; only flags strong outliers |
| Q057 | Double spacing between consecutive section entries | ❌ not implemented | — | Inter-entry spacing geometry |
| Q058 | Single appendix labeled "APPENDIX" + title | ❌ not implemented | — | Requires appendix section detection |
| Q059 | Multiple appendices labeled by letters | ❌ not implemented | — | Same |

### List of Tables (Q060–Q069)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q060 | List of Tables continues Roman numeral sequence | 🟡 partial | P013/P019 | Approximate; not LoT-specific |
| Q061 | First LoT page heading correct ("LIST OF TABLES") | 🟡 partial | P014 checks heading style | P014 confirms format |
| Q062 | Subsequent LoT pages show "(Continued)" | ❌ not implemented | — |  |
| Q063 | "Table" label bold, left-aligned under heading | ❌ not implemented | — | Column-header detection not yet implemented |
| Q064 | "Page" label bold, right-aligned under heading | ❌ not implemented | — | Same |
| Q065 | Table titles in title case, no final period | 🟡 partial | P017 checks title-case signals + P020 checks title case | P017 flags low-confidence title-case issues; P020 checks title bodies; P017 also flags terminal periods |
| Q066 | Wrapped table titles single-spaced | ❌ not implemented | — | Intra-entry spacing |
| Q067 | Double spacing between consecutive table entries | ❌ not implemented | — | Inter-entry spacing |
| Q068 | Table numbers aligned in left column | 🟡 partial | P018 detects indentation outliers | Not specifically a left-column check |
| Q069 | Table page numbers aligned in right column | 🟡 partial | P018 detects page-number column misalignment | P018 flags misaligned page-number columns |

### List of Figures (Q070–Q079)

| ID | Rule Summary | Status | Covered By | Notes |
|----|-------------|:------:|-----------|-------|
| Q070 | First LoF page heading correct ("LIST OF FIGURES") | 🟡 partial | P014 checks heading style | P014 confirms format |
| Q071 | Subsequent LoF pages show "(Continued)" | ❌ not implemented | — |  |
| Q072 | "Figure" label bold, left-aligned under heading | ❌ not implemented | — |  |
| Q073 | "Page" label bold, right-aligned under heading | ❌ not implemented | — |  |
| Q074 | Figure descriptions in sentence case | ❌ not implemented | — | P020 intentionally excludes figure captions (sentence case by guideline) |
| Q075 | Figure descriptions end with terminal punctuation | 🟡 partial | P017 checks figure caption terminal punctuation | P017 flags missing period on figure captions |
| Q076 | Wrapped figure descriptions single-spaced | ❌ not implemented | — |  |
| Q077 | Double spacing between consecutive figure entries | ❌ not implemented | — |  |
| Q078 | Figure numbers aligned in left column | ❌ not implemented | — |  |
| Q079 | Figure page numbers aligned in right column | 🟡 partial | P018 detects page-number column misalignment on list pages | P018 checks LoF page-number alignment |

### Q-Rule Summary Counts

| Status | Count | IDs |
|--------|------:|-----|
| ✅ implemented | 2 | Q004, Q005 |
| 🟡 partial (P-rule covers partially) | 30 | Q001–Q003, Q006, Q008, Q012–Q014, Q021–Q022, Q035–Q036, Q044–Q047, Q049–Q050, Q052, Q056, Q060–Q061, Q065, Q068–Q070, Q075, Q079 |
| ❌ not implemented (automatable) | 25 | Q009–Q011, Q023–Q030, Q031, Q033–Q034, Q043, Q048, Q051, Q053–Q055, Q057–Q059, Q062–Q064, Q066–Q067, Q071–Q074, Q076–Q078 |
| 👤 manual-only | 22 | Q007, Q015–Q020, Q037–Q042, Q032\*, Q033, Q034, Q039–Q042, Q015–Q020 |

\* Q032 (no header in margin) is partially structural but mostly visual/manual.

---

## 2. Project-Added P-Rule Coverage (P001–P025)

| ID | Scope | What It Checks | Status | Guideline Basis | Known Caveats |
|----|-------|---------------|:------:|----------------|---------------|
| P001 | TeX source | Risky manual formatting commands (\\vspace, \\setlength, etc.) | ✅ | Guideline: avoid manual layout overrides | Allowlist-based; may miss custom commands |
| P002 | TeX source | Duplicate \\label identifiers | ✅ | LaTeX best practice | Only checks simple label forms |
| P003 | TeX source | Whitespace in label names | ✅ | LaTeX best practice | |
| P004 | TeX source | Unresolved \\ref/\\eqref targets | ✅ | LaTeX best practice | Heuristic; may miss complex forms |
| P005 | TeX source | Missing \\caption in figure/table environments | ✅ | Guidelines: all figures/tables need captions | Simple environment parsing only |
| P006 | TeX source | Missing \\label in figure/table environments | ✅ | Cross-reference consistency | |
| P007 | TeX source | Caption terminal punctuation | ✅ | Guidelines: captions end with punctuation | Heuristic; sentence detection is approximate |
| P008 | TeX source | Required document structure commands present | ✅ | Formatting Guidelines: TOC, abstract, LOT/LOF required | Presence-only; does not validate layout |
| P009 | TeX source | ChkTeX warnings (optional) | ✅ | TeX linting best practice | Skipped gracefully if chktex not installed |
| P010 | TeX source | lacheck warnings (optional) | ✅ | TeX linting best practice | Skipped gracefully if lacheck not installed |
| P011 | PDF layout | Text crossing margin boundaries (1.5"/1") | ✅ | Guidelines: margins 1.5" left, 1" right/top/bottom | Heuristic; compression may give false positives |
| P012 | PDF layout | Embedded PDF annotation objects | ✅ | Review workflow: no annotations in final submission | Flattened annotations are undetectable |
| P013 | PDF layout | Page-number candidate detection (top/bottom zones) | ✅ | Guidelines: page numbers at bottom 0.5" from edge | Candidate detector; high volume by design |
| P014 | PDF layout | Named front-matter heading layout/style (7 headings) | ✅ | Guidelines: headings bold, all-caps, centered, near-top | Only checks the 7 named headings; not all front matter |
| P015 | PDF layout | Paragraph indentation (first-paragraph flush-left; subsequent indented) | ✅ | Guidelines: first para flush-left, rest indented | Conservative; may miss subtle cases |
| P016 | PDF layout | Spacing/blank-line gaps | ✅ | Guidelines: double-spaced text, controlled blank lines | Front-matter focused; body pages underrepresented |
| P017 | PDF layout | Caption/title punctuation and case signals | ✅ | Guidelines: figure captions need punctuation; table titles no period | Low-confidence case hints only; intentionally conservative |
| P018 | PDF layout | TOC/list entry alignment (leader dots, page-number column, indentation) | ✅ | Guidelines: leaders, aligned columns, indented hierarchy | Activates on named TOC/list pages only |
| P019 | PDF layout | Page-number sequence/style consistency | ✅ | Guidelines: sequential Arabic then Roman, consistent position | Candidate-based; does not enforce full NJIT policy |
| P020 | PDF layout | Title-case capitalization for Level 2 headings and table titles | ✅ | `Titles Examples Level 1–5.docx`; Formatting Guidelines | Bold metadata may be absent; misses Level 2 in non-bold PDFs |
| P021 | TeX+PDF | Abstract word count (PhD ≤350, MS ≤150) | ✅ | Formatting Guidelines | Single-page extraction only; PDF mode uses conservative PhD threshold |
| P022 | PDF layout | No visible page number on no-number front-matter pages (Abstract, Title, Approval, Copyright) | ✅ | Formatting Guidelines; Front Matter Pages Lorem Ipsum.pdf | Heuristic; title page = page 1 assumption; year suppression on title page; copyright detection requires text-layer signal; EF eval: 0 findings on all 4 EF PDFs |
| P023 | PDF layout | Body-text double-spacing (line spacing ≥ 1.55× font size) | ✅ | Formatting Guidelines; Self-Assessment Sheet | Conservative: requires ≥8 suspicious gaps, ≥60% fraction, median < 1.55×; EF eval: 0 findings on clean Yin 4th review |
| P024 | PDF layout | TOC/LoT/LoF entry capitalization and terminal punctuation | ✅ | `Titles Examples Level 1–5.docx`; Formatting Guidelines | Conservative; requires ≥3 entries on page; only classifiable TOC levels; EF eval: 12 findings on Yin 4th review (3 other files have no detectable TOC pages) |
| P025 | PDF layout | Front-matter structure: abstract body, title page elements, approval page content, front-matter order | ✅ | Formatting Guidelines; Front Matter Pages Lorem Ipsum.pdf; PhD Title Pages.pdf | Conservative; title page checks require extractable text layer; EF eval: 0 on Yin 4th review (text-rich); 2 on others (title page image-based, likely false positives) |
| P026 | PDF layout | Body font compliance: size ≈12pt and Times New Roman or accepted equivalent | ✅ | Thesis and Dissertation Formatting Guidelines; Self-Self Assessment Sheet.pdf | Heuristic; one finding per (page, issue_type); EF eval: 92–117 family warnings per document (all 4 PDFs use CMR or Georgia, not TNR); 0–1 size warnings |

---

## 3. Guideline-Source Coverage Map

| Source File | Key Rules Found | Already Covered By | Missing Coverage | Recommended Next |
|-------------|----------------|-------------------|------------------|-----------------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Margins; font (Times New Roman 12pt); page numbering; heading levels 1–5; table/figure formatting; abstract word-limit; graduation month; front-matter ordering | P011 (margins), P013–P020 (headings/captions/pages), Q004–Q006 (abstract/month) | Font validation (size + family throughout); body double-spacing; abstract word-count for PhD/MS | P021: font compliance check; P022: body spacing check |
| `Titles Examples Level 1 to 5.docx` | L1=ALL CAPS bold centered; L2=Title Case bold centered; L3=Sentence case bold; L4/5=Sentence case with period; L4/5 not in TOC | P020 covers L2 title case (bold lines); P014 catches all-caps headings indirectly | L3/L4/L5 style not verified; TOC entry capitalization by level not checked; L2 numbering (X.x) not used to distinguish from L3 | P021: heading-level detection via numbering; Q049–Q051 coverage improvement |
| `Self-Self Assessment Sheet.pdf` | All items from Guidelines in checklist form; adds: double-spacing rule; bullet spacing; table/figure centering; equation formatting; references consistency | Most structural checks partially covered; spacing/indent by P015/P016 | Body double-spacing; table/figure centering; equation numbering; references consistency check | P022: double-spacing; P023: figure/table centering |
| `Front Matter Pages Lorem Ipsum.pdf` | Visual layout of all front-matter pages with exact positioning of each element | P014 (heading style); P015/P016 (indent/spacing) | Roman numeral placement; precise title block positioning; abstract word-count limit | P021: abstract word count via PDF text extraction |
| `PhD Title Pages.pdf` | Department-specific title page formats (differs by department/program) | Q006 partially (month/year); not the department-specific block | Department-specific institutional block validation | Q007 improvement: department template matching |
| `Dissertation Review Process.pdf` | 3-stage review process overview; materials required at each stage | Not an automated formatting rule; informational | N/A | N/A |
| `PhD Dissertation Process Roadmap.xlsx` | Administrative timeline | Not a formatting rule | N/A | N/A |

---

## 4. Priority Backlog

### High Priority for Graduate Studies

These rules fire in EF's actual review comments and are visible in the expanded
evaluation dataset. They are automatable with moderate effort.

| Priority | Rule Area | Guideline Source | Implementation Approach | Estimated Complexity |
|----------|-----------|-----------------|------------------------|----------------------|
| ✅ DONE | Abstract word-count (PhD ≤350, MS ≤150) | Formatting Guidelines | P021 implemented — LaTeX + PDF modes | See `docs/evaluation/abstract_word_count_evaluation.md` |
| 🔴 HIGH | P020 font-size fallback for heading detection | Titles Examples | Add font-size ≥ body heuristic when bold metadata absent | Medium — requires font-size distribution analysis |
| 🔴 HIGH | Acknowledgements paragraph order and key words | Self-Assessment Sheet | Keyword/pattern matching per paragraph | Medium — fragile on varied writing |
| ✅ DONE | Body text double-spacing (line height ≥ ~2× font size) | Formatting Guidelines | P023 implemented — conservative median+fraction threshold; 0 findings on clean Yin 4th review | See `docs/evaluation/phase2_p023_body_double_spacing_evaluation.md` |
| ✅ DONE | TOC entry capitalization by level (L1=ALL CAPS, L2=title case) | Q049–Q050 | P024 implemented — level classified by numbering pattern + indentation; conservative all-caps and title-case checks | See `docs/evaluation/phase2_p024_toc_list_formatting_evaluation.md` |
| ✅ DONE | LoT/LoF entry title-case and terminal punctuation | Q065 area | P024 implemented — LoT checks title case + no terminal period; LoF checks sentence case | See `docs/evaluation/phase2_p024_toc_list_formatting_evaluation.md` |

### Useful but Heuristic

These are automatable but will produce noise and require calibration.

| Priority | Rule Area | Approach | Notes |
|----------|-----------|----------|-------|
| 🟡 MED | Font compliance (Times New Roman 12pt throughout) | Check span font names from PDF text layer | Embedded fonts make this fragile |
| 🟡 MED | First paragraph of each section flush-left | Extend P015 to body chapters (currently front-matter focused) | Higher false-positive risk in body |
| 🟡 MED | Figure/table centering (center-alignment in PDF) | Check block bbox center vs page center | Reasonable with ±tolerance |
| 🟡 MED | Table titles above table (not below) | Check relative position of caption block vs table image block | Requires image-block detection |
| 🟡 MED | Approval page honorific detection (Dr./Mr./Ms.) | Regex on approval page text | High false-positive risk |
| 🟡 MED | Page-number absence on specific pages (abstract, title, copyright, approval) | Detect page-number candidates on specific named pages and warn if present | Requires mapping page name → PDF page |

### Manual-Only / Difficult to Automate

These require human judgment or structured data not available in the PDF/TeX text layer.

| Rule Area | Why Manual | IDs |
|-----------|-----------|-----|
| Committee member ordering by rank/affiliation | Requires institutional knowledge | Q015–Q020 |
| Acknowledgements semantic intent | Requires natural language understanding | Q037–Q042 |
| Dedication text centering/italics | Visual inspection required | Q033–Q034 |
| Publication order by date | Requires date parsing across varied citation formats | Q027 |
| Department-specific title page validation | Template library needed per department | Q007 |
| References style consistency | Style detection is unsolved without a rules engine | — |
| Copyright year/author cross-check | Page-text extraction + entity matching across pages | Q010–Q011 |

### Needs More Data/Examples

These cannot be safely implemented without more annotated examples.

| Rule Area | Why Needs Data |
|-----------|---------------|
| Biographical sketch content checks (Q023–Q025) | Need examples of correct vs. incorrect bios |
| Level-3/4/5 heading sentence-case check | Need confirmed heading-level detection first |
| Multi-page TOC/List "(Continued)" header | Need example PDFs with multi-page TOC |
| Equation numbering (X.x format) | Need PDF examples with equation content |

---

## 5. Special Analysis: P020 and Heading-Level Coverage

Per `Titles Examples Level 1 to 5.docx` and `Self-Self Assessment Sheet.pdf`:

| Level | Expected Style | P020 Coverage | Gap |
|-------|---------------|:-------------:|-----|
| Chapter (L1) | ALL CAPS bold centered | P014 checks heading layout; all-caps is confirmed | P014 doesn't verify this in body chapters, only named front-matter |
| L2 (X.x) | Title Case bold centered | **Yes** — P020 checks bold lines for title case | Bold metadata absent → misses 3 of 4 Ester PDFs |
| L3 (X.x.x) | Sentence case bold | Not checked — by design (sentence case) | P020 correctly excludes these |
| L4 (X.x.x.x) | Sentence case, ends with period | Not checked | Period enforcement not yet implemented |
| L5 (X.x.x.x.x) | Sentence case, italicized, ends with period | Not checked | Italic detection + period enforcement not implemented |

**Key gap:** P020 uses bold font metadata to identify headings, but 3 of 4 tested PDFs do not expose this metadata reliably. A font-size threshold (e.g., span size ≥ 13pt) as a secondary trigger would significantly improve recall.

**TOC entry capitalization (Q049–Q050)** is now partially covered by P024: Level 1 entries are checked for obvious non-ALL-CAPS, Level 2 entries (numbered 1.x) are checked using the title-case helper. Q051 (Level 3 sentence case) is not enforced.

---

## 6. Title-Page / Front-Matter Rule Gaps Summary

| Check | Status | Missing Work |
|-------|:------:|-------------|
| Heading present and styled correctly (7 named headings) | 🟡 partial | P014 covers 7 headings; body chapter headings not covered |
| Front-matter page is free of page numbers (abstract, title, copyright, approval) | 🟡 partial | P013 detects candidates globally; page-absent-on-named-page not confirmed |
| Roman numeral sequence through front matter | 🟡 partial | P013/P019 detect candidates; sequence through named sections not validated |
| Title spelling consistent across abstract/title/approval pages | ❌ | Cross-page text matching not implemented |
| Graduation month is Aug/Dec/May | 🟡 partial | Q006 / `title_page.py` heuristic; may miss PDF-only submissions |

---

## 7. Source vs. PDF Rule Requirements

| Rule Category | Requires TeX Source | Requires Compiled PDF | Notes |
|--------------|:-------------------:|:---------------------:|-------|
| P001–P010 (TeX hygiene, labels, structure, linting) | ✅ | — | PDF-only submissions cannot run these |
| Q004, Q005 (abstract language) | ✅ | — | Currently TeX-only; could be ported to PDF text extraction |
| P011–P020 (PDF layout checks) | — | ✅ | Runs on compiled PDF regardless of source |
| Q006 (graduation month) | ✅ + PDF partial | ✅ partial | Two implementations: TeX metadata + PDF title page |
| Q007 (department template) | — | 👤 manual | Would need template library |
| Most Q-rules (layout/visual) | — | ✅ (if implemented) | PDF is the authoritative artifact for visual checks |

---

## 8. Implementation Coverage Summary

| Category | Total | Implemented | Partial | Not Implemented | Manual-Only |
|----------|------:|:-----------:|:-------:|:--------------:|:-----------:|
| Q-rules (Q001–Q079) | 79 | 2 | 38 | 17 | 22 |
| P-rules (P001–P028) | 28 | 28 | — | — | — |
| **Total** | **107** | **30** | **38** | **17** | **22** |

The 22 manual-only rules (all in Approval Page and Acknowledgements sections) are
unlikely to be automated without LLM-based semantic analysis.

The 27 not-implemented automatable rules concentrate in:
- Front-matter page visual checks (copyright, dedication, biographical sketch)
- TOC/list internal formatting (wrapping, spacing, column headers)
- Body formatting (double-spacing, figure centering)

---

See also:
- `docs/evaluation/expanded_ef_feedback_dataset_evaluation.md` — observed rule firing on real PDFs
- `docs/implementation/phase2_pdf_layout_foundation.md` — P011–P020 implementation details
- `docs/status/phase2_pdf_milestone_summary.md` — milestone summary
