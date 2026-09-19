# Rule Architecture

This document explains the P-rule / Q-rule / issue-type / detector taxonomy, names the current
source of truth for each kind of rule metadata, and documents the duplication that exists across
the codebase as of this audit (2026-07-13) so future changes don't add more of it by accident.

## Vocabulary

| Term | Meaning |
|---|---|
| **Q-rule** | A rule from Esther's original formatting-review spreadsheets (`data/specs/ester_q_matrix.json`, `data/specs/ester_p_rule_feedback.json`). Not all Q-rules are automatable; many require human/manual review. |
| **P-rule** ("project-added rule") | This project's internal rule ID (`P001`-`P085` today). A P-rule may implement one Q-rule, several Q-rules (a "broad" rule), or no Q-rule at all (project-added, e.g. infrastructure rules). |
| **Public question / public rule card** | The student-facing rendering of a P-rule on `/rules` and per-finding pages. Not every P-rule is a standalone public card — see "Detector vs. reporting-only" below. |
| **Issue type** | A specific machine-readable string a detector emits (e.g. `possible_body_font_size_issue`). One P-rule can emit several issue types. |
| **Detector** | The `src/njit_auditor/rules/*.py` function that actually inspects the document and produces `AuditFinding` objects. |
| **Reporting-only rule** | A P-rule with no detector of its own — it post-processes another rule's findings into a triage rollup (e.g. P073 rolls up P019). Never a standalone student-visible finding. |
| **Experimental rule** | Disabled by default; opt-in via `--enable-experimental <ID>` or `AuditOptions.experimental_rules`. Currently only P082. |
| **Finding** | One `AuditFinding` produced by a detector for a specific location. |
| **Warning** | The severity label most findings carry (`Severity.WARNING`); this project does not currently emit hard failures for formatting checks. |
| **Remediation** | The suggested fix text attached to a finding (student-facing). |
| **Evaluation sample** | A PDF (private, e.g. `ester_sample_a`–`d`, or synthetic, e.g. `tests/fixtures/web_demo/*.pdf`) used to run the auditor against and check results — never a "test case" in the unit-test sense. |

## Detector vs. reporting-only vs. experimental vs. evaluation-only

- **Detector rules** (most of P011-P068, P074, P078, P084, P085, and opt-in P082): have a dedicated module under
  `src/njit_auditor/rules/`, are called directly from `audit_runner.py`, and can produce
  standalone `AuditFinding`s with their own issue types.
- **Reporting-only / infrastructure rules** (P069–P073, P076, P077, P079, P081): improve
  recall/precision of an existing detector or add a triage rollup to the JSON/Markdown report.
  They have **no standalone issue type** and must never appear as an independent student-facing
  finding — see the new consistency test added by this audit
  (`tests/test_rule_registry_consistency.py::test_reporting_only_rules_have_no_issue_types`).
- **Experimental rules** (P082 today): implemented but disabled by default. Public rule pages and
  the default web/CLI audit must not present these as active findings unless explicitly enabled.
- **Infrastructure/evaluation-task rules** (P080, P083): produce metadata reports or analysis
  artifacts, not runtime findings at all.

The web UI's `_classify_rule()` and `_technical_reason()` (`src/njit_auditor/web_app.py`) are the
current source of truth for this classification at render time, driven by the JSON catalog's
`rule_type` and `phase` fields (see below). **Update (2026-07-16 atomic-presentation audit):**
these two functions used to independently re-derive the same if/elif chain — real, live
duplication, not just a stylistic echo: it let `_classify_rule` compare a raw `phase` value while
`_technical_reason` compared a lowercased one, so a mixed-case catalog `phase` (e.g.
`"Evaluation_Task"`) could make them disagree. Both now delegate to one private helper,
`_rule_technical_classification()`, so disagreement is structurally impossible rather than merely
tested-for; see `tests/test_rule_classification_consistency.py` (includes a regression case proving
the old code really did disagree on mixed-case input).

## Where each piece of metadata actually lives

