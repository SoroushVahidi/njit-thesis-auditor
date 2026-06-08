# P070 — TOC/LoT/LoF Entry Parser Recall Refinement: Scope and Design

## 1. Metadata

| Field | Value |
|---|---|
| **P-rule** | P070 |
| **Rule name** | TOC/LoT/LoF Entry Parser Recall Refinement |
| **Date** | 2026-06-08 |
| **Baseline commit** | `738a39b` (PR #250 — post-P069 aggregate evaluation snapshot) |
| **Status** | **Implemented (v1)** — see `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_synthetic_validation.md` |
| **Validation baseline** | 976 pytest (`ruff check .`, `mypy src`, 87 source files) |
| **Type** | **Shared infrastructure / parser recall refinement** (not a standalone semantic checker) |
| **Companion utilities** | `pdf_toc_alignment.py` (`detect_toc_like_pages`, `extract_toc_entry_lines`, `TocEntryLine`, `TocPageContext`); P069 gate helpers already wired into TOC/List page-type detection |

---

## 2. Post-P069 Backlog Audit Summary

### Repository state (audit date 2026-06-08)

| Item | Value |
|---|---|
| Branch | `main` (clean working tree at `738a39b`) |
| Highest implemented P-rule | **P069** |
| Implemented P-rule count | **69** (`P001`–`P069`) |
| Q-rules in inventory | **79** total |
| Q-rule `implemented` | **2** (Q004, Q005) |
| Q-rule `partially_implemented` | **~60** |
| Q-rule `not_implemented` | **~17** (manual-only + automatable gaps) |
| Pytest count | **976** |
| Post-P069 aggregate snapshot | `docs/evaluation/current_auditor_after_p069_evaluation.md` — **1,590** findings; delta **0** vs P068-era |
| Post-P069 gate evaluation | `docs/evaluation/p069_frontmatter_heading_gate_recall_current_dataset_evaluation.md` — ACKNOWLEDGEMENTS +4; P065–P068 totals unchanged |

### Stale metadata still present (historical docs)

Some older evaluation and status docs intentionally retain P068-era or P063-era baselines
(`963 pytest`, `P001–P068`, commit `5d8ebaf`). Current canonical scope is **P001–P069** /
**976 pytest** / post-P069 aggregate **1,590**. This scope doc does not rewrite those
historical snapshots.

### No existing P070/P071 planning docs

Confirmed before this document: no prior `p070_*` or `p071_*` files under `docs/planning/`.

---

## 3. Motivation

After P069 improved front-matter **heading gate** recall, the highest-value remaining
**non-semantic** gap is shared **TOC/List entry parsing** recall. P069 explicitly deferred
LoT/LoF entry parsing (`project_added_rules.json` P069 notes). Twenty-plus dependent rules
(P018, P024, P027–P032, P036, P039–P040, P046–P058, P053–P056, P060–P062) consume
`detect_toc_like_pages()` and `extract_toc_entry_lines()` from `pdf_toc_alignment.py`.

Why P070 is the best next task after P069:

1. **EF-overlap gap:** `list_of_tables_figures_toc` has **4** EF comments on the two
   extractable-comment PDFs but **0** tool findings in that category after P068/P069
   (`docs/evaluation/ef_overlap_after_p068_evaluation.md`). Parser recall, not absent rules.
2. **Evaluation skip pattern:** P061 formal eval found **0/5** files with qualifying
   comparable LoT/LoF entries; **3/5** had no LoT/LoF pages detected at all
   (`docs/evaluation/p061_current_dataset_evaluation.md`). Yin H 4th had a 2-page LoF run but
   **0** parseable entries under current gates.
3. **Aggregate asymmetry:** The five-PDF post-P069 aggregate reports **130**
   `list_of_tables_figures_toc` findings, concentrated on Yin H 4th compressed (**77** from
   P036 alone). Comparison PDFs (Cibaku, Yin Haotian) remain at **0** in that category —
   indicating recall is file-layout dependent, not uniformly effective.
4. **Cross-rule leverage:** Ordering, spacing, alignment, terminal-period, and hierarchy rules
   all share the same entry-extraction substrate. Improving recall raises downstream rule
   reach without adding new semantic checks.
5. **Non-duplication of P069:** P069 improved canonical **heading** resolution for TOC/List
   page detection via `resolve_gate_heading_from_line()` in `_detect_toc_page_type()`. P070
   targets **entry line** extraction, multi-line wrapping, split page-number columns, and
   conservative page-run grouping — a separate parser track.
6. **Privacy-safe infrastructure:** Outputs remain numeric/structural (counts, page indices,
   indent x-coordinates, boolean flags). No entry titles, captions, or dissertation text.

### Relation to other backlog items

| Track | Status after P069 | P070 relationship |
|---|---|---|
| Front-matter heading gates | Improved (P069) | Complementary — headings detected; entries still sparse |
| References/citations (P064) | Implemented; skipped on comparison PDFs | Separate track — body-region and x-variance gates, not shared TOC parser |
| Approval Page blocks (P068) | Implemented; APPROVAL PAGE gate unchanged on comparison PDFs | Separate track — image-only / true-absence likely |
| Acknowledgements semantics (Q039–Q043) | Manual-only | Out of scope |

---

## 4. Candidate Comparison (post-P069)

| Candidate | Q/guideline basis | Current coverage | EF / eval motivation | Automatable? | Privacy / FP risk | Decision |
|---|---|---|---|---|---|---|
| **P070 TOC/LoT/LoF entry parser recall** | Q052–Q079 partials | P018/P030–P062 implemented | 4 EF `list_of_tables_figures_toc`; 130 aggregate but 0 on comparison PDFs; P061 3/5 no LoT/LoF detected | **Yes — infra** | Low privacy; **medium FP** if gates loosened | **Selected** |
| References/citations v2 / recall | Q028/Q029 analogy; P064 | P064 structural v1 | **9** EF `references_citations`, 0 tool on comparison PDFs | Partial — gate/localization | Low privacy; medium FP on noisy text layers | **Deferred (P071 candidate)** — P064 skipped due to body-region and x-variance gates, not missing entry parser |
| Committee approval page v2 | Q015–Q020 partial | P068 v1 | **5** EF `committee_approval_page`, 0 tool on comparison PDFs | Partial | Medium FP; semantic risk | **Deferred** — APPROVAL PAGE gate unchanged post-P069; likely image-only on comparison set |
| Acknowledgements structural (Q039–Q043) | Q039–Q043 | P043 indentation partial | 2 EF `acknowledgements` | **No — semantic** | High privacy / FP | **Rejected** for P070 |
| Appendix-before-references placement | Weak explicit Q-rule | P042/P063/P064 partial | Low EF signal | Weak basis | Medium FP | **Deferred** |
| Equation numbering/layout | Self-Assessment mention only | None | None | **No confirmed Q-rule** | Unknown | **Rejected** |
| Bio Sketch / Approval Page heading recall v2 | Q013, Q021 | P069 gate | Gate counts unchanged on five-PDF set | Infra | Low | **Deferred** — P069 completed; further recall blocked by image-only/true absence |
| Remaining Q026/Q030 style semantics | Q026, Q030 | Partial/manual | Low | Style semantic | High FP | **Manual-only** |

### Selection rationale

P070 is selected because it is the only high-value gap that (a) has confirmed guideline
partial coverage across many Q-rules, (b) is explicitly called out in EF-overlap and P069
follow-up notes, (c) affects the largest cluster of already-implemented dependent rules, and
(d) can be implemented as conservative shared infrastructure without reading private content.

References/citations v2 ranks second by EF volume but is a **different failure mode**
(body-start detection, reference-section x-variance from annotation artifacts) and should not
be mixed into the TOC/List parser track.

---

## 5. Guideline / Q-Rule Basis

### Source files consulted

| File | Relevance |
|---|---|
| `data/processed/rules/njit_rule_inventory.json` | Q046–Q079 TOC/LoT/LoF requirements |
| `data/raw/guidelines/Self-Self Assessment Sheet.pdf` | TOC/LoT/LoF checklist expectations (paraphrased only) |
| `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf` | Named list headings and layout cues (paraphrased only) |
| `docs/evaluation/ef_overlap_after_p068_evaluation.md` | `list_of_tables_figures_toc` EF gap |
| `docs/evaluation/current_auditor_after_p069_evaluation.md` | Aggregate category totals and per-file asymmetry |
| `docs/evaluation/p061_current_dataset_evaluation.md` | LoT/LoF detection and parseability skips |
| `src/njit_auditor/rules/pdf_toc_alignment.py` | Current parser implementation |
| `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py` | P069 heading gate already used in page-type detection |

### Q-rule classification for P070

| Q-rule | Paraphrased requirement | Classification for P070 |
|---|---|---|
| Q046 | TOC uses correct Roman numeral continuation | **Already covered** by P037 — out of P070 scope |
| Q047 | TOC exact heading on first page | **Partial — heading gate** (P069/P038); P070 does not re-check |
| Q048 | TOC continuation pages use "(Continued)" | **Partial** — P030; depends on page-run detection |
| Q049–Q051 | TOC entry capitalization by level | **Partial** — P024/P027; depends on entry extraction |
| Q052 | Consistent leader-dot style | **Partial** — P018; depends on entry extraction |
| Q053–Q055 | Wrapped TOC entry single-spacing | **Partial** — P032; depends on multi-line entry grouping |
| Q056–Q057 | TOC hierarchy indent and inter-entry spacing | **Partial** — P039/P036; depends on entry extraction |
| Q058–Q059 | Appendix entry format in TOC | **Partial** — P042; depends on entry extraction |
| Q060 | TOC page numbers non-decreasing | **Partial** — P058; depends on `page_number_token` recall |
| Q061–Q073 | LoT/LoF heading, column, alignment, spacing | **Partial** — P031/P046–P056/P048–P050; depends on entry extraction |
| Q063–Q072 | LoT/LoF entry numbering and format | **Partial** — P055/P056/P059; depends on entry prefix parsing |
| Q074–Q079 | LoF terminal punctuation and spacing | **Partial** — P040/P053; depends on entry completeness detection |
| Q015–Q020 | Committee semantics | **Out of scope** |
| Q028–Q030 | Citation/publication style | **Out of scope** |

---

## 6. P070 v1 Scope

### Included (shared PDF text-layer infrastructure)

1. **Refine `extract_toc_entry_lines()`** in `pdf_toc_alignment.py` (or a dedicated
   companion module imported by it) to improve recall of complete list entries without
   exporting entry text in findings.
2. **Multi-line entry grouping:** merge consecutive lines below a heading when a later line
   carries the page-number token and earlier lines lack one (wrapped titles).
3. **Split-column page-number pairing:** extend numeric-only right-column pairing beyond the
   current single-line heuristic; tolerate slightly larger y-delta when x-position clearly
   indicates a right column.
4. **Prefix-tolerant entry starts:** accept `Table N` / `Figure N` / numeric section prefixes
   with shorter cleaned length than the current `_likely_entry_line` 8-character minimum
   when a page-number token or right-column numeric sibling is present.
5. **Conservative continuation-line filter:** reject prose-like lines (sentence terminators,
   excessive word count) from entry candidates while allowing short wrapped fragments.
6. **Page-run context helper (optional v1):** expose consecutive same-type TOC/LoT/LoF page
   groups so cross-page rules (P061, P062) and spacing rules see a unified entry stream.
7. **Wire refined parser into all consumers** of `extract_toc_entry_lines()` without
   changing individual rule thresholds in v1.
8. **Regression guarantee:** when the refined parser yields the same entry set as v1 on a
   page, dependent rules must produce identical findings.

### Excluded

- OCR or image-based list detection
- Reading or emitting entry titles, captions, figure labels, or section names
- Citation style, capitalization semantics, or APA title-case enforcement beyond what
  existing rules already do once entries are parsed
- References/bibliography entry parsing (P064 track)
- Approval Page or Bio Sketch content checks
- TeX-source list checks in v1
- Fuzzy matching on arbitrary entry text
- New standalone semantic issue types in v1
- Changing P069 heading-gate behavior

### Input type

**PDF text layer only** for v1.

### Standalone issue types

**None in v1.** P070 is infrastructure-first. Any new findings should appear through
dependent rules (P018, P036, P046, P058–P062, etc.) when pages previously produced zero or
too-few entries. No `P070_*` issue type codes in v1.

---

## 7. Detection / Refinement Algorithm

### Step 1 — Reuse P069 heading detection (unchanged)

`detect_toc_like_pages()` continues to use `passes_standalone_line_gate()` and
`resolve_gate_heading_from_line()` for page-type classification. P070 does not alter this
step in v1 except through shared imports if helper code is relocated.

### Step 2 — Collect raw candidate lines

For each `TocPageContext`:

- Iterate text lines strictly below `heading_bottom_y + 2pt`.
- Skip numeric-only lines initially; retain in a right-column pool.
- Apply relaxed `_likely_entry_line_v2()`:
  - minimum cleaned length **4** when line matches `^(TABLE|FIGURE|CHAPTER|APPENDIX)\b` or
    leading numeric section prefix;
  - default minimum cleaned length **8** otherwise;
  - reject ALL-CAPS lines ≤4 tokens only when no page-number signal exists (column header
    guard);
  - reject lines ending with `.` when word count > 6 (prose guard).

### Step 3 — Page-number attachment

1. Inline trailing token via existing `PAGE_NUMBER_TOKEN_RE`.
2. Right-column numeric-only pairing with `PAGE_NUMBER_LINE_Y_TOLERANCE_PT` (default 5pt);
   v1 may increase to **8pt** only when numeric line x0 exceeds entry indent + 200pt.
3. If still missing, look at the **next** candidate line within 12pt vertical gap for a
   numeric-only right-column token (wrapped-entry pattern).

### Step 4 — Multi-line merge

When line *i* lacks `page_number_token` and line *i+1* has one within 12pt:

- Merge bbox/indent metadata using the first line's indent_x.
- Do not concatenate or store combined text for findings — keep structural fields only.
- Mark merged entry `is_wrapped=True` for downstream spacing rules.

### Step 5 — Entry list post-filter

- Drop entries with neither `page_number_token` nor paired right-column numeric (incomplete).
- Require ≥1 retained entry per page for parser diagnostics; dependent rules keep their own
  ≥2/≥3 entry gates.
- Sort by y0, then x0.

### Step 6 — Optional page-run grouping

Build runs of consecutive pages with the same `page_type` (allow 1-page gap only when both
pages share the same type and Roman/front-matter region). Expose `TocPageRun` with combined
entry iterators for P061/P062.

### Confidence scoring (internal only)

| Signal | Confidence |
|---|---|
| Inline page-number token at line end | high |
| Right-column numeric paired within tight y-tolerance | medium |
| Wrapped merge with page number on following line | medium |
| Entry lacks page number after pairing | **excluded** |

Confidence is not exported in findings; it governs optional debug/evaluation counters only.

---

## 8. Finding / Output Fields

P070 emits **no findings** in v1. Dependent rules continue to emit existing issue types with
unchanged field shapes.

### Fields that may appear in dependent-rule findings (unchanged)

| Field | Allowed |
|---|---|
| `page` | yes |
| `issue_type` | yes (existing codes only) |
| `entry_count` | yes |
| `indent_x` / `page_number_right_x` | yes (numeric) |
| `inversion_count` | yes |
| `confidence` | yes (existing enums) |

### Explicitly excluded from all outputs

- Entry title text, section names, table/figure captions
- Leader-dot content beyond boolean `has_leader_dots`
- Author names, dissertation titles, DOI/URL strings
- EF comment text

---

## 9. Conservative Skip Conditions

| Condition | Action |
|---|---|
| No TOC/LoT/LoF page detected | Skip page-level parsing (unchanged) |
| Image-only page / zero text blocks | Skip |
| Fewer than 1 candidate line below heading | Skip entry extraction for that page |
| Ambiguous dual headings on same page | Keep highest heading (existing behavior) |
| Multi-column body layout detected on page | Skip entry extraction (avoid false merges) |
| Numeric lines clustered at left margin (not right column) | Do not pair as page numbers |
| Flattened PDF with collapsed spacing and no right-column numerics | Skip — same as today |
| Manual-only semantic judgment (capitalization intent, wording) | Never attempted |

---

## 10. False-Positive and False-Negative Risks

### False-positive risks

| Risk | Mitigation |
|---|---|
| Body text mistaken for list entry | Prose guards; heading-bottom y cutoff; max word count |
| Random margin numbers paired as page numbers | Require right-column x-position; minimum indent separation |
| Column headers parsed as entries | ALL-CAPS short-line guard without page-number signal |
| Duplicate entries after merge | Deduplicate by y0 within 2pt |

### False-negative risks

| Risk | Mitigation |
|---|---|
| Wrapped entries still missed | Step 4 merge; slightly relaxed y-tolerance for right column |
| Chapter-prefixed short entries skipped | Prefix-tolerant length gate |
| Comparison PDFs still at zero after P070 | Document as dataset limitation; do not loosen gates enough to parse body paragraphs |
| Flattened PDFs remain unsupported | Accept; no OCR in v1 |

---

## 11. Synthetic Test Plan

Target: **12 tests** in `tests/test_p070_toc_lot_lof_entry_parser_recall.py`

| # | Test | Purpose |
|---|---|---|
| 1 | Single-line TOC entry with inline page number | Baseline regression |
| 2 | Wrapped TOC entry — title line + numeric-only right column on next line | Core recall case |
| 3 | `Table 1` prefix with short cleaned length | LoT prefix tolerance |
| 4 | `Figure 2` prefix with split page number | LoF prefix tolerance |
| 5 | Numeric-only right column paired within relaxed y-tolerance | Pairing refinement |
| 6 | `(Continued)` LoT page appended to prior run | Page-run grouping |
| 7 | Prose paragraph below heading rejected | FP guard |
| 8 | ALL-CAPS `CHAPTER 1` line without page number rejected as entry | Header guard |
| 9 | Multi-page TOC run exposes combined entry count to P062 helper | Cross-page consumer |
| 10 | Privacy — synthetic fixture findings contain no entry title strings in details | Privacy |
| 11 | Regression — P018 dot-style check unchanged when parser returns same entries | No degradation |
| 12 | Regression — P061 skips when <3 comparable entries even if parser recall improves | Gate preservation |

All fixtures use clearly fake placeholder text only (e.g., `LOREM SECTION`, `TABLE 9`,
`PAGE 99`).

---

## 12. Current-Dataset Evaluation Plan (post-implementation)

1. **Parser reach evaluation** on five documented PDFs (labels only):
   - count TOC/LoT/LoF pages detected per file;
   - count extracted entries per page (numeric only);
   - count pages where entry count increased vs pre-P070 baseline.
2. **Dependent-rule before/after table** for high-leverage consumers: P036, P046, P058, P059,
   P060, P061, P062 (aggregate counts only).
3. **EF overlap refresh** on two extractable-comment PDFs — measure whether
   `list_of_tables_figures_toc` tool findings move from 0 without quoting comments.
4. **Full five-PDF aggregate rerun** only if dependent-rule totals change.
5. Generated outputs under `data/evaluation/generated/p070_evaluation/` (gitignored).

No private text in evaluation docs.

---

## 13. Implementation Checklist

| Item | Path / action |
|---|---|
| Parser module | Extend `src/njit_auditor/rules/pdf_toc_alignment.py` or add `pdf_toc_lot_lof_entry_parser.py` |
| Wire consumers | Import refined `extract_toc_entry_lines()` — no per-rule threshold edits in P070 PR |
| P070 inventory entry | Add to `data/processed/rules/project_added_rules.json` as `infrastructure_refinement` |
| Evaluation category | No new category — findings flow through `list_of_tables_figures_toc` |
| Tests | `tests/test_p070_toc_lot_lof_entry_parser_recall.py` (12 tests) |
| Synthetic validation doc | `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_synthetic_validation.md` |
| Current-dataset eval doc | `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md` |
| Status docs | `docs/status/current_project_state_and_next_steps.md` |
| Validation | `ruff check .`, `mypy src`, `python -m pytest` |

---

## 14. Recommendation

**Implemented (2026-06-08):** parser refinements in `pdf_toc_alignment.py`; 12 synthetic
tests; five-PDF current-dataset before/after evaluation **pending** (PDFs unavailable in
workspace). No standalone P070 findings.

Exact next PR:

1. Implement parser recall refinements per sections 6–7.
2. Add 12 synthetic tests and synthetic validation doc.
3. Run parser-reach and dependent-rule before/after evaluation on five PDFs.
4. Refresh EF overlap if `list_of_tables_figures_toc` counts change on comparison PDFs.
5. Add P070 entry to `project_added_rules.json` with `issue_types: []` and affected-rule list.

**Caveats:** Zero findings on comparison PDFs after P070 would not prove the EF comments were
wrong — they may target semantic layout issues the text layer cannot see. Parser recall is
necessary but not sufficient for full guideline coverage.

---

## Cross-References

- Post-P069 aggregate: `docs/evaluation/current_auditor_after_p069_evaluation.md`
- P069 scope (deferred parser track): `docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`
- EF overlap gaps: `docs/evaluation/ef_overlap_after_p068_evaluation.md`
- P061 eval skips: `docs/evaluation/p061_current_dataset_evaluation.md`
- Shared parser: `src/njit_auditor/rules/pdf_toc_alignment.py`
