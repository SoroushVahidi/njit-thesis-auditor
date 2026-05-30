# Source-to-Implementation Coverage Audit (after P001-P029)

- Date: 2026-05-30
- Baseline main before this branch: `7139e76a9fe5`
- Scope: strict source-to-implementation verification of current rule/guideline sources and implementation surface (no new rule additions)

## 1. Executive summary

- **Are all source rules implemented?** **No.**
- **P-rule implementation:** **29/29 implemented** (`P001-P029`).
- **Q-rule coverage:** 79 total = **2 implemented**, **11 partially implemented**, **57 not implemented**, **9 manual-only**.
- **Guideline-source coverage:** core formatting signals are partially automated via P-rules; semantic/admin/process requirements remain mostly manual or process-only.
- **Biggest remaining gaps:**
  1. TOC/List deep formatting details (continued-page headings, wrapped-entry spacing, column-label formatting/alignment).
  2. Approval/Acknowledgements/Biographical semantic checks (committee rank/order, required paragraph intent/content).
  3. Cross-page semantic consistency checks (e.g., title/metadata consistency and department-specific title-page variants).

## 2. Source file coverage table

| Source file | Rule/requirement area | Implemented by | Status | Notes |
|---|---|---|---|---|
| `data/processed/rules/njit_rule_inventory.json` | Q001-Q079 authoritative inventory | `tests/test_rule_inventory.py`, mapped modules in `src/njit_auditor/rules/` | partially implemented | Inventory is complete and represented; implementation coverage is mixed (2 implemented, 11 partial, 66 not fully implemented). |
| `data/processed/rules/project_added_rules.json` | P001-P029 project rule set | `src/njit_auditor/rules/*.py`, `src/njit_auditor/cli.py`, `tests/` | implemented | All 29 P-rules are marked implemented and wired in the CLI/testing/docs. |
| `data/raw/guidelines/Thesis and Dissertation Formatting Guidelines (WIP).docx` | Core format rules (margins, headings, spacing, page numbering, front matter) | `P011-P029` family (PDF) plus `P021` (abstract length) | partially implemented | Broad heuristic coverage exists; many detailed/semantic checks are still missing or manual. |
| `data/raw/guidelines/Titles Examples Level 1 to 5.docx` | Heading capitalization/style by level | `P020`, `P024`, `P027` | partially implemented | Level-style coverage is present for targeted scopes; full visual/typographic enforcement is incomplete. |
| `data/raw/guidelines/Self-Self Assessment Sheet.pdf` | Checklist-style visual formatting expectations | `P011`, `P015`, `P016`, `P017`, `P026`, `P028` | partially implemented | Core layout signals covered heuristically; checklist semantics and some visual specifics remain unimplemented. |
| `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf` | Front-matter structure/page examples | `P014`, `P018`, `P022`, `P024`, `P025`, `P028`, `P029` | partially implemented | Major structural checks exist; all page-template and content-intent details are not automated. |
| `data/raw/guidelines/PhD Title Pages.pdf` | Department/title-page patterns | `P025` (partial), `Q006` (partial via month check) | partially implemented | Department-specific exceptions and semantic template matching remain largely manual. |
| `data/raw/guidelines/Dissertation Review Process.pdf` | Review workflow/process policy | status/evaluation docs only | process-only | Administrative process reference; not a direct auditor rule source. |
| `data/raw/guidelines/PhD Dissertation Process Roadmap .xlsx` | Milestones, approvals, process flow | status/evaluation docs only | process-only | Administrative roadmap; intentionally outside current automated audit scope. |
| `docs/sources/ester_materials.md` | Source index and usage constraints | documentation references | process-only | Catalog and policy context; does not define executable rule logic directly. |
| `docs/status/rule_coverage_audit.md` | Prior coverage baseline and gaps | documentation only | partially implemented | Useful as historical status, but now superseded by this stricter audit snapshot. |
| `docs/status/current_project_state_and_next_steps.md` | Rolling state summary | documentation only | process-only | Project status tracker, not a direct rule-definition source. |

