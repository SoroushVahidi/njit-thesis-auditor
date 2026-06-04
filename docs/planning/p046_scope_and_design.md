# P046 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Implemented** (implementation PR — P001–P046 implemented; see `docs/evaluation/p046_lot_lof_entry_number_alignment_synthetic_validation.md`)
- **Baseline main:** `480cd6e` (PR #128 — post-P045 consistency audit; P001–P045 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **45/45** implemented (`P001`–`P045`) |
| Q-rules (updated inventory, post-P045) | **79** total — **2** implemented, **53** partially_implemented, **24** not_implemented (9 manual-only, 15 automatable gaps) |
| LoT/LoF column label presence | **P031** — checks "Table"/"Figure" and "Page" label presence; does NOT check that all entry number columns (Table 1, Table 2…) are left-aligned at a consistent x0 |
| LoT/LoF page number column | **P018** — `misaligned_page_number_column` checks right-edge alignment of page numbers |
| LoT/LoF entry number left-column | **Not yet implemented** — Q068/Q078 remain `not_implemented`; no P-rule checks that all LoT table numbers and LoF figure numbers are left-aligned in a consistent left column |
| Bio Sketch publication hanging indent | **P045** — Q029; implemented |
| Bio Sketch publication entry spacing | **P045** — Q028; implemented |
| Bio Sketch bullet single-spacing | **Not yet implemented** — Q026; deferred from P045 v1 |

**Gap:** P018 checks page number right-column alignment and P031 checks column label presence, but no P-rule checks that the table/figure number column itself (the prefix "Table N" / "Figure N") is left-aligned consistently across all LoT/LoF entries (Q068/Q078).

---

## Candidate comparison

### Candidate 1 — LoT/LoF entry number left-column alignment (Q068, Q078) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q068: all table numbers aligned vertically in one left column; Q078: all figure numbers aligned vertically in one left column |
| **Proposed rule** | **P046** — LoT/LoF entry number left-column alignment check |
| **Module** | `src/njit_auditor/rules/pdf_lot_lof_number_alignment.py` |
| **Issue types** | `lot_entry_number_column_misaligned`, `lof_entry_number_column_misaligned` |
| **Implementation risk** | **Low-medium** — uses existing `detect_toc_like_pages` and `extract_toc_entry_lines` from `pdf_toc_alignment.py`; extracts per-entry x0 and checks variance across LoT/LoF pages; no text reading required |
| **Noise risk** | **Low-medium** — x0 variance check across multiple entries is reliable when ≥3 entries are present; gate: require ≥3 entries; conservative x0-variance threshold |
| **Privacy** | **Low** — findings contain only geometry (entry count, x0 variance, page number); no table/figure title text, author names, or private content |
| **Likely tests** | (1) No LoT/LoF detected → no finding; (2) All entries at consistent x0 → no finding; (3) Entries with varied x0 → misaligned finding; (4) Too few entries (gate) → no finding; (5) Privacy metadata check |
| **Why selected** | Q068/Q078 are the highest-value remaining automatable gaps after P045; extends existing TOC/List infrastructure (detect_toc_like_pages, extract_toc_entry_lines); geometry-only; 2 Q-rules covered; P018 already handles right-column (page numbers), P046 completes with left-column (entry numbers) |

### Candidate 2 — Bio Sketch bullet single-spacing (Q026)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q026: bullet items in education section single-spaced within each bullet |
| **Why not selected** | Deferred from P045 v1 due to ambiguous gap detection — distinguishing within-bullet spacing from between-bullet spacing requires a different multi-threshold grouping approach; will be reconsidered for P047 with improved section detection |

### Candidate 3 — Dedication centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: dedication text block visually centered on the page |
| **Why not selected** | High FP risk — PDF text layer has no reliable centering signal; consistently deferred |

### Candidate 4 — Dedication italic (Q034)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q034: dedication text italicized |
| **Why not selected** | High FP risk — italic metadata unreliable in many PDFs; consistently deferred |

### Candidate 5 — Bio Sketch semantic content (Q023–Q025, Q027, Q030)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q023–Q025: content exclusions; Q027: ordering; Q030: citation style |
| **Why not selected** | All require reading Bio Sketch text content — semantic/NLP checks with high privacy risk |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value | Decision |
|------|-----------|--------|------|-------|----------|
| **1** | **LoT/LoF entry number left-column alignment** | **Q068, Q078** | **Low-med** | **Medium** | **SELECTED** |
| 2 | Bio Sketch bullet single-spacing | Q026 | Medium | Low | Deferred — ambiguous gap detection |
| 3 | Dedication centering | Q033 | High | Low | High FP; defer |
| 4 | Dedication italic | Q034 | High | Low | Metadata unreliable; defer |
| 5 | Bio Sketch semantic content | Q023–Q027/Q030 | High | Low | Semantic/privacy; defer |

---

## Selected P046 scope

### Rule title

**P046 — LoT/LoF entry number left-column alignment check**

### Source basis

- **Q068**: "Are all table numbers aligned vertically in one left column?"
- **Q078**: "Are all figure numbers aligned vertically in one left column?"

### Scope included

1. **LoT/LoF page detection** — use `detect_toc_like_pages` from `pdf_toc_alignment.py` to identify `list_of_tables` and `list_of_figures` pages.
2. **Entry x0 extraction** — use `extract_toc_entry_lines` to get per-entry first-line x0 positions across all LoT/LoF pages.
3. **Gate** — skip if fewer than `MIN_ENTRIES = 3` entries detected (insufficient data for alignment check).
4. **Q068 check** — across all LoT entries: compute x0 variance. If variance exceeds `X0_VARIANCE_THRESHOLD_PT = 6.0pt`, emit `lot_entry_number_column_misaligned`.
5. **Q078 check** — same check applied to all LoF entries: if x0 variance > threshold, emit `lof_entry_number_column_misaligned`.
6. **Privacy-safe findings** — include only: `page_number`, `issue_type`, `entry_count`, `observed_x0_variance_points`, `required_max_variance_points`, `triage_tier`, `source_q_rule_id`. No table title, figure description, or arbitrary text content.

### Scope excluded

- Table/figure title case checks (Q065/Q074) — already covered by P024
- Page number column right-alignment (Q069/Q079) — already covered by P018
- Column label bold/alignment (Q063/Q064/Q072/Q073) — already covered by P031
- Inter-entry spacing (Q067/Q077) — already covered by P036
- Wrapped entry spacing (Q066/Q076) — already covered by P032
- Reading table/figure title text or caption content
- OCR/raster analysis

### Expected module path

`src/njit_auditor/rules/pdf_lot_lof_number_alignment.py`

Imports from:
- `pdf_toc_alignment.py` — `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocPageContext`
- `pdf_models.py` — `PdfDocument`
- `njit_auditor.models` — `AuditFinding`, `Severity`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_lot_lof_number_alignment()` |
| `data/processed/rules/project_added_rules.json` | Add **P046** entry |
| `src/njit_auditor/evaluation.py` | Map P046 → `list_of_tables_figures_toc` category (same as P018, P031, P036) |
| Reports | Standard `AuditFinding` details |

### Expected tests

| Test | Expectation |
|------|-------------|
| No LoT/LoF detected | No P046 finding |
| LoT with consistent x0 across entries | No finding |
| LoT with varied x0 (misaligned) | `lot_entry_number_column_misaligned` (Q068) |
| LoF with varied x0 (misaligned) | `lof_entry_number_column_misaligned` (Q078) |
| Too few entries (gate) | No finding |
| Finding metadata privacy check | No table/figure title text in details |

### Privacy constraints

- Findings contain only: `page_number`, `issue_type`, `entry_count`, `observed_x0_variance_points`, `required_max_variance_points`, `triage_tier`, `source_q_rule_id`.
- No table title, figure description, caption text, or author names.
- Test fixtures use synthetic placeholder entries.

### Acceptance criteria

1. P046 emits `lot_entry_number_column_misaligned` when LoT entries have inconsistent x0 above threshold.
2. P046 emits `lof_entry_number_column_misaligned` when LoF entries have inconsistent x0 above threshold.
3. P046 emits nothing when no LoT/LoF is detected.
4. P046 emits nothing when fewer than MIN_ENTRIES are found.
5. P046 does not duplicate P018 or P031 issue types.
6. CLI runs P046 without changing P001–P045 behavior.
7. All existing 515 tests pass; new P046 synthetic tests added.
8. `project_added_rules.json` lists P046.

### Known false-positive risks

| Risk | Mitigation |
|------|-----------|
| Single-page LoT/LoF with few entries | `MIN_ENTRIES = 3` gate |
| Intentional numbering sub-formats (e.g., appendix table "A-1") | Conservative variance threshold; FP rate expected low for typical NJIT dissertations |
| Compressed/flattened PDFs with unreliable x0 | Same gate as existing TOC checks |

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_lot_lof_number_alignment.py`:
   - Import `detect_toc_like_pages`, `extract_toc_entry_lines` from `pdf_toc_alignment.py`
   - Define `MIN_ENTRIES = 3`, `X0_VARIANCE_THRESHOLD_PT = 6.0`
   - Implement `_collect_entry_x0s(pdf_document, page_type)` → `list[float]`
   - Implement `check_pdf_lot_lof_number_alignment(pdf_document)` → `list[AuditFinding]`
2. Wire in `src/njit_auditor/cli.py`.
3. Add P046 to `data/processed/rules/project_added_rules.json`.
4. Map P046 → `list_of_tables_figures_toc` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests; update `tests/test_rule_inventory.py` to **46** rules.
6. Run full validation.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| P046 synthetics | `python -m pytest tests/test_pdf_rules.py -k p046 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

---

## Privacy notes

- Findings report only geometry — no table/figure title text or caption content.
- Test fixtures use synthetic placeholder entries.
- P046 findings never contain title text, author names, or private content.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON or per-PDF reports.

## Canonical rerun note

Only 4 of 5 evaluation PDFs are directly accessible. Sebastian Fine Revised is ZIP-only.
A canonical five-PDF run is not possible until all five PDFs are mounted or extracted.
