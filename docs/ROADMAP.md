# Roadmap

For what's true *right now* (SHA, test count, open PRs), see
[docs/status/CURRENT_STATUS.md](status/CURRENT_STATUS.md). This file is about direction, not
a snapshot — it should change rarely and shouldn't need dated entries.

## Completed capabilities

- **TeX source audit (P001–P010, Q004–Q006):** structure/label/reference/caption checks on
  uncompiled LaTeX source trees.
- **PDF layout audit (P011–P068, P074, P078):** heuristic, deterministic checks on compiled PDF
  geometry, fonts, spacing, headings, TOC/List of Tables/List of Figures structure, page
  numbering, front matter, and references — see
  [docs/RULE_ARCHITECTURE.md](RULE_ARCHITECTURE.md) for the full rule taxonomy.
- **Reporting-only infrastructure rules (P069–P073, P076, P077, P079, P081):** recall/precision
  refinements and triage rollups with no standalone student-visible issue type of their own.
- **Web UI:** FastAPI app for PDF-only upload/URL/sample audits, findings-by-topic and
  findings-in-page-order views, JSON/Markdown export, privacy-reduced web exports.
- **CLI:** `njit-audit tex`, `njit-audit pdf`, `njit-audit pdf-comments`, `njit-audit
  docx-comments`.
- **Evaluation pipeline:** private EF-reviewed dissertation samples (`ester_sample_a`–`d`),
  synthetic web-demo fixtures, and cross-referencing tooling against Esther's raw
  rule/audit-matrix spreadsheets (`scripts/ester_rule_consistency_audit.py`).

## Current Phase

Human-feedback calibration before deployment. R011, R015, and R017 are closed;
R019 evidence has been repaired and returned to Ester; deployment waits until
the feedback cycle stabilizes and CI is green.

## Near-term engineering work

1. Wait for Ester's R019 judgment on the repaired 23-page reviewer PDF.
2. R024 audit/fix/validate. Known feedback: Anthony proper nouns/taxa and
   Praneeth beta-casein/hyphen capitalization should not trigger the selected
   sentence-case findings.
3. R027 audit/fix/validate. Known feedback: a wrapped Level-4 heading period is
   on the continuation line.
4. R030 audit/fix/validate, plus a separate ownership audit for Ester's
   chapter-title-spacing question.
5. Prepare discussion evidence for R016/R018/R020/R023/R026/R028/R033, capture
   Ester's decisions as authoritative ground truth, then tune those rules one
   at a time.
6. Continue with R034+ as Ester reviews them.
7. Run a final global human-feedback regression audit.
8. Deploy only after the feedback cycle stabilizes and CI is green.

Repository-maintenance work remains separate from detector tuning:

- Clean local branch clutter conservatively. Do not delete remote branches
  without explicit authorization.
- Continue the canonical-rule-registry consolidation started in this audit
  (`docs/RULE_ARCHITECTURE.md`, Phase 4) by collapsing detector registration,
  public rule cards, Ester Q/P mappings, wording maps, and issue-type templates
  one safe slice at a time. Do not attempt this as a single rewrite.
- Make `scripts/ester_rule_consistency_audit.py` runnable in a fresh clone/CI
  by adding a redacted or synthetic stand-in for the local-only Ester workbook
  inputs, if Ester approves that data strategy.

## Policy-dependent work (needs Esther, not engineering judgment)

Do not implement any of these without an explicit answer from Esther — they are formatting-policy
calls, not bugs:

- R016: page-one/blank-space false positives; why only a subset of LaTeX
  documents are flagged.
- R018: current selected findings look false-positive; Ester pointed to actual
  TOC misalignments around 1.3.3 / 1.3.4 / 1.3.5.
- R020: sentence case/title case details, including conjunctions,
  prepositions, articles, and capitalization after punctuation.
- R023: figure-description single spacing, bullet-point single-spacing
  exceptions, and whether a bullet-spacing rule exists.
- R026: whether figure-source text may be 10 pt and single-spaced.
- R028: Philip false positive; Patrick may be meaningful but the underlying
  issue may be missing `CHAPTER 1`.
- R033: Praneeth title-consistency finding false positive; root cause still
  needs investigation.
- P011 margin coverage for non-text elements (images/drawings), currently
  text-layer only.
- Whether a new TOC-entry sentence-case rule is warranted.

## Longer-term / optional AI-VLM work

These are **not** committed work — they are directions that would require a real design doc,
a privacy/cost review (this project is local-first and free by design; anything that calls an
external model changes that promise), and explicit sign-off before any implementation starts:

- Image-only floats (figures/tables with no extractable text layer) are currently skipped by
  P035 and related rules — a vision-language model could evaluate centering/caption placement
  on rasterized pages where the text layer is absent or unreliable.
- Image-embedded Approval Pages (P068/P072's "structural fallback" path) currently rely on
  curated phrase/signature-indicator heuristics because OCR/VLM extraction isn't in the
  pipeline; a VLM pass could raise recall on these without changing the deterministic-first
  approach for text-layer PDFs.
- Fully scanned (non-native-text) dissertation PDFs are out of scope today; any OCR/VLM addition
  here would need its own privacy review before being wired into the free, local-first public
  web UI, since document content would then reach an external service.