## 3. Q001-Q079 coverage table

| Q-rule ID | Short summary | Current status | Implemented/covered by | Remaining gap | Manual-only reason if applicable |
|---|---|---|---|---|---|
| Q001 | Is the Abstract page free of any visible page number? | partially implemented | `njit_auditor.rules.pdf_frontmatter_no_page_number` | Primarily visual/layout formatting check on compiled output. | — |
| Q002 | Look at the very first word of the first body paragraph. Is its starting position hor... | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q003 | Look at the left side of Paragraph 2. Imagine the left edge of the main body text is... | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q004 | Does the Abstract text contain any standalone form of the words “paper” or “article,”... | implemented | `njit_auditor.rules.latex_abstract` | — | — |
| Q005 | Is the Abstract text completely free of first-person pronouns (I, me, my, we, etc.)? | implemented | `njit_auditor.rules.latex_abstract` | — | — |
| Q006 | Does the Title Page display a graduation month that is exactly August, December, or May? | partially implemented | `njit_auditor.rules.latex_metadata` | Graduation month detection is heuristic and context-driven. | — |
| Q007 | Does the institutional identity block on the Title Page exactly match the department/... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q008 | Is the Title Page free of any visible page number? | partially implemented | `njit_auditor.rules.pdf_frontmatter_no_page_number` | Primarily visual/layout formatting check on compiled output. | — |
| Q009 | Is there no header text in the top margin area of the Copyright page? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q010 | Does the visible copyright year exactly match the year shown on the Title Page? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q011 | Does the visible author name on the Copyright page exactly match the author’s name on... | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q012 | Is the Copyright page free of any visible page number? | partially implemented | `njit_auditor.rules.pdf_frontmatter_no_page_number` | Primarily visual/layout formatting check on compiled output. | — |
| Q013 | Does the Approval Page display the exact phrase “APPROVAL PAGE” in all caps, bold, ce... | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q014 | Is the Approval Page free of any visible page number? | partially implemented | `njit_auditor.rules.pdf_frontmatter_no_page_number` | Primarily visual/layout formatting check on compiled output. | — |
| Q015 | Does every committee-member entry begin with an honorific such as Dr., Mr., or Ms.? | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q016 | Do all entries identified as Dissertation Advisor appear before any non-advisor commi... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q017 | Are committee members listed in descending rank order? | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q018 | Among members with the same explicitly stated rank, are the surnames listed in alphab... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q019 | Do all committee-member entries whose affiliation is not NJIT appear after all entrie... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q020 | Does every external or non-NJIT committee-member entry include institution/company na... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q021 | Does the Biographical Sketch page display the exact phrase “BIOGRAPHICAL SKETCH” corr... | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q022 | Is the visible page number on the first Biographical Sketch page exactly the lowercas... | partially implemented | `njit_auditor.rules.pdf_page_numbering_regime` | Primarily visual/layout formatting check on compiled output. | — |
| Q023 | Does the Biographical Sketch text exclude both place of birth and date of birth? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q024 | Does the Biographical Sketch exclude all work experience and professional positions? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q025 | Are all postgraduate degrees listed from most recent to oldest? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q026 | Are the bullet items in the education section single-spaced within each bullet? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q027 | Are the entries in “Publications and Presentations” ordered from most recent to oldest? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q028 | Is each entry in “Publications and Presentations” single-spaced with a blank line bet... | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q029 | Do all entries in “Publications and Presentations” use a hanging indent? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q030 | Do all entries in “Publications and Presentations” follow one consistent citation pat... | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q031 | Does the Dedication page display the next sequential lowercase Roman numeral? | partially implemented | `njit_auditor.rules.pdf_page_numbering_regime` | Primarily visual/layout formatting check on compiled output. | — |
| Q032 | Is there no header text in the top margin area of the Dedication page? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q033 | Is the full dedication text block visually centered on the page? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q034 | If the dedication text uses the Latin alphabet, is the entire text italicized? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q035 | Does the Acknowledgements page display the next sequential lowercase Roman numeral? | partially implemented | `njit_auditor.rules.pdf_page_numbering_regime` | Primarily visual/layout formatting check on compiled output. | — |
| Q036 | Does the Acknowledgements page display the exact word correctly formatted? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q037 | Does the first paragraph of the Acknowledgements explicitly thank the advisor(s)? | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q038 | Does the second paragraph explicitly thank the committee members? | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q039 | Does the third paragraph explicitly mention both technical and financial support? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q040 | If grant support is mentioned, does it include full agency name and grant number? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q041 | Does the fifth paragraph explicitly thank peers, colleagues, or fellow students? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q042 | If a sixth paragraph is present, does it explicitly mention family or friends? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q043 | For every named person mentioned, is the full first and last name used? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q044 | Does the first Acknowledgements paragraph begin flush with the left margin? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q045 | Does every Acknowledgements paragraph after the first begin with a visible indent? | not implemented | `—` | Needs human metadata/template interpretation beyond strict source parsing. | — |
| Q046 | Does the TOC continue the Roman numeral sequence correctly? | partially implemented | `njit_auditor.rules.pdf_page_numbering_regime` | Primarily visual/layout formatting check on compiled output. | — |
| Q047 | Does the first TOC page display the exact heading correctly? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q048 | Do subsequent TOC pages display the correct "(Continued)" heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q049 | In the TOC, are all level-1 chapter titles displayed in all caps? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q050 | In the TOC, are all level-2 section titles (X.x) displayed in title case? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q051 | In the TOC, are all level-3 section titles (X.xx) displayed in sentence case? | partially implemented | `njit_auditor.rules.pdf_heading_levels` | Primarily visual/layout formatting check on compiled output. | — |
| Q052 | Is each entry connected to a page number by a consistent leader style? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q053 | Is every wrapped level-1 TOC entry single-spaced internally? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q054 | Is every wrapped level-2 TOC entry single-spaced internally? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q055 | Is every wrapped level-3 TOC entry single-spaced internally? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q056 | Are level-2 and level-3 entries indented to show hierarchy? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q057 | Is there visible double spacing between consecutive section-title entries? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q058 | If only one appendix is listed, does it begin with “APPENDIX” plus title? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q059 | If multiple appendices are listed, are they identified by letters? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q060 | Does the List of Tables continue the Roman numeral sequence correctly? | partially implemented | `njit_auditor.rules.pdf_page_numbering_regime` | Primarily visual/layout formatting check on compiled output. | — |
| Q061 | Does the first List of Tables page display the exact heading correctly? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q062 | Do subsequent List of Tables pages display the correct "(Continued)" heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q063 | Does the label “Table” appear in bold and left-aligned under the heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q064 | Does the label “Page” appear in bold and right-aligned under the heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q065 | Are all listed table titles in title case and free of a final period? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q066 | Is every wrapped table title single-spaced internally? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q067 | Is there visible double spacing between consecutive table entries? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q068 | Are all table numbers aligned vertically in one left column? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q069 | Are all table page numbers aligned vertically in one right column? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q070 | Does the first List of Figures page display the exact heading correctly? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q071 | Do subsequent List of Figures pages display the correct "(Continued)" heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q072 | Does the label “Figure” appear in bold and left-aligned under the heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q073 | Does the label “Page” appear in bold and right-aligned under the heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q074 | Are all figure descriptions written in sentence case? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q075 | Does every figure description end with a terminal punctuation mark? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q076 | Is every wrapped figure description single-spaced internally? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q077 | Is there visible double spacing between consecutive figure entries? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q078 | Are all figure numbers aligned vertically in one left column? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q079 | Are all figure page numbers aligned vertically in one right column? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |

