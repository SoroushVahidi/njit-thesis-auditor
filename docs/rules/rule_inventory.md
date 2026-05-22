# NJIT Rule Inventory

This inventory maps Ester's front-matter matrix rules to implementation phases and required inputs.

- Total Ester rules: 79
- Total project-added rules: 8
- Phase 1 TeX-source implemented/partially implemented Ester rules: Q004, Q005, Q006

## Phase 1 coverage

- Q004 (`paper/article` forbidden terms in abstract): implemented in `njit_auditor.rules.latex_abstract`.
- Q005 (first-person pronouns in abstract): implemented in `njit_auditor.rules.latex_abstract`.
- Q006 (graduation month validity): partially implemented heuristically in `njit_auditor.rules.latex_metadata`.

## Why most rules are not in Phase 1

Many Ester rules depend on compiled-page geometry and visual placement:

- visible page numbers and suppression
- indentation and margin geometry
- heading centering/capitalization rendering
- spacing and visual sequence constraints

These cannot be validated reliably from TeX source alone because macro expansion, class/package side effects, and template rendering behavior determine final output.

## Rules requiring PDF/layout analysis

Rules such as Q001, Q002, Q003, Q008, Q009, Q012, Q013, Q014, Q021, Q022, Q031-Q036, and Q046-Q079 are classified as `pdf_layout` with `compiled_pdf` input requirements.

## Rules requiring manual/human metadata

Rules involving committee identity/order, external affiliation details, acknowledgements semantic checks, and exact template-specific wording are classified as `manual_review` or `mixed`, typically requiring:

- `human_metadata`
- `template_reference`
- optional source/PDF corroboration
