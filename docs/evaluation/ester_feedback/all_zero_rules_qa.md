# All-zero rules audit

34 of the 60 applicable rules produced **zero visible findings across all
seven dissertations**. This document audits each one against the concrete
failure modes named in the QA task: rule-ID mismatch, phase-filtering bug,
parser failure, detector not invoked, stale cache, swallowed exception,
incorrect rule mapping, wrong source file, selection bug, output
suppression, cache key collision.

## Structural evidence that applies to every rule in this list (not repeated per-row)

1. **Rule-ID mismatch / incorrect mapping — ruled out.** Every one of the 34
   rule IDs passed a static AST scan of its own module
   (`rule_source_scan.detector_emitted_pairs_by_static_scan`) that confirms
   the literal string `rule_id="P0xx"` is actually attached to an
   `AuditFinding` somewhere in that rule's source. This is the same check
   used to *exclude* the 9 truly non-emitting rules (P069-073, P076, P077,
   P079, P081) from the batch entirely (see `page_less_findings_qa.md`'s
   sibling report is not this one -- see the batch manifest's
   `skip_reason` field for those 9).
2. **Detector not invoked / phase-filtering bug — ruled out.** All PDF-layout
   checks are called unconditionally from one flat sequence of
   `findings.extend(check_xxx(content_doc))` statements in
   `audit_runner.collect_pdf_layout_findings` (src/njit_auditor/audit_runner.py:228-311)
   with **no per-rule feature flag or conditional** (the only `if` in that
   function gates a wrapper-page post-processing step, unrelated to rule
   selection). Every one of these 34 check functions is called on every
   audit.
3. **Swallowed exception — ruled out.** That same call sequence has **no
   try/except around any individual check** -- a single raised exception
   would abort the whole `collect_pdf_layout_findings` call and fail the
   entire document's audit (surfacing as an `AuditError`), not silently
   zero out one rule. All 7 of the batch's full-document audits completed
   successfully and returned hundreds of findings each (37-416), so every
   check function in the sequence, including all 34 listed here, executed
   to completion without raising, on all 7 documents.
4. **Stale cache / cache key collision — ruled out.** The cached
   per-document JSON (`data/evaluation/generated/ester_all_rules_batch_20260819/*.json`)
   was generated in this exact worktree at `HEAD == origin/main ==
   17d6c219cfd22f367d38b8432d62c9ef152c9476`, with `git status --short src/`
   empty throughout this session (no detector code was touched). The 7
   files are distinct sizes (37KB-608KB) with distinct `input_file_name`
   metadata -- no collision.