## 4. P001-P029 implementation table

| P-rule ID | Rule name | Module | Source basis | What it covers | Known caveats |
|---|---|---|---|---|---|
| P001 | Risky manual TeX formatting commands | `latex_risky_commands.py` | TeX linting guardrails | Detects risky spacing/formatting commands | Pattern-based; may not catch custom macros |
| P002 | Duplicate labels | `latex_labels.py` | TeX cross-reference hygiene | Flags duplicate \label definitions | Scope limited to parsed source tree |
| P003 | Whitespace in labels | `latex_labels.py` | TeX label syntax hygiene | Flags label names containing whitespace | Does not enforce naming style beyond whitespace |
| P004 | Unresolved refs/eqrefs | `latex_labels.py` | TeX cross-reference hygiene | Flags refs without matching labels | Depends on parse completeness |
| P005 | Missing figure/table captions | `latex_figures_tables.py` | TeX figure/table quality checks | Detects floats missing caption commands | Heuristic around float-like blocks |
| P006 | Missing figure/table labels | `latex_figures_tables.py` | TeX figure/table quality checks | Detects captions without labels | Heuristic around nearby label placement |
| P007 | Caption terminal punctuation | `latex_figures_tables.py` | TeX figure/table style checks | Checks caption ending punctuation | Conservative text-pattern checks |
| P008 | Required document structure commands | `latex_structure.py` | NJIT required front-matter commands | Checks presence of abstract/TOC/LoT/LoF structure | Command-presence only, not final layout |
| P009 | chktex integration | `latex_linters.py` | External TeX linter integration | Runs chktex when available | Tool availability dependent |
| P010 | lacheck integration | `latex_linters.py` | External TeX linter integration | Runs lacheck when available | Tool availability dependent |
| P011 | PDF margin overflow guard | `pdf_margins.py` | Guideline margins + EF artifact refinement | Flags text crossing margin bounds | Heuristic text-layer geometry |
| P012 | PDF annotations present | `pdf_annotations.py` | Submission cleanliness requirement | Flags embedded comments/annotations | Binary/object-level, not semantic |
| P013 | Page-number candidate extraction/grouping | `pdf_page_numbers.py` | Pagination signal extraction for downstream checks | Emits grouped page-level numbering candidates | Candidate signal can still be noisy |
| P014 | Named front-matter heading layout | `pdf_headings.py` | Guideline heading placement/style | Checks top-zone, centering, caps, bold for named headings | Depends on text-layer/bold metadata |
| P015 | Paragraph indentation pattern | `pdf_indentation.py` | Body/front-matter paragraph formatting | Checks first-paragraph flush and subsequent indent pattern | Heuristic paragraph grouping |
| P016 | Front-matter spacing/blank-line checks | `pdf_spacing.py` | Front-matter vertical spacing rules | Flags excessive gaps and suspicious spacing patterns | Front-matter focused by design |
| P017 | Caption punctuation/style checks | `pdf_captions.py` | Figure/table caption formatting rules | Checks obvious punctuation/case issues | Complex multi-line captions may be missed |
| P018 | TOC/LoT/LoF alignment checks | `pdf_toc_alignment.py` | TOC/list alignment rules | Checks leader/page-column/indent alignment patterns | Heuristic line reconstruction |
| P019 | Page-number sequence/style consistency | `pdf_page_numbers.py` | Pagination consistency rules | Checks gaps, multi-candidate pages, mixed styles | Candidate-quality dependent |
| P020 | Title-case checks for L2/table titles | `pdf_title_capitalization.py` | Titles Examples Level 1-5 + guideline title case | Flags under-capitalized title words | Heading detection sensitive to bold/font cues |
| P021 | Abstract word-count limit | `abstract.py + pdf_abstract.py` | Guideline abstract length limits | Checks PhD/MS abstract length for TeX/PDF | PDF extraction quality dependent |
| P022 | No page number on no-number front-matter pages | `pdf_frontmatter_no_page_number.py` | Abstract/title/approval/copyright pagination rules | Flags visible numbers on prohibited pages | Page identification heuristic |
| P023 | Body double-spacing check | `pdf_body_spacing.py` | Guideline body spacing requirement | Checks body spacing ratio and suspicious gaps | Conservative thresholds can under-report |
| P024 | TOC/LoT/LoF entry formatting | `pdf_toc_list_formatting.py` | Titles-level + list punctuation/style rules | Checks capitalization/punctuation for TOC/LoT/LoF entries | Multi-line entry edge cases remain |
| P025 | Front-matter structure and content presence | `pdf_frontmatter_structure.py` | Guideline-required front-matter elements/order | Checks abstract body, title/approval cues, ordering | Semantic correctness still manual |
| P026 | Body font compliance | `pdf_font_compliance.py` | Guideline body font requirement | Checks body spans for ≈12pt Times-family compliance | Equivalent fonts/department exceptions require judgment |
| P027 | Numbered heading-level style | `pdf_heading_levels.py` | Titles examples level-style mapping | Checks level-specific capitalization/case for numbered headings | Unnumbered headings not covered |
| P028 | Roman/Arabic numbering regime | `pdf_page_numbering_regime.py` | Front-matter vs body numbering regime | Checks roman-front and arabic-body regime | Requires reliable body-start detection |
| P029 | Front-matter Roman sequence ordering | `pdf_roman_sequence.py` | Roman ordering requirement refinement | Flags repeats/gaps/decreases in visible roman sequence | Heuristic candidate filtering applies |

