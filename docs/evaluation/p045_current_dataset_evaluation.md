# P045 Current Dataset Evaluation

- **Date:** 2026-06-03
- **Rule:** P045 — Biographical Sketch publication paragraph layout (Q028/Q029)
- **Status:** **No canonical audit run** — only 4 of 5 evaluation PDFs are directly accessible; Sebastian Fine Revised is ZIP-only
- **Baseline main at implementation:** `6fa22df` (PR #126)

---

## Evaluation status

No P045 current-dataset finding counts are available. A canonical five-PDF run requires all
five evaluation PDFs to be directly accessible. At the time of implementation:

- 4 PDFs are directly accessible in `data/raw/ester/`
- The fifth (Sebastian Fine Revised) is archive-contained in
  `Dissertations with no Feedback -20260529T012213Z-3-001.zip` and not committed as a
  standalone tracked file

**What was validated:**

- 8 synthetic unit tests covering the P045 gate conditions, Q028/Q029 issue types, correct
  format (no findings), hanging indent detection, inter-entry spacing, finding metadata
  privacy. All pass.
- `ruff check .` — clean
- `mypy src` — clean (59 source files)
- `python -m pytest` — **515 passed**

---

## Canonical aggregate baseline (unchanged)

| Field | Value |
|-------|-------|
| Canonical pre-P035/…/P045 five-PDF aggregate | **1,446** total findings |
| `generated_for_commit` | `00b9c2d` |
| Canonical eval doc | `docs/evaluation/current_auditor_after_p034_evaluation.md` |

P045 does not alter the canonical 1,446 baseline.

---

## P045 v1 limitations

| Limitation | Detail |
|-----------|--------|
| Heading detection gate | Emits nothing if BIOGRAPHICAL SKETCH heading absent (flattened/compressed PDFs) |
| Multi-line block gate | Emits nothing if fewer than 2 multi-line blocks detected |
| Q029 approach | Checks for complete absence of hanging indent; does not flag individual non-compliant entries |
| Q028 approach | Checks only consecutive hanging-indent block pairs; single-entry Bio Sketches not checked |
| Q026 deferred | Within-entry spacing deferred to v2 — ambiguous with single gap threshold |
| Multi-page Bio Sketch | Only the first Bio Sketch page is checked |

---

## Future canonical rerun

When all five evaluation PDFs are directly accessible:

1. Run `njit-audit pdf` on the five canonical evaluation PDFs.
2. Collect P045 aggregate counts only (no per-PDF biographical text).
3. Save outputs to `data/evaluation/generated/current_auditor_after_p045/` (gitignored).
4. Add a summary of aggregate P045 counts to this doc.
5. Do **not** update `generated_for_commit` unless the run is complete and validated.

---

## Privacy

Findings from P045 contain geometry metadata only:
`page_number`, `issue_type`, `multi_line_block_count`, `entry_index`, `observed_gap_points`,
`required_gap_points`, `hanging_indent_threshold_points`, `triage_tier`, `source_q_rule_id`.
No Biographical Sketch text, publication titles, author names, citation content, or private
student information is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/`.
