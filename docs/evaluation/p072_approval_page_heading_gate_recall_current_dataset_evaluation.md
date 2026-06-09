# P072 Current-Dataset Evaluation — Approval Page Heading-Gate Recall Refinement

- **Auditor scope:** P001–P072 implemented
- **Baseline commit:** `1476a51` (PR #262 merge — P072 implementation)
- **Evaluation date:** 2026-06-08
- **Validation:** ruff clean, mypy 87 files, **1014 pytest**
- **Generated outputs:** `data/evaluation/generated/p072_evaluation/` (gitignored, not committed)
- **Privacy:** Aggregate detection-mode and finding counts only; no approval-page text, names,
  signatures, dates, or private content quoted

---

## 1. Purpose

Measure the before/after effect of P072's structural localization fallback on P068 reach
across all five evaluation PDFs, and confirm the five-PDF aggregate remains 1,543.

P072 is an infrastructure companion to P068. It adds a structural fallback path:
when `find_gate_matches_for_heading()` returns 0 APPROVAL PAGE matches,
`_find_structural_approval_page_candidate()` scans eligible front-matter/ambiguous pages
for role-label phrase density (≥ `_MIN_ROLE_LABELS = 2`). If exactly 1 candidate is found,
existing P068 structural checks run on it. If 0 or ≥2 candidates: skip.

No new issue types. The only new field is `detected_via` in P068 findings
(`"heading_gate"` or `"structural_fallback"`).

---

## 2. Files Evaluated

| File label | Available | Source | Notes |
|---|---|---|---|
| Cibaku Elson 1st Review | Yes | tracked PDF | EF-comparison PDF; 99 pages |
| Yin Haotian 2nd Review | Yes | tracked PDF | EF-comparison PDF; 108 pages |
| Yin H 2nd Review (flattened) | Yes | tracked PDF | Flattened variant; 108 pages |
| Yin H 4th Review (compressed) | Yes | tracked PDF | Compressed variant; 137 pages |
| Sebastian Fine clean baseline | Yes | extracted from tracked ZIP | 29 pages; clean (no EF feedback) |

All five PDFs evaluated in this run.

---

## 3. P072 Structural Fallback Trace

### Heading gate and structural fallback results per file

| File label | Heading gate matches | Eligible pages w/ text | Role labels found | Structural candidates | Detection mode |
|---|---:|---:|---|---:|---|
| Cibaku Elson 1st Review | 0 | 20 of 20 | 0 on all pages | 0 | skipped — no role labels |
| Yin H 2nd Review (flattened) | 0 | 108 of 108 | 0 on all pages | 0 | skipped — no role labels |
| Yin Haotian 2nd Review | 0 | 108 of 108 | 0 on all pages | 0 | skipped — no role labels |
| Yin H 4th Review (compressed) | 1 | n/a (heading gate fired) | n/a | n/a | heading_gate |
| Sebastian Fine clean baseline | 1 | n/a (heading gate fired) | n/a | n/a | heading_gate |

**Key diagnostic:** On the three non-detecting files, eligible pages return `_mostly_single_token_noise = True`
for all pages and `role_label_count = 0` for all pages. The text extraction layer yields characters
but not word-level role-label phrases. This confirms the approval pages on these PDFs are
image-embedded or otherwise lack a machine-readable text layer — the same root cause documented
in the P072 scope doc.

### Detection mode summary across five PDFs

| Detection mode | File count |
|---|---:|
| heading_gate | 2 |
| structural_fallback (fired) | 0 |
| skipped — 0 role-label candidates | 3 |
| skipped — ambiguous (≥2 candidates) | 0 |
| skipped — sparse text | 0 |

---

## 4. P068 Reach and Finding Counts

### Per-file P068 results

| File label | P068 reached | P068 findings | Issue types observed | detected_via |
|---|---|---:|---|---|
| Cibaku Elson 1st Review | No | 0 | — | — |
| Yin H 2nd Review (flattened) | No | 0 | — | — |
| Yin Haotian 2nd Review | No | 0 | — | — |
| Yin H 4th Review (compressed) | Yes | 1 | `approval_page_signature_blocks_sparse` | heading_gate |
| Sebastian Fine clean baseline | Yes | 2 | `approval_page_advisor_role_label_missing`, `approval_page_signature_blocks_sparse` | heading_gate (both) |

### Comparison: P071 era vs P072 era

| File label | P071 reach | P072 reach | Change |
|---|---|---|---|
| Cibaku Elson 1st Review | No | No | None |
| Yin H 2nd Review (flattened) | No | No | None |
| Yin Haotian 2nd Review | No | No | None |
| Yin H 4th Review (compressed) | Yes (heading) | Yes (heading) | Unchanged |
| Sebastian Fine clean baseline | Yes (heading) | Yes (heading) | Unchanged |

**P068 reach: 2/5 files (unchanged vs P071 era).**

P072 structural fallback returned 0 candidates on all 3 non-reaching files.

---

## 5. Aggregate Impact

**Five-PDF aggregate total: 1,543** (unchanged). P072 is infrastructure-only.

| File label | Findings (P072 era) | Findings (P071 era) | Delta |
|---|---:|---:|---:|
| Cibaku Elson 1st Review | 325 | 325 | 0 |
| Yin H 2nd Review (flattened) | 281 | 281 | 0 |
| Yin Haotian 2nd Review | 346 | 346 | 0 |
| Yin H 4th Review (compressed) | 532 | 532 | 0 |
| Sebastian Fine clean baseline | 59 | 59 | 0 |
| **Total** | **1,543** | **1,543** | **0** |

No separate `current_auditor_after_p072_evaluation.md` is needed.
`docs/evaluation/current_auditor_after_p070_evaluation.md` (1,543 findings) remains canonical.

---

## 6. Root Cause Analysis: Why Structural Fallback Finds No Candidates

On the three non-reaching PDFs (Cibaku 1st, Yin H 2nd flattened, Yin Haotian 2nd), the
structural fallback trace reveals:

- All eligible front-matter/ambiguous pages return `_mostly_single_token_noise = True`
- All pages return `role_label_count = 0` (no recognizable role-label phrases)
- The blocker is not: sparse text (pages have 3–70 usable character-level fragments)
- The blocker is: the approval page approval text is embedded as an image, so PDF text
  extraction returns either nothing or noise-level fragments that do not form role-label
  phrases like "Advisor:", "Co-Advisor:", "Member:", etc.

The structural fallback requires recognizable word-level role-label phrases in the text layer.
Image-only approval pages cannot satisfy this requirement without OCR, which is out of scope.

---

## 7. EF-Overlap Implication

The two EF-comparison PDFs (Cibaku Elson 1st Review, Yin Haotian 2nd Review) remain at:
- **0 tool findings** on `committee_approval_page`
- **5 EF annotations** (unchanged)

A formal EF-overlap refresh after P072 is documented in
`docs/evaluation/ef_overlap_after_p072_evaluation.md`. The `committee_approval_page` gap
is confirmed unchanged: 5 EF, 0 tool.

---

## 8. Interpretation

P072 correctly adds a tested structural fallback path. The fallback finds nothing on the
current comparison PDFs because their approval pages are image-embedded with no extractable
role-label text. This is the **expected and documented** outcome from the P072 scope doc.

P072 adds value for future PDFs: any dissertation with a machine-readable approval page
but absent/variant heading text will benefit from the structural fallback. The `detected_via`
field in P068 findings provides transparency about which path was used.

---

## 9. Limitations

- Image-only approval pages (no machine-readable text) remain undetectable without OCR
- Structural fallback skips when 0 or ≥2 role-label candidates are found (conservative by design)
- `committee_approval_page` EF gap (5 EF, 0 tool) is persistent for this dataset and is
  not a localization failure — the approval page text itself is inaccessible
- `_mostly_single_token_noise` heuristic correctly rejects character-level noise from
  flattened/scanned pages; this is protective but means partial-OCR artifacts also fail
- Localization recall ≠ approval-page compliance; detection only enables P068 structural checks

---

## 10. Generated Outputs

| Path | Contents | Tracked |
|---|---|---|
| `data/evaluation/generated/p072_evaluation/` | 5× JSON + MD audit reports | gitignored |
| `data/evaluation/generated/p072_evaluation/Sebastian.Fine...Revision3.pdf` | extracted clean baseline | gitignored |

Generated outputs are not committed. Do not add them to git.

---

## Cross-References

- P072 scope/design: `docs/planning/p072_approval_page_heading_gate_recall_refinement_scope_and_design.md`
- P072 synthetic validation: `docs/evaluation/p072_approval_page_heading_gate_recall_synthetic_validation.md`
- Canonical five-PDF aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md` (1,543)
- EF-overlap after P072: `docs/evaluation/ef_overlap_after_p072_evaluation.md`
- Prior EF-overlap (P071 era): `docs/evaluation/ef_overlap_after_p071_evaluation.md`
- P068 implementation: `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py`
