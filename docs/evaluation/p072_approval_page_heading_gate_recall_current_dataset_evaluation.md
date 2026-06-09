# P072 Current-Dataset Evaluation — Approval Page Heading-Gate Recall Refinement

- **Auditor scope:** P001–P072 implemented
- **Baseline commit:** `045e93b` (P072 scoped; PR #261); implementation commit: see PR #262
- **Evaluation date:** 2026-06-08
- **Privacy:** Aggregate detection-mode and finding counts only; no approval-page text, names,
  signatures, dates, or private content quoted

---

## 1. Purpose

Measure the before/after effect of P072's structural localization fallback on P068 reach
across the four directly accessible evaluation PDFs. Sebastian Fine (ZIP-only) is noted but
not evaluated here.

---

## 2. Files Evaluated

| File label | Available | Notes |
|---|---|---|
| Cibaku Elson 1st Review | Yes | EF-comparison PDF |
| Yin Haotian 2nd Review | Yes | EF-comparison PDF |
| Yin H 2nd Review (flattened) | Yes | Flattened variant |
| Yin H 4th Review (compressed) | Yes | Compressed variant |
| Sebastian Fine clean baseline | No (ZIP-only) | Not evaluated in this run |

---

## 3. Results

### Post-P072 detection mode per file

| File label | Heading gate matches | Detection mode | P068 page reached | P068 findings |
|---|---|---|---|---|
| Cibaku Elson 1st Review | 0 | skipped — no candidate | No | 0 |
| Yin Haotian 2nd Review | 0 | skipped — no candidate | No | 0 |
| Yin H 2nd Review (flattened) | 0 | skipped — no candidate | No | 0 |
| Yin H 4th Review (compressed) | 1 | heading_gate | Yes | 1 |

### Comparison: pre-P072 (P069/P071 era) vs post-P072

| File label | Pre-P072 reach | Post-P072 reach | Change |
|---|---|---|---|
| Cibaku Elson 1st Review | No | No | None |
| Yin Haotian 2nd Review | No | No | None |
| Yin H 2nd Review (flattened) | No | No | None |
| Yin H 4th Review (compressed) | Yes (heading) | Yes (heading) | Unchanged |
| Sebastian Fine (ZIP) | Yes (heading, P069 era) | Expected unchanged | Not re-run |

**P068 reach: 1/4 files evaluated (unchanged vs P069/P071 era on these 4 files).**

P072 structural fallback returned 0 candidates on all 3 non-reaching files. This confirms the
scope limitation: the approval pages in Cibaku, Yin Haotian 2nd Review, and Yin H 2nd Review
(flattened) have no machine-readable role-label text. The structural fallback requires at least
`_MIN_ROLE_LABELS = 2` role-label phrases in the text layer — which are absent, confirming
these pages are likely fully image-scanned or otherwise have absent text layers.

---

## 4. Aggregate Impact

**Five-PDF aggregate total: 1,543** (unchanged). P072 is infrastructure-only. On the evaluated
files, P068 firing count remains 1 (Yin H 4th Review compressed: 1 finding
`approval_page_signature_blocks_sparse`). No new findings were added by the structural
fallback on this dataset.

No separate `current_auditor_after_p072_evaluation.md` is needed because the aggregate is
unchanged. `docs/evaluation/current_auditor_after_p070_evaluation.md` (1,543 findings)
remains canonical.

---

## 5. EF-Overlap Expectation

The two EF-comparison PDFs (Cibaku Elson 1st Review, Yin Haotian 2nd Review) remain at:
- **0 tool findings** on `committee_approval_page`
- **5 EF annotations** (unchanged)

No EF-overlap refresh is needed because the comparison-PDF tool finding counts did not change.
`docs/evaluation/ef_overlap_after_p071_evaluation.md` remains the canonical EF overlap doc.

---

## 6. Interpretation

P072 correctly adds a structural fallback path that is tested and ready. The fallback finds
nothing on the current comparison PDFs because their approval pages are fully image-only or
have no extractable role-label text. This is the **expected and documented** outcome from the
P072 scope doc.

P072 is still valuable because:
1. Future PDFs with machine-readable approval pages but absent/malformed heading text will
   benefit from the structural fallback
2. The implementation is tested (14 synthetic tests), conservative (skip gates), and
   privacy-safe
3. The `detected_via` diagnostic field provides transparency about which localization path
   was used

---

## 7. Limitations

- Sebastian Fine (ZIP-only) not evaluated here; from P069 evaluation it was reached via
  heading gate and is not expected to change
- Image-only approval pages (no machine-readable text) remain undetectable without OCR
- Structural fallback skips when 0 or ≥2 role-label candidates are found
- `committee_approval_page` EF gap (5 EF, 0 tool) is confirmed as persistent for this dataset
