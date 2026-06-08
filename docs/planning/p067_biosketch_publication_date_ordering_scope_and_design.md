# P067 Scope and Design — Biographical Sketch Publication Date Ordering

- **P-rule:** P067
- **Date:** 2026-06-08
- **Baseline commit:** `100cac7`
- **Status:** Implemented after scope approval; see `src/njit_auditor/rules/pdf_biosketch_publication_ordering.py`
- **Validation baseline:** 937 pytest, `ruff check .`, `mypy src`

## Implementation Note

This scope was implemented as `src/njit_auditor/rules/pdf_biosketch_publication_ordering.py`
with issue type `biosketch_publication_order_suspicious`. The implementation stayed within
the scoped v1 boundaries: unique Bio Sketch page detection, explicit Publications/
Presentations subsection gating, grouped citation-like entry blocks, representative year-only
ordering checks, and privacy-safe findings. Current-dataset evaluation is documented in
`docs/evaluation/p067_current_dataset_evaluation.md`.

## 1. Motivation

P066 closed the strongest remaining Bio Sketch education-ordering gap (`Q025`), but the
same section still has one privacy-safe, structurally checkable chronology requirement with
no current coverage: `Q027`, which requires publication/presentation entries to appear from
most recent to oldest.

This is the strongest next P067 candidate after the post-P066 backlog audit because it:

- has explicit Q-rule basis in `data/processed/rules/njit_rule_inventory.json`
- avoids semantic content reading and can operate on year integers only
- reuses proven detection surfaces from P045 and P066:
  `BIOGRAPHICAL SKETCH` heading detection, publications-zone detection, line grouping,
  and conservative year extraction
- does not duplicate P045 (layout) or P066 (degree chronology)
- keeps findings privacy-safe: no citation text, titles, author names, or venue names

Backlog-audit note: the Q-rule inventory still lags some recent implementations
(`Q025`, `Q033`, `Q034` remain marked `not_implemented` despite P066/P065). This scope
uses the codebase plus current status docs as the source of truth for actual coverage.

## 2. Why This Candidate Over Others

### Candidate comparison

| Candidate | Basis | Current coverage | Automation fit | Privacy / FP risk | Decision |
|---|---|---|---|---|---|
| **P067 Bio Sketch publication date ordering** | **Q027** | **No current rule** | **Good: year-order heuristic on grouped entries** | **Low privacy, medium FP risk** | **Selected** |
| Committee / approval-page structural completeness refinement | Q013–Q020, EF `committee_approval_page` gap | P025/P038 already cover heading/body presence | Small automatable increment; most remaining gaps are semantic/manual | Medium privacy, high FP risk | Deferred |
| LoT/LoF/TOC extraction-recall improvement | Q052–Q079 partials | Broadly covered by P018/P024/P030–P032/P036/P039/P042/P046/P048–P062 | Real work is parser refinement, not a clean new rule | Low privacy, medium complexity | Defer as refinement, not P067 |
| Appendix/reference placement or appendix content presence follow-up | Q058/Q059, references area | P042, P063, and P064 already cover the safest structural gaps | No clearly isolated new rule remains | Low privacy, low value | Deferred |
| Equation numbering / equation layout | No confirmed repository basis found | No scoped rule | Guideline requirement not confirmed in current sources | Unknown | Rejected |
| References/citations v2 | EF `references_citations` gap | P064 covers heading/indentation/spacing structure | Remaining gaps trend toward citation-style semantics | Low privacy, medium-high FP risk | Deferred |
| P035 image-heavy figure/table detection | Self-Assessment Sheet figure/table layout expectations | P035 text-layer only | Real gap, but best framed as P035 v2 refinement | Low privacy, high complexity | Defer as refinement, not P067 |

## 3. Guideline / Q-rule Basis

### Primary basis

