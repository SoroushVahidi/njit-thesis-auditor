# Evaluation data and privacy

Use generated synthetic fixtures for hosted CI and public demonstrations.
Student manuscripts, reviewer annotations, real audit outputs, and case-level
evidence require explicit use authorization and approved restricted storage.
Visibility of a Git path or an LFS pointer does not authorize access, retrieval,
or redistribution. Keep LFS smudging disabled for routine development and CI.

Use the website's approved sample surface or construct a synthetic fixture for
a public example. Private replays must document authorization and distinguish
an exact original-case result from a verified excerpt or a synthetic control.
Maintain the exact source and test scope in the restricted evidence index.

Checked-in processed specifications and rule data are application and build
inputs. Keep them versioned with the implementation and validate behavior
before changing them.

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
- `docs/REPRODUCIBILITY.md` — setup, CI boundaries, and private validation prerequisites.