## 5. Missing automatable backlog

### High priority

| Source/Q basis | Expected implementation approach | Risk/noise |
|---|---|---|
| TOC/List continued headings (`Q048`, `Q062`, `Q071`) | Add explicit multi-page continued-heading detection and page-role linking in `pdf_toc_alignment.py`/`pdf_toc_list_formatting.py` | Medium (heading variants and OCR/text-layer variance) |
| Wrapped-entry spacing rules (`Q053-Q055`, `Q066-Q067`, `Q076-Q077`) | Add entry block reconstruction and intra-entry/inter-entry spacing checks | High (line wrapping ambiguity can inflate false positives) |
| TOC/List column-label + alignment checks (`Q063-Q064`, `Q068-Q069`, `Q072-Q073`, `Q078-Q079`) | Add robust column anchor detection and tolerance-based alignment validators | Medium |

### Medium priority

| Source/Q basis | Expected implementation approach | Risk/noise |
|---|---|---|
| TOC title-case/case hierarchy checks (`Q049-Q051`, `Q065`, `Q074-Q075`) | Extend current title/case logic to TOC/list entry extraction pipeline | Medium |
| Front-matter page heading exact-format checks (`Q013`, `Q021`, `Q036`, `Q047`, `Q061`, `Q070`) | Reuse named-heading detector with stricter phrase/style assertions | Medium |
| Cross-page metadata consistency (`Q010-Q011` and title-page consistency cues) | Add normalized string-extraction + cross-page comparison in `pdf_frontmatter_structure.py` | Medium-High |

