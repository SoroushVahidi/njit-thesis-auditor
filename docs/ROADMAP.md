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

## Near-term engineering work

- Land PR #505 and close the PRs it supersedes (#499, #500, #502, #504, #483) — see
  [CURRENT_STATUS.md](status/CURRENT_STATUS.md).
- Delete stale merged-PR remote branches (~24 as of this audit).
- Continue the canonical-rule-registry consolidation started in this audit
  (`docs/RULE_ARCHITECTURE.md`, Phase 4) — collapse the remaining duplication between detector
  registration, public rule cards, Esther Q/P mappings, wording maps, and issue-type templates
  one safe slice at a time. Do not attempt this as a single rewrite.
- Make `scripts/ester_rule_consistency_audit.py` runnable in a fresh clone/CI (currently requires
  untracked local `results/ester_feedback_raw/*.xlsx` input) — likely needs a redacted or
  synthetic stand-in for Esther's raw spreadsheets, decided with her input.
- Add `results/` (script scratch output) to `.gitignore` — see Phase 5 of the repository-polish
  audit.

## Policy-dependent work (needs Esther, not engineering judgment)

Do not implement any of these without an explicit answer from Esther — they are formatting-policy
calls, not bugs:

- Footer-zone P011 body-text margin policy (an 8-page cluster on Sample A).
- P011 margin coverage for non-text elements (images/drawings), currently text-layer only.
- 6 unreviewed Sample B medium-confidence P011 pages.
- Whether a new TOC-entry sentence-case rule is warranted.
- P084 (next rule ID) — intentionally not started; scope needs a source requirement from Esther's
  matrix before implementation begins.

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
