# P071 — References Section Localization Recall Refinement: Scope and Design

## 1. Metadata

| Field | Value |
|---|---|
| **P-rule** | P071 |
| **Rule name** | References Section Localization Recall Refinement |
| **Date** | 2026-06-08 |
| **Baseline commit** | `12f01b3` (PR #254 — post-P070 canonical aggregate snapshot) |
| **Status** | **Implemented** — scoped PR #255; merged PR #256; EF overlap refresh PR #257; polish PR #258 |
| **Validation baseline** | 1000 pytest (`ruff check .`, `mypy src`, 87 source files) |
| **Type** | **Shared infrastructure / localization recall refinement** (not a new semantic checker) |
| **Companion module** | `src/njit_auditor/rules/pdf_references_citations_structural.py` (P064) |
| **Expected issue types in v1** | **None new** — P064 issue types only when checks reach the section |

---

## 2. Post-P070 Backlog Audit Summary

### Repository state (audit date 2026-06-08)

| Item | Value |
|---|---|
| Branch | `main` (clean working tree at `12f01b3`) |
| Highest implemented P-rule | **P070** |
| Implemented P-rule count | **70** (`P001`–`P070`) |
| Q-rules in inventory | **79** total |
| Q-rule `implemented` | **2** (Q004, Q005) |
| Q-rule `partially_implemented` | **~56** |
| Q-rule `not_implemented` | **~21** (manual-only + automatable gaps) |
| Pytest count | **988** |
| Post-P070 aggregate snapshot | `docs/evaluation/current_auditor_after_p070_evaluation.md` — **1,543** findings; −47 vs P069-era 1,590 |
| P070 parser-reach evaluation | `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md` — entries 185→167; EF comparison PDFs still 0 list pages |

### Metadata consistency

Canonical status docs now reflect **P001–P070**, **988 pytest**, and post-P070 aggregate
**1,543**. Historical snapshots (P034: 1,446; P061–P067: 1,587; P068/P069: 1,590) remain
intentionally preserved as historical baselines. Some older evaluation docs still cite
963/976 pytest or P068-era scope by design.

### No prior P071 planning doc

Confirmed before this document: no `p071_*` file existed under `docs/planning/`.

---

## 3. Motivation

After P070 improved TOC/LoT/LoF **entry parser** recall, the largest remaining **automatable
EF zero-coverage gap** is `references_citations`: **9** EF annotations on the two
extractable-comment PDFs and **0** tool findings in that category after P064
(`docs/evaluation/ef_overlap_after_p068_evaluation.md`). P070 did not change this gap because
comparison PDFs still have no detected list pages and P064 was already skipped on both files.

Why P071 is the best next task after P070:

1. **Largest automatable EF miss:** `references_citations` (9 EF) exceeds
   `committee_approval_page` (5) and `list_of_tables_figures_toc` (4 on comparison PDFs).
2. **Rule exists but does not reach:** P064 is implemented with conservative structural
   checks; the five-PDF evaluation showed **0** P064 findings because **3/5** files were
   skipped by localization gates, including **both EF-comparison PDFs**
   (`docs/evaluation/p064_current_dataset_evaluation.md`).
3. **Known skip patterns, not missing semantics:** Yin Haotian 2nd and Yin H 2nd flat fail
   `body_start` detection (collapsed `CHAPTER1` text layer). Cibaku reaches a references
   heading but is skipped by high x-variance (59.7 pt > 50 pt threshold), likely EF
   annotation geometry noise.
4. **Non-duplication:** P070 addressed list-entry parsing; references section localization is
   a separate failure mode (body-region detection, back-matter heading scan, noisy geometry).
5. **Privacy-safe infrastructure:** Refinements expose only page numbers, counts, x-coordinates,
   and skip/confidence enums — no reference entry text.
6. **Low new-issue-type risk:** v1 does not add citation-style checks; it helps P064 run where
   it currently skips silently.

### Relation to aggregate / P070 results

Post-P070 aggregate decreased by −47, driven by Yin H 4th list-parser noise reduction. EF
comparison PDF totals were unchanged. P071 targets the comparison PDFs' references gap, not
aggregate volume reduction.

---

## 4. Candidate Comparison (post-P070)

| Candidate | Q/guideline basis | Current coverage | EF / eval motivation | Automatable? | Privacy / FP risk | Decision |
|---|---|---|---|---|---|---|
| **P071 References section localization recall** | Self-Assessment p.4; Guidelines para 138; Q028/Q029 analogy | P064 v1 implemented | **9** EF `references_citations`, 0 tool; P064 skipped on both comparison PDFs | **Yes — infra** | Low privacy; **medium FP** if gates too loose | **Selected** |
| Committee approval page v2 | Q013–Q020 partial | P068 v1 | **5** EF `committee_approval_page`, 0 tool on comparison PDFs | Partial | Medium FP; semantic risk (Q015–Q020 manual) | **Deferred** — APPROVAL PAGE gate still 0/2 on comparison set; likely image-only / true absence |
| LoT/LoF/TOC parser follow-up | Q052–Q079 partial | P070 v1 | 4 EF `list_of_tables_figures_toc`, 0 on comparison PDFs | Partial | Medium FP | **Deferred** — comparison PDFs have no detected list pages; text-layer limitation dominates |
| Acknowledgements structural (Q039–Q043) | Q039–Q043 | P043 indentation partial | 2 EF `acknowledgements` | **No — semantic** | High privacy / FP | **Rejected** — content/gratitude semantics |
| Appendix-before-references placement | Weak explicit Q-rule | P042/P063/P064 partial | Low EF signal | Weak basis | Medium FP | **Deferred** — no confirmed guideline hook |
| Equation numbering/layout | Self-Assessment mention only | None | None | **No confirmed Q-rule** | Unknown | **Rejected** |
| Bio Sketch / Approval / Dedication heading recall v2 | Q013, Q021, Q032 | P069 gate | Gate counts unchanged on five-PDF set | Infra | Low | **Deferred** — P069 completed; further recall blocked on this dataset |
| Citation style / Q030 consistency | Q030 | Manual-only | None | **No** | Style semantic | **Manual-only** |

### Selection rationale

P071 is selected because it (a) targets the highest-volume remaining automatable EF gap,
(b) builds on an implemented rule (P064) with documented skip causes on the comparison set,
(c) can be delivered as conservative shared localization without reading reference content,
and (d) does not overlap P070's completed parser track.

---

## 5. Guideline / Q-Rule Basis

### Source files consulted

| File | Relevance |
|---|---|
| `data/raw/guidelines/Self-Self Assessment Sheet.pdf` | References must exist and be consistently formatted (advisor-agreed style) |
| `data/raw/guidelines/Thesis and Dissertation Formatting Guidelines (WIP).docx` | Body-section "References" heading; sequential page numbering through references |
| `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf` | REFERENCES listed in TOC at body level |
| `data/processed/rules/njit_rule_inventory.json` | Q028/Q029 Bio Sketch spacing/indent analogy |
| `docs/evaluation/ef_overlap_after_p068_evaluation.md` | `references_citations` EF gap |
| `docs/evaluation/p064_current_dataset_evaluation.md` | Skip patterns on five-PDF set |
| `docs/evaluation/current_auditor_after_p070_evaluation.md` | Post-P070 aggregate context |
| `src/njit_auditor/rules/pdf_references_citations_structural.py` | P064 implementation |

### Q-rule / basis classification

| Basis item | Paraphrased requirement | Classification for P071 |
|---|---|---|
| Self-Assessment p.4 | References section exists and is internally consistent; style is advisor-dependent | **Automatable (structural)** — P064 checks; P071 improves reach |
| Guidelines para 138 | Body heading "References" (or equivalent) | **Automatable (heading localization)** — P071 back-matter fallback |
| Guidelines para 69 | Page numbers continue through references | **Already covered** by P013/P022 family — out of P071 scope |
| Front Matter Lorem p.9 | REFERENCES in TOC | **Partial** — TOC rules; not P071 primary target |
| Q028 | Bio Sketch publication inter-entry spacing | **Analogy only** — spacing check already in P064 check C |
| Q029 | Bio Sketch hanging indent | **Analogy only** — indent check already in P064 check B |
| Q030 | Consistent citation style in Bio Sketch | **Manual-only** — out of scope |
| Q039–Q043 | Acknowledgements content/layout semantics | **Manual-only** — out of scope |
| Q015–Q020 | Committee rank/order/honorifics | **Manual-only** — out of scope |

No direct Q-rule ID maps exclusively to the main references section; P064 and P071 are
justified via guideline text and Q028/Q029 structural analogy, same as P064 v1.

---

## 6. P071 v1 Scope

### Included (shared PDF text-layer infrastructure)

1. **Collapsed body-start tolerant matching:** extend `_CHAPTER_APPENDIX_RE` (or companion
   helper) to recognize `CHAPTER1`, `CHAPTERI`, `APPENDIXA` patterns where PDF text layers
   collapse inter-token spaces — without matching arbitrary body sentences.
2. **Back-matter references heading fallback:** when `body_start` is None **or** forward scan
   from `body_start` finds no heading, scan the last **N** pages (default: min(30, 25% of
   document)) for a standalone REFERENCES / BIBLIOGRAPHY / WORKS CITED / LITERATURE CITED
   heading using existing `_is_references_heading()` gates.
3. **Robust x-variance gate:** replace raw stdev-on-all-lines skip with cluster-based left
   margin detection — compute variance on the dominant entry-indent cluster only; ignore
   outlier x0 bands consistent with EF annotation sidebars or margin comment boxes.
4. **Annotation-noise line filter (conservative):** optionally exclude lines whose bbox width
   is tiny, whose text is all-caps ≤3 tokens, or whose x0 is far from the entry cluster when
   collecting reference section lines for variance/entry grouping.
5. **Wire refinements into P064** without changing P064 issue-type codes or severity in v1.
6. **Regression guarantee:** when localization resolves to the same section geometry as v1,
   P064 checks B/C must produce identical findings.

### Excluded

- Citation style enforcement (APA, IEEE, ACM, MLA, Chicago)
- Reference entry content reading (authors, titles, DOIs, URLs, years)
- In-text citation marker analysis in body paragraphs
- Completeness checks (every cite has a bibliography entry)
- OCR or image-based reference detection
- New standalone P071 issue types in v1
- Committee approval semantics (P068 track)
- TOC/LoT/LoF entry parsing (P070 track)
- TeX/BibTeX source checks

### Input type

**PDF text layer only** for v1.

### Standalone issue types

**None in v1.** P071 is infrastructure-first. Any new findings appear only through existing
P064 issue types when checks previously skipped now reach the references section.

---

## 7. Detection / Refinement Algorithm

### Step 1 — Body start (enhanced)

1. Try existing `_CHAPTER_APPENDIX_RE` on normalized lines.
2. If no match, try collapsed-token variant: `^(CHAPTER|APPENDIX)([IVXLC\d]+)\b` on
   whitespace-stripped uppercase line text.
3. Require standalone-line gate where available (short line, near page top third) to avoid
   matching inline "Chapter 1 introduces..." prose when possible.
4. Record `body_start_source`: `strict`, `collapsed`, or `none`.

### Step 2 — References heading localization

1. **Primary path:** scan pages `>= body_start` (existing `_find_references_heading`).
2. **Fallback path** (only if primary returns None and `page_count >= 20`):
   - Define `tail_start = max(1, page_count - min(30, ceil(0.25 * page_count)))`.
   - Scan `tail_start..page_count` for first `_is_references_heading` match.
   - Require heading line in upper half of page or standalone short line.
3. If both fail, run existing P064 check A (heading not detected) when body page count gate met.

### Step 3 — Section page collection (unchanged logic)

Reuse `_collect_references_section_pages()` from heading page to next CHAPTER/APPENDIX or EOF.

### Step 4 — Line collection with noise filter

1. Collect lines below heading using existing helpers.
2. Build primary x0 cluster via 1-D clustering (12 pt tolerance); retain cluster with most lines
   longer than `_MIN_ENTRY_LINE_LEN`.
3. For x-variance skip: compute stdev on **cluster lines only**.
4. If cluster stdev ≤ 50 pt (existing threshold), proceed; else skip (unchanged conservative outcome).

### Step 5 — Entry grouping and P064 checks B/C

Unchanged P064 indentation and spacing checks on grouped entries.

### Confidence scoring (internal / evaluation only)

| Signal | Confidence |
|---|---|
| Body start via strict regex | high |
| Body start via collapsed-token regex | medium |
| References heading via forward scan | high |
| References heading via tail fallback | medium |
| Entry cluster stdev within threshold | high |
| Tail fallback with <5 entries | low — checks may still skip |

---

## 8. Finding / Output Fields

P071 emits **no findings** in v1. P064 continues to emit:

| Issue type | When |
|---|---|
| `references_section_heading_not_detected` | Long document, no heading after refined localization |
| `references_entry_indentation_inconsistent` | Mixed hanging-indent pattern (gates met) |
| `references_entry_spacing_inconsistent` | Irregular inter-entry gaps (gates met) |

### Allowed metadata fields (unchanged from P064)

`page`, `issue_type`, `entry_count`, `section_page_count`, `heading_type`, `body_start_page`,
`indent_inconsistency_score`, `spacing_outlier_ratio`, `confidence`

### Explicitly excluded

Reference entry text, author names, titles, DOI/URL strings, citation content, EF comments,
dissertation body prose.

---

## 9. Conservative Skip Conditions

| Condition | Action |
|---|---|
| Document has no text-layer pages | Skip (unchanged) |
| Tail fallback finds heading but <5 entry candidates | Skip checks B/C |
| Multi-column layout detected (≥3 margin clusters) | Skip (unchanged) |
| Cluster stdev still > 50 pt after noise filter | Skip (unchanged) |
| Image-only references pages (no lines) | Skip (unchanged) |
| Heading found only in front-matter region before page 10 without body context | Do not accept via tail fallback |
| Manual citation-style judgment | Never attempted |

---

## 10. False-Positive and False-Negative Risks

### False-positive risks

| Risk | Mitigation |
|---|---|
| Tail scan matches inline "References" in body sentence | `_MAX_HEADING_LEN`, no leading digit, exact keyword match |
| Collapsed CHAPTER regex matches non-heading token | Standalone-line position gate; require near top of page |
| Loosened x-variance includes body paragraphs | Cluster on long lines only; minimum entry length |
| P064 check B/C fires on EF-noisy but structurally odd sections | Keep ≥5 entry and ≥3 multi-line gates |

### False-negative risks

| Risk | Mitigation |
|---|---|
| References heading text not in accepted keyword set | Keep four keywords only in v1 |
| Flattened PDF still lacks text layer | No OCR — documented limitation |
| True absence of references section | Check A still applies for long docs |

---

## 11. Synthetic Test Plan

**12 tests** in `tests/test_p071_references_section_localization_recall.py`:

| # | Scenario |
|---:|---|
| 1 | Strict `CHAPTER 1` body start still detected; P064 behavior unchanged |
| 2 | Collapsed `CHAPTER1` body start detected via P071 helper |
| 3 | Tail fallback finds `BIBLIOGRAPHY` when forward scan from body_start fails |
| 4 | Tail fallback does not match front-matter early-page false heading |
| 5 | Cluster x-variance excludes annotation outlier lines; P064 checks run |
| 6 | High cluster stdev still skips (regression) |
| 7 | Yin-like synthetic: body_start recovered → heading found → entries grouped |
| 8 | Cibaku-like synthetic: noisy side lines ignored; indent/spacing checks reachable |
| 9 | <5 entries after localization → checks B/C skip |
| 10 | Multi-column layout still skips |
| 11 | P064 check A still fires when no heading in long doc |
| 12 | Privacy — findings contain no synthetic reference entry strings |

**Regression:** full suite must remain **988+** pytest; P064 synthetic tests unchanged.

---

## 12. Current-Dataset Evaluation Plan

After implementation:

1. Re-run P064 reach metrics on five-PDF set; report aggregate only in
   `docs/evaluation/p071_references_section_localization_recall_current_dataset_evaluation.md`.
2. Metrics: files where P064 previously skipped now reach checks; P064 finding counts;
   `references_citations` category delta on comparison PDFs; body_start/heading source counts.
3. Compare to P064 baseline: Cibaku skip (x-variance), Yin Haotian/Yin H 2nd skip (body_start).
4. Do **not** quote reference entries or EF comments.
5. Generated outputs under `data/evaluation/generated/p071_evaluation/` (gitignored).

EF-overlap refresh recommended only if comparison PDFs gain `references_citations` findings.

---

## 13. Implementation Checklist

| Item | Path / action |
|---|---|
| Module changes | `src/njit_auditor/rules/pdf_references_citations_structural.py` |
| Optional helper extraction | `references_section_localization.py` only if needed for testability |
| Audit wiring | No `audit_runner.py` change if P064 entry point unchanged |
| Evaluation category | Existing `references_citations` via P064 |
| Metadata | `project_added_rules.json` — add P071 `infrastructure_refinement`, `issue_types: []` |
| Tests | `tests/test_p071_references_section_localization_recall.py` (12 tests) |
| Synthetic validation doc | `docs/evaluation/p071_references_section_localization_recall_synthetic_validation.md` |
| Current-dataset eval doc | After implementation run |
| Status docs | `current_project_state_and_next_steps.md`, manifest refresh |
| Validation | `ruff check .`, `mypy src`, `python -m pytest` |

---

## 14. Recommendation

**Status: implemented (v1).** Scoped PR #255; merged PR #256; post-P071 EF overlap refresh PR #257.

---

## 12. Implementation note (2026-06-08)

P071 v1 implemented in `pdf_references_citations_structural.py`:

1. `_matches_chapter_appendix_heading()` — collapsed `CHAPTER1` / `APPENDIXA` tolerance.
2. `_localize_references_heading()` — forward scan plus tail fallback (min 20 pages, window min(30, 25%)).
3. `_TOC_LEADER_RE` rejection in `_is_references_heading()`.
4. `_cluster_lines_by_x0()` / `_dominant_entry_cluster()` — cluster-based x-variance for skip gate only.
5. `check_pdf_references_citations_structural()` — allows tail path when `body_start` is None on long docs.

**Synthetic validation:** `docs/evaluation/p071_references_section_localization_recall_synthetic_validation.md` (12 tests).

**Current-dataset evaluation:** `docs/evaluation/p071_references_section_localization_recall_current_dataset_evaluation.md` —
P064 reach improved from 2/5 to 5/5 files; aggregate unchanged at 1,543 findings.

**Post-P071 EF overlap:** `docs/evaluation/ef_overlap_after_p071_evaluation.md` — P064 reach on
comparison PDFs 0/2→2/2; `references_citations` EF gap unchanged (9 EF, 0 tool); gap is now
semantic/style/manual-only after localization (Q030 manual-only).

**Do not implement P072** in follow-on polish PRs without a scope doc. Strongest next candidate:
approval-page heading-gate recall (P068 companion).

---

## Cross-references

- P064 scope (implemented): `docs/planning/p064_references_citations_structural_check_scope_and_design.md`
- P064 evaluation: `docs/evaluation/p064_current_dataset_evaluation.md`
- EF overlap: `docs/evaluation/ef_overlap_after_p068_evaluation.md`
- Post-P070 aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md`
- P070 scope (implemented): `docs/planning/p070_toc_lot_lof_entry_parser_recall_refinement_scope_and_design.md`