### Low priority

| Source/Q basis | Expected implementation approach | Risk/noise |
|---|---|---|
| Dedication visual centering/italic details (`Q033-Q034`) | Add text-block centroid + style checks on detected Dedication page | High (weak text-style metadata) |
| Biographical ordering/content structure checks (`Q023-Q030`) | Section parser for Bio Sketch bullets and chronology patterns | High (semantic parsing complexity) |
| Process/doc-driven admin requirements (review roadmap/process docs) | Keep as documentation/checklist hooks, not hard-coded audit rules | Low |

## 6. Manual-only / process-only backlog

Rules that should remain manual-only or process-only for now:

- **Committee semantics and approval validity**: `Q015-Q020` (honorific correctness, rank ordering, affiliation interpretation).
- **Acknowledgements paragraph-intent checks**: `Q037-Q042` plus name/intent semantics (`Q043` context).
- **Department-specific title-page exceptions**: template interpretation from `PhD Title Pages.pdf` where rigid automation may over-flag.
- **Administrative process steps**: Dissertation review workflow / ProQuest and milestone logistics from `Dissertation Review Process.pdf` and `PhD Dissertation Process Roadmap .xlsx`.
- **Signature/approval authenticity**: outside current local deterministic formatting scope.

## 7. Recommendation

- **Should more rules be implemented now?** Yes, but only targeted high-value automatable TOC/List rules where signal quality is defensible.
- **Should focus stay on EF overlap/refinement/reporting?** **Yes.** Current evidence shows this gives safer precision/recall gains than broad semantic automation.