| Source | Rule | Status in repository today | Relevance to P067 |
|---|---|---|---|
| `data/processed/rules/njit_rule_inventory.json` | `Q027` — publications/presentations ordered from most recent to oldest | `not_implemented` in inventory | Primary scope target |
| `docs/planning/p045_scope_and_design.md` | `Q028`/`Q029` publication layout | Implemented as P045 | Reusable publication-zone / grouping context |
| `docs/planning/p066_biosketch_structural_ordering_scope_and_design.md` | `Q025` degree ordering | Implemented as P066 | Reusable year-ordering pattern and privacy model |

### Classification of nearby Bio Sketch rules

| Rule | Current state | P067 relation |
|---|---|---|
| `Q023` no birthplace/date of birth | Manual / semantic | Deferred; out of scope |
| `Q024` no work experience | Manual / semantic | Deferred; out of scope |
| `Q025` degree order | Covered by P066 | Already covered |
| `Q026` bullet single spacing in education section | Covered by P047 | Already covered |
| `Q027` publication/presentation reverse chronology | Uncovered | In scope |
| `Q028` blank line between entries | Covered by P045 | Already covered |
| `Q029` hanging indent | Covered by P045 | Already covered |
| `Q030` consistent citation style | Manual / style-dependent | Deferred; out of scope |

## 4. P067 v1 Scope

### Included

- Input type: **PDF only**
- Section: **Biographical Sketch page only**
- Detect whether grouped publication/presentation entries appear in **non-increasing year order**
  from top to bottom
- Emit a warning only when:
  - a unique `BIOGRAPHICAL SKETCH` heading is detected
  - a publication/presentation subsection boundary is detected
  - at least 3 comparable entry blocks are extractable
  - extracted representative years contain a clear inversion

### Excluded

- Citation style consistency (`Q030`)
- Whether entries are publications versus presentations by content semantics
- Whether an entry is complete or correctly formatted bibliographically
- Any author-name, title, venue, DOI, URL, or prose-content checks
- OCR or image-only PDF handling
- Institution / discipline-specific bibliography conventions

## 5. Detection Algorithm

### Overview

1. Detect a **unique** `BIOGRAPHICAL SKETCH` page using the same heading strategy as P066.
2. On that page, scan lines below the heading to find the first
   `PUBLICATIONS`, `PRESENTATIONS`, or `PUBLICATIONS AND PRESENTATIONS` boundary.
3. Restrict analysis to the zone **below** that boundary and before page-end noise.
4. Reconstruct likely publication-entry blocks using conservative vertical-gap grouping and
   hanging-indent cues adapted from P045.
5. For each grouped entry:
   - normalize whitespace
   - gather 4-digit year tokens in the range used by P066
   - keep the entry only if it yields **exactly one unique representative year**
6. Sort comparable entries by page order and compare the year sequence.
7. If a later entry has a year greater than an earlier one by more than a small tolerance,
   emit one page-level finding.

### Practical details

- Reuse / mirror:
  - P066 unique Bio Sketch heading detection
  - P066 publications-boundary regex
  - P045 line usability filtering and paragraph grouping
- Entry grouping should require one of:
  - a multi-line hanging-indent pattern, or
  - a single long citation-like line with sufficient alpha content
- Candidate blocks with sparse text, page-number-like tokens, or ambiguous geometry are skipped.

### Representative year extraction

- Accept year tokens matching P066’s conservative range (`1960`–`2029`).
- Treat an entry as comparable only if:
  - the grouped block contains at least one year token
  - all detected year tokens collapse to one unique year value
- Skip entries containing multiple distinct years, because those likely indicate:
  page ranges, reprint years, conference/book combinations, or ambiguous citations.

### Ordering rule

- Expected order: **descending**
- Allow equal years (ties) without findings
- Count an inversion when `later_year > earlier_year + 1`
- Emit only when:
  - `comparable_entry_count >= 3`
  - at least one inversion exists

### Confidence

- `high`: 4+ comparable entries and clear publications boundary
- `medium`: 3 comparable entries with one or more inversions
- `low`: not emitted; ambiguous cases should skip rather than warn

## 6. Issue Type

- `biosketch_publication_order_suspicious`

## 7. Finding Fields

### Allowed fields

