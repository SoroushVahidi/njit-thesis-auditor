# Evaluation Data

## Privacy — read this first

**Real dissertations are private and must never be committed as new content, quoted in docs, or
reproduced in tests.** This project's own house rules (`docs/status/evaluation_data_manifest.md`
§6) already say: don't quote dissertation body text anywhere, don't commit raw generated audit
outputs, prefer aggregate counts/page numbers/rule IDs over content in reporting, keep
generated/private material under the gitignored `data/evaluation/generated/` and
`data/evaluation/private/` paths, and **do not make this repository public without a student-data
handling review.**

**Finding from this audit (2026-07-13):** `data/raw/ester/` — real, private dissertation drafts
and reviewer-annotated PDFs/DOCX files with student and reviewer names — is already tracked in
git history. **Independent review note (same day):** of the tracked files under `data/raw/ester/`
plus guidelines/demo binaries covered by `.gitattributes`, only a subset are true Git LFS
*pointer* objects in the tree; several private PDFs/DOCX/ZIP files are stored as **full Git
blobs** (multi‑MB) despite the LFS attribute rules — classic "should have been a pointer, but
wasn't" drift. Filenames themselves often contain student/author personal names. The repository
is currently **private** on GitHub, which is the load-bearing control. This pass did not attempt
to remove or rewrite history (destructive / not authorized). If anyone ever considers making this
repository public, that must trigger the "student-data handling review" the manifest already calls
for, plus a coordinated LFS/history cleanup (see the privacy migration plan in
`docs/status/repository_polish_and_organization_20260713.md`). This is a maintainer/Esther
decision, not an engineering one for this PR.

## Available evaluation sources

### Private (real, EF-reviewed dissertations)

| Sample | Where | Notes |
|---|---|---|
| `ester_sample_a`, `ester_sample_b`, `ester_sample_c`, `ester_sample_d` | `data/evaluation/generated/` (gitignored) and `data/raw/ester/` (tracked; mix of LFS pointers and full blobs — see privacy note above) | Reviewer "Esther Flaim" (EF) — some docs historically misspelled the surname "Farfan"; confirmed as Flaim during a prior forensic pass, see `docs/status/sample_b_annotation_ground_truth_forensics_20260710.md`. |
| Raw EF comment files | `data/raw/ester/*.pdf`, `*.docx` | Native reviewer annotations. Confirmed (2026-07-10 forensic audit) to never leak into any non-P012 detector's findings — only `src/njit_auditor/rules/pdf_annotations.py` calls `page.annots()`; every other rule reads `page.get_text()` only. |
| Raw spreadsheets | `results/ester_feedback_raw/*.xlsx` (untracked, local; entire `/results/` tree is gitignored as of this audit) | Esther's formatting-rules spreadsheet and YES/NO audit-logic matrix. Required by `scripts/ester_rule_consistency_audit.py`; not present in a fresh clone. |

### Synthetic (safe for CI, demos, and the public web UI)

| Sample | Where | Notes |
|---|---|---|
| `clean_minimal.pdf`, `issues_pdf.pdf`, `demo_project.zip` | `tests/fixtures/web_demo/` | Committed synthetic placeholder text (intended as LFS-tracked; some checkout trees currently materialize them as ordinary blobs). Used by the web-demo guide and manual QA checklist. |
| `examples/latex/good_minimal_thesis/`, `examples/latex/bad_minimal_thesis/` | `examples/` | Synthetic TeX fixtures for the CLI `tex` audit demo. |
| Per-rule synthetic PDFs | Generated inline by most `tests/test_*.py` files via `reportlab` | Not checked in as static files; built at test time. |
| Review-label example JSON | `tests/fixtures/review_labels/synthetic_example.json` | Synthetic-only records for `njit_auditor.review_labels` (see `docs/EVALUATION_REVIEW_LABELS.md`). |

### Processed rule specs (not raw student data, safe to read/edit with care)

- `data/specs/ester_q_matrix.json`, `data/specs/ester_p_rule_feedback.json` — Esther's rule
  content, transcribed to JSON. Contains her rule text, not student dissertation content.
- `data/processed/rules/project_added_rules.json`, `njit_rule_inventory.json`,
  `front_matter_rules.json` — this project's internal rule catalog (see
  `docs/RULE_ARCHITECTURE.md`).

## Desired labeling taxonomy for evaluation review

When a human (Esther or a maintainer) reviews auditor output against a real or synthetic sample,
each finding should be labeled with exactly one of the following. This taxonomy did not exist in
a single documented place before this audit — it's collected here so future review passes
(manual or scripted) use consistent labels instead of ad hoc prose judgments.

| Label | Meaning |
|---|---|
| **True positive** | The finding correctly identifies a real formatting problem, at the right location, with correct wording. |
| **False positive** | The finding fires but there is no real problem — the document is actually compliant. |
| **False negative** | A real problem exists but no finding was emitted for it (requires reviewing the document independently of the tool's output). |
| **Correct but too strict** | The finding is technically accurate but flags something that shouldn't be treated as a formatting violation (a policy-tightness question, not a bug). |
| **Wrong location** | The underlying issue is real, but the reported page/position doesn't point at it (or points at the wrong instance of a repeated pattern). |
| **Wrong highlight** | The location/page is right but the drawn highlight box doesn't visually cover the actual offending text/region. |
| **Wrong wording** | The finding is substantively correct but the explanation or remediation text is confusing, inaccurate, or leaks internal detail (e.g. a raw `P###`/`Q###` ID). |
| **Duplicate** | The same real issue is reported more than once (across rules or within one rule) in a way that isn't useful triage grouping. |
| **Policy decision needed** | Whether this is even a violation depends on an NJIT/Esther formatting-policy judgment call this project hasn't resolved yet — do not silently pick an answer; log it (see `docs/status/CURRENT_STATUS.md`'s "Unresolved Esther-policy questions"). |

Existing per-sample review docs (e.g. `docs/status/ester_sample_b_feedback_audit.md`,
`docs/status/warning_actionability_audit_20260622.md`) predate this taxonomy and use free-form
prose labels; they were not retroactively relabeled in this pass. New review passes should use
the table above.

Typed validation for the same vocabulary lives in `njit_auditor.review_labels` and
`docs/EVALUATION_REVIEW_LABELS.md`. It rejects unknown labels and forbids path-like sample IDs.
Using it is optional; labeling the full existing corpus is not required immediately.

## Cross-references

- `docs/status/evaluation_data_manifest.md` — older, more detailed manifest (guideline sources,
  processed rule sources, the Sebastian Fine clean-baseline caveat).
- `docs/status/data_inventory_and_evaluation_sources.md` — older data-category breakdown.
- `docs/sources/ester_materials.md` — catalog of Esther's raw source materials.
- `docs/status/CURRENT_STATUS.md` — which samples are in the current evaluation corpus right now.
