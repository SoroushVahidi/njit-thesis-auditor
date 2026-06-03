# P039 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Scoped — not yet implemented**
- **Baseline main:** `1f5bc9a` (PR #98 — post-P038 consistency audit; P001–P038 implemented)

---

## Current state

| Area | State |
|------|--------|
| P-rules | **38/38** implemented (`P001`–`P038`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| TOC capitalization | **P024** — L1 ALL CAPS, L2 title case, LoT title case/no-period, LoF sentence case (Q049, Q050, Q065, Q074 partially covered) |
| TOC inter-entry spacing | **P036** — gap-ratio threshold between distinct entries (Q057, Q067, Q077) |
| TOC wrapped-entry spacing | **P032** — intra-entry wrap continuations (Q053–Q055, Q066–Q067, Q076–Q078) |
| TOC continued headings | **P030** — multi-page (Continued) detection (Q048, Q062, Q071) |
| TOC column header labels | **P031** — LoT/LoF "Table"/"Figure"/"Page" label presence (Q063–Q064, Q072–Q073) |
| TOC hierarchy / indentation | **Not implemented** — Q056 completely unaddressed |
| LoF terminal punctuation | **Not implemented** — Q075 completely unaddressed |
| Dedication no-header | **Not implemented** — Q032 completely unaddressed |
| Front-matter heading style | P014 covers bold/centered/all-caps/near-top; P038 covers required presence and phrase variants; no remaining actionable gaps identified |

---

## Candidate comparison

### Candidate 1 — TOC level indentation hierarchy (Q056) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q056: "Are level-2 and level-3 entries indented to show hierarchy?" |
| **Proposed rule** | **P039** — TOC level indentation hierarchy check |
| **Module** | `src/njit_auditor/rules/pdf_toc_entry_hierarchy.py` |
| **Issue types** | `toc_level2_not_indented`, `toc_level3_not_indented` |
| **Implementation risk** | **Medium-low** — reuses `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocEntryLine.indent_x`; requires level classification analogous to P024's `_CHAPTER_RE`/`_LEVEL2_NUM_RE` patterns; gated on having at least one L1 and one L2 entry on the same page |
| **Noise risk** | **Medium** — false positives if single-level TOC (no L2 entries) or if level classification misidentifies entries; conservative gate (require ≥2 L2 entries at insufficient indent before flagging) reduces noise |
| **Privacy** | **Low** — findings contain only geometry (indent coordinates, page number); no entry text, no body text |
| **Likely tests** | (1) L1 at x=72, L2 at x=90 → no finding; (2) L1 and L2 at same indent → `toc_level2_not_indented`; (3) only L1 → no finding; (4) only L2 → no finding; (5) L3 at x=108 relative to L2 at x=90 → no finding; (6) L2 and L3 at same x → `toc_level3_not_indented` |
| **Finding count impact** | Low — most well-formatted theses should show 0; theses where L2 section entries happen to align with L1 chapter entries would show findings |
| **Why selected** | Q056 is completely unimplemented; P024's level classification already identifies which entries are L1/L2/L3 but never enforces that their indent positions are hierarchically ordered; the infrastructure in `pdf_toc_alignment.py` already extracts `indent_x` for every TOC entry; low privacy risk; complements P024 capitalization checks naturally |

### Candidate 2 — LoF terminal punctuation (Q075)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q075: "Does every figure description end with a terminal punctuation mark?" |
| **Proposed rule** | P039 — LoF terminal punctuation check |
| **Module** | Extension of `src/njit_auditor/rules/pdf_toc_list_formatting.py` (P024) or new module |
| **Issue types** | `lof_entry_missing_terminal_punctuation` |
| **Implementation risk** | **Low** — P024 already has `_check_lof_page` and LoF entry parsing; extending to check terminal punctuation is minimal code |
| **Noise risk** | **Medium** — multi-line wrapped LoF entries: only the last wrapped line carries the terminal punctuation; intermediate lines would be false positives unless wrapped-entry grouping is applied (same complication as P032) |
| **Privacy** | **Low** — punctuation check only; no text content in findings |
| **Why not recommended** | (1) Very narrow scope (single Q-rule, single character check); (2) wrapped-entry handling requires P032-style grouping, adding non-trivial complexity; (3) better handled as a P024 refinement than a standalone P-rule; (4) lower value relative to Q056 which covers structural hierarchy |

### Candidate 3 — Dedication page no-header (Q032)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q032: "Is there no header text in the top margin area of the Dedication page?" |
| **Proposed rule** | P039 — Dedication page no-header check |
| **Module** | `src/njit_auditor/rules/pdf_dedication_page.py` (new) |
| **Issue types** | `dedication_header_in_top_margin` |
| **Implementation risk** | **Medium** — analogous to P034 copyright page header check (Q009); DEDICATION page detection uses `_find_heading_first_page("DEDICATION", ...)` from P037 infrastructure; gate: skip if no DEDICATION heading detected |
| **Noise risk** | **Medium** — DEDICATION not in `EXPECTED_HEADINGS`; detection requires verbatim "DEDICATION" text in front-matter text layer; compressed PDFs may miss the heading entirely, resulting in silently skipped checks |
| **Privacy** | **Low** — top margin check only; dedication content is never read or quoted |
| **Why not recommended** | (1) Detection reliability lower than Q056: "DEDICATION" not in `EXPECTED_HEADINGS`, requires separate detection path; (2) optional page means check fires rarely; (3) P034's existing Q009 already validates Copyright page — extending the same pattern to Dedication adds less incremental value than Q056 which covers all TOC pages |

### Candidate 4 — Dedication text centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: "Is the full dedication text block visually centered on the page?" |
| **Implementation risk** | **High** — requires detecting the dedication text block (not the heading), computing block centroid, comparing to page horizontal midpoint; multi-paragraph dedications complicate block detection |
| **Noise risk** | **High** — dedication content can be single lines, multiple paragraphs, or indented blocks; centroid detection unreliable without precise block boundaries |
| **Privacy** | **Medium** — must not read or quote dedication prose; only geometric centroid is checked; but page-level structure detection is harder than heading-level checks |
| **Why not recommended** | High false-positive risk from block detection ambiguity; P038 design doc (Candidate B) also identified this as high-FP; optional section with low incremental value |

### Candidate 5 — P035 image-block body layout refinement

| Field | Detail |
|-------|--------|
| **Source basis** | P035 v1 skips image-only floats; improvement uses PyMuPDF image/vector bbox extraction |
| **Proposed scope** | Add image-body bbox support to `pdf_layout.py`; extend P035 centering check to image-only figure/table pages |
| **Implementation risk** | **High** — requires PyMuPDF image bbox extraction (not currently in `pdf_layout.py`); non-trivial infrastructure change; not a new Q-rule, a refinement of P035 |
| **Noise risk** | **Medium** — image bboxes may not reliably distinguish figure body from decorative images |
| **Privacy** | **Low** — image geometry only |
| **Why not recommended** | Not a new Q-rule (P035 refinement task); infrastructure-heavy; reusable-tooling audit noted deepdoctection as future P035 v2 candidate, but no v2 has been scoped; better addressed as a P035 v2 refinement PR, not a new P039 |

### Candidates from task brief (lower priority)

| Candidate | Q-rule basis | Why deferred |
|-----------|-------------|--------------|
| Front-matter heading style refinement | Unspecified gaps | P014 + P038 together cover presence, phrase, bold, centering, all-caps, near-top; no actionable remaining layout gap identified post-P038 |
| Biographical Sketch content/layout (Q023–Q030) | Q023–Q030 | Semantic parsing (content ordering, degree types, publication formats); high privacy risk; unsuitable for heuristic v1; manual-only per coverage audit |
| Bibliography/reference formatting | No Q-rule in inventory | No NJIT Q-rule basis in `njit_rule_inventory.json`; thesis-compliance reference has hanging-indent checks but we have no NJIT-specific rule to map to |
| Full canonical P001–P038 evaluation rerun | Evaluation maintenance | Evaluation PDFs unavailable in workspace; docs-only task; not an implementation rule |
| YAML/spec abstraction | Infrastructure | Future enhancement after rule set stabilizes; not a Q-rule |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value |
|------|-----------|--------|------|-------|
| **1** | **TOC level indentation hierarchy** | **Q056** | **Medium-low** | **High** |
| 2 | LoF terminal punctuation | Q075 | Low | Medium (narrow) |
| 3 | Dedication no-header | Q032 | Medium | Low (optional, infrequent) |
| 4 | Dedication centering | Q033 | High | Low |
| 5 | P035 image-block refinement | — (P035 v2) | High | Medium |

---

## Selected P039 scope

### Rule title

**P039 — PDF TOC level indentation hierarchy check**

### Source basis

- **Q056**: "Are level-2 and level-3 entries indented to show hierarchy?" (Table of Contents)
- Complements **P024** (which checks capitalization per level but not indentation ordering)

### Scope included

1. **TOC pages only** — apply only to pages classified as `table_of_contents` by `detect_toc_like_pages`.
2. **Level identification** — classify TOC entry lines as L1 (matching `^(?:chapter|appendix)\b` or lowest indent cluster), L2 (matching `^[0-9]+\.[0-9]+(?:\s|$)` or second indent cluster), L3 (matching `^[0-9]+\.[0-9]+\.[0-9]+`).
3. **Indentation check** — for each page with at least one L1 and at least one L2 entry:
   - Compute `l1_median_indent` = median `indent_x` of all L1 entries on the page
   - Compute `l2_median_indent` = median `indent_x` of all L2 entries on the page
   - If `l2_median_indent - l1_median_indent < MIN_HIERARCHY_INDENT_PT` (proposed: 6pt), emit `toc_level2_not_indented`
4. **L3 check** — same logic for L2 vs L3 when both are present. Emit `toc_level3_not_indented`.
5. **One finding per page** per violated level pair — not one per entry.
6. **Gate condition**: require `>= 2` L2 entries before flagging (single L2 may be an ambiguous edge case).
7. **Privacy-safe findings**: report only `page_number`, `issue_type`, `l1_median_indent`, `l2_median_indent`, `entry_count`. No entry text.

### Scope excluded

- LoT and LoF pages — indentation hierarchy in LoT/LoF is not specified by Q056.
- Multi-page TOC continuation pages that lack their own L1 headers — handled by requiring both L1 and L2 entries on the same page.
- Front-matter entries (ABSTRACT, DEDICATION, etc.) that appear in the TOC as L1-equivalent — these may be at the same level as CHAPTER entries by design; the CHAPTER_RE guard handles this.
- Capitalization of levels — owned by **P024** (Q049, Q050).
- Spacing between entries — owned by **P036** (Q057) and **P032** (Q053–Q055).
- LoF terminal punctuation (Q075) — narrow scope; better as a P024 refinement.
- Dedication checks (Q032–Q034) — lower value/higher risk; deferred.

### Expected module path

`src/njit_auditor/rules/pdf_toc_entry_hierarchy.py`

Imports from:
- `pdf_toc_alignment.py` — `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocEntryLine`, `TocPageContext`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Call `check_pdf_toc_entry_hierarchy()` in the PDF audit block after P036 |
| `data/processed/rules/project_added_rules.json` | Add **P039** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P039 → `toc_formatting` category (same as P024/P030/P031/P032/P036) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| L1 at x=72, L2 at x=90 (8pt gap) | No P039 finding |
| L1 at x=72, L2 at x=72 (same indent) | `toc_level2_not_indented` |
| L1 entries only (no L2) | No P039 finding |
| L2 entries only (no L1) | No P039 finding |
| Single L2 entry (below gate threshold) | No P039 finding (gate: require ≥2 L2) |
| L2 at x=90, L3 at x=108 | No P039 finding for L3 |
| L2 at x=90, L3 at x=90 (same) | `toc_level3_not_indented` |
| Finding details privacy-safe | No entry text in details |
| CLI integration | P039 present in JSON output when triggered |

Update `tests/test_rule_inventory.py` count to **39** when implemented.

### Privacy constraints

- Findings include only: `page_number`, `issue_type`, `l1_median_indent` (float), `l2_median_indent` (float), `entry_count` (int), `source_q_rule_id`.
- Do not include entry text, chapter titles, section titles, or any dissertation prose in finding details.
- Test fixtures use synthetic placeholder entry text, not real dissertation content.

### Acceptance criteria

1. P039 emits `toc_level2_not_indented` when L2 TOC entries are not indented relative to L1 entries.
2. P039 emits `toc_level3_not_indented` when L3 TOC entries are not indented relative to L2 entries.
3. P039 does not fire when only L1 entries are present.
4. P039 does not fire when only L2 entries are present.
5. P039 does not fire when fewer than 2 L2 entries exist on the page (conservative gate).
6. P039 does not duplicate P024 issue types (capitalization).
7. CLI runs P039 on `njit-audit pdf` without changing P001–P038 behavior.
8. All existing 456 tests pass; new P039 synthetic tests added.
9. `project_added_rules.json` lists P039 (implementation PR only).

### Known false-positive risks

- **Single-level TOC**: some dissertations have only chapter-level L1 entries with no numbered subsection L2 entries. Gate condition (require L1 + L2 both present) eliminates this.
- **Front-matter L1 entries misclassified**: entries like "ABSTRACT" or "TABLE OF CONTENTS" at different indents from CHAPTER entries could skew L1 median. Mitigate by anchoring L1 median to `CHAPTER_RE`-matched entries when available.
- **Multi-page TOC**: later pages may have only L2/L3 entries. Require both L1 and L2 on the same page to compare; skip pages without both.
- **Compressed PDFs**: coordinate extraction may be unreliable. The conservative `MIN_HIERARCHY_INDENT_PT = 6pt` threshold reduces noise from coordinate compression artifacts.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p039/` and add
`docs/evaluation/p039_current_dataset_evaluation.md` with aggregate P039 counts only.

Do **not** commit generated JSON/MD outputs. Do **not** update `generated_for_commit` or
the pre-P035/P036/P037/P038 canonical **1,446** aggregate until a documented full P001–P039 rerun.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_toc_entry_hierarchy.py`:
   - Import `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocEntryLine`, `TocPageContext` from `pdf_toc_alignment.py`
   - Define `MIN_HIERARCHY_INDENT_PT = 6.0` (minimum indent difference for hierarchy to be present)
   - Define `MIN_L2_ENTRIES_TO_CHECK = 2` (gate threshold)
   - Implement level classification using `_CHAPTER_RE`, `_LEVEL2_NUM_RE`, `_LEVEL3_NUM_RE` patterns (same as P024)
   - Implement `_check_toc_hierarchy_page(context, entries) -> list[AuditFinding]`
   - Implement `check_pdf_toc_entry_hierarchy(pdf_document) -> list[AuditFinding]`
2. Wire CLI in `src/njit_auditor/cli.py` after P036 call.
3. Add P039 entry to `data/processed/rules/project_added_rules.json`.
4. Map P039 → `toc_formatting` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests in `tests/test_pdf_rules.py`; update `tests/test_rule_inventory.py` to 39 rules.
6. Run full validation (`ruff check .`, `mypy src`, `python -m pytest`).
7. Optional: local evaluation doc (aggregate only, gitignored outputs).

No changes to P001–P038 detector behavior in the scoping PR.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory (post-impl) | `python -m pytest tests/test_rule_inventory.py -q` |
| P039 synthetics | `python -m pytest tests/test_pdf_rules.py -k p039 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

Scoping PR (this document): `python -m pytest tests/test_rule_inventory.py -q` minimum.

---

## Privacy notes

- Design and evaluation docs must remain aggregate and metadata-only.
- Test fixtures use synthetic placeholder chapter/section titles, not real dissertation content.
- P039 findings report only geometric measurements (indent coordinates, entry counts) — no entry title text, no section body, no author names.
- `toc_level2_not_indented` and `toc_level3_not_indented` findings never contain dissertation prose.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON, per-PDF reports, or regenerated full-audit bundles from local runs.
