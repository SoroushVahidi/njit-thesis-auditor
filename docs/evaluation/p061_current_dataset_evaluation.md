# P061 Current-Dataset Evaluation — LoT/LoF Cross-Page Entry-Number Ordering

- **Date:** 2026-06-07
- **Rule:** P061 — LoT/LoF cross-page entry-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_cross_page_entry_ordering.py`
- **Baseline commit:** `82e8361d0fe7e8550c6dbc001855f13bfe822c99` (PR #202 — P061 implementation)
- **Validation at evaluation time:** ruff, mypy, **744 pytest** passed
- **Evaluation scope:** Formal P061-only audit on all five evaluation PDFs (not a canonical five-PDF P001–P061 aggregate rerun)

## Document history

| Phase | PR | What was recorded |
|---|---|---|
| Pre-implementation structural inventory | **#201** (`05f23a1`) | LoT/LoF page-run metadata using P059 parsing helpers; P061 module absent; projected 0 findings |
| P061 implementation | **#202** (`82e8361`) | `pdf_lot_lof_cross_page_entry_ordering.py` wired into CLI/evaluation |
| Formal post-implementation evaluation | **#204** (`8930c88`) | `check_pdf_lot_lof_cross_page_entry_ordering()` on five evaluation PDFs; **0** findings |

## 1. Purpose and scope

Privacy-safe current-dataset evaluation of P061 after implementation. Reporting is
**aggregate/metadata-only** — no entry text, captions, dissertation body text, title text,
author names, or committee names.

Generated outputs under `data/evaluation/generated/p061_evaluation_after_implementation/` were
**not** committed.

## 2. Evaluation PDFs (5 available)

| File label | Access |
|---|---|
| Cibaku Elson 1st review | Tracked standalone PDF |
| Yin H 2nd review (flattened) | Tracked standalone PDF |
| Yin Haotian 2nd review | Tracked standalone PDF |
| Yin H 4th review (compressed) | Tracked standalone PDF |
| Sebastian Fine clean baseline | Extracted locally from tracked ZIP to gitignored `.extracted/` path |

## 3. Formal P061 audit results

Comparable entries and inversions are summed across multi-page LoT and LoF runs per file
(LoT and LoF evaluated separately by P061; totals shown for inventory).

| File label | LoT runs | LoF runs | Comparable entries | Inversions | Formal P061 count | Pages | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Cibaku Elson 1st review | 0 | 0 | 0 | 0 | **0** | — | No LoT/LoF pages detected |
| Yin H 2nd review (flattened) | 0 | 0 | 0 | 0 | **0** | — | No LoT/LoF pages detected |
| Yin Haotian 2nd review | 0 | 0 | 0 | 0 | **0** | — | No LoT/LoF pages detected |
| Yin H 4th review (compressed) | 0 | 1 | 0 (LoT 0 / LoF 0) | 0 (LoT 0 / LoF 0) | **0** | — | One 2-page LoF run (pp. 17–18); insufficient comparable entries |
| Sebastian Fine clean baseline | 0 | 0 | 0 | 0 | **0** | — | Single-page LoT and LoF only — outside P061 scope |

**Formal P061 total:** **0** across five files.

**Issue-type mix:** none (`lot_cross_page_entry_numbers_not_nondecreasing`, `lof_cross_page_entry_numbers_not_nondecreasing` not observed).

## 4. Outcome categories (conservative)

| Category | Files |
|---|---|
| No LoT/LoF pages detected | Cibaku, Yin H 2nd flat, Yin Haotian 2nd |
| LoT/LoF detected but no multi-page same-type run | Sebastian |
| Multi-page run but insufficient comparable entries | Yin H 4th (LoF run; 0 parseable entries under P059 gates) |
| Comparable sequence with inversions below threshold (≥2 required) | **None** |
| P061 findings emitted | **None** |

## 5. Interpretation

- **Does not prove compliance.** Zero findings may mean no qualifying cross-page comparable
  LoT/LoF sequence was found, not verified ordering compliance.
- **Consistent with PR #201 inventory.** Formal P061 audit after PR #202 confirms the same
  structural picture.
- **Usefulness signal is low on this dataset.** Evaluation PDFs provide limited multi-page
  LoT/LoF text-layer extraction; P061’s value is better assessed on documents with dense
  multi-page lists.
- **Noise risk:** No positive findings — empirical false-positive rate not measurable here.

## 6. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035 baseline) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| P061 increment to canonical total | **None** — P061-only local subset, not full P001–P061 rerun |

## 7. Limitations

- Text-layer geometry only; compressed/flattened PDFs may under-detect LoT/LoF pages and entry numbers.
- Sebastian PDF extracted locally; not committed.
- P061-only evaluation — not a full `njit-audit pdf` P001–P061 aggregate rerun.
- No OCR; no entry text in committed docs or gitignored JSON.

## 8. Related docs

- Design: `docs/planning/p061_scope_and_design.md`
- Within-page companion: `docs/evaluation/p059_current_dataset_evaluation.md`
- Synthetic tests: `tests/test_p061_lot_lof_cross_page_entry_ordering.py` (15 tests)
