# P071 Q028/Q029 Metadata Cleanup (2026-10-06)

**Base:** `fix/p071-p024-q-metadata-reconciliation-20261006` at `933e3e4`.
Canonical edit: P071 `source_q_rule_ids` only. Ester's Q-matrix, P045 and
detector code are unchanged.

## Decision: P071_DOES_NOT_IMPLEMENT_Q028_Q029

| Dimension | P071 | Q028 | Q029 |
|---|---|---|---|
| Section | main References section | Biographical Sketch, Publications and Presentations | same |
| Object | reference-section localization for P064 | entry spacing | entry hanging indent |
| Spacing checked | no (P064 check C does, on References) | yes | — |
| Hanging indent checked | no (P064 check B does, on References) | — | yes |
| Compliance finding | none (`issue_types: []`) | — | — |
| Role | infrastructure refinement | requirement | requirement |

P071's design doc
(`docs/planning/p071_references_section_localization_recall_refinement_scope_and_design.md`)
classifies Q028 and Q029 as "Analogy only" and states that no Q-rule maps to
the main References section. The module labels its basis
"Q028,Q029 analogy". P071 now declares `source_q_rule_ids: []` (same
convention as P064), which also keeps the notes fallback out.

## Resulting coverage

| Q | Before | After |
|---|---|---|
| Q028 | P045, P071, implemented | P045, implemented |
| Q029 | P071, implemented | none, unimplemented |

Summary 63/12/4 → 62/12/5. P045 (`pdf_biosketch_publication_layout.py`)
reports Q028 spacing only: Ester confirmed on 2026-10-05 that a hanging
indent is optional, so the missing-hanging-indent issue type is no longer
emitted. Q029's matrix text is unchanged; whether it should be marked
optional or manual is Ester's data and not decided here.
