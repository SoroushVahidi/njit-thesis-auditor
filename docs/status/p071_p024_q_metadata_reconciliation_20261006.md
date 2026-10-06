# P071/Q030 and P024/Q074 Q-Metadata Reconciliation (2026-10-06)

**Base:** `fix/q-rule-coverage-note-semantics-20261006` at `ead1609`.
Canonical edits: P071 and P024 only. Ester's Q-matrix and detector code are
unchanged.

## P071 / Q030: P071_DOES_NOT_IMPLEMENT_Q030

- Q030 (Ester matrix, Biographical Sketch): "Do all entries in Publications
  and Presentations follow one consistent citation pattern?"
- P071 is References-section localization infrastructure for P064 (no issue
  types, no findings, no citation-style logic).
- The Q030 claim and the note "Q030 remains manual-only" arrived together in
  #256. P071's own design doc
  (`docs/planning/p071_references_section_localization_recall_refinement_scope_and_design.md`)
  lists Q030 as "Manual-only — out of scope". No Ester authority for an
  automated Q030 check exists (P045, P047, P067 design docs also defer it).
- Change: Q030 removed from P071 `source_q_rule_ids`. Q030 now has no
  implementing rule and reports `unimplemented` (the matrix marks it
  automatable).

Not changed here: P071 also lists Q028/Q029, which its design doc calls
"analogy only" (P071/P064 work on the References section, Q028/Q029 on the
Biographical Sketch). After this change Q029 is still covered only by P071.

## P024 / Q074: P024_SHOULD_DECLARE_Q074

- Q074's matrix text says sentence case, but Ester's 2026-10-05 answer
  ("List of Figures have title case and list of Tables have title case ...
  different codes") superseded that reading
  (`docs/status/ester_feedback_round_20261005.md`). The Q074 slot now means
  List of Figures title case, public card R024E.
- P024 implements it: `pdf_toc_list_formatting.py` emits
  `list_of_figures_title_case` with `source_q_rule_id` Q074, and the R024E card
  spec carries Q074. P017's List of Figures sentence-case branch was removed in
  the same round.
- P024 had no structured field, and no Q-IDs in its notes, so coverage
  credited it with nothing. A structured field is authoritative, so it lists
  every Q row the detector emits: Q049, Q050 (TOC levels, public R018A/B),
  Q065 (R024D) and Q074 (R024E).

## Coverage (generated report)

| Q | Before | After |
|---|---|---|
| Q030 | P071, implemented | none, unimplemented |
| Q074 | P070, implemented | P024, P070, implemented |
| Q049, Q050 | P018, P054, P070 | + P024 |
| Q065 | P017, P053, P070 | + P024 |

Summary 64/12/3 → 63/12/4 (implemented/manual/unimplemented).