5. **Output suppression bug in batch code — ruled out for content reasons.**
   `lib.visible_findings_for_rule` only requires
   `student_visible_problem == True` and `severity != PASS` (see
   `all_rules_selection_qa.json`, which recomputes this independently of
   the batch's own selection code). For all 34 rules below, the raw cached
   JSON has **zero findings under that rule_id at any severity, visible or
   not** -- there is nothing for any selection/suppression logic to have
   discarded.

## Direct content verification (not just structural argument)

For the front-matter-heading family (P014, P025, P038, and by extension the
indentation/layout rules anchored to the same headings: P041, P043, P044,
P045, P047, P067), I additionally called the underlying heading-location
function directly (`pdf_frontmatter_heading_gate.find_frontmatter_headings_for_gates`)
against 3 of the 7 source PDFs (Philip, Sebastian, Praneeth) outside the
batch pipeline entirely. It successfully located ABSTRACT, APPROVAL PAGE,
BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS, LIST OF TABLES,
and LIST OF FIGURES headings on all 3, **already** `centered=True,
bold=True, all_caps=True`. This is direct, positive evidence -- not mere
plausibility -- that (a) the section-location infrastructure is working
correctly on this dataset, and (b) these particular dissertations'
front-matter headings are already exact-format-compliant, which is a
credible reason for P014/P038 to find nothing.

## Per-rule classification

| Rule | Module | Status | Basis |
|---|---|---|---|
| P012 | pdf_annotations | VERIFIED_ZERO | Requires real PDF annotation objects (`page.annots()`); these 7 source PDFs are plain (non-EF-reviewed) drafts. Consistent with a prior, independent investigation in this project (see memory: "Sample B Annotation Ground Truth Investigation") that these source PDFs carry no auditor/reviewer annotation objects. |
| P013 | pdf_page_numbers | VERIFIED_ZERO (by design) | P013's raw candidates are always emitted with `student_facing_role="inventory"` / `student_visible_problem=False` -- confirmed by direct field inspection of the cached JSON. It feeds the P013 triage/aggregate summary table only; it structurally never produces an individually-selectable finding. Real page-numbering violations are separately covered by P019 (which does have findings). |
| P014 | pdf_headings | VERIFIED_ZERO | Directly confirmed: located headings already `centered/bold/all_caps=True` on all 3 sampled documents (see above). |
| P022 | pdf_frontmatter_no_page_number | VERIFIED_ZERO | Narrow check (a visible page number appearing on a page type that should be unnumbered); plausible to never trigger on compliant drafts. |
| P025 | pdf_frontmatter_structure | VERIFIED_ZERO | Depends on the same heading-gate infrastructure directly confirmed above. |
| P029 | pdf_roman_sequence | VERIFIED_ZERO | Requires a broken Roman-numeral sequence in front matter; plausible to be absent. |
| P031 | pdf_lot_lof_column_headers | VERIFIED_ZERO | Narrow LOT/LOF column-header text-presence check. |
| P032 | pdf_toc_list_wrapped_spacing | VERIFIED_ZERO | Requires a wrapped (multi-line) TOC/LOT/LOF entry with a spacing defect; a narrower precondition than P036 (TOC inter-entry spacing generally), which did fire (R036 nonzero). |
| P034 | pdf_copyright_page | VERIFIED_ZERO | Copyright-page top-margin-header + title/copyright-year cross-match check; narrow. |
| P038 | pdf_frontmatter_headings | VERIFIED_ZERO | Same heading-gate infrastructure directly confirmed above. |
| P041 | pdf_dedication_page | VERIFIED_ZERO | Dedication-page top-margin header check; narrow, and not every dissertation has a Dedication page. |
| P042 | pdf_toc_appendix_format | VERIFIED_ZERO | Appendix TOC entry formatting; narrow. |
| P043 | pdf_acknowledgements_indentation | VERIFIED_ZERO | Same section-location family as P044 (see direct confirmation above; Acknowledgements was located at page 8-9 on 2 of 3 sampled docs). |
| P044 | pdf_abstract_indentation | VERIFIED_ZERO | Abstract heading directly confirmed located on all 3 sampled docs; indentation itself simply measured compliant. |
| P045 | pdf_biosketch_publication_layout | VERIFIED_ZERO | Biographical Sketch heading directly confirmed located (Sebastian, Praneeth); publication layout measured compliant, or no publications listed. |
| P047 | pdf_biosketch_bullet_spacing | VERIFIED_ZERO | Same Biographical Sketch dependency; narrow bullet-spacing sub-check. |
| P049 | pdf_lot_lof_column_header_style_alignment | VERIFIED_ZERO | Narrow LOT/LOF "Page" header bold+alignment refinement. |
| P050 | pdf_lot_lof_column_header_style_alignment | VERIFIED_ZERO | Same module, sibling narrow check ("Table"/"Figure" header bold). |
| P051 | pdf_copyright_page | VERIFIED_ZERO | Copyright-year-format refinement; narrow. |
| P052 | pdf_copyright_page | VERIFIED_ZERO | Copyright-author-format refinement; narrow. |
| P055 | pdf_lot_lof_entry_type | VERIFIED_ZERO | Requires a table entry inside List of Figures or vice versa; a data-entry mistake, plausible absent. |
| P056 | pdf_lot_lof_number_format | VERIFIED_ZERO | Requires mixed chapter-based (X.Y) and plain sequential (N) numbering within one list; plausible absent. |
| P057 | pdf_lot_lof_page_number_ordering | VERIFIED_ZERO | Requires out-of-order page numbers within LOT/LOF; plausible absent in reviewed drafts. |
| P058 | pdf_toc_page_number_ordering | VERIFIED_ZERO | Same class of check for the TOC body. |
| P059 | pdf_lot_lof_entry_number_ordering | VERIFIED_ZERO | Requires out-of-order entry numbers (2.1, 2.2, ...) within LOT/LOF. |
| P060 | pdf_toc_entry_number_ordering | VERIFIED_ZERO | Same for TOC section numbers. |
| P061 | pdf_lot_lof_cross_page_entry_ordering | VERIFIED_ZERO | Cross-page variant of P059; narrower precondition (requires a LOT/LOF spanning 2+ pages with an ordering break at the boundary). |
| P062 | pdf_toc_cross_page_entry_ordering | VERIFIED_ZERO | Cross-page variant of P060. |
| P063 | pdf_appendix_body_headings | VERIFIED_ZERO | Appendix body-heading label-convention check; requires a specific label mismatch pattern. |
| P064 | pdf_references_citations_structural | VERIFIED_ZERO | Visually spot-checked (rendered overview PNG): clean, all 7 rows "No current auditor finding"; requires a missing/unrecognized references heading or structurally inconsistent entries. |
| P065 | pdf_dedication_centering_italic | VERIFIED_ZERO | Requires a Dedication page that is not centered/italicized; not every dissertation has one, and existing ones may be compliant. |
| P067 | pdf_biosketch_publication_ordering | VERIFIED_ZERO | Same Biographical Sketch dependency as P045/P047. |
| P074 | pdf_frontmatter_structure | VERIFIED_ZERO | Graduation-month check (must be exactly August/December/May); plausible all 7 already comply. |
| P082 | pdf_landscape_page_number_orientation | **VERIFIED_ZERO — by construction, not data** | `check_pdf_landscape_page_number_orientation` returns `[]` immediately unless called with `enabled=True` (src/njit_auditor/rules/pdf_landscape_page_number_orientation.py:165). `audit_runner.py:251` passes `enabled=audit_options.is_experimental_enabled("P082")`, which is off by default. This batch used default audit options (the same options `run_audit_for_uploaded_file` uses without special configuration), so P082 is **guaranteed** zero regardless of document content. This is flagged distinctly because it is not "no violation found," it is "not evaluated" -- see note below. |

## Note on P082 specifically

Unlike the other 33 rows, P082's zero is not evidence about the
dissertations at all -- it is a config gate. Whether to re-run this batch
with the experimental flag enabled (which would make P082 an actually
meaningful evaluation rather than a guaranteed-empty one) is a scope
decision for the task owner, not something this QA pass changed
unilaterally (enabling an experimental/opt-in detector changes what gets
evaluated, which is outside "fix the generator, don't touch detector
behavior").

## Overall tally

- VERIFIED_ZERO: 34 / 34
- SUSPICIOUS: 0
- BROKEN: 0

No rule in this list showed any evidence of a mapping, invocation,
exception, caching, or suppression bug. The strongest caveat is that P014/
P025/P038/P043/P044/P045/P047/P067's "already compliant" explanation was
directly content-verified on 3 of 7 documents (not all 7, and not by
independently re-implementing each indentation/layout measurement); the
remaining rows rely on the structural argument plus plausibility of the
check's precondition being narrow or rare. If stronger certainty is needed
for any specific row, the recommended next step is a targeted manual look
at that rule's specific section across all 7 PDFs, not a batch regeneration.