Top 3 next tasks:

1. Implement multi-page TOC/List `(Continued)` coverage and column-label/alignment checks (`Q048/Q062/Q071`, `Q063/Q064/Q072/Q073`).
2. Add wrapped-entry spacing checks for TOC/LoT/LoF (`Q053-Q055`, `Q066-Q067`, `Q076-Q077`) with conservative grouping thresholds.
3. Expand structured reporting to clearly separate **automated-pass**, **partial-coverage**, and **manual-review-required** items per source section.

## 8. Post-audit update (P030)

- **Date:** 2026-05-30
- **Change:** Added **P030** — conservative continued-heading checks for multi-page TOC, List of Tables, and List of Figures sections.
- **Q-rule basis:** partial/heuristic PDF coverage for **Q048**, **Q062**, and **Q071** only.
- **Limitations:** Does not verify bold/centering of continued headings; skips single-page sections and non-consecutive pages; does not claim full visual compliance with the rule matrix wording.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; status note in `docs/evaluation/p030_toc_continued_heading_synthetic_validation.md`.
- **Current-dataset evaluation (2026-05-30):** `docs/evaluation/p030_current_dataset_evaluation.md` — 3 P030 findings on Yin H 4th compressed only; 0 on other evaluated PDFs (see doc for detection caveats).

## 9. Post-audit update (P031)

- **Date:** 2026-05-30
- **Change:** Added **P031** — conservative List of Tables/Figures column header label checks.
- **Q-rule basis:** partial/heuristic PDF coverage for **Q063**, **Q064**, **Q072**, and **Q073** only.
- **Limitations:** Does not verify bold styling or exact alignment; skips TOC pages and ambiguous pages without extractable list entries.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; status note in `docs/evaluation/p031_lot_lof_column_header_synthetic_validation.md`.
- **Current-dataset evaluation (2026-05-30):** `docs/evaluation/p031_current_dataset_evaluation.md` — PR #54 initially reported 2 Sebastian P031 findings (page 11); PR #55 resolved these as header-band false positives; post-fix rerun shows **0 P031 findings** on all evaluated PDFs.
- **Sebastian investigation/refinement (2026-05-30):** `docs/evaluation/p031_sebastian_clean_baseline_investigation.md` — page-11 warnings were likely false positives from header-band geometry; P031 band extended upward conservatively.

## 10. Post-audit update (P032)

- **Date:** 2026-05-30
- **Change:** Added **P032** — conservative wrapped-entry internal spacing checks for Table of Contents, List of Tables, and List of Figures pages.
- **Q-rule basis:** partial/heuristic PDF coverage for **Q053–Q055**, **Q066–Q067**, and **Q076–Q078** only.
- **Limitations:** Does not verify spacing between separate entries, leader formatting, or full visual compliance; skips ambiguous wrap grouping and very large gaps that likely indicate separate entries.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; status note in `docs/evaluation/p032_toc_list_wrapped_spacing_synthetic_validation.md`.
- **Current-dataset evaluation (2026-05-30):** `docs/evaluation/p032_current_dataset_evaluation.md` — 3 P032 findings on Yin H 4th compressed (LoF page 15 only); 0 on other evaluated PDFs.
