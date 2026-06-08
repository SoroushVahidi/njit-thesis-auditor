# Source-to-Implementation Coverage Audit (after P001-P029)

- Date: 2026-06-07
- Baseline main before this branch: `7139e76a9fe5`
- Scope: strict source-to-implementation verification of current rule/guideline sources and implementation surface (no new rule additions)

## 1. Executive summary

- **Are all source rules implemented?** **No.**
- **P-rule implementation:** **70/70 implemented** (`P001`–`P070`) — P069–P070 are infrastructure-only; post-P070 aggregate is **1,543** (−47 vs P069-era 1,590); see `docs/evaluation/current_auditor_after_p070_evaluation.md`.
- **Q-rule coverage (current inventory):** **79** total = **2** `implemented`, **60** `partially_implemented`, **17** `not_implemented` (9 manual-only, 8 automatable gaps after P065–P067 inventory refresh).
- **Q-rule coverage (framing used in this audit):** 9 manual-only (`checkability=manual`) + 12 automatable not_implemented = 21 raw `not_implemented`; see `docs/status/q_rule_coverage_after_p044.md` for full detail.
- **Reporting triage (not new P-rules):** `p011_margin_triage`, `p012_annotation_triage`, `p013_triage`, `p026_font_triage` improve JSON/Markdown actionability only; detector counts unchanged.
- **Guideline-source coverage:** core formatting signals are partially automated via P-rules; semantic/admin/process requirements remain mostly manual or process-only.
- **Biggest remaining gaps:**
  1. Approval/Acknowledgements/Biographical semantic checks (committee rank/order, required paragraph intent/content).
  2. Dedication/Biographical visual-semantic checks and richer figure/table body detection on image-heavy PDFs.
  3. A reproducible full five-PDF P001–P068 evaluation now exists; `00b9c2d` remains the historical pre-P035 baseline and `5d8ebaf` is the current post-P068 aggregate snapshot (`afe4ef6` / 1,587 remains the P067-era historical baseline).

## 2. Source file coverage table

| Source file | Rule/requirement area | Implemented by | Status | Notes |
|---|---|---|---|---|
| `data/processed/rules/njit_rule_inventory.json` | Q001-Q079 authoritative inventory | `tests/test_rule_inventory.py`, mapped modules in `src/njit_auditor/rules/` | partially implemented | Inventory is complete and represented; implementation coverage updated after P044 audit: 2 implemented, 51 partial, 26 not fully implemented. |
| `data/processed/rules/project_added_rules.json` | P001–P068 project rule set | `src/njit_auditor/rules/*.py`, `src/njit_auditor/cli.py`, `tests/` | 68 implemented | P001–P068 implemented and wired in CLI/testing/docs. |
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
| Q013 | Does the Approval Page display the exact phrase “APPROVAL PAGE” in all caps, bold, ce... | partially implemented | `njit_auditor.rules.pdf_frontmatter_headings` | Heading presence and phrase-variant check covered by P038; bold/centered/near-top layout still via P014. | — |
| Q014 | Is the Approval Page free of any visible page number? | partially implemented | `njit_auditor.rules.pdf_frontmatter_no_page_number` | Primarily visual/layout formatting check on compiled output. | — |
| Q015 | Does every committee-member entry begin with an honorific such as Dr., Mr., or Ms.? | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q016 | Do all entries identified as Dissertation Advisor appear before any non-advisor commi... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q017 | Are committee members listed in descending rank order? | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q018 | Among members with the same explicitly stated rank, are the surnames listed in alphab... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q019 | Do all committee-member entries whose affiliation is not NJIT appear after all entrie... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q020 | Does every external or non-NJIT committee-member entry include institution/company na... | manual-only | `—` | Needs human metadata/template interpretation beyond strict source parsing. | Semantic/administrative interpretation requires human review. |
| Q021 | Does the Biographical Sketch page display the exact phrase “BIOGRAPHICAL SKETCH” corr... | partially implemented | `njit_auditor.rules.pdf_frontmatter_headings` | Required heading presence and phrase-variant check covered by P038; full formatting (bold/centered/near-top) still via P014. | — |
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
| Q036 | Does the Acknowledgements page display the exact word correctly formatted? | partially implemented | `njit_auditor.rules.pdf_frontmatter_headings` | Required heading presence and phrase-variant check (e.g. ACKNOWLEDGMENTS variant) covered by P038; full formatting checks via P014. | — |
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
| Q047 | Does the first TOC page display the exact heading correctly? | partially implemented | `njit_auditor.rules.pdf_frontmatter_headings` | Required heading presence and phrase-variant check covered by P038; full formatting via P014. | — |
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
| Q061 | Does the first List of Tables page display the exact heading correctly? | partially implemented | `njit_auditor.rules.pdf_frontmatter_headings` | Optional heading phrase-variant check covered by P038; missing not flagged (optional section); full formatting via P014/P031. | — |
| Q062 | Do subsequent List of Tables pages display the correct "(Continued)" heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q063 | Does the label “Table” appear in bold and left-aligned under the heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q064 | Does the label “Page” appear in bold and right-aligned under the heading? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q065 | Are all listed table titles in title case and free of a final period? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q066 | Is every wrapped table title single-spaced internally? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q067 | Is there visible double spacing between consecutive table entries? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q068 | Are all table numbers aligned vertically in one left column? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q069 | Are all table page numbers aligned vertically in one right column? | not implemented | `—` | Primarily visual/layout formatting check on compiled output. | — |
| Q070 | Does the first List of Figures page display the exact heading correctly? | partially implemented | `njit_auditor.rules.pdf_frontmatter_headings` | Optional heading phrase-variant check covered by P038; missing not flagged (optional section); full formatting via P014/P031. | — |
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
| LoT/LoF cross-page entry ordering (`Q063`, `Q072` extension) | **Implemented as P061** — see `docs/planning/p061_scope_and_design.md` and `docs/evaluation/p061_current_dataset_evaluation.md` | Medium (cross-page grouping and sparse-page gating) |
| Figure/table body detection on image-heavy PDFs | Extend P035 beyond text-layer bodies, likely via image-block extraction in `pdf_layout.py` | High (image geometry reliability and false positives) |
| Canonical five-PDF aggregate refresh | Maintain the committed P001–P067 aggregate snapshot and re-run only when audit behavior changes | Low implementation risk; current aggregate is already reproducible |

