# P045 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Implemented** (implementation PR — P001–P045 implemented; see `docs/evaluation/p045_biosketch_publication_layout_synthetic_validation.md`)
- **Baseline main:** `9b1fed3` (PR #124 — tmux CLI test robustness; P001–P044 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **44/44** implemented (`P001`–`P044`) |
| Q-rules (updated inventory, post-P044 audit) | **79** total — **2** implemented, **51** partially_implemented, **26** not_implemented (9 manual-only, 17 automatable gaps; see `docs/status/q_rule_coverage_after_p044.md`) |
| Bio Sketch heading presence | **P038** — "BIOGRAPHICAL SKETCH" phrase detected |
| Bio Sketch Roman numeral | **P037** — Section-anchor value check |
| Bio Sketch publication layout | **Not yet implemented** — Q026/Q028/Q029 are `not_implemented`; no P-rule checks hanging indent, inter-entry spacing, or internal bullet spacing on the Bio Sketch page |
| Abstract indentation | **P044** — Q002/Q003; directly analogous page-scoped check |
| Acknowledgements indentation | **P043** — Q044/Q045 |

**Gap:** The Bio Sketch page has no layout checks for the Publications/Presentations section. NJIT guidelines require:
- Q029: Publication entries use hanging indent (first line flush-left; continuation lines indented)
- Q028: Publication entries are single-spaced internally with a blank line between entries
- Q026: Education bullet items are single-spaced within each bullet

These are geometry checks that do not require reading publication text, citation content, or any private Bio Sketch prose.

---

## Candidate comparison

### Candidate 1 — Bio Sketch publication/entry layout (Q026, Q028, Q029) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q029: publication entries use hanging indent; Q028: entries single-spaced + blank line between; Q026: education bullet items single-spaced within each bullet |
| **Proposed rule** | **P045** — Bio Sketch publication paragraph layout check |
| **Module** | `src/njit_auditor/rules/pdf_biosketch_publication_layout.py` |
| **Issue types** | `biosketch_publication_missing_hanging_indent`, `biosketch_publication_entry_spacing_not_double`, `biosketch_publication_wrapped_line_spacing_not_single` |
| **Implementation risk** | **Medium** — Bio Sketch page has multiple sub-sections; detecting publication blocks without reading text requires classifying multi-line blocks by their indentation pattern rather than by content; more complex than P043/P044 |
| **Noise risk** | **Medium** — Hanging indent is reliably detectable from geometry alone; inter-entry spacing check is noisier because sub-section boundaries are invisible without text; gate: require ≥2 multi-line blocks before reporting |
| **Privacy** | **Low** — findings contain geometry only: page number, block index, observed x0 values, line gap measurements; no publication title, author name, citation text, or any Bio Sketch prose |
| **Likely tests** | (1) No BIOGRAPHICAL SKETCH page → no finding; (2) Correct hanging indent and spacing → no finding; (3) Missing hanging indent → biosketch_publication_missing_hanging_indent; (4) Flat (flush-left) continuation lines where hanging indent expected → Q029 finding; (5) Insufficient gap between entries → Q028 finding; (6) Finding privacy check — no text in details; (7) CLI integration |
| **Why selected** | Q029/Q028/Q026 are the highest-value remaining automatable geometry checks; Bio Sketch page is always present in NJIT dissertations; BIOGRAPHICAL SKETCH is in EXPECTED_HEADINGS (reliable detection); geometry-only approach is privacy-safe; extends the heading-detection → line-grouping → geometry-check pattern established by P043/P044 |

### Candidate 2 — TOC/LoT/LoF column number alignment (Q068, Q078)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q068: table numbers aligned in left column; Q078: figure numbers aligned in left column |
| **Why not selected** | Extends P018 (TOC alignment); moderate value (2 Q-rules); P018 already checks page-number right-column alignment; number-column left-alignment is a narrower gap; P045 Bio Sketch covers more Q-rules with higher value |

### Candidate 3 — Dedication centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: dedication text block visually centered on the page |
| **Why not selected** | High FP risk — PDF text layer has no reliable centering signal; centering detection would require comparing text block extents to page width, which varies with text length; deferred every prior cycle |

### Candidate 4 — Dedication italic (Q034)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q034: dedication text italicized if Latin alphabet |
| **Why not selected** | High FP risk — italic metadata is unreliable in many PDFs (missing, embedded incorrectly, or font-name-based which is inconsistent); deferred every prior cycle |

### Candidate 5 — Bio Sketch content ordering (Q024, Q025, Q027)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q024: no work experience; Q025: degrees most-recent-first; Q027: publications most-recent-first |
| **Why not selected** | Requires reading Bio Sketch text content (work experience detection, degree date ordering, publication date ordering) — semantic/NLP checks with high privacy risk; no reliable geometry-only approach |

### Candidate 6 — Bio Sketch birth/current info (Q023)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q023: Bio Sketch excludes place of birth and date of birth |
| **Why not selected** | Requires reading content to detect birthplace/date keywords — high privacy risk; manual/semantic check |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value | Decision |
|------|-----------|--------|------|-------|----------|
| **1** | **Bio Sketch publication layout** | **Q026, Q028, Q029** | **Medium** | **High** | **SELECTED** |
| 2 | TOC/LoT/LoF column alignment | Q068, Q078 | Low-med | Low | Defer |
| 3 | Dedication centering | Q033 | High | Low | High FP risk; defer |
| 4 | Dedication italic | Q034 | High | Low | Metadata unreliable; defer |
| 5 | Bio Sketch ordering | Q024/Q025/Q027 | High | Low | Semantic/privacy; defer |
| 6 | Bio Sketch birth info | Q023 | High | Low | Semantic/privacy; defer |

---

## Selected P045 scope

### Rule title

**P045 — PDF Biographical Sketch publication paragraph layout check**

### Source basis

- **Q029**: "Do all entries in 'Publications and Presentations' use a hanging indent?"
- **Q028**: "Is each entry in 'Publications and Presentations' single-spaced with a blank line between entries?"
- **Q026**: "Are the bullet items in the education section single-spaced within each bullet?" (secondary; same spacing gate)

### Scope included

1. **Bio Sketch page detection** — use `find_named_frontmatter_headings` (from `pdf_headings.py`) to locate pages with a "BIOGRAPHICAL SKETCH" heading. If not detected, emit nothing.
2. **Multi-line block extraction** — collect text line groups below the heading, grouped by vertical gap (same `MAX_PARA_GAP_PT = 14.0` as P043/P044). Filter short lines, page-number candidates, and low-alpha content.
3. **Hanging indent classification** — for each block with ≥2 lines: compare first-line x0 (`first_x0`) with the median x0 of continuation lines (`rest_x0`). If `rest_x0 - first_x0 >= HANGING_THRESHOLD_PT` (default: 12pt), the block has a hanging indent.
4. **Q029 check** — if ≥ `MIN_HANGING_BLOCKS = 2` multi-line blocks exist and none have a hanging indent, emit `biosketch_publication_missing_hanging_indent`. This flags the complete absence of hanging indent on the Bio Sketch page.
5. **Q028 check** — among consecutive block pairs classified as hanging-indent blocks: check that the vertical gap between the last line of block N and the first line of block N+1 is ≥ `ENTRY_GAP_THRESHOLD_PT` (approximately double-spacing). If the gap is below the threshold, emit `biosketch_publication_entry_spacing_not_double`.
6. **Q026 check (within-block single-spacing)** — for each hanging-indent block: check that all internal line gaps are ≤ `SINGLE_LINE_GAP_PT` (approximately single-spacing). If an unusually large gap is found within a block, emit `biosketch_publication_wrapped_line_spacing_not_single`.
7. **Gates** — skip all checks if BIOGRAPHICAL SKETCH heading is absent. Skip Q028/Q026 if fewer than `MIN_HANGING_BLOCKS` hanging-indent blocks are found (insufficient data to establish the section style).
8. **Privacy-safe findings** — include only: `page_number`, `issue_type`, `block_index`, `observed_first_x0`, `observed_rest_x0`, `hanging_delta_points`, `required_hanging_points` (for Q029), or gap measurements (for Q028/Q026). No Bio Sketch text, publication title, author name, citation content, or arbitrary extracted text.

### Scope excluded

- Birth/current info content checks (Q023) — requires reading private text
- Degree/work/publication ordering (Q024/Q025/Q027) — semantic; privacy risk
- Citation format/style checks (Q030) — semantic
- Academic degree parsing or date extraction
- OCR/raster analysis
- Reading any text content from Bio Sketch paragraphs
- Broad rewrite of P015 (general indentation) or P016 (spacing)

### Expected module path

`src/njit_auditor/rules/pdf_biosketch_publication_layout.py`

Imports from:
- `pdf_headings.py` — `find_named_frontmatter_headings`, `normalize_heading_text`
- `pdf_models.py` — `PdfDocument`, `PdfPage`, `PdfTextLine`
- `njit_auditor.models` — `AuditFinding`, `Severity`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_biosketch_publication_layout()` after `check_pdf_abstract_indentation` (P044) |
| `data/processed/rules/project_added_rules.json` | Add **P045** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P045 → `indentation` category (closest match; hanging indent is primary check) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| No BIOGRAPHICAL SKETCH heading detected | No P045 finding |
| Bio Sketch with correct hanging indent + double inter-entry spacing | No P045 finding |
| Bio Sketch where all multi-line blocks are flush (no hanging indent) | `biosketch_publication_missing_hanging_indent` (Q029) |
| Bio Sketch with hanging indent but insufficient inter-entry gap | `biosketch_publication_entry_spacing_not_double` (Q028) |
| Bio Sketch with only one multi-line block (gate) | No Q028/Q029 finding (insufficient blocks) |
| Finding metadata privacy check | No Bio Sketch text or citation content in finding details |
| CLI integration | P045 in JSON output when triggered |

Update `tests/test_rule_inventory.py` count from **44** to **45** when implemented.

### Privacy constraints

- Findings contain only: `page_number`, `issue_type`, `block_index`, `observed_first_x0`, `observed_rest_x0`, `hanging_delta_points`, `required_hanging_points`, `triage_tier`, `source_q_rule_ids`.
- No Bio Sketch paragraph text, no publication titles, no author names, no citation text, no degree information, no dates.
- Test fixtures use synthetic placeholder content.

### Acceptance criteria

1. P045 emits `biosketch_publication_missing_hanging_indent` when no multi-line blocks on the Bio Sketch page have hanging indent, and ≥ MIN_HANGING_BLOCKS multi-line blocks exist.
2. P045 emits `biosketch_publication_entry_spacing_not_double` when consecutive hanging-indent blocks have insufficient inter-entry gap.
3. P045 emits nothing when no BIOGRAPHICAL SKETCH page is detected (gate).
4. P045 emits nothing when insufficient multi-line blocks are found (gate).
5. P045 does not duplicate P043, P044, or P015 issue types.
6. CLI runs P045 without changing P001–P044 behavior.
7. All existing 507 tests pass; new P045 synthetic tests added.
8. `project_added_rules.json` lists P045 (implementation PR only).

### Known false-positive risks

| Risk | Mitigation |
|------|-----------|
| Bio Sketch sections with no publications (single-entry or education-only) | `MIN_HANGING_BLOCKS = 2` gate — require ≥2 multi-line blocks before reporting |
| Short paragraphs misclassified as hanging-indent blocks | `HANGING_THRESHOLD_PT = 12pt` and `MIN_TEXT_LEN = 20` filters |
| BIOGRAPHICAL SKETCH heading absent in compressed/flattened PDFs | Gate silently skips |
| Variation in publication formatting across disciplines | Conservative thresholds; emit only on clear violations |

### Local evaluation rerun (not committed)

After implementation, run five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p045/` when all five PDFs are accessible.
Add `docs/evaluation/p045_current_dataset_evaluation.md` with aggregate P045 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the
pre-P035/.../P044 canonical **1,446** aggregate.

**Canonical rerun blocker:** Only 4 of 5 evaluation PDFs are directly accessible. Sebastian
Fine Revised is ZIP-only. A canonical five-PDF run is not possible until all five PDFs are
mounted or extracted.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_biosketch_publication_layout.py`:
   - Import `find_named_frontmatter_headings`, `normalize_heading_text` from `pdf_headings.py`
   - Define constants: `HANGING_THRESHOLD_PT = 12.0`, `MAX_PARA_GAP_PT = 14.0`, `ENTRY_GAP_THRESHOLD_PT = 18.0`, `MIN_HANGING_BLOCKS = 2`, `MIN_TEXT_LEN = 20`, `SINGLE_LINE_GAP_PT = 16.0`
   - Implement `_find_biosketch_page_and_heading_y(pdf_document)` → `tuple[PdfPage, float] | None`
   - Implement `_lines_below_heading(page, heading_bottom_y)` → `list[PdfTextLine]`
   - Implement `_group_blocks(lines)` → `list[list[PdfTextLine]]`
   - Implement `_has_hanging_indent(block)` → `bool` (checks first_x0 < rest_median_x0 - HANGING_THRESHOLD_PT)
   - Implement `check_pdf_biosketch_publication_layout(pdf_document)` → `list[AuditFinding]`
2. Wire in `src/njit_auditor/cli.py` after `check_pdf_abstract_indentation` (P044).
3. Add P045 entry to `data/processed/rules/project_added_rules.json`.
4. Map P045 → `indentation` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests; update `tests/test_rule_inventory.py` to **45** rules.
6. Run full validation: `ruff check .`, `mypy src`, `python -m pytest`.

No changes to P001–P044 detector behavior.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| P045 synthetics | `python -m pytest tests/test_pdf_rules.py -k p045 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

---

## Privacy notes

- Findings report only geometry — no Bio Sketch text, publication titles, citation content.
- Test fixtures use synthetic placeholder biographical text.
- P045 findings never contain author names, degree information, advisor names, or institution names.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON or per-PDF reports.
