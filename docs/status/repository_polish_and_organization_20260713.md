# Repository Polish and Organization — 2026-07-13

## Summary

Baseline SHA: `dcadd61c7688a9e244d56d84cf39dca469f55006` (`origin/main`, PR #507).
Branch: `chore/repo-polish-and-organization-20260713`, in a fresh worktree at
`njit-thesis-auditor-clean-worktrees/repo-polish-and-organization-20260713` created from
`origin/main` (not the pre-existing, 139-commits-behind, dirty `main` worktree).

This was a documentation-organization, terminology-normalization, and small-safe-registry pass —
not a detector, threshold, or rule-ID change. One real bug was found and fixed (a raw internal
rule-ID leak into student-facing text), because Phase 6's own required test would otherwise have
had to assert broken behavior.

**The live server was never touched.** No request was made to port 8000, the deploy worktree
(`archives/njit-thesis-auditor-deploy`) was not modified, and `systemctl` was never invoked. The
only live-deployment evidence in this report was read via `git worktree list` / `git log` — a
read-only, local, non-network operation.

## Phase 1 — Initial findings (before any edit)

- **`docs/status/current_project_state_and_next_steps.md`** (121 KB) was the "Start here" doc but
  its newest snapshot was PR #407/#408 at SHA `70dcd95` — over 100 commits stale. It exemplifies
  exactly the "one enormous status file with years of appended history" anti-pattern the task
  warned about.
- **`docs/status/open_pr_triage.md`** and **`docs/status/live_deployment_checklist.md`** were
  similarly stale (dated 2026-07-06 and 2026-07-05 respectively, both superseded by 20+ merged
  PRs since).
- **`data/processed/evaluation_data_manifest.json`**, a machine-readable status snapshot several
  markdown docs were tested against for "alignment," was itself stale: `07db2fa` / 2512 pytest
  (PR #433 era), not `dcadd61` / current.
- **`README.md`** (429 lines, 47 KB) mixed genuinely useful reference content (install, usage,
  privacy, report schema) with a ~100-line per-rule table, a ~40-line "Current Live Status" table
  with a stale test count, and an ~80-line flat list of links to historical evaluation docs. It
  also called the project "the initial MVP" despite P001–P083 being implemented.
- **A prior session already attempted this exact cleanup once** (`docs/status/repo_polish_inventory.md`,
  2026-07-03) and documented the same staleness pattern in the same three files. It fixed nothing
  destructively (by design, per its own stated scope) and the docs drifted stale again within
  10 days — evidence that a short, narrowly-scoped canonical doc (this audit's
  `docs/status/CURRENT_STATUS.md`) is needed structurally, not just another one-time fix.
- **Open PRs:** #505 (open, `MERGEABLE`/`CLEAN`) adopts cherry-picks from #499/#500/#502/#504;
  its P026 hunk in `pdf_font_compliance.py` is now a **byte-identical no-op** against `main`
  because PR #506 (merged 2026-07-13, same day) independently fixed the same concatenated-heading
  false positive with an equivalent (more general) implementation. #483 is `CONFLICTING` and,
  per its own follow-up PR's description, superseded by already-merged #482. Full detail and
  recommended disposition: `docs/status/CURRENT_STATUS.md`.
- **30 remote branches**, only 6 of which correspond to the open PRs above; the other 24
  correspond to already-merged PRs GitHub did not auto-delete.
- **Local git worktree sprawl** (not a repository-tracked issue, but observed while working):
  90+ worktrees under `~/njit-thesis-auditor/{archives,worktrees,njit-thesis-auditor-clean-worktrees}`
  on this host, plus a long-lived, 139-commits-behind, dirty `main` working copy at
  `~/njit-thesis-auditor/main` with 28 uncommitted changes and untracked `results/`/
  `njit-thesis-auditor-clean-worktrees/` directories inside it. This is host/local-machine
  hygiene, not something a repository-level PR can fix — noted here so it isn't lost, not
  actioned.
- **`results/`** (script scratch-output directory, written by `scripts/ester_rule_consistency_audit.py`
  and similar tools) was **not gitignored**. It can contain analysis derived from private
  dissertation content. Fixed in Phase 5.
- **Naming:** "Ester" (not "Esther") appears 342 times across the tracked codebase, "Esther" zero
  times, and it is load-bearing as an identifier prefix (`ester_sample_a`, `ester_rule_consistency_audit.py`,
  `data/specs/ester_q_matrix.json`, etc. — see `docs/TERMINOLOGY.md`). Separately, `docs/sources/ester_materials.md`
  had the collaborator's surname wrong ("Farfan" instead of "Flaim") — confirmed against her own
  raw source materials, which spell it "Flaim" consistently — fixed in Phase 3.
- **Pre-existing privacy finding (not new, not introduced by this pass):** `data/raw/ester/`
  contains real, private dissertation drafts and reviewer annotations, tracked via Git LFS. The
  GitHub repository is currently **private**, which is the control keeping this compliant with
  the project's own `docs/status/evaluation_data_manifest.md` rule against making the repo public
  without a student-data handling review. Documented explicitly in `docs/EVALUATION_DATA.md` so
  it isn't lost; not acted on (rewriting LFS history was out of scope and would be destructive).

## Phase 2 — Documentation organization

Added, as the new canonical set:

| File | Purpose |
|---|---|
| `docs/status/CURRENT_STATUS.md` | Short, current-only status: SHA, tests, open PRs, live-deploy evidence, next actions. |
| `docs/ROADMAP.md` | Completed capabilities / near-term / policy-dependent / longer-term AI-VLM work. |
| `docs/RULE_ARCHITECTURE.md` | Full rule table (moved from README) + taxonomy + canonical-metadata-source table + documented duplication. |
| `docs/EVALUATION_DATA.md` | Evaluation sources, privacy rules, and a new finding-review labeling taxonomy (true/false positive/negative, too strict, wrong location/highlight/wording, duplicate, policy decision needed). |
| `docs/DEPLOYMENT.md` | Consolidated deploy procedure (systemd primary), clean-worktree requirement, smoke test, rollback. |
| `docs/TERMINOLOGY.md` | The Ester/Esther identifier-vs-name decision, explained. |

`README.md` was trimmed from 429 to ~150 lines: removed the "initial MVP" framing, the ~100-line
per-rule table (moved to `RULE_ARCHITECTURE.md`), the stale "Current Live Status" table, and the
~80-line historical-evaluation-doc link dump — replaced with a "Documentation map" pointing to the
files above. A **Limitations** section (requested by the task, previously absent) was added.

`docs/status/current_project_state_and_next_steps.md`, `open_pr_triage.md`, and
`live_deployment_checklist.md` each got a one-line banner at the top marking them historical and
pointing to their replacement — **no content below the banner was deleted or rewritten**, per the
"preserve forensic reports" instruction. `docs/status/README.md`'s index was updated to point to
the new canonical docs first.

`docs/planning/` (65 files) and `docs/evaluation/` (150 files) were **not** reorganized — auditing
and safely relinking that many dated reports is a separate, much larger effort than "smallest safe
step" allows; they already function as a de facto dated archive by directory convention. Deferred,
tracked in `docs/ROADMAP.md`.

## Phase 3 — Terminology

- `docs/TERMINOLOGY.md` documents the decision: use "Esther" in new prose; do **not** rename
  `ester_*` identifiers (data files, sample IDs, script/test/doc filenames) — that's a
  compatibility-breaking rename across dozens of files the task explicitly said not to do.
  Existing prose with "Ester" was **not** bulk-edited (real but low-value, tedious cleanup;
  tracked in `docs/ROADMAP.md`).
- Fixed the one factual name error found: `docs/sources/ester_materials.md` said "Ester Farfan";
  her own raw source files (`data/specs/ester_p_rule_feedback.json`, `ester_q_matrix.json`, and
  several files under `data/raw/ester/`) consistently spell it "Flaim" — corrected, with a note
  explaining the evidence.
- Removed "the initial MVP" framing from `README.md` (project is materially beyond that stage:
  P001–P083 implemented, deployed web UI).
- `docs/RULE_ARCHITECTURE.md`'s vocabulary table gives one standard definition each for finding,
  warning, issue type, public question/rule card, remediation, detector, reporting-only rule,
  experimental rule, evaluation sample — and explicitly states not every `P###` is a standalone
  student-visible rule (reporting-only/experimental/evaluation-task rules are called out).

## Phase 4 — Canonical rule registry: smallest safe step

**Duplication documented** (full detail in `docs/RULE_ARCHITECTURE.md`): internal rule metadata
is scattered across `data/processed/rules/project_added_rules.json` (the closest thing to
canonical), two independent classification functions in `web_app.py` (`_classify_rule` and
`_technical_reason`) that must always agree but aren't tested against each other, four separate
places that can each claim an issue type exists (catalog `issue_types` field, detector source,
`issue_type_explanations._ISSUE_TYPE_LABELS`, `polished_comments._ISSUE_TEMPLATES`), and four
separately-keyed wording dicts in `polished_comments.py`.

**Schema drift found and fixed:** `project_added_rules.json` entries carry 9 fields
(`title`, `description`, `rule_type`, `issue_types`, `source_q_rule_ids`, `source_q_rule_basis`,
`source_files`, `scope_doc`, `triage_tier`, `affected_rules`) that `rule_loader.RuleDefinition`
did not type — Pydantic v2 silently ignores unmodeled fields, so `load_rule_file()` (the one
function meant to validate this catalog, exercised by `tests/test_rule_inventory.py` and
`tests/test_basic.py`) was accepting the file while silently dropping these fields for every rule
that used them. **Fix:** widened `RuleDefinition` to type all of them, with `rule_type` validated
against a `Literal` of the 6 values actually used in the catalog today
(`src/njit_auditor/rule_loader.py`). Verified this changes no detector or report output — only
`load_rule_file()`'s own return value, used only by the two test files above and the new one.

**New tests added:** `tests/test_rule_registry_consistency.py` (14 test functions covering ~21
parametrized cases) — catalog round-trips the full schema; no duplicate public rule IDs; every
`rule_type` value is recognized; reporting-only rules never declare a standalone issue type;
every `implemented` rule has a real, importable `implementation_module` (or is an
evaluation-task rule); a ratchet test that fails if a *new* default-enabled issue type appears
with zero wording coverage (13 pre-existing gaps — P057/P059/P062/P065/P066/P067/P078/P082 — are
allowlisted by name with an explanation, not silently expanded); and a direct regression test
that the generic fallback comment never leaks a raw `P###`/`Q###` token.

**Bug found and fixed by writing that last test:** `polished_comments.py`'s generic fallback
(reached whenever a `(rule_id, issue_type)` pair has no specific template) interpolated the raw
`rule_id` directly into student-facing text — e.g. *"This check (P065) found a possible ...
issue"*. Live, default-enabled detectors **P057, P059, P062, P065, P066, P067, P078** had zero
template coverage and always hit this path (P082 too, but it's experimental/opt-in). Fixed with a
2-line wording change (`"This check (P065)"` → `"This automated check"`) — no detector, threshold,
confidence, or highlight-geometry change. One pre-existing test
(`tests/test_report_view.py::test_polished_comment_fallback_unknown_rule`) had encoded the leak
as expected behavior (`assert "P999" in comment`) and was corrected to assert the opposite.

**Note for reviewers:** open PR #505 (not merged by this audit — merging PRs was out of scope)
independently fixes this exact same bug, described in its own PR body as "a raw rule_id leak in
polished_comments.py's generic fallback." Whichever of the two PRs merges first will make the
other's hunk on this file a no-op, the same way #505/#506 already converged on the P026 fix — see
`docs/status/CURRENT_STATUS.md`.

**Deliberately not done:** unifying the four issue-type sources or the two `web_app.py`
classification functions into one code path, and writing the 13 missing wording templates. Each
needs its own careful, behavior-preserving change with dedicated verification — bundling them
here would violate "smallest safe step." Tracked in `docs/ROADMAP.md`.

## Phase 5 — Repository hygiene

- Added `/results/` to `.gitignore` (script scratch output; can contain analysis derived from
  private dissertation content; was previously untracked-but-unignored).
- Checked and found clean: no `.env`/secret/credential-looking files tracked, no `__pycache__`/
  `.egg-info`/build artifacts tracked, script executable-permission split (shell scripts `+x`,
  Python scripts run via `python scripts/...`) is a legitimate existing convention, not a bug.
- Ran an internal-markdown-link check across all 297 tracked `.md` files (new ones included):
  **0 broken relative links.**
- `pyproject.toml`, lint (`ruff`), and type-check (`mypy`) configuration were already reasonable;
  no changes made.
- Did **not** reorganize `docs/status/`'s flat 20-ish-row link table into the grouped sections a
  prior session (`repo_polish_inventory.md`) proposed but never applied — that's a same-file,
  every-line-touched edit; deferred to keep this PR's diff reviewable, tracked in `docs/ROADMAP.md`.
- Did **not** delete branches, worktrees, or close PRs — recommendations only, listed in
  `docs/status/CURRENT_STATUS.md` and below.

## Phase 6 — Tests and validation

All commands run directly in a fresh venv inside the clean worktree above (`python -m venv .venv
&& pip install -e ".[dev]"`), never in the pre-existing dirty `main` worktree.

| Check | Result |
|---|---|
| `ruff check .` | **All checks passed** |
| `mypy src` | **Success, 107 source files** |
| `python -m pytest -q tests` | **2755 passed, 2 skipped** (baseline was 2734 passed, 2 skipped on `origin/main` before this PR's changes; +21 new tests, 2 pre-existing tests corrected, net +21) |
| Internal markdown link check (297 files) | **0 broken links** |
| In-process PDF-link crawl (`TestClient`, no live server, no port 8000) | `ester_sample_a` 21/21, `ester_sample_b` 32/32, `ester_sample_d` 148/148 — **201/201 links returned 200 + `application/pdf` + a `%PDF` body** |
| Anti-overfitting grep (`src/` runtime conditionals vs. sample filenames/student/author names) | **Clean** — the only two hits were code *comments* citing a doc for context, not conditional logic; the sample-ID declarations in `web_samples.py` are the legitimate, expected sample catalog |
| Student-facing raw-ID-leak check | **Fixed and tested** (see Phase 4) |
| `scripts/ester_rule_consistency_audit.py` | **Not run** — requires untracked, local, generated `results/ester_feedback_raw/*.xlsx` input not present in a fresh clone; documented as a known limitation in `docs/status/CURRENT_STATUS.md` and `docs/ROADMAP.md`, not fixed in this pass |

I did not claim any result above without running it in this session.

## Files changed

**Added:** `docs/status/CURRENT_STATUS.md`, `docs/ROADMAP.md`, `docs/RULE_ARCHITECTURE.md`,
`docs/EVALUATION_DATA.md`, `docs/DEPLOYMENT.md`, `docs/TERMINOLOGY.md`,
`tests/test_rule_registry_consistency.py`, this report.

**Edited:** `README.md` (trimmed/reorganized), `docs/status/README.md` (index updated),
`docs/status/current_project_state_and_next_steps.md` / `open_pr_triage.md` /
`live_deployment_checklist.md` (banners added, content otherwise untouched),
`docs/sources/ester_materials.md` (name correction), `.gitignore` (`/results/` added),
`src/njit_auditor/rule_loader.py` (schema widened), `src/njit_auditor/polished_comments.py`
(2-line leak fix), `data/processed/evaluation_data_manifest.json` (snapshot fields refreshed),
`tests/test_evaluation_data_manifest.py` (alignment test rewritten for the new doc architecture),
`tests/test_report_view.py` (one test corrected to match the fixed behavior).

**Not touched:** any detector in `src/njit_auditor/rules/`, any threshold, any rule ID, any JSON
report schema, `docs/planning/`, `docs/evaluation/`, the live deployment, any branch, any PR.

## Intentionally deferred work

- Rebase/merge PR #505; close #499/#500/#502/#504/#483 as superseded.
- Delete ~24 stale merged-PR remote branches.
- Reorganize `docs/status/README.md`'s flat link table into grouped sections (proposal already
  exists in `docs/status/repo_polish_inventory.md`, never applied).
- Bulk "Ester" → "Esther" prose cleanup in existing files (`docs/TERMINOLOGY.md` explains why this
  is safe-but-tedious, not risky).
- Write the 13 allowlisted missing wording templates (`_KNOWN_WORDING_GAPS` in the new test file).
- Unify `web_app.py`'s two rule-classification functions; unify the four issue-type sources.
- Make `scripts/ester_rule_consistency_audit.py` runnable without local generated Ester-spreadsheet
  exports.
- The 4 unresolved Esther-policy questions and P084 (listed in `docs/status/CURRENT_STATUS.md`).

## Recommended cleanup after this PR is reviewed

- Merge PR #505 (or rebase if needed), then close #499, #500, #502, #504, #483.
- Delete these stale remote branches (already-merged, no open PR references them):
  `docs/confidence-calibration-audit`, `docs/post-470-status`, `fix/confidence-grouping-sorting`,
  `fix/ester-email-alignment-audit`, `fix/ester-rule-consistency-audit`,
  `fix/ester-sample-a-correctness-alignment`, `fix/ester-sample-a-correctness-pass1`,
  `fix/ester-sample-b-font-false-positive-highlight`, `fix/ester-sample-b-p011-margin-low-overflow`,
  `fix/ester-sample-b-p015-page23`, `fix/ester-sample-b-p019-page-numbering-highlights`,
  `fix/ester-sample-b-p020-specific-remediation`, `fix/ester-sample-b-p023-figure-description-spacing`,
  `fix/ester-sample-b-p038-front-matter-headings`, `fix/ester-sample-b-p051-copyright-category`,
  `fix/ester-sample-b-spacing-duplicate-section`, `fix/esther-live-spec-overnight-20260713`,
  `fix/issue-type-summary-table-visible-runtime`, `fix/overnight-esther-correctness-20260712`
  (only after #505 merges), `fix/p011-content-aware-remediation`,
  `fix/p011-margin-precision-false-negative-audit`, `fix/p015-equation-continuation-indent`,
  `fix/p019-location-evidence`, `fix/p033-location-wording-and-duplicate-analysis`,
  `fix/p035-table-centering-presentation`, `fix/page-numbering-false-positives`,
  `investigate/sample-b-annotation-ground-truth`.
- Separately, on the host that manages local dev worktrees: the long-lived dirty `main` working
  copy at `~/njit-thesis-auditor/main` (139 commits behind, 28 uncommitted changes) and the 90+
  local git worktrees are host-local housekeeping, not something this PR can or should touch —
  flagged for whoever owns that host.

## Confirmation

The live server was not restarted, no request was made to port 8000, and the deploy worktree
(`archives/njit-thesis-auditor-deploy`) was not modified — the only interaction with it in this
entire pass was a read-only `git worktree list` / `git log` to report its checked-out SHA in
`docs/status/CURRENT_STATUS.md`.

## Independent review follow-up (PR #508 finalize, same day)

Performed in a fresh review worktree from `origin/chore/repo-polish-and-organization-20260713`
after GitHub CI was already green, because automated Codex review had hit a usage limit.

### Findings and corrections applied on this branch

1. **Additional public-output ID leak:** `issue_type_title()` embedded raw `(P###)` into
   student-facing drilldown/category H1 titles (separate from the polished-comment fallback).
   Fixed to return human/Esther labels only; dedicated rule-reference links still show IDs.
   Strengthened `tests/test_rule_registry_consistency.py` to cover title/label/explanation/
   suggested-fix surfaces; updated the one web test that previously required `(P011)` in the
   title prose.
2. **P066/P067 wording-gap claim:** those rules have dedicated `build_polished_comment` handlers
   (they never hit the generic fallback). The allowlist comment now says so; leak coverage still
   includes them.
3. **Private data storage claim refined:** not all of `data/raw/ester/` is LFS *pointer* objects —
   several private binaries are ordinary Git blobs (multi‑MB) despite `.gitattributes`. Filenames
   often contain personal names. Repo is private (verified). Documented a later migration plan
   below; no history rewrite in this PR. Package builds remain source-only (`setuptools` finds
   packages under `src/` only) — private evaluation files are not packaged.
4. **`CURRENT_STATUS.md`:** removed the already-fixed "`results/` not gitignored" unresolved
   item; recommended merge sequence updated to Outcome A (#508 first, then reduced #505).

### Exact #505 overlap analysis (vs `origin/main` @ `dcadd61` and #508)

| #505 commit | Classification |
|---|---|
| `df71d7c` P015 continuation-indent + Sample B forensics | **Still unique and valuable** (detector + docs/tests) |
| `5ba3acc` Sample B P026 font false positive | **Already merged into main** via #506 — `pdf_font_compliance.py` diff vs main is **empty** (byte-identical no-op) |
| `822ad2e` P011 content-aware remediation | **Still unique and valuable** |
| `5eb0bfb` P011 precision audit + regression tests | **Still unique and valuable** |
| `a9efeff` P033 page-role wording + duplicate-candidate tooling | **Still unique and valuable** |
| `9f6d4f8` overnight status docs | **Documentation-only**; largely superseded once #508's canonical status exists — drop/rebase |
| `ab2c2c3` generic polished-comment rule_id leak fix | **Duplicated semantically (not byte-identical)** by #508 (`This formatting check` vs `This automated check`); drop after #508 merges |
| `e772f5f` P015 mixed-case continuation heuristic (pH/mRNA/eBay) | **Still unique and valuable** |

Overlapping files with #508 only: `polished_comments.py`, `tests/test_report_view.py`,
`docs/status/README.md`, `docs/status/current_project_state_and_next_steps.md`.

**Chosen sequence: Outcome A** (merge #508 first; rebase #505; strip duplicated/superseded hunks;
retain unique validated detector/remediation/tooling). Porting unique #505 detector work into
#508 would widen this polish PR's blast radius without benefit — Outcome B rejected.

Source PRs #499/#500/#502/#504 remain superseded by #505 once the reduced #505 merges; #483
remains close-without-merge.

### Private LFS / package risk assessment

- Repo visibility: **private** (GitHub).
- `.gitattributes` marks `*.pdf`/`*.docx`/`*.xlsx`/`*.zip` as LFS filters.
- Tree reality: mix of LFS pointers and full blobs under `data/raw/ester/` and guidelines;
  synthetic `tests/fixtures/web_demo/` binaries are also in the "should-be-pointer" set.
- `.gitignore` correctly ignores `data/evaluation/generated/`, `data/evaluation/private/`, and
  (as of this PR) `/results/`.
- `pyproject.toml` packages only `src/njit_auditor` — wheel/sdist should not ship private samples.
- **Later migration plan (do not execute here):** (1) move private evaluation corpora to
  access-controlled external storage (Drive or encrypted local volume) with an env-provided path
  manifest; (2) stop adding new private binaries to git; (3) exclude any remaining private paths
  from package/release tooling explicitly; (4) coordinated LFS/history purge only after backups
  and Esther/maintainer authorization; (5) rename path segments that encode personal names in any
  *new* storage layout (history rename is optional / separate).

### Live server

Untouched throughout this independent review — no port 8000 access, no deploy, no
`systemctl`/tmux restart.