- `page`
- `issue_type`
- `entry_candidate_count`
- `comparable_entry_count`
- `first_entry_year`
- `last_entry_year`
- `inversion_count`
- `first_inversion_index`
- `expected_order`
- `confidence`
- `triage_tier`
- `source_q_rule_ids`

### Explicitly excluded fields

- publication or presentation text
- author names
- title text
- journal / conference / publisher names
- institution names
- DOI / URL strings
- page ranges copied from citations
- any dissertation body or biographical prose

## 8. Conservative Skip Conditions

- no unique `BIOGRAPHICAL SKETCH` heading detected
- no `PUBLICATIONS` / `PRESENTATIONS` subsection boundary detected
- image-only or text-sparse page
- fewer than 3 comparable grouped entries after filtering
- entries contain multiple distinct years and become too sparse after skipping
- ambiguous grouping caused by compressed / flattened text layer
- suspected multi-column or nonstandard layout
- year tokens appear only in isolated noise lines or page-number-like content

## 9. False-Positive / False-Negative Risks

### False-positive risks

- citation entries with multiple year-like tokens but only one survives parsing incorrectly
- malformed compressed PDFs that collapse unrelated lines into one block
- publication lists where chronology is intentionally grouped by type rather than pure date

### False-negative risks

- image-rendered or flattened Bio Sketch pages
- entries without extractable year tokens
- entries with multiple distinct year tokens that are conservatively skipped
- datasets where the publications heading is absent or merged into another block

### Expected risk profile

- Privacy risk: **low**
- False-positive risk: **moderate**
- Implementation complexity: **moderate**

## 10. Synthetic Test Plan

Target: **12 tests**

1. No Bio Sketch heading → skip
2. Multiple Bio Sketch headings → skip
3. No publications boundary detected → skip
4. Fewer than 3 comparable entries → skip
5. Descending years across entries → no finding
6. Equal adjacent years allowed → no finding
7. Ascending sequence emits finding
8. Single inversion in otherwise descending list emits finding
9. Multi-year entry block skipped without crashing
10. Education-zone lines above publications boundary are excluded
11. Long noisy prose line with year token does not become a comparable entry
12. Privacy test: finding message/details contain no citation text or author/title strings

## 11. Current-Dataset Evaluation Plan

After implementation:

1. Run P067 on the documented five-PDF evaluation set.
2. Write raw outputs only under a gitignored generated path.
3. Report aggregate-only metrics:
   - files where Bio Sketch heading detected
   - files where publications boundary detected
   - files with 3+ comparable entries
   - total P067 findings
4. Do not quote any citation text or publication metadata from real files.

Expected limitation: the same heading/text-layer gate that limited P066 may also limit P067 on
the current dataset.

## 12. Implementation Checklist

- Module: `src/njit_auditor/rules/pdf_biosketch_publication_date_ordering.py`
- Wire into `collect_pdf_layout_findings()` after P066 or adjacent to existing Bio Sketch rules
- Extend `PDF_AUDIT_POST_P054_RULE_IDS` / callable parity tuples or create the next parity range
- Add `P067` entry to `data/processed/rules/project_added_rules.json`
- Update `tests/test_rule_inventory.py`
- Add dedicated synthetic tests: `tests/test_p067_biosketch_publication_date_ordering.py`
- Add evaluation category mapping in `src/njit_auditor/evaluation.py`
- Add synthetic validation doc
- Add current-dataset evaluation doc after implementation
- Update status docs and README
- Validation commands:
  - `python -m pip install -e ".[dev]"`
  - `ruff check .`
  - `mypy src`
  - `python -m pytest`

## 13. Recommendation

**P067 is ready for implementation** as a conservative Q027-only chronology heuristic.

Recommended implementation PR:

- Branch: `rules/p067-biosketch-publication-date-ordering`
- Scope: implement only the year-order check described here
- Do not expand to citation-style or semantic content checks in the same PR

If implementation spikes reveal that publication-entry grouping is too unreliable on
realistic text layers, the fallback should be to keep this document as scope-only and shift the
next effort to a refinement task rather than broadening P067 semantically.