| Metadata | Canonical-ish source today | Notes |
|---|---|---|
| Internal rule ID, section, question, rule definition, severity, phase, checkability, priority | `data/processed/rules/project_added_rules.json`, loaded/validated by `src/njit_auditor/rule_loader.py` (`RuleDefinition`) | This is the closest thing to a canonical registry. See "Schema drift" below — the Pydantic model did not (until this audit) type several fields that are actually present in the JSON. |
| Public name / title / description | `title` / `description` fields in the same JSON | Falls back to `question`/`rule_definition` text elsewhere when not populated. |
| Detector vs. reporting-only vs. experimental vs. evaluation-task classification | `rule_type` field in the same JSON + `phase` field, rendered through `web_app.py` classification helpers | See duplication note above. |
| Esther Q-rule mapping | `source_q_rule_ids` field (present on 25/85 entries) **and** `docs/status/ester_q_p_rule_public_rule_mapping.md` **and** `src/njit_auditor/specs/q_rule_coverage.py` | Three places that should agree; `scripts/ester_rule_consistency_audit.py` is the only thing that cross-checks all three, and it requires local, untracked, generated Ester spreadsheet exports to run (not runnable in a fresh clone or CI today). |
| Emitted issue types | `issue_types` field in the JSON (present on 29/85 entries) **and** the literal `issue_type=` strings detectors actually emit in `src/njit_auditor/rules/*.py` **and** the keys of `_ISSUE_TYPE_LABELS` in `src/njit_auditor/issue_type_explanations.py` **and** the `(rule_id, issue_type)` keys of `_ISSUE_TEMPLATES` in `src/njit_auditor/polished_comments.py` | Four places. Only the detector source is ground truth; the other three are supposed to be supersets/mirrors of it and can silently drift (this is exactly the class of bug PR #505 fixed: P057/P059/P062/P065/P078 issue types had zero `_ISSUE_TEMPLATES` coverage and fell through to a fallback that leaked the raw `rule_id`). |
| Confidence policy | Computed inline, per detector, in each `src/njit_auditor/rules/*.py` module | Not centralized; no single "confidence policy" registry exists. Out of scope to centralize in this pass — would risk changing detector output, which the task that produced this document explicitly forbids. |
| Highlight capability | `src/njit_auditor/pdf_highlight.py` (`has_visible_highlight`, `is_drawable_bbox`) evaluated per-finding from stored geometry, not declared per-rule | A rule's highlight support is an emergent property of whether its findings happen to carry a valid bbox, not a static fact you can look up by rule ID. |
| Wording/remediation coverage | `src/njit_auditor/polished_comments.py` (`_ISSUE_TEMPLATES`, `_RULE_FALLBACKS`, `_REMEDIATION_OVERRIDES`, `_ISSUE_REMEDIATION_OVERRIDES`) | Four separate dicts with different keying (`rule_id` alone vs. `(rule_id, issue_type)` tuples); a rule can have partial coverage across some but not all of them. |

## Schema drift found and fixed in this audit

`data/processed/rules/project_added_rules.json` entries actually carry these fields beyond what
`RuleDefinition` (in `rule_loader.py`) validated before the July architecture audit:

`title`, `description`, `rule_type`, `issue_types`, `source_q_rule_ids`, `source_files`,
`scope_doc`, `triage_tier`, `affected_rules`, `source_q_rule_basis`

Because Pydantic v2 silently ignores unmodeled fields by default, `load_rule_file()` — the one
function meant to validate this catalog — was accepting the file while silently dropping 9 of its
fields for every rule that used them. Nothing caught this because
`load_rule_file()` is exercised only by `tests/test_rule_inventory.py` and `tests/test_basic.py`,
which check structural things (uniqueness, required fields) rather than round-tripping every field.

**Fix applied in this audit:** `RuleDefinition` now types all fields actually present in the
catalog (see `src/njit_auditor/rule_loader.py`), with `rule_type` constrained to the values
actually used in the JSON today. This changes no detector or report behavior — it only makes an
already-existing, already-tested loader actually validate the full schema instead of silently
truncating it. See `tests/test_rule_registry_consistency.py` for the new tests this enables.

## Full rule table

Moved here from `README.md` in this audit so the top-level README doesn't grow by one row every
time a rule is added.

### TeX source audit (P001–P010, plus Q004–Q006)

```bash
njit-audit tex path/to/main.tex
njit-audit tex path/to/main.tex --linters
```

Checks TeX source files without compiling — recursively loads `\input{}`/`\include{}` trees.

| Rule | Check |
|------|-------|
| P001 | Risky manual formatting commands |
| P002 | Duplicate `\label` identifiers |
| P003 | Whitespace in label names |
| P004 | Unresolved `\ref`/`\eqref` targets |
| P005 | Missing `\caption` in figure/table environments |
| P006 | Missing `\label` in figure/table environments |
| P007 | Caption terminal punctuation |
| P008 | Required document structure commands |
| P009 | chktex warnings (optional) |
| P010 | lacheck warnings (optional) |
| Q004 | Abstract forbidden words ("paper"/"article") |
| Q005 | Abstract first-person pronouns |
| Q006 | Graduation month validation (Aug/Dec/May) |

### PDF layout audit (P011-P068, P074, P078, P084, P085 standalone; P069-P073/P076/P077/P079/P081 infrastructure)

| Rule | Area | Check |
|------|------|-------|
| P011 | Margins | Text crossing 1.5"/1" margin boundaries; compression artifact guard reduces false positives on compressed PDFs |
| P012 | Annotations | Embedded PDF annotation objects |
| P013 | Page numbers | Page-number candidate detection (top/bottom zones) |
| P014 | Headings | Named front-matter heading style (bold/all-caps/centered/near-top) |
| P015 | Indentation | Paragraph indentation (first-para flush-left; subsequent indented) |
| P016 | Spacing | Spacing/blank-line gaps on front-matter pages |
| P017 | Captions | Caption/title punctuation and case signals |
| P018 | TOC/List | TOC/list entry alignment (leaders, page-number column, hierarchy) |
| P019 | Page numbers | Page-number sequence/style consistency |
| P020 | Capitalization | Title-case check for Level 2 headings and table titles |
| P021 | Abstract | Abstract word count (PhD ≤350, MS ≤150) |
| P022 | Page numbers | No visible page number on Abstract/Title/Approval/Copyright pages |
| P023 | Spacing | Body text double-spacing (line spacing ≥ 1.55× font size) |
| P024 | TOC/List | TOC/LoT/LoF entry capitalization and terminal punctuation |
| P025 | Front matter | Front-matter structure: abstract body, title-page elements, approval-page content |
| P026 | Font | Body text font compliance (Times New Roman 12pt or accepted equivalent) |
| P027 | Headings | Numbered heading level-specific style (L1 ALL CAPS, L2 Title Case, L3-5 Sentence case) |
| P028 | Page numbers | Front-matter Roman / body Arabic page-numbering regime |
| P029 | Page numbers | Front-matter lowercase Roman numeral ordering (sequence checks) |
| P030 | TOC/List | Multi-page TOC/LoT/LoF continued-heading checks on continuation pages |
| P031 | TOC/List | List of Tables/Figures column header labels (Table/Figure and Page) |
| P032 | TOC/List | Wrapped TOC/LoT/LoF entry internal spacing (continuation gap vs line height) |
| P033 | Front matter | Cross-page title consistency (Title Page, Abstract, Approval) |
| P034 | Front matter | Copyright Page top-margin header, year/author consistency with Title Page |
| P035 | Figures/Tables | Body-page figure/table centering and caption placement; text-layer bodies only (image-only floats skipped) |
| P036 | TOC/List | Inter-entry double spacing between distinct entries on TOC, LoT, and LoF pages; complements P032 |
| P037 | Page numbers | Section-anchored front-matter Roman numerals (BIOGRAPHICAL SKETCH=iv, DEDICATION=v optional, ACKNOWLEDGEMENTS=vi, TABLE OF CONTENTS=vii, LIST OF TABLES continues); silent if BIOGRAPHICAL SKETCH absent |
| P038 | Front matter | Required front-matter heading presence and known phrase-variant detection (covers DEDICATION, LIST OF TABLES, LIST OF FIGURES); complements P014/P025/P030/P031 |
| P039 | TOC/List | TOC level indentation hierarchy (L2 right of L1, L3 right of L2); TOC-only; covers Q056 |
| P040 | TOC/List | List of Figures entry terminal punctuation; LoF-only; covers Q075 |
| P041 | Front matter | Dedication page top-margin header check; covers Q032 |
| P042 | TOC/List | TOC appendix entry format (single vs. multiple appendix labeling); covers Q058/Q059 |
| P043 | Indentation | Acknowledgements page paragraph indentation (Q044/Q045); complement to P015 |
| P044 | Indentation | Abstract page paragraph indentation (Q002/Q003); complement to P015 |
| P045 | Indentation | Biographical Sketch publication layout: hanging indent (Q029), inter-entry spacing (Q028) |
| P046 | TOC/List | LoT/LoF entry-number left-column alignment (Q068/Q078) |
| P047 | Indentation | Biographical Sketch bullet/list section single-spacing (Q026) |
| P048 | TOC/List | LoT/LoF page-number right-column alignment (Q069/Q079) |
| P049 | TOC/List | LoT/LoF "Page" column header right-alignment and bold style (Q064/Q073) |
| P050 | TOC/List | LoT/LoF left-column header ("Table"/"Figure") bold style (Q063/Q072) |
| P051 | Copyright | Copyright page year-format advisory when no year token found (Q010); extends P034 |
| P052 | Copyright | Copyright page author-format advisory when no owner name extracted (Q011); extends P034/P051 |
| P053 | TOC/List | List of Tables entry must NOT end with terminal period (Q065); symmetric counterpart to P040 |
| P054 | TOC/List | TOC entry must NOT end with terminal period (Q049/Q050/Q051) |
| P055 | TOC/List | LoT/LoF cross-type entry check (LoT entry starting "Figure" or LoF entry starting "Table") |
| P056 | TOC/List | LoT/LoF mixed chapter-based vs. sequential entry-numbering format |
| P057 | TOC/List | LoT/LoF page-number non-decreasing ordering check |
| P058 | TOC/List | TOC page-number non-decreasing ordering check |
| P059 | TOC/List | LoT/LoF entry-number non-decreasing ordering check |
| P060 | TOC/List | TOC section-number non-decreasing ordering check |
| P061 | TOC/List | LoT/LoF cross-page entry-number ordering check |
| P062 | TOC/List | TOC cross-page section-number ordering check |
| P063 | Appendices | Body-page appendix heading label check (single vs. lettered multiple); companion to P042 |
| P064 | References | References/citations structural check (heading presence, hanging-indent consistency, entry spacing); does not enforce citation style |
| P065 | Front matter | Dedication page centering and italic style check |
| P066 | Front matter | Biographical Sketch degree-ordering (most-recent-first) check |
| P067 | Front matter | Biographical Sketch publication/presentation reverse-chronology check |
| P068 | Front matter | Approval Page committee/signature-block structural check |
| P074 | Front matter | Title Page graduation month validation (Aug/Dec/May) |
| P078 | Abstract | PDF Abstract forbidden-term (Q004) and first-person pronoun (Q005) check |
| P084 | Biographical Sketch | High-confidence birth-information pattern check for place/date of birth (Q023); Biographical Sketch page only |
| P085 | PDF body structure | First body chapter must begin with the required literal CHAPTER 1 heading |
| P082 | Page numbering | **Experimental, opt-in.** Landscape page-number orientation/position advisory; disabled by default |

**Infrastructure/reporting refinements (no standalone issue types):** P069 front-matter heading
gate recall; P070 TOC/LoT/LoF entry parser recall; P071 references-section localization recall
(P064 companion); P072 approval-page heading-gate recall; P073 P019 triage rollup; P080 DOCX
comment/tracked-change extraction; P076 P036
triage rollup; P077 P038 triage rollup; P079 P044 triage rollup; P081 P013/P026 calibration
refinement.

**Evaluation task (no runtime findings):** P083 EF-comment coverage taxonomy — see
`data/processed/ef_comment_coverage.json`.

All findings are heuristic warnings and require manual review.

## What was intentionally not done in this pass

Per the task that produced this document: no risky full rewrite, no detector/threshold/output
changes, no attempt to unify the four issue-type sources or the two `web_app.py` classification
functions into one code path. Those are real, valid follow-up work (tracked in
`docs/ROADMAP.md`), but each needs its own careful, behavior-preserving change with dedicated
before/after verification — bundling them into a "repo polish" pass would violate the "smallest
safe step" instruction this work was scoped under.

## Update: 2026-07-16 atomic-presentation audit

A follow-up pass closed two of the items listed above as still-open — both as small, independently
verified, behavior-preserving slices rather than the "risky full rewrite" this document originally
ruled out:

- **The two `web_app.py` classification functions are unified.** `_classify_rule()` and
  `_technical_reason()` now both delegate to one private helper, `_rule_technical_classification()`
  (see the updated "Detector vs. reporting-only..." section above). Proven equivalent, not just
  visually merged, via `tests/test_rule_classification_consistency.py`.
- **A real, previously-invisible wording bug (P014) was found and fixed**, and closed 24 more of
  the 140 active `(rule_id, issue_type)` pairs' documented wording debt (P057, P059, P061, P062,
  P065, P078, P034, plus removal of 3 confirmed-dead dict entries). See
  `docs/status/atomic_presentation_inventory_20260716.md` for the full before/after table and
  methodology. The 4-way issue-type-source duplication itself (catalog `issue_types` /
  `_ISSUE_TYPE_LABELS` / `_ISSUE_TEMPLATES` keys / detector source) is **not** unified — that
  remains real, valid follow-up work — but a new read-only static scanner,
  `src/njit_auditor/rule_source_scan.py`, now cross-checks the detector source against the catalog
  in `tests/test_rule_registry_consistency.py`'s wording-coverage ratchet, so a rule whose catalog
  entry is missing `issue_types` (P014's exact failure mode) can no longer silently evade that test.

**Same-day follow-up:** `rule_source_scan.py`'s scanner was substantially deepened (module-level
config-dict resolution through intermediate variables, same-module cross-function argument tracing,
finite-domain f-string templates) — mechanical discovery went from 56/72 raw/catalog-unioned pairs to
134 raw / 145 full-universe pairs, essentially matching the manually-audited universe. See
`docs/status/issue_type_universe_coverage_20260716.md` for the full root-cause analysis, alternatives
considered, and two pre-existing `suggested_fix` leaks (P014, P018) this broadened testing surfaced
but deliberately did not fix.