### Medium priority

| Source/Q basis | Expected implementation approach | Risk/noise |
|---|---|---|
| Dedication visual checks (`Q033-Q034`) | Add centered-block and italic-style heuristics on detected Dedication pages | High (weak text-style metadata) |
| Biographical content/ordering checks (`Q023-Q030`) | Build a conservative Bio Sketch section parser for chronology/order/layout cues | High (semantic parsing complexity) |
| Heading/list exact-style enforcement | Extend current style checks where bold/italic metadata is reliable; keep privacy-safe reporting | Medium |

### Low priority

| Source/Q basis | Expected implementation approach | Risk/noise |
|---|---|---|
| Process/doc-driven admin requirements (review roadmap/process docs) | Keep as documentation/checklist hooks, not hard-coded audit rules | Low |
| Configurable institution-spec layer | Keep as a future architecture option rather than immediate rule work | Medium |

## 6. Manual-only / process-only backlog

Rules that should remain manual-only or process-only for now:

- **Committee semantics and approval validity**: `Q015-Q020` (honorific correctness, rank ordering, affiliation interpretation).
- **Acknowledgements paragraph-intent checks**: `Q037-Q042` plus name/intent semantics (`Q043` context).
- **Department-specific title-page exceptions**: template interpretation from `PhD Title Pages.pdf` where rigid automation may over-flag.
- **Administrative process steps**: Dissertation review workflow / ProQuest and milestone logistics from `Dissertation Review Process.pdf` and `PhD Dissertation Process Roadmap .xlsx`.
- **Signature/approval authenticity**: outside current local deterministic formatting scope.

## 7. Recommendation

- **Should more rules be implemented now?** Yes, but only targeted high-value automation with defensible signal quality and a clear path to evaluation.
- **Should focus stay on EF overlap/refinement/reporting?** **Yes.** Current evidence shows this gives safer precision/recall gains than broad semantic automation.

Top 3 next tasks:

1. **P069 implemented** — front-matter heading gate recall refinement; see `docs/evaluation/p069_frontmatter_heading_gate_recall_synthetic_validation.md` and current-dataset eval doc.
2. Maintain the full five-PDF **P001–P069** aggregate snapshot (`docs/evaluation/current_auditor_after_p069_evaluation.md`) and re-run only when detector behavior changes.
3. Extend **P035** beyond text-layer-only bodies so image-heavy figure/table pages are no longer skipped by default.

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
- **Current-dataset evaluation (2026-05-30):** `docs/evaluation/p032_current_dataset_evaluation.md` — PR #58 initially reported 3 Yin H 4th P032 findings (LoF page 15); PR #59 resolved these as split-page-number false positives; post-fix rerun shows **0 P032 findings** on all evaluated PDFs.
- **Yin H 4th page-15 investigation (2026-05-30):** `docs/evaluation/p032_yin_h_4th_page15_investigation.md` — structural explanation and intervening page-number guard (PR #59).

## 11. Post-audit update (P033)

- **Date:** 2026-06-01
- **Change:** Added **P033** — conservative cross-page dissertation title consistency checks for Title Page, Abstract page, and Approval Page.
- **Gap basis:** documented remaining cross-page title consistency gap; front-matter/title-page guideline sources.
- **Limitations:** PDF text-layer only; does not quote title text in findings; skips ambiguous, image-only, or single-candidate cases; uses normalized hashes and similarity scores.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; status note in `docs/evaluation/p033_title_consistency_synthetic_validation.md`.
- **Current-dataset evaluation (2026-06-01):** `docs/evaluation/p033_current_dataset_evaluation.md` — PR #62 initially skipped comparison on all files; PR #63 added below-heading fallback; post-fix rerun shows **0 P033 findings**, comparison on **2/5** files (Yin H 4th, Sebastian).
- **Candidate-extraction recall investigation (2026-06-01):** `docs/evaluation/p033_candidate_extraction_recall_investigation.md` — below-heading fallback for ABSTRACT/APPROVAL PAGE layouts.

## 12. Post-audit update (P034)

- **Date:** 2026-06-01
- **Change:** Added **P034** — conservative Copyright Page checks (top-margin header text, year/author consistency with Title Page).
- **Q-rule basis:** partial/heuristic PDF coverage for **Q009–Q011** only.
- **Limitations:** Skips ambiguous or image-only copyright pages; does not quote author names or title text; Q012 (no page number on copyright page) remains with **P022**.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; `docs/evaluation/p034_copyright_page_synthetic_validation.md`.
- **Current-dataset evaluation (2026-06-01):** `docs/evaluation/p034_current_dataset_evaluation.md` — PR #66 initially reported **2** author findings; PR #67 added middle-initial tolerance; post-fix rerun shows **0 P034 findings**, copyright detected **5/5**, author comparison **2/5** with no mismatches.

## 13. Post-audit update (P035)

- **Date:** 2026-06-01
- **Change:** Added **P035** — conservative body-page figure/table body centering and caption placement (text-layer bodies).
- **Source basis:** Self-Assessment Sheet figure/table centering; status gap after P034.
- **Limitations:** Text-layer bodies only; image-only floats skipped; same-page floats only; ambiguous multi-cluster pages skipped; does not replace P017 caption punctuation checks.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; `docs/evaluation/p035_figure_table_layout_synthetic_validation.md`.
- **Current-dataset evaluation (2026-06-01, local subset):** `docs/evaluation/p035_current_dataset_evaluation.md` — four available PDFs: **0 / 0 / 0 / 13** (Yin H 4th compressed only); issue mix on flagged pages: `figure_caption_not_below_body` 7, `table_caption_not_above_body` 5, `table_body_not_centered` 1. **Not** a canonical five-PDF aggregate rerun.

## 14. Post-audit update (P036)

- **Date:** 2026-06-01
- **Change:** Added **P036** — conservative TOC/LoT/LoF inter-entry double-spacing checks (distinct entries only).
- **Q-rule basis:** partial/heuristic PDF coverage for **Q057**, **Q067**, and **Q077**.
- **Limitations:** Text-layer geometry only; gap threshold 1.4× line height; skips wrapped internal continuations (P032); sparse/ambiguous pages skipped; no entry title text in findings.
- **Validation:** Synthetic coverage in `tests/test_pdf_rules.py`; `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md`.
- **Current-dataset evaluation (2026-06-01):** **Not run** — evaluation PDFs unavailable in workspace; see `docs/evaluation/p036_current_dataset_evaluation.md`.

## 15. Post-audit updates through P044 (consolidated current state)

**Current repository (main `5d8ebaf`; five-PDF historical baseline `00b9c2d`):** P001–P068 implemented; web UI present; **963** pytest; full guideline/Q-rule coverage remains incomplete. Reporting triage rollups: `p011_margin_triage`, `p012_annotation_triage`, `p013_triage`, `p026_font_triage` (detection unchanged on the pre-P035 five-PDF snapshot; raw counts 169 / 143 / 461 / 415). The current full aggregate snapshot is `docs/evaluation/current_auditor_after_p068_evaluation.md` at **1,590** findings with **3** P068 findings.

| Rule | Q basis (partial) | Current-dataset snapshot (5 PDFs) | Notes |
|---|---|---|---|
| **P030** | Q048, Q062, Q071 | **3** on Yin H 4th in full P034 snapshot; 0 on other four files | Continued-heading checks on multi-page TOC/LoT/LoF |
| **P031** | Q063–Q064, Q072–Q073 | PR #54: 2 Sebastian false positives; **0** after PR #55 header-band fix | LoT/LoF column header labels |
| **P032** | Q053–Q055, Q066–Q067, Q076–Q078 | PR #58: 3 Yin H 4th LoF page 15; **0** after PR #59 split-page-number guard | Wrapped-entry internal spacing |
| **P033** | Cross-page title consistency | PR #62: no comparison; PR #63: comparison on **2/5**; **0** findings | Below-heading recall fallback |
| **P034** | Q009–Q011 | PR #66: 2 author mismatches; PR #67: middle-initial tolerance; **0** findings | Copyright page detected **5/5** |
| **P035** | Figure/table layout (heuristic) | Local **4-PDF subset:** **0 / 0 / 0 / 13**; not canonical five-PDF aggregate | Text-layer bodies; image floats skipped in v1 |
| **P036** | TOC/List inter-entry spacing (Q057, Q067, Q077) | **Not run** — evaluation PDFs unavailable | Complements P032; no current counts |
| **P037** | Section-anchored front-matter Roman numerals (Q022, Q031, Q035, Q046, Q060) | **Not run** — evaluation PDFs unavailable | bio=iv anchor; synthetic validation only; see `docs/evaluation/p037_current_dataset_evaluation.md` |
| **P038** | Front-matter required heading presence and phrase-variant checks (Q013, Q021, Q036, Q047, Q061, Q070) | **Not run** — evaluation PDFs unavailable | Covers required headings (APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS) and optional (DEDICATION, LIST OF TABLES, LIST OF FIGURES) phrase variants; gated on heading detection; see `docs/evaluation/p038_current_dataset_evaluation.md` |
| **P039** | TOC level indentation hierarchy (Q056) | **Not run** — evaluation PDFs unavailable | Checks L2 indented relative to L1, L3 relative to L2; TOC-only; gate ≥2 child entries; see `docs/evaluation/p039_current_dataset_evaluation.md` |
| **P040** | LoF entry terminal punctuation (Q075) | **Not run** — evaluation PDFs unavailable | Checks complete LoF entries end with `.`/`?`/`!`; LoF-only; skips wrap continuations; see `docs/evaluation/p040_current_dataset_evaluation.md` |
| **P041** | Dedication page top-margin header (Q032) | **Not run** — evaluation PDFs unavailable | Checks no running header in top 15% of Dedication page; gate: skip if DEDICATION heading absent; see `docs/evaluation/p041_current_dataset_evaluation.md` |
| **P042** | TOC appendix entry format (Q058/Q059) | **Not run** — evaluation PDFs unavailable | Single appendix: APPENDIX + title; multiple: each APPENDIX + letter; TOC-only; see `docs/evaluation/p042_current_dataset_evaluation.md` |
| **P043** | Acknowledgements paragraph indentation (Q044/Q045) | **Not run** — evaluation PDFs unavailable | Checks paragraph indentation in Acknowledgements section; see `docs/evaluation/p043_current_dataset_evaluation.md` |
| **P044** | Abstract paragraph indentation (Q002/Q003) | **Not run** — evaluation PDFs unavailable | Checks paragraph indentation in Abstract section; see `docs/evaluation/p044_abstract_indentation_synthetic_validation.md` |
| **P045** | Bio Sketch publication paragraph layout (Q028/Q029) | **Not run** — evaluation PDFs unavailable | Checks hanging indent and inter-entry spacing on Bio Sketch page; see `docs/evaluation/p045_biosketch_publication_layout_synthetic_validation.md` |
| **P046** | LoT/LoF entry number left-column alignment (Q068/Q078) | **Not run** — evaluation PDFs unavailable | Checks x0 consistency of LoT/LoF entry first-line positions; see `docs/evaluation/p046_lot_lof_entry_number_alignment_synthetic_validation.md` |
| **P047** | Bio Sketch bullet/list section single-spacing (Q026) | **Not run** — evaluation PDFs unavailable | Checks non-hanging-indent Bio Sketch multi-line blocks for excessive internal gaps; geometry-only findings |
| **P048** | LoT/LoF page-number right-column alignment (Q069/Q079) | **Not run** — only 4/5 evaluation PDFs directly accessible | Checks page-number right-edge consistency on LoT/LoF complete entries; see `docs/evaluation/p048_lot_lof_page_number_alignment_synthetic_validation.md` and `docs/evaluation/p048_current_dataset_evaluation.md` |
| **P049** | LoT/LoF Page-column header right-alignment and bold-style (Q064/Q073) | **Not run** — only 4/5 evaluation PDFs directly accessible | Checks 'Page' header right-edge alignment and bold style; see `docs/evaluation/p049_lot_lof_column_header_refinement_synthetic_validation.md` |
| **P050** | LoT/LoF left-column header bold-style (Q063/Q072) | **Not run** — only 4/5 evaluation PDFs directly accessible | Checks 'Table'/'Figure' header bold style when font metadata is reliable; see `docs/evaluation/p050_lot_lof_left_column_header_bold_synthetic_validation.md` |
| **P051** | Copyright page year-format refinement (Q010) | **Not run** — only 4/5 evaluation PDFs directly accessible | Emits advisory when copyright page detected but no year token found; adjacent-line extraction; see `docs/evaluation/p051_copyright_year_format_refinement_synthetic_validation.md` and `docs/evaluation/p051_current_dataset_evaluation.md` |
| **P052** | Copyright page author-format refinement (Q011) | **Not run** — only 4/5 evaluation PDFs directly accessible | Emits advisory when copyright page + year detected but no author extractable; adjacent-line author extraction; only fires when year confirmed; hash-only metadata; see `docs/evaluation/p052_copyright_author_format_refinement_synthetic_validation.md` and `docs/evaluation/p052_current_dataset_evaluation.md` |
| **P053** | LoT entry terminal-period check (Q065) | **Not run** — only 4/5 evaluation PDFs directly accessible | Emits warning when complete LoT entry ends with `.`; symmetric to P040 (LoF must have terminal punct); new `pdf_lot_terminal_period.py`; see `docs/evaluation/p053_lot_terminal_period_synthetic_validation.md` and `docs/evaluation/p053_current_dataset_evaluation.md` |
| **P054** | TOC entry terminal-period absence check (Q049/Q050/Q051 refinement) | **Implemented** | `pdf_toc_terminal_period.py`; emits `toc_entry_has_terminal_period` when complete TOC entry ends with `.`; symmetric counterpart to P053 for TABLE OF CONTENTS pages; 9 synthetic tests; see `docs/planning/p054_scope_and_design.md` and `docs/evaluation/p054_toc_terminal_period_synthetic_validation.md` |
| **P055** | LoT/LoF cross-type entry check (Q063/Q072 extension) | **Implemented** | `pdf_lot_lof_entry_type.py`; emits `lot_entry_is_figure` when complete LoT entry starts with "Figure", `lof_entry_is_table` when complete LoF entry starts with "Table"; 10 synthetic tests; see `docs/planning/p055_scope_and_design.md` and `docs/evaluation/p055_lot_lof_entry_type_synthetic_validation.md` |
| **P056** | LoT/LoF entry numbering format consistency check (Q063/Q072 extension) | **Implemented** | `pdf_lot_lof_number_format.py`; emits advisory when section mixes chapter-based (X.Y) and sequential (N) numbering; gates: ≥2 entries of each format type, page_number_token present, ≥10 chars; appendix-prefixed entries skipped; triage_tier: low; 13 synthetic tests; **Not run** — only 4/5 evaluation PDFs accessible; see `docs/planning/p056_scope_and_design.md` and `docs/evaluation/p056_lot_lof_number_format_synthetic_validation.md` |
| **P057** | LoT/LoF page-number ordering check (Q069/Q079 refinement) | **Implemented** | `pdf_lot_lof_page_number_ordering.py`; emits advisory when listed page numbers are not non-decreasing; gates: ≥3 comparable integer entries, ≥2 inversions; non-integer tokens skipped; TOC excluded; triage_tier: medium; 12 synthetic tests; **Not run** — only 4/5 evaluation PDFs accessible; see `docs/planning/p057_scope_and_design.md` and `docs/evaluation/p057_lot_lof_page_number_ordering_synthetic_validation.md` |
| **P058** | TOC page-number ordering check (Q057 refinement) | **Implemented** | `pdf_toc_page_number_ordering.py`; emits advisory when TABLE OF CONTENTS entries have page numbers that are not non-decreasing; gates: ≥3 comparable integer entries, ≥2 inversions; non-integer tokens skipped; LoT/LoF excluded; triage_tier: medium; 10 synthetic tests; **Not run** — only 4/5 evaluation PDFs accessible |
| **P059** | LoT/LoF entry-number ordering check (Q063/Q072 refinement) | **Implemented** | `pdf_lot_lof_entry_number_ordering.py`; emits warning when List of Tables or List of Figures entries have entry numbers that are not non-decreasing; gates: ≥3 comparable entries, ≥2 inversions; mixed sequential+chapter-based pages skipped; appendix/letter-prefixed entries skipped; TOC excluded; triage_tier: medium; 12 synthetic tests; **Not run** — only 4/5 evaluation PDFs accessible; see `docs/evaluation/p059_lot_lof_entry_number_ordering_synthetic_validation.md` |
| **P060** | TOC section-number ordering check (Q056/Q057 implied) | **Implemented** | `pdf_toc_entry_number_ordering.py`; emits warning when parseable numeric section entries in TABLE OF CONTENTS are not non-decreasing; word-prefix entries (CHAPTER, ABSTRACT, APPENDIX) skipped; conservative gates: ≥3 comparable entries, ≥2 inversions; triage_tier: medium; 12 synthetic tests; **Not run** — only 4/5 evaluation PDFs accessible; see `docs/evaluation/p060_toc_entry_number_ordering_synthetic_validation.md` |
| **P061** | LoT/LoF cross-page entry-number ordering check (Q063/Q072 extension) | **0** on five-PDF local subset (not canonical aggregate) | `pdf_lot_lof_cross_page_entry_ordering.py`; issue types `lot_cross_page_entry_numbers_not_nondecreasing`, `lof_cross_page_entry_numbers_not_nondecreasing`; requires ≥2 consecutive same-type pages; gates: ≥3 combined comparable entries, ≥2 inversions; see `docs/evaluation/p061_current_dataset_evaluation.md` |

Privacy: per-rule evaluation docs are aggregate-only; do not quote dissertation title text, author names, caption/body/entry text, or body text. Generated JSON summaries remain under `data/evaluation/generated/` (gitignored).

**Full aggregate snapshot (2026-06-07, P061-era):** `docs/evaluation/current_auditor_after_p061_evaluation.md` — five-PDF run with P011–P061; **1,587** total findings (gitignored per-file JSON under `data/evaluation/generated/current_auditor_after_p061/`). P011–P034 subtotal unchanged at **1,446**; +141 from P035–P061; P061 **0** (sparse comparable LoT/LoF entries).

**Historical aggregate snapshot (2026-06-01, pre-P035 canonical):** `docs/evaluation/current_auditor_after_p034_evaluation.md` — five-PDF run with P011–P034; **1,446** total findings (`generated_for_commit: 00b9c2d`).

**P013 reporting refinement (2026-06-01):** `docs/evaluation/p013_reporting_actionability_refinement.md` — `p013_triage` rollup and Markdown triage section; detection unchanged.

**P034 + P013 triage output refresh (2026-06-01):** `docs/evaluation/current_auditor_after_p034_p013_triage_refresh.md` — regenerated five-PDF JSON/MD under gitignored `current_auditor_after_p034_p013_triage/`; aggregate counts unchanged (1,446 / 461 P013).

**P026 reporting refinement (2026-06-01):** `docs/evaluation/p026_reporting_actionability_refinement.md` — `p026_font_triage` rollup; five-PDF rerun under gitignored `current_auditor_after_p034_p026_triage/` (415 P026 unchanged).

**P011 reporting refinement (2026-06-01):** `docs/evaluation/p011_reporting_actionability_refinement.md` — `p011_margin_triage` rollup; five-PDF rerun under gitignored `current_auditor_after_p034_p011_triage/` (169 P011 unchanged).

**P012 reporting refinement (2026-06-01):** `docs/evaluation/p012_reporting_actionability_refinement.md` — `p012_annotation_triage` rollup; raw P012 count expected unchanged (143 on five-PDF snapshot).

**Canonical full-triage outputs (2026-06-01):** `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md` — use `current_auditor_after_p034_p011_triage/` for latest JSON/MD with P011/P012/P013/P026 triage rollups; older `current_auditor_after_p034*` folders are historical.
